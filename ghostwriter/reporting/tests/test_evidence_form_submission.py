"""
JSON form submissions retain browser files without weakening revision checks.
"""

# Standard Libraries
from pathlib import Path
from unittest.mock import patch

# Django Imports
from django.db import DatabaseError
from django.test import TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import EvidenceFactory
from ghostwriter.reporting.models import Evidence
from ghostwriter.reporting.tests.test_evidence_image_safety import image_upload
from ghostwriter.reporting.tests.test_evidence_update_safety import EvidenceUpdateSetup
from ghostwriter.reporting.views import EvidenceUpdate


class EvidenceFormSubmissionTests(EvidenceUpdateSetup, TestCase):
    """
    Exercise enhanced form responses and revision-checked image downloads.
    """

    def post_json(self, data):
        return self.client.post(self.page_uri, data, HTTP_ACCEPT="application/json")

    def test_current_revision_metadata_is_private_and_not_cached(self):
        response = self.client.get(self.page_uri, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "document": self.old_name,
                "download_url": reverse(
                    "reporting:evidence_download", args=[self.evidence.pk]
                ),
            },
        )
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertTrue(self.old_path.exists())

    def test_duplicate_name_returns_field_errors_then_corrected_file_saves(self):
        EvidenceFactory(report=self.evidence.report, friendly_name="Already used")
        payload = self.page_payload(image_upload("black"), edited=True)
        payload["friendly_name"] = "Already used"
        response = self.post_json(payload)
        self.assertEqual(response.status_code, 400)
        self.assertIn("friendly_name", response.json()["errors"])
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)
        upload = image_upload("black")
        expected_bytes = upload.read()
        upload.seek(0)
        with self.captureOnCommitCallbacks(execute=True):
            retry = self.post_json(self.page_payload(upload, edited=True))
        self.assertEqual(retry.status_code, 200)
        self.assertEqual(retry.json(), {"redirect_url": self.evidence.get_absolute_url()})
        self.evidence.refresh_from_db()
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), expected_bytes)
        self.assertFalse(self.old_path.exists())

    def test_missing_file_reminder_still_blocks_json_submission(self):
        response = self.post_json(self.page_payload(edited=True))
        self.assertEqual(response.status_code, 400)
        self.assertIn("document", response.json()["errors"])
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, self.old_name)

    def test_empty_existing_document_accepts_its_explicit_empty_revision(self):
        self.evidence.document = ""
        self.evidence.save(update_fields=["document"])
        data = self.page_payload(image_upload("black"), edited=True)
        data["expected_document"] = ""
        response = self.post_json(data)
        self.assertEqual(response.status_code, 200)
        self.evidence.refresh_from_db()
        self.assertTrue(self.evidence.document.name)
        self.assertTrue(Path(self.evidence.document.path).exists())

    def test_empty_existing_document_still_requires_a_revision_field(self):
        self.evidence.document = ""
        self.evidence.save(update_fields=["document"])
        response = self.post_json(
            self.page_payload(image_upload("black"), expected=False, edited=True)
        )
        self.assertEqual(response.status_code, 400)
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, "")

    def test_json_conflict_preserves_newer_file(self):
        self.evidence.document.save("newer.png", image_upload("black"))
        current_name = self.evidence.document.name
        current_bytes = Path(self.evidence.document.path).read_bytes()
        response = self.post_json(self.page_payload(image_upload("white"), edited=True))
        self.assertEqual(response.status_code, 409)
        self.assertIn("document", response.json()["errors"])
        self.evidence.refresh_from_db()
        self.assertEqual(self.evidence.document.name, current_name)
        self.assertEqual(Path(self.evidence.document.path).read_bytes(), current_bytes)

    def test_database_save_failure_returns_json_without_losing_current_file(self):
        with patch.object(Evidence, "save", side_effect=DatabaseError("unavailable")):
            response = self.post_json(
                self.page_payload(image_upload("black"), edited=True)
            )
        self.assertEqual(response.status_code, 503)
        self.assertIn("__all__", response.json()["errors"])
        self.assertTrue(self.old_path.exists())
        self.assertEqual(list(Path(self.media.name).rglob("*.png")), [self.old_path])

    def test_locked_load_failure_returns_json_errors(self):
        with patch.object(
            EvidenceUpdate,
            "get_object",
            side_effect=[self.evidence, DatabaseError("unavailable")],
        ):
            response = self.post_json(self.page_payload(image_upload(), edited=True))
        self.assertEqual(response.status_code, 503)
        self.assertIn("__all__", response.json()["errors"])
        self.assertTrue(self.old_path.exists())

    def test_locked_permission_failure_returns_json_forbidden(self):
        with patch(
            "ghostwriter.reporting.models.Report.user_can_edit", side_effect=[True, False]
        ):
            response = self.post_json(self.page_payload(image_upload(), edited=True))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(self.old_path.exists())

    def test_revision_checked_download_returns_exact_current_bytes(self):
        uri = reverse("reporting:evidence_download", args=[self.evidence.pk])
        response = self.client.get(uri, {"expected_document": self.old_name})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertEqual(b"".join(response.streaming_content), self.old_path.read_bytes())
        response.close()

    def test_revision_checked_download_rejects_changed_source(self):
        uri = reverse("reporting:evidence_download", args=[self.evidence.pk])
        response = self.client.get(uri, {"expected_document": "older.png"})
        self.assertEqual(response.status_code, 409)
        self.assertIn("document", response.json())
        self.assertEqual(response["Cache-Control"], "private, no-store")
        self.assertNotIn(self.old_name, response.content.decode())

    def test_ordinary_download_and_form_still_support_html_clients(self):
        response = self.client.get(self.page_uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "evidence-upload-form")
        data = self.page_payload()
        data["caption"] = ""
        response = self.client.post(self.page_uri, data)
        self.assertEqual(response.status_code, 200)
        self.assertIn("caption", response.context["form"].errors)
