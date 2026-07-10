# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ProjectAssignmentFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    UserFactory,
)
from ghostwriter.reporting.consumers import (
    user_can_access_report,
    user_can_access_report_finding,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class ReportingConsumerAccessTests(TestCase):
    """Tests for reporting WebSocket access decisions."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.finding = ReportFindingLinkFactory(report=cls.report)
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)
        ProjectAssignmentFactory(project=cls.report.project, operator=cls.user)

    def test_assigned_user_can_access_report_socket(self):
        self.assertTrue(user_can_access_report(self.report.id, self.user))

    def test_unassigned_user_cannot_access_report_socket(self):
        self.assertFalse(user_can_access_report(self.report.id, self.other_user))

    def test_inactive_user_cannot_access_report_socket(self):
        self.assertFalse(user_can_access_report(self.report.id, self.inactive_user))

    def test_missing_report_denies_socket_access(self):
        self.assertFalse(user_can_access_report(0, self.user))

    def test_non_integer_report_id_denies_socket_access(self):
        self.assertFalse(user_can_access_report("abc", self.user))

    def test_none_report_id_denies_socket_access(self):
        self.assertFalse(user_can_access_report(None, self.user))

    def test_assigned_user_can_access_report_finding_socket(self):
        self.assertTrue(user_can_access_report_finding(self.finding.id, self.user))

    def test_unassigned_user_cannot_access_report_finding_socket(self):
        self.assertFalse(
            user_can_access_report_finding(self.finding.id, self.other_user)
        )

    def test_inactive_user_cannot_access_report_finding_socket(self):
        self.assertFalse(
            user_can_access_report_finding(self.finding.id, self.inactive_user)
        )

    def test_missing_report_finding_denies_socket_access(self):
        self.assertFalse(user_can_access_report_finding(0, self.user))

    def test_non_integer_finding_id_denies_socket_access(self):
        self.assertFalse(user_can_access_report_finding("abc", self.user))

    def test_none_finding_id_denies_socket_access(self):
        self.assertFalse(user_can_access_report_finding(None, self.user))
