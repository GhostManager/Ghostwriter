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

        # Test clean-up Signal on profile change
        refetch = UserProfile.objects.get(user=user)
        old_avatar_path = refetch.avatar.path
        self.assertTrue(os.path.exists(old_avatar_path))
        refetch.avatar = self.uploaded_image_file
        refetch.save()
        self.assertFalse(os.path.exists(old_avatar_path))

        # Delete
        user.delete()
        self.assertFalse(UserProfile.objects.all().exists())
