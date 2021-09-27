# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory

logging.disable(logging.CRITICAL)


class UserModelTests(TestCase):
    """Collection of tests for :model:`users.User`."""

    @classmethod
    def setUpTestData(cls):
        cls.User = UserFactory._meta.model

    def test_crud_finding(self):
        # Create
        user = UserFactory(name="Christopher Maddalena", username="cmaddalena")

        # Read
        self.assertEqual(user.name, "Christopher Maddalena")

        # Update
        user.name = "Jason Frank"
        user.save()
        user.refresh_from_db()
        self.assertEqual(user.name, "Jason Frank")

        # Delete
        user.delete()
        self.assertFalse(self.User.objects.all().exists())

    def test_get_display_name_property(self):
        user = UserFactory(name="Christopher Maddalena", username="cmaddalena")
        self.assertEqual(user.get_display_name(), "Christopher Maddalena (cmaddalena)")

        user.name = ""
        user.save()
        self.assertEqual(user.get_display_name(), "Cmaddalena")

        user.is_active = False
        user.save()
        self.assertEqual(user.get_display_name(), "DISABLED – Cmaddalena")
