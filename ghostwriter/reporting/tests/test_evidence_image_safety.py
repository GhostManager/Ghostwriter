"""
Regression coverage for immutable image revisions and deferred evidence cleanup.
"""

# Standard Libraries
import io
import json
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

# Django Imports
from django.conf import settings
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import resolve, reverse

# 3rd Party Libraries
from PIL import Image

# Ghostwriter Libraries
from ghostwriter.factories import EvidenceFactory, UserFactory
from ghostwriter.reporting.models import Evidence
from ghostwriter.reporting.views import EvidenceImageReplace


def image_upload(color="white"):
    """
    Create a small, real PNG upload with the same basename for collision tests.
    """
    buffer = io.BytesIO()
    Image.new("RGB", (8, 8), color).save(buffer, "PNG")
    return SimpleUploadedFile("proof.png", buffer.getvalue(), content_type="image/png")


class EvidenceImageSafetyTests(TestCase):
    """
    Exercise save failures, stale revisions, and authenticated cleanup events.
    """

    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.user = UserFactory(role="manager")
        self.client.force_login(self.user)
        self.evidence = EvidenceFactory(document=image_upload())
        self.uri = reverse(
            "reporting:evidence_image_replace", kwargs={"pk": self.evidence.pk}
        )
        self.old_name = self.evidence.document.name
        self.old_path = Path(self.evidence.document.path)
        self.storage = Evidence._meta.get_field("document").storage

    def replace(self, expected=None):
        with self.captureOnCommitCallbacks(execute=True):
            return self.client.post(
                self.uri,
                {
                    "document": image_upload("black"),
                    "expected_document": self.old_name if expected is None else expected,
                },
            )

    def event(self, old_name, new_name):
        old = {
            "id": self.evidence.pk,
            "document": old_name,
            "friendly_name": self.evidence.friendly_name,
            "report_id": self.evidence.report_id,
        }
        return self.client.post(
            reverse("api:graphql_evidence_update_event"),
            json.dumps(
                {
                    "event": {
                        "op": "UPDATE",
                        "data": {"old": old, "new": {**old, "document": new_name}},
                    }
                }
            ),
            content_type="application/json",
            HTTP_HASURA_ACTION_SECRET=settings.HASURA_ACTION_SECRET,
        )

    def test_requires_revision_and_rejects_stale_editor(self):
        missing = self.client.post(self.uri, {"document": image_upload()})
        self.assertEqual(missing.status_code, 400)
        self.assertEqual(self.replace().status_code, 200)
        self.evidence.refresh_from_db()
        current = self.evidence.document.name
        current_bytes = Path(self.evidence.document.path).read_bytes()

        stale = self.replace()

        self.assertEqual(stale.status_code, 409)
        self.assertIn("document", stale.json())
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, current)
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), current_bytes)

    def test_csrf_protects_image_replacement(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.user)
        response = client.post(
            self.uri, {"document": image_upload(), "expected_document": self.old_name}
        )
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.old_path.exists())

    def test_get_does_not_modify_image(self):
        self.assertEqual(self.client.get(self.uri).status_code, 405)
        self.assertTrue(self.old_path.exists())

    @override_settings(GHOSTWRITER_MAX_FILE_SIZE=1)
    def test_upload_limit_preserves_current_file(self):
        self.assertEqual(self.replace().status_code, 413)
        self.assertTrue(self.old_path.exists())

    def test_database_failure_removes_new_blob_and_preserves_original(self):
        before = set(Path(self.media.name).rglob("*.png"))
        with patch.object(
            Evidence, "save", side_effect=DatabaseError("database unavailable")
        ):
            response = self.replace()
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(set(Path(self.media.name).rglob("*.png")), before)

    def test_storage_write_failure_preserves_original(self):
        with patch.object(
            self.storage, "save", side_effect=OSError("storage unavailable")
        ):
            response = self.replace()
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertTrue(self.old_path.exists())

    def test_retirement_waits_for_commit_and_does_not_run_on_rollback(self):
        # Django Imports
        from django.db import transaction

        with self.captureOnCommitCallbacks(execute=True) as callbacks:
            with transaction.atomic():
                response = self.client.post(
                    self.uri,
                    {"document": image_upload(), "expected_document": self.old_name},
                )
                self.assertEqual(response.status_code, 200)
                self.assertTrue(self.old_path.exists())
                transaction.set_rollback(True)
        self.assertEqual(callbacks, [])
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertTrue(self.old_path.exists())

    def test_storage_cleanup_failure_is_retryable_without_losing_committed_save(self):
        with patch.object(
            self.storage, "delete", side_effect=OSError("disk unavailable")
        ):
            response = self.replace()
        self.assertEqual(response.status_code, 200)
        self.evidence.refresh_from_db()
        current = self.evidence.document.name
        self.assertNotEqual(current, self.old_name)
        self.assertTrue(self.old_path.exists())

        with patch.object(
            self.storage, "delete", side_effect=OSError("disk unavailable")
        ):
            self.assertEqual(self.event(self.old_name, current).status_code, 503)
        self.assertEqual(self.event(self.old_name, current).status_code, 200)
        self.assertFalse(self.old_path.exists())
        self.assertTrue(Path(self.evidence.document.path).exists())
        self.assertEqual(self.event(self.old_name, current).status_code, 200)

    def test_same_basename_upload_survives_delayed_and_duplicate_events(self):
        self.assertEqual(self.replace().status_code, 200)
        self.evidence.refresh_from_db()
        new_evidence = EvidenceFactory(
            report=self.evidence.report, document=image_upload()
        )
        self.assertEqual(new_evidence.filename, "proof.png")
        self.assertNotEqual(new_evidence.document.name, self.old_name)
        self.assertNotEqual(new_evidence.document.name, self.evidence.document.name)
        for _ in range(2):
            self.assertEqual(
                self.event(self.old_name, self.evidence.document.name).status_code, 200
            )
            self.assertTrue(Path(new_evidence.document.path).exists())
            self.assertTrue(Path(self.evidence.document.path).exists())

    def test_delayed_legacy_event_does_not_delete_a_referenced_path(self):
        self.assertEqual(self.replace().status_code, 200)
        self.evidence.refresh_from_db()
        # A legacy caller or restored backup can still reference a previously used path.
        self.old_path.write_bytes(image_upload().read())
        restored = EvidenceFactory(report=self.evidence.report, document=self.old_name)
        self.assertEqual(restored.document.name, self.old_name)
        self.assertEqual(
            self.event(self.old_name, self.evidence.document.name).status_code, 200
        )
        self.assertTrue(self.old_path.exists())


@skipUnless(connection.vendor == "postgresql", "Row-lock concurrency requires PostgreSQL")
class EvidenceImageConcurrencyTests(TransactionTestCase):
    """
    Ensure only one editor can replace the same source revision.
    """

    def setUp(self):
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.user = UserFactory(role="manager")
        self.evidence = EvidenceFactory(document=image_upload())
        self.uri = reverse(
            "reporting:evidence_image_replace", kwargs={"pk": self.evidence.pk}
        )

    def test_route_owns_commit_outside_atomic_requests(self):
        self.assertTrue(connection.settings_dict["ATOMIC_REQUESTS"])
        self.assertIn("default", resolve(self.uri).func._non_atomic_requests)
        client = Client()
        client.force_login(self.user)
        cleanup_transaction_states = []
        cleanup = EvidenceImageReplace.cleanup_file

        def record_cleanup(name):
            cleanup_transaction_states.append(connection.in_atomic_block)
            cleanup(name)

        with patch.object(
            EvidenceImageReplace, "cleanup_file", side_effect=record_cleanup
        ):
            response = client.post(
                self.uri,
                {
                    "document": image_upload("black"),
                    "expected_document": self.evidence.document.name,
                },
            )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(cleanup_transaction_states, [False])

    def test_failed_commit_removes_new_blob_and_preserves_original(self):
        client = Client()
        client.force_login(self.user)
        expected = self.evidence.document.name
        before = set(Path(self.media.name).rglob("*.png"))
        with patch.object(
            connection, "commit", side_effect=DatabaseError("commit failed")
        ):
            response = client.post(
                self.uri,
                {"document": image_upload("black"), "expected_document": expected},
            )
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, expected)
        self.assertEqual(set(Path(self.media.name).rglob("*.png")), before)

    def test_concurrent_editors_do_not_overwrite_each_other(self):
        barrier = Barrier(2)
        expected = self.evidence.document.name

        def replace_image(color):
            close_old_connections()
            try:
                client = Client()
                client.force_login(self.user)
                barrier.wait(timeout=15)
                return client.post(
                    self.uri,
                    {"document": image_upload(color), "expected_document": expected},
                ).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = sorted(workers.map(replace_image, ["black", "red"]))
        self.assertEqual(statuses, [200, 409])
        self.evidence.refresh_from_db()
        self.assertNotEqual(self.evidence.document.name, expected)
        self.assertEqual(
            list(Path(self.media.name).rglob("*.png")),
            [Path(self.evidence.document.path)],
        )
