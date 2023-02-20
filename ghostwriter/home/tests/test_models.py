# Standard Libraries
import logging
import os
from base64 import b64decode
from io import BytesIO

# Django Imports
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.models import UserProfile

logging.disable(logging.CRITICAL)


class UserProfileModelTests(TestCase):
    """Collection of tests for :model:`home.UserProfile`."""

    @classmethod
    def setUpTestData(cls):
        image_data = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        image_file = ContentFile(image_data, "fake.png")

        image = InMemoryUploadedFile(
            BytesIO(image_data),
            field_name="tempfile",
            name="fake.png",
            content_type="image/png",
            size=len(image_data),
            charset="utf-8",
        )
        cls.in_memory_image = image

        cls.uploaded_image_file = SimpleUploadedFile(image_file.name, image_file.read(), content_type="image/png")

    def test_crud_finding(self):
        # Create
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        self.assertTrue(UserProfile.objects.all().exists())
        self.assertTrue(UserProfile.objects.filter(user=user.id).exists())

        # Update
        # profile.avatar = SimpleUploadedFile("new_avatar.png", b"lorem ipsum")
        profile.avatar = self.uploaded_image_file
        profile.save()
        self.assertIn("fake.png", profile.avatar.path)

        # Delete
        user.delete()
        self.assertFalse(UserProfile.objects.all().exists())

    def test_avatar_url_property(self):
        user = UserFactory()
        profile = UserProfile.objects.get(user=user)
        try:
            # Test default avatar file is returned
            url = profile.avatar_url
            self.assertIn("images/default_avatar.png", url)

            # Set avatar file and confirm URL changes
            profile.avatar = self.uploaded_image_file
            profile.save()
            profile.refresh_from_db()
            url = profile.avatar_url
            self.assertIn(f"images/user_avatars/{user.id}/fake.png", url)

            # Delete the avatar file and confirm default avatar is returned
            os.remove(profile.avatar.path)
            profile.refresh_from_db()
            url = profile.avatar_url
            self.assertIn("images/default_avatar.png", url)
        except Exception:
            self.fail("UserProfile model `avatar_url` property failed unexpectedly!")
