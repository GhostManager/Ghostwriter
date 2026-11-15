"""
Cross-entry-point revision and file-lifecycle coverage for evidence page edits.
"""

# Standard Libraries
import tempfile
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from threading import Barrier
from unittest import skipUnless
from unittest.mock import patch

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import DatabaseError, close_old_connections, connection
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import resolve, reverse

# Ghostwriter Libraries
from ghostwriter.factories import EvidenceFactory, UserFactory
from ghostwriter.reporting.models import Evidence
from ghostwriter.reporting.tests.test_evidence_image_safety import image_upload
from ghostwriter.reporting.views import EvidenceImageReplace, EvidenceUpdate


class EvidenceUpdateSetup:
    """
    Create isolated evidence storage and a manager for each save-path scenario.
    """

    def setUp(self):
        super().setUp()
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        self.media_override = override_settings(MEDIA_ROOT=self.media.name)
        self.media_override.enable()
        self.addCleanup(self.media_override.disable)
        self.user = UserFactory(role="manager")
        self.client.force_login(self.user)
        self.evidence = EvidenceFactory(document=image_upload())
        self.old_name = self.evidence.document.name
        self.old_path = Path(self.evidence.document.path)
        self.page_uri = reverse(
            "reporting:evidence_update", kwargs={"pk": self.evidence.pk}
        )
        self.image_uri = reverse(
            "reporting:evidence_image_replace", kwargs={"pk": self.evidence.pk}
        )

    def page_payload(self, document=None, expected=True, edited=False):
        """
        Build the same fields submitted by the ordinary evidence form.
        """
        data = {
            "friendly_name": self.evidence.friendly_name,
            "caption": "Evidence caption",
            "description": "",
            "tags": "",
            "report_width_unit": "",
            "report_width_value": "",
            "document_was_edited": str(edited),
        }
        if document is not None:
            data["document"] = document
        if expected:
            data["expected_document"] = self.old_name
        return data


class EvidenceUpdateSafetyTests(EvidenceUpdateSetup, TestCase):
    """
    Protect page edits without changing text uploads or metadata-only updates.
    """

    def test_get_renders_both_hidden_safety_fields(self):
        response = self.client.get(self.page_uri)
        self.assertContains(response, 'name="expected_document"')
        self.assertContains(response, 'name="document_was_edited"')
        self.assertEqual(
            response.context["form"]["expected_document"].value(), self.old_name
        )
        self.assertFalse(response.context["form"]["document_was_edited"].value())

    def test_page_rejects_upload_without_source_revision(self):
        response = self.client.post(
            self.page_uri, self.page_payload(image_upload(), expected=False)
        )
        self.assertEqual(response.status_code, 400)
        self.assertIn("document", response.context["form"].errors)
        self.assertTrue(self.old_path.exists())

    def test_image_endpoint_rejects_missing_upload(self):
        response = self.client.post(self.image_uri, {"expected_document": self.old_name})
        self.assertEqual(response.status_code, 400)
        self.assertIn("document", response.json())
        self.assertTrue(self.old_path.exists())

    def test_page_cannot_overwrite_newer_editor_redaction(self):
        with self.captureOnCommitCallbacks(execute=True):
            first = self.client.post(
                self.image_uri,
                {"expected_document": self.old_name, "document": image_upload("black")},
            )
        self.assertEqual(first.status_code, 200)
        self.evidence.refresh_from_db()
        current = self.evidence.document.name
        current_bytes = Path(self.evidence.document.path).read_bytes()
        response = self.client.post(
            self.page_uri, self.page_payload(image_upload("white"), edited=True)
        )
        self.assertEqual(response.status_code, 409)
        self.assertEqual(
            response.context["form"]["expected_document"].value(), self.old_name
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, current)
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), current_bytes)

    def test_editor_cannot_overwrite_newer_page_redaction(self):
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                self.page_uri, self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 302)
        self.evidence.refresh_from_db()
        current = self.evidence.document.name
        stale = self.client.post(
            self.image_uri,
            {"expected_document": self.old_name, "document": image_upload("white")},
        )
        self.assertEqual(stale.status_code, 409)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, current)
        self.assertFalse(self.old_path.exists())

    def test_metadata_only_update_does_not_require_a_file_revision(self):
        data = self.page_payload(expected=False)
        data.update(
            caption="Changed caption",
            report_width_unit="percent",
            report_width_value="50",
        )
        response = self.client.post(self.page_uri, data)
        self.assertEqual(response.status_code, 302)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(self.evidence.caption, "Changed caption")
        self.assertEqual(self.evidence.report_width_value, 50)

    def test_text_replacement_preserves_the_regular_upload_workflow(self):
        document = SimpleUploadedFile("notes.txt", b"Text evidence")
        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(self.page_uri, self.page_payload(document))
        self.assertEqual(response.status_code, 302)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.filename, "notes.txt")
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), b"Text evidence")
        self.assertFalse(self.old_path.exists())

    def test_validation_retry_cannot_silently_discard_staged_edits(self):
        data = self.page_payload(image_upload("black"), edited=True)
        data["caption"] = ""
        response = self.client.post(self.page_uri, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("caption", response.context["form"].errors)
        self.assertTrue(response.context["form"]["document_was_edited"].value())
        self.assertEqual(
            response.context["form"]["expected_document"].value(), self.old_name
        )
        retry = self.client.post(self.page_uri, self.page_payload(edited=True))
        self.assertEqual(retry.status_code, 200)
        self.assertIn("document", retry.context["form"].errors)
        self.assertIn(
            "Re-edit the image or select the edited file again",
            str(retry.context["form"].errors["document"]),
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])

    def test_locked_permission_recheck_blocks_both_save_paths(self):
        for uri in (self.page_uri, self.image_uri):
            with self.subTest(uri=uri):
                data = (
                    self.page_payload(image_upload("black"))
                    if uri == self.page_uri
                    else {
                        "expected_document": self.old_name,
                        "document": image_upload("black"),
                    }
                )
                with patch(
                    "ghostwriter.reporting.models.Report.user_can_edit",
                    side_effect=[True, False],
                ) as permission:
                    response = self.client.post(uri, data)
                self.assertEqual(
                    response.status_code, 302 if uri == self.page_uri else 403
                )
                self.assertEqual(permission.call_count, 2)
                self.evidence.refresh_from_db()
                self.assertEqual(self.evidence.document.name, self.old_name)
                self.assertEqual(
                    list(Path(self.media.name).rglob("*.png")), [self.old_path]
                )

    def test_failed_page_save_compensates_storage(self):
        with patch.object(Evidence, "save", side_effect=DatabaseError("save failed")):
            response = self.client.post(
                self.page_uri, self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])

    def test_locked_load_failure_returns_unavailable_without_changing_image(self):
        original_bytes = self.old_path.read_bytes()
        with patch.object(
            EvidenceUpdate,
            "get_object",
            side_effect=[self.evidence, DatabaseError("locked load unavailable")],
        ) as load:
            response = self.client.post(
                self.page_uri,
                self.page_payload(image_upload("black"), edited=True),
            )
        self.assertEqual(response.status_code, 503)
        self.assertEqual(load.call_count, 2)
        self.assertTrue(load.call_args_list[1].kwargs["queryset"].query.select_for_update)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(self.old_path.read_bytes(), original_bytes)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])

    def test_failed_storage_write_preserves_current_file(self):
        storage = Evidence._meta.get_field("document").storage
        with patch.object(storage, "save", side_effect=OSError("storage unavailable")):
            response = self.client.post(
                self.page_uri, self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertTrue(self.old_path.exists())

    def test_staged_image_requires_real_image_content(self):
        document = SimpleUploadedFile(
            "edited.png", b"not an image", content_type="image/png"
        )
        response = self.client.post(
            self.page_uri, self.page_payload(document, edited=True)
        )
        self.assertEqual(response.status_code, 200)
        self.assertIn(
            "not a valid image", str(response.context["form"].errors["document"])
        )
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])


@skipUnless(connection.vendor == "postgresql", "Row locking requires PostgreSQL")
class EvidenceUpdateTransactionTests(EvidenceUpdateSetup, TransactionTestCase):
    """
    Exercise real request commits and simultaneous page/editor saves.
    """

    def test_page_owns_its_commit_and_compensates_commit_failure(self):
        self.assertTrue(connection.settings_dict["ATOMIC_REQUESTS"])
        self.assertIn("default", resolve(self.page_uri).func._non_atomic_requests)
        commit = connection.commit
        attempts = 0

        def fail_evidence_commit_once():
            nonlocal attempts
            attempts += 1
            if attempts == 1:
                raise DatabaseError("commit failed")
            commit()

        with patch.object(connection, "commit", side_effect=fail_evidence_commit_once):
            response = self.client.post(
                self.page_uri, self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 503)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])

    def test_page_retires_original_only_after_its_commit(self):
        states = []
        cleanup = EvidenceImageReplace.cleanup_file

        def record_cleanup(name):
            states.append(connection.in_atomic_block)
            cleanup(name)

        with patch.object(
            EvidenceImageReplace, "cleanup_file", side_effect=record_cleanup
        ):
            response = self.client.post(
                self.page_uri, self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 302)
        self.assertEqual(states, [False])
        self.assertFalse(self.old_path.exists())

    def test_simultaneous_page_and_editor_have_one_winner(self):
        barrier = Barrier(2)

        def submit(page):
            close_old_connections()
            try:
                client = Client()
                client.force_login(self.user)
                data = (
                    self.page_payload(image_upload("black"), edited=True)
                    if page
                    else {
                        "expected_document": self.old_name,
                        "document": image_upload("red"),
                    }
                )
                barrier.wait(timeout=15)
                return client.post(
                    self.page_uri if page else self.image_uri, data
                ).status_code
            finally:
                close_old_connections()

        with ThreadPoolExecutor(max_workers=2) as workers:
            statuses = list(workers.map(submit, [True, False]))
        self.assertIn(statuses, ([302, 409], [409, 200]))
        self.evidence.refresh_from_db()
        self.assertEqual(
            list(Path(self.media.name).rglob("*.png")),
            [Path(self.evidence.document.path)],
        )
