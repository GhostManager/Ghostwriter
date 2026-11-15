"""
Keep committed evidence available while Hasura retries obsolete-file cleanup.
"""

# Standard Libraries
import json
import logging
import tempfile
from pathlib import Path
from unittest.mock import patch

# Django Imports
from django.conf import settings
from django.db import DatabaseError, connection
from django.test import SimpleTestCase, TestCase, override_settings
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.api.tests.test_hasura_metadata import HASURA_TABLE_DIR, load_yaml
from ghostwriter.factories import EvidenceFactory, ReportFindingLinkFactory, UserFactory
from ghostwriter.modules.reportwriter import jinja_string_literal
from ghostwriter.reporting.models import Evidence, Report
from ghostwriter.reporting.tests.test_evidence_image_safety import image_upload


class EvidenceCleanupRetryTests(TestCase):
    """
    Retry storage outages without deleting current or restored evidence files.
    """

    def setUp(self):
        previous_disable_level = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        self.addCleanup(logging.disable, previous_disable_level)
        self.media = tempfile.TemporaryDirectory()
        self.addCleanup(self.media.cleanup)
        storage_settings = override_settings(MEDIA_ROOT=self.media.name)
        storage_settings.enable()
        self.addCleanup(storage_settings.disable)
        self.user = UserFactory(role="manager")
        self.client.force_login(self.user)
        self.evidence = EvidenceFactory(document=image_upload())
        self.old_name = self.evidence.document.name
        self.old_path = Path(self.evidence.document.path)
        self.storage = Evidence._meta.get_field("document").storage
        self.event_uri = reverse("api:graphql_evidence_update_event")

    def replace_with_failed_cleanup(self):
        """
        Commit a replacement while its immediate cleanup callback fails.
        """
        with patch.object(self.storage, "delete", side_effect=PermissionError("denied")):
            with self.captureOnCommitCallbacks(execute=True):
                response = self.client.post(
                    reverse(
                        "reporting:evidence_image_replace",
                        kwargs={"pk": self.evidence.pk},
                    ),
                    {
                        "expected_document": self.old_name,
                        "document": image_upload("black"),
                    },
                )
        self.assertEqual(response.status_code, 200)
        self.evidence.refresh_from_db()
        self.assertNotEqual(self.evidence.document.name, self.old_name)
        self.assertTrue(self.old_path.exists())
        return Path(self.evidence.document.path).read_bytes()

    def event_payload(self, current_retry=0, max_retries=60):
        """
        Build an authenticated delivery with Hasura's retry metadata.
        """
        old = {
            "id": self.evidence.pk,
            "document": self.old_name,
            "friendly_name": self.evidence.friendly_name,
            "report_id": self.evidence.report_id,
        }
        return {
            "id": "qa-obsolete-evidence-event",
            "delivery_info": {
                "current_retry": current_retry,
                "max_retries": max_retries,
            },
            "event": {
                "op": "UPDATE",
                "data": {
                    "old": old,
                    "new": {**old, "document": self.evidence.document.name},
                },
            },
        }

    def deliver(self, payload):
        """
        Deliver the event with the shared secret required by its webhook.
        """
        return self.client.post(
            self.event_uri,
            json.dumps(payload),
            content_type="application/json",
            HTTP_HASURA_ACTION_SECRET=settings.HASURA_ACTION_SECRET,
        )

    def assert_current_image(self, expected_bytes):
        """
        Verify cleanup has not changed the committed revision or its bytes.
        """
        name = self.evidence.document.name
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, name)
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), expected_bytes)

    def test_persistent_failure_then_recovery_keeps_committed_image(self):
        expected_bytes = self.replace_with_failed_cleanup()
        for retry in (0, 1, 2, 59):
            with self.subTest(retry=retry):
                with patch.object(
                    self.storage, "delete", side_effect=PermissionError("denied")
                ):
                    with self.assertLogs("ghostwriter.api.views", level="ERROR") as logs:
                        response = self.deliver(self.event_payload(retry))
                self.assertEqual(response.status_code, 503)
                self.assertTrue(self.old_path.exists())
                self.assert_current_image(expected_bytes)
                self.assertIn("qa-obsolete-evidence-event", logs.output[0])
                self.assertIn(f"retry {retry}/60", logs.output[0])
                self.assertIn("Hasura can retry", logs.output[0])
                self.assertEqual(logs.records[0].levelno, logging.ERROR)

        self.assertEqual(self.deliver(self.event_payload(60)).status_code, 200)
        self.assertFalse(self.old_path.exists())
        self.assert_current_image(expected_bytes)
        self.assertEqual(self.deliver(self.event_payload(60)).status_code, 200)
        self.assert_current_image(expected_bytes)

    def test_exhausted_retries_log_actionable_recovery_and_allow_redelivery(self):
        expected_bytes = self.replace_with_failed_cleanup()
        with patch.object(self.storage, "delete", side_effect=PermissionError("denied")):
            with self.assertLogs("ghostwriter.api.views", level="CRITICAL") as logs:
                response = self.deliver(self.event_payload(60))
        self.assertEqual(response.status_code, 503)
        self.assertIn("Automatic retries exhausted", logs.output[0])
        self.assertIn("redeliver this EvidenceUpdate event in Hasura", logs.output[0])
        self.assertIn("qa-obsolete-evidence-event", logs.output[0])
        self.assertIn(self.old_name, logs.output[0])
        self.assertTrue(self.old_path.exists())
        self.assert_current_image(expected_bytes)

        # An administrator can redeliver the failed event after restoring storage.
        self.assertEqual(self.deliver(self.event_payload(60)).status_code, 200)
        self.assertFalse(self.old_path.exists())
        self.assert_current_image(expected_bytes)

    def test_no_configured_retries_logs_exhaustion_on_first_delivery(self):
        self.replace_with_failed_cleanup()
        with patch.object(self.storage, "delete", side_effect=OSError("unavailable")):
            with self.assertLogs("ghostwriter.api.views", level="CRITICAL") as logs:
                response = self.deliver(self.event_payload(0, 0))
        self.assertEqual(response.status_code, 503)
        self.assertIn("Automatic retries exhausted", logs.output[0])

    def test_database_failure_is_also_retryable(self):
        expected_bytes = self.replace_with_failed_cleanup()
        with patch(
            "ghostwriter.api.views.delete_unreferenced_evidence_file",
            side_effect=DatabaseError("unavailable"),
        ):
            with self.assertLogs("ghostwriter.api.views", level="ERROR"):
                response = self.deliver(self.event_payload())
        self.assertEqual(response.status_code, 503)
        self.assertTrue(self.old_path.exists())
        self.assert_current_image(expected_bytes)

    def test_retry_does_not_delete_a_path_that_was_restored_as_active_evidence(self):
        expected_bytes = self.replace_with_failed_cleanup()
        restored = EvidenceFactory(report=self.evidence.report, document=self.old_name)
        with patch.object(self.storage, "delete") as delete:
            response = self.deliver(self.event_payload(60))
        self.assertEqual(response.status_code, 200)
        delete.assert_not_called()
        self.assertTrue(Path(restored.document.path).exists())
        self.assert_current_image(expected_bytes)

    def test_malformed_or_missing_retry_metadata_does_not_hide_cleanup_failure(self):
        expected_bytes = self.replace_with_failed_cleanup()
        for delivery in (
            None,
            [],
            "bad",
            {},
            {"current_retry": "60", "max_retries": 60},
            {"current_retry": "bad\nforged-log", "max_retries": "bad"},
            {"current_retry": True, "max_retries": 0},
            {"current_retry": 0, "max_retries": -1},
            {"current_retry": -1, "max_retries": 0},
        ):
            with self.subTest(delivery=delivery):
                payload = self.event_payload()
                payload["delivery_info"] = delivery
                with patch.object(
                    self.storage, "delete", side_effect=OSError("unavailable")
                ):
                    with self.assertLogs("ghostwriter.api.views", level="ERROR") as logs:
                        response = self.deliver(payload)
                self.assertEqual(response.status_code, 503)
                self.assertEqual(logs.records[0].levelno, logging.ERROR)
                self.assertNotIn("exhausted", logs.output[0])
                self.assertNotIn("forged-log", logs.output[0])
                self.assert_current_image(expected_bytes)

    def test_unauthenticated_event_cannot_trigger_cleanup(self):
        self.replace_with_failed_cleanup()
        with patch.object(self.storage, "delete") as delete:
            response = self.client.post(
                self.event_uri, self.event_payload(), content_type="application/json"
            )
        self.assertEqual(response.status_code, 403)
        delete.assert_not_called()
        self.assertTrue(self.old_path.exists())

    def test_failed_cleanup_does_not_delay_rename_or_repeat_reference_changes(self):
        expected_bytes = self.replace_with_failed_cleanup()
        old_friendly_name = self.evidence.friendly_name
        finding = ReportFindingLinkFactory(
            report=self.evidence.report,
            description=(
                f"<p>{{{{.{old_friendly_name}}}}}</p>"
                f"<p>{{{{.ref {old_friendly_name}}}}}</p>"
            ),
        )
        self.evidence.friendly_name = f"Renamed {{{{.{old_friendly_name}}}}}"
        self.evidence.save(update_fields=["friendly_name"])
        payload = self.event_payload()
        payload["event"]["data"]["old"]["friendly_name"] = old_friendly_name
        encoded_name = jinja_string_literal(self.evidence.friendly_name)
        expected_description = (
            "<p>{{ mk_evidence(" + encoded_name + ") }}</p>"
            "<p>{{ mk_ref(" + encoded_name + ") }}</p>"
        )

        for retry in (0, 59, 60):
            with self.subTest(retry=retry):
                payload["delivery_info"]["current_retry"] = retry
                with patch.object(
                    self.storage, "delete", side_effect=PermissionError("denied")
                ):
                    with self.assertLogs("ghostwriter.api.views", level="ERROR"):
                        response = self.deliver(payload)
                self.assertEqual(response.status_code, 503)
                finding.refresh_from_db()
                self.assertEqual(finding.description, expected_description)
                self.assertTrue(self.old_path.exists())
                self.assert_current_image(expected_bytes)

        response = self.deliver(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        self.assertFalse(self.old_path.exists())
        finding.refresh_from_db()
        self.assertEqual(finding.description, expected_description)
        self.assert_current_image(expected_bytes)

    def test_cleanup_database_error_does_not_abort_reference_updates(self):
        self.replace_with_failed_cleanup()
        old_name = self.evidence.friendly_name
        finding = ReportFindingLinkFactory(
            report=self.evidence.report, description=f"<p>{{{{.{old_name}}}}}</p>"
        )
        self.evidence.friendly_name = "Renamed during database error"
        self.evidence.save(update_fields=["friendly_name"])
        payload = self.event_payload()
        payload["event"]["data"]["old"]["friendly_name"] = old_name

        def fail_database_query(name):
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1 FROM evidence_cleanup_nonexistent_table")

        with patch(
            "ghostwriter.api.views.delete_unreferenced_evidence_file",
            side_effect=fail_database_query,
        ):
            with self.assertLogs("ghostwriter.api.views", level="ERROR"):
                response = self.deliver(payload)
        self.assertEqual(response.status_code, 503)
        finding.refresh_from_db()
        self.assertEqual(
            finding.description,
            "<p>{{ mk_evidence("
            + jinja_string_literal(self.evidence.friendly_name)
            + ") }}</p>",
        )
        self.assertTrue(self.old_path.exists())

    def test_report_cascade_delete_remains_retryable_after_report_is_gone(self):
        payload = self.event_payload()
        payload["event"]["op"] = "DELETE"
        payload["event"]["data"]["new"] = None
        report_id = self.evidence.report_id
        self.evidence.report.delete()
        self.assertFalse(Report.objects.filter(pk=report_id).exists())
        self.assertFalse(Evidence.objects.filter(pk=self.evidence.pk).exists())
        self.assertTrue(self.old_path.exists())

        with patch.object(self.storage, "delete", side_effect=PermissionError("denied")):
            with self.assertLogs("ghostwriter.api.views", level="ERROR"):
                response = self.deliver(payload)
        self.assertEqual(response.status_code, 503)
        self.assertTrue(self.old_path.exists())

        response = self.deliver(payload)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), payload)
        self.assertFalse(self.old_path.exists())
        self.assertEqual(self.deliver(payload).status_code, 200)


class EvidenceCleanupMetadataTests(SimpleTestCase):
    """
    Keep the retry window long enough for a temporary storage outage.
    """

    def test_evidence_cleanup_has_at_least_one_hour_of_bounded_retries(self):
        table = load_yaml(HASURA_TABLE_DIR / "public_reporting_evidence.yaml")
        trigger = next(
            t for t in table["event_triggers"] if t["name"] == "EvidenceUpdate"
        )
        config = trigger["retry_conf"]
        self.assertGreaterEqual(config["interval_sec"], 10)
        self.assertGreaterEqual(config["num_retries"] * config["interval_sec"], 3600)
        self.assertLessEqual(config["num_retries"], 60)
        self.assertEqual(trigger["webhook"], "{{ACTIONS_URL_BASE}}/event/evidence/update")
