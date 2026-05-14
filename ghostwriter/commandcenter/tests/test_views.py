# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.factories import ReportFactory, ReportFindingLinkFactory, UserFactory

logging.disable(logging.CRITICAL)


class CollabModelUpdateTests(TestCase):
    """Collection of tests for collaborative model update views."""

    def test_context_data_uses_collab_jwt_type(self):
        user = UserFactory()

        context = CollabModelUpdate.context_data(user, obj_id=1)

        self.assertEqual(
            utils.get_jwt_type(context["collab_jwt"]), utils.COLLAB_JWT_TYPE
        )

    def test_context_data_includes_collab_scope_claims(self):
        user = UserFactory()
        report_finding = ReportFindingLinkFactory()

        context = CollabModelUpdate.context_data(
            user,
            obj_id=report_finding.id,
            collab_claims=CollabModelUpdate.collab_jwt_claims(
                "report_finding_link",
                report_finding,
            ),
        )
        payload = utils.get_jwt_payload(context["collab_jwt"])

        self.assertEqual(payload[utils.COLLAB_MODEL_CLAIM], "report_finding_link")
        self.assertEqual(payload[utils.COLLAB_OBJECT_ID_CLAIM], report_finding.id)
        self.assertEqual(
            payload[utils.COLLAB_REPORT_ID_CLAIM], report_finding.report_id
        )
        self.assertEqual(payload[utils.COLLAB_FINDING_ID_CLAIM], report_finding.id)

    def test_context_data_preserves_zero_object_id(self):
        user = UserFactory()

        context = CollabModelUpdate.context_data(user, obj_id=0)
        payload = utils.get_jwt_payload(context["collab_jwt"])

        self.assertEqual(payload[utils.COLLAB_OBJECT_ID_CLAIM], 0)

    def test_collab_model_name_matches_collab_server_model(self):
        report_finding = ReportFindingLinkFactory()
        view = CollabModelUpdate()
        view.model = report_finding.__class__

        self.assertEqual(view.collab_model_name(), "report_finding_link")

    def test_report_collab_scope_uses_no_id_for_missing_finding(self):
        report = ReportFactory()

        claims = CollabModelUpdate.collab_jwt_claims("report", report)

        self.assertEqual(claims[utils.COLLAB_MODEL_CLAIM], "report")
        self.assertEqual(claims[utils.COLLAB_OBJECT_ID_CLAIM], report.id)
        self.assertEqual(claims[utils.COLLAB_REPORT_ID_CLAIM], report.id)
        self.assertEqual(claims[utils.COLLAB_FINDING_ID_CLAIM], utils.COLLAB_NO_ID)
