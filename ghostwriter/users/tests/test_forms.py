# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# 3rd Party Libraries
from allauth.mfa.totp.internal.auth import generate_totp_secret, TOTP, hotp_value, format_hotp_value, yield_hotp_counters_from_time

# Add at the top with other imports
from unittest.mock import patch

# Ghostwriter Libraries
from ghostwriter.factories import GroupFactory, UserFactory
from ghostwriter.users.forms import (
    GroupAdminForm,
    UserMFAAuthenticateForm,
    UserMFADeviceRemoveForm,
    UserChangeForm,
    UserSignupForm,
)

logging.disable(logging.CRITICAL)


PASSWORD = "SuperNaturalReporting!"


class GroupAdminFormTests(TestCase):
    """Collection of tests for :form:`users.GroupAdminForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.group = GroupFactory()
        cls.user = UserFactory()
        cls.added_user = UserFactory(groups=(cls.group,))

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        permissions=None,
        users=None,
        instance=None,
        **kwargs,
    ):
        return GroupAdminForm(
            data={
                "name": name,
                "permissions": permissions,
                "users": users,
            },
            instance=instance,
        )

    def test_valid_data(self):
        form = self.form_data(
            name="Test Group",
            permissions=[25, 250],
            users=[
                self.user.id,
            ],
        )
        self.assertTrue(form.is_valid())

    def test_existing_group(self):
        form = self.form_data(
            name=self.group.name,
            instance=self.group,
        )
        self.assertTrue(form.is_valid())


class UserChangeFormTests(TestCase):
    """Collection of tests for :form:`users.UserUpdateForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        phone=None,
        timezone=None,
        **kwargs,
    ):
        return UserChangeForm(
            data={
                "name": name,
                "timezone": timezone,
                "phone": phone,
            },
        )

    def test_valid_data(self):
        form = self.form_data(**self.user.__dict__)
        self.assertTrue(form.is_valid())

def get_code_from_totp_device(secret) -> str:
    # To generate a valid code for the form:
    counter = next(yield_hotp_counters_from_time())
    code = format_hotp_value(hotp_value(secret, counter))
    return code

class UserMFAAuthenticateFormTests(TestCase):
    """Collection of tests for :form:`users.UserMFAAuthenticateForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.secret = generate_totp_secret()
        cls.totp_device = TOTP.activate(cls.user, cls.secret)

    def setUp(self):
        # Add patch for the rate limiting
        self.rate_limit_patcher = patch('allauth.mfa.base.internal.flows.check_rate_limit',
                                        return_value=mock_rate_limit_check)
        self.mock_rate_limit = self.rate_limit_patcher.start()

        # Also mock clear() to avoid the request.META access
        self.clear_patcher = patch('allauth.core.ratelimit.clear',
                                    return_value=None)
        self.mock_clear = self.clear_patcher.start()

        # Also patch the consume function
        self.consume_patcher = patch('allauth.core.ratelimit.consume',
                                     return_value=MockRateLimitUsage())
        self.mock_consume = self.consume_patcher.start()

    def tearDown(self):
        self.rate_limit_patcher.stop()
        self.consume_patcher.stop()
        self.clear_patcher.stop()  # Stop the new patcher

    def createAuthenticator(self, user):
        """Helper function to create an Authenticator instance for a user."""
        return user.totpdevice_set.create()


    def form_data(
        self,
        user=None,
        otp_token=None,
        **kwargs,
    ):

        return UserMFAAuthenticateForm(
            user=user,
            data={"code": otp_token},
        )

    def test_valid_data(self):
        token = get_code_from_totp_device(self.secret)
        form = self.form_data(self.user, token)
        v = form.is_valid()
        if not v:
            print(f"\nForm errors: {form.errors}")
            print(f"Form data: {form.data}")
        self.assertTrue(v)

    def test_invalid_data(self):
        form = self.form_data(self.user, "123456")
        self.assertFalse(form.is_valid())


class UserMFADeviceRemoveFormTests(TestCase):
    """Collection of tests for :form:`users.UserMFADeviceRemoveForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.secret = generate_totp_secret()
        cls.totp_device = TOTP.activate(cls.user, cls.secret)

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        otp_token=None,
        **kwargs,
    ):
        # Get the TOTP device to use as authenticator
        authenticator = self.totp_device if user else None
        data = {"code": otp_token} if otp_token else {}
        return UserMFADeviceRemoveForm(
            data=data,
            authenticator=authenticator,
        )

    def test_valid_data(self):
        token = get_code_from_totp_device(self.secret)
        form = self.form_data(self.user, token)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = self.form_data(None, None)
        self.assertFalse(form.is_valid())


class UserSignUpFormTests(TestCase):
    """Collection of tests for :form:`users.UserSignUpForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        email=None,
        username=None,
        name=None,
        password1=None,
        password2=None,
        **kwargs,
    ):
        return UserSignupForm(
            data={
                "name": name,
                "email": email,
                "username": username,
                "password1": password1,
                "password2": password2,
            },
        )

    def test_valid_data(self):
        form = self.form_data(
            "benny@gmail.com",
            "benny",
            "Benny Ghostwriter",
            PASSWORD,
            PASSWORD,
        )
        self.assertTrue(form.is_valid())




# Add this helper function
def mock_rate_limit_check():
    """Mock rate limit check that always succeeds"""
    def clear_rate_limit():
        pass
    return clear_rate_limit

# Create a mock RateLimitUsage class that always returns True for allowed
class MockRateLimitUsage:
    def __init__(self):
        self.usage = []

    def rollback(self):
        pass

