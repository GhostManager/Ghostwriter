# Standard Libraries
import logging
from datetime import datetime
from unittest.mock import Mock

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.factories import (
    ClientInviteFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectInviteFactory,
    UserFactory,
)

# 3rd Party Libraries
from allauth.mfa.models import Authenticator

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class JwtUtilsTests(TestCase):
    """Collection of tests for JWT utilities and GraphQL Action endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        pass

    def test_generate_jwt(self):
        try:
            payload, encoded_payload = utils.generate_jwt(self.user)
        except AttributeError:
            self.fail("generate_jwt() raised an AttributeError unexpectedly!")

    def test_generate_jwt_with_expiration(self):
        expiration = datetime(2099, 1, 1).timestamp()
        payload, encoded_payload = utils.generate_jwt(self.user, exp=expiration)
        self.assertTrue(payload["exp"], expiration)

    def test_get_jwt_payload(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        try:
            self.assertTrue(utils.get_jwt_payload(encoded_payload))
        except AttributeError:
            self.fail("get_jwt_payload() raised an AttributeError unexpectedly!")

    def test_get_jwt_payload_with_invalid_token(self):
        token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwic3Vi"
            "X25hbWUiOiJCZW5ueSB0aGUgR2hvc3QiLCJzdWJfZW1haWwiOiJiZW5ue"
            "UBnaG9zdHdyaXRlci53aWtpIiwidXNlcm5hbWUiOiJiZW5ueSIsImlhdC"
            "I6MTUxNjIzOTAyMn0.DZSXsRRAr3sS2fIOmhxFxzdzjoMGG-JzKLB2QGGFhFk"
        )
        try:
            self.assertFalse(utils.get_jwt_payload(token))
        except AttributeError:
            self.fail("get_jwt_payload() raised an AttributeError unexpectedly!")

    def test_get_user_from_token(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        user_obj = utils.get_user_from_token(payload)
        try:
            self.assertEqual(user_obj, self.user)
        except AttributeError:
            self.fail("get_user_from_token() raised an AttributeError unexpectedly!")


class TestUserHasValidWebAuthnDevice(TestCase):
    """Test cases for the user_has_valid_webauthn_device function."""

    def setUp(self):
        """Set up test data."""
        self.user = UserFactory(password="testpass123")

    def test_unauthenticated_user_returns_false(self):
        """Test that unauthenticated user returns False."""
        unauthenticated_user = Mock()
        unauthenticated_user.is_authenticated = False

        result = utils.user_has_valid_webauthn_device(unauthenticated_user)

        self.assertFalse(result)

    def test_authenticated_user_with_no_webauthn_device_returns_false(self):
        """Test that authenticated user with no WebAuthn device returns False."""
        # Ensure no WebAuthn authenticators exist for this user
        Authenticator.objects.filter(user=self.user, type=Authenticator.Type.WEBAUTHN).delete()

        result = utils.user_has_valid_webauthn_device(self.user)

        self.assertFalse(result)

    def test_authenticated_user_with_webauthn_device_returns_true(self):
        """Test that authenticated user with WebAuthn device returns True."""
        # Create a WebAuthn authenticator for the user
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "test_credential_id"}
        )

        result = utils.user_has_valid_webauthn_device(self.user)

        self.assertTrue(result)

    def test_authenticated_user_with_totp_only_returns_false(self):
        """Test that authenticated user with only TOTP device returns False."""
        # Create a TOTP authenticator (not WebAuthn)
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "test_secret"}
        )

        result = utils.user_has_valid_webauthn_device(self.user)

        self.assertFalse(result)

    def test_authenticated_user_with_multiple_webauthn_devices_returns_true(self):
        """Test that authenticated user with multiple WebAuthn devices returns True."""
        # Create multiple WebAuthn authenticators
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "test_credential_id_1"}
        )
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "test_credential_id_2"}
        )

        result = utils.user_has_valid_webauthn_device(self.user)

        self.assertTrue(result)

    def test_authenticated_user_with_mixed_authenticators_returns_true(self):
        """Test that authenticated user with both TOTP and WebAuthn returns True."""
        # Create both TOTP and WebAuthn authenticators
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.TOTP,
            data={"secret": "test_secret"}
        )
        Authenticator.objects.create(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "test_credential_id"}
        )

        result = utils.user_has_valid_webauthn_device(self.user)

        self.assertTrue(result)

    def test_different_user_webauthn_device_isolation(self):
        """Test that WebAuthn devices are properly isolated between users."""
        # Create another user with WebAuthn device
        other_user = UserFactory(password="otherpass123")
        
        Authenticator.objects.create(
            user=other_user,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "other_credential_id"}
        )

        # Test that our user still returns False
        result = utils.user_has_valid_webauthn_device(self.user)
        self.assertFalse(result)

        # Test that other user returns True
        other_result = utils.user_has_valid_webauthn_device(other_user)
        self.assertTrue(other_result)