# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# 3rd Party Libraries
from django_otp.oath import TOTP
from django_otp.plugins.otp_static.models import StaticToken

# Ghostwriter Libraries
from ghostwriter.factories import GroupFactory, UserFactory
from ghostwriter.users.forms import (
    GroupAdminForm,
    User2FAAuthenticateForm,
    User2FADeviceRemoveForm,
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


def get_token_from_totp_device(totp_model) -> str:
    return TOTP(
        key=totp_model.bin_key,
        step=totp_model.step,
        t0=totp_model.t0,
        digits=totp_model.digits,
    ).token()


class User2FAAuthenticateFormTests(TestCase):
    """Collection of tests for :form:`users.User2FAAuthenticateForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.totp_model = cls.user.totpdevice_set.create()
        static_model = cls.user.staticdevice_set.create()
        static_model.token_set.create(token=StaticToken.random_token())

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        otp_token=None,
        **kwargs,
    ):
        return User2FAAuthenticateForm(
            user=user,
            data={"otp_token": otp_token},
        )

    def test_valid_data(self):
        token = get_token_from_totp_device(self.totp_model)
        form = self.form_data(self.user, token)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = self.form_data(self.user, "123456")
        self.assertFalse(form.is_valid())


class User2FADeviceRemoveFormTests(TestCase):
    """Collection of tests for :form:`users.User2FADeviceRemoveForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()
        cls.totp_model = cls.user.totpdevice_set.create()
        static_model = cls.user.staticdevice_set.create()
        static_model.token_set.create(token=StaticToken.random_token())

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        otp_token=None,
        **kwargs,
    ):
        return User2FADeviceRemoveForm(
            user=user,
            data={"otp_token": otp_token},
        )

    def test_valid_data(self):
        token = get_token_from_totp_device(self.totp_model)
        form = self.form_data(self.user, token)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        form = self.form_data(self.user, "123456")
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
