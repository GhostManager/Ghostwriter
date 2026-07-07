# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.consumers import user_can_access_channel

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class UserConsumerAccessTests(TestCase):
    """Tests for user notification WebSocket access decisions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)

    def test_user_can_access_own_notification_channel(self):
        self.assertTrue(
            user_can_access_channel(self.user.get_clean_username(), self.user)
        )

    def test_user_cannot_access_another_users_notification_channel(self):
        self.assertFalse(
            user_can_access_channel(self.other_user.get_clean_username(), self.user)
        )

    def test_active_user_can_access_all_notification_channel(self):
        self.assertTrue(user_can_access_channel("all", self.user))

    def test_inactive_user_cannot_access_notification_channel(self):
        self.assertFalse(
            user_can_access_channel(
                self.inactive_user.get_clean_username(), self.inactive_user
            )
        )
