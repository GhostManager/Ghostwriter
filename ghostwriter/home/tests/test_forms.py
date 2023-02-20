# Standard Libraries
import logging
from base64 import b64decode
from io import BytesIO

# Django Imports
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.forms import SignupForm, UserProfileForm

logging.disable(logging.CRITICAL)


class UserProfileFormTests(TestCase):
    """Collection of tests for :form:`home.UserProfileForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

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

        text_data = b64decode("R2hvc3R3cml0ZXIK")
        text_file = ContentFile(text_data, "fake.txt")

        text = InMemoryUploadedFile(
            BytesIO(text_data),
            field_name="tempfile",
            name="fake.txt",
            content_type="text/html",
            size=len(text_data),
            charset="utf-8",
        )
        cls.in_memory_text = text

        cls.uploaded_text_file = SimpleUploadedFile(text_file.name, text_file.read(), content_type="text/html")

        cls.uploaded_mismatched_file = SimpleUploadedFile(image_file.name, image_file.read(), content_type="text/html")

    def setUp(self):
        pass

    def form_data(
        self,
        avatar=None,
        **kwargs,
    ):
        return UserProfileForm(
            data={},
            files={
                "avatar": avatar,
            },
        )

    def test_valid_data(self):
        form = self.form_data(avatar=self.uploaded_image_file)
        self.assertTrue(form.is_valid())

    def test_text_file(self):
        form = self.form_data(avatar=self.uploaded_text_file)
        errors = form["avatar"].errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_image")

    def test_invalid_data(self):
        form = self.form_data(avatar=self.uploaded_mismatched_file)
        errors = form["avatar"].errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "empty")


class SignupFormTests(TestCase):
    """Collection of tests for :form:`home.SignupForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        **kwargs,
    ):
        return SignupForm(
            data={
                "name": name,
            },
        )

    def test_valid_data(self):
        form = self.form_data(name="Ghostwriter")
        self.assertTrue(form.is_valid())
