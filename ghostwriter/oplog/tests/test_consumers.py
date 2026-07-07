# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import OplogFactory, ProjectAssignmentFactory, UserFactory
from ghostwriter.oplog.consumers import user_can_access_oplog

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class OplogConsumerAccessTests(TestCase):
    """Tests for oplog WebSocket access decisions."""

    @classmethod
    def setUpTestData(cls):
        cls.oplog = OplogFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)
        ProjectAssignmentFactory(project=cls.oplog.project, operator=cls.user)

    def test_assigned_user_can_access_oplog_socket(self):
        self.assertTrue(user_can_access_oplog(self.oplog.id, self.user))

    def test_unassigned_user_cannot_access_oplog_socket(self):
        self.assertFalse(user_can_access_oplog(self.oplog.id, self.other_user))

    def test_inactive_user_cannot_access_oplog_socket(self):
        self.assertFalse(user_can_access_oplog(self.oplog.id, self.inactive_user))

    def test_missing_oplog_denies_socket_access(self):
        self.assertFalse(user_can_access_oplog(0, self.user))
