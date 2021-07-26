# Standard Libraries
import logging

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.models import UserProfile

logging.disable(logging.INFO)


class UserProfileModelTests(TestCase):
    """Collection of tests for :model:`home.UserProfile`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def test_crud_finding(self):
        # Create
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(UserProfile.objects.all().exists())
        self.assertTrue(UserProfile.objects.filter(user=user.id).exists())

        # Update
        profile.avatar = SimpleUploadedFile("new_avatar.png", b"lorem ipsum")
        profile.save()
        self.assertIn("new_avatar.png", profile.avatar.path)

        # Delete
        user.delete()
        self.assertFalse(UserProfile.objects.all().exists())

    def test_avatar_url_property(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        try:
            url = profile.avatar_url
            self.assertIn("images/default_avatar.png", url)

            profile.avatar = SimpleUploadedFile("new_avatar.png", b"lorem ipsum")
            profile.save()
            profile.refresh_from_db()

            url = profile.avatar_url
            self.assertIn(f"images/user_avatars/{user.id}/new_avatar.png", url)
        except Exception:
            self.fail("UserProfile model `avatar_url` property failed unexpectedly!")
