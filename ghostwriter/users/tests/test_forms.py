# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import GroupFactory, UserFactory
from ghostwriter.users.forms import GroupAdminForm, UserChangeForm

logging.disable(logging.CRITICAL)


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
        email=None,
        phone=None,
        timezone=None,
        **kwargs,
    ):
        return UserChangeForm(
            data={
                "name": name,
                "email": email,
                "timezone": timezone,
                "phone": phone,
            },
        )

    def test_valid_data(self):
        form = self.form_data(**self.user.__dict__)
        self.assertTrue(form.is_valid())
