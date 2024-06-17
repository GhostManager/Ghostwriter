# Standard Libraries
from binascii import hexlify
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
        user.is_active = True
        user.save()

    def test_get_full_name_property(self):
        user = UserFactory(name="Christopher Maddalena", username="cmaddalena")
        self.assertEqual(user.get_full_name(), "Christopher Maddalena")

    def test_get_clean_username_property(self):
        cleaned = hexlify("benny@ghostwriter.wiki".encode()).decode()
        user = UserFactory(username="benny@ghostwriter.wiki")
        self.assertEqual(user.get_clean_username(), cleaned)
