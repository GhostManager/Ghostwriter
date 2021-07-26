# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.users.forms import GroupAdminForm

logging.disable(logging.INFO)


class GroupAdminFormTests(TestCase):
    """Collection of tests for :form:`users.GroupAdminForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        permissions=None,
        users=None,
        **kwargs,
    ):
        return GroupAdminForm(
            data={
                "name": name,
                "permissions": permissions,
                "users": users,
            },
        )

    def test_valid_data(self):
        form = self.form_data(
            name="Test Group",
            permissions=[25, 250],
            users=[
                self.user.id,
            ],
        )
        print(form.errors.as_data())
        self.assertTrue(form.is_valid())
