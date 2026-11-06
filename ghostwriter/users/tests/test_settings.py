"""Checks account settings that affect authentication and email management."""

from django.conf import settings
from django.test import SimpleTestCase


class AccountSettingsTests(SimpleTestCase):
    def test_email_verification_uses_allauth_string_value(self):
        self.assertIn(
            settings.ACCOUNT_EMAIL_VERIFICATION,
            {"mandatory", "optional", "none"},
        )
