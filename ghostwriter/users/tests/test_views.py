# Standard Libraries
import logging
import os
from base64 import b64decode
from io import BytesIO

# Django Imports
from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.models import UserProfile

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class UserDetailViewTests(TestCase):
    """Collection of tests for :view:`users.UserDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile.html")


class UserUpdateViewTests(TestCase):
    """Collection of tests for :view:`users.UserUpdateView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:user_update", kwargs={"username": cls.user.username})
        cls.success_uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.other_client_auth = Client()
        self.other_client_auth.login(username=self.other_user.username, password=PASSWORD)
        self.assertTrue(self.other_client_auth.login(username=self.other_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile_form.html")

    def test_view_blocks_improper_access(self):
        response = self.other_client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_successful_redirect(self):
        response = self.client_auth.post(
            self.uri,
            {
                "name": self.user.name,
                "email": self.user.email,
                "timezone": self.user.timezone,
                "phone": self.user.phone,
            },
        )
        self.assertRedirects(response, self.success_uri)


class UserProfileUpdateViewTests(TestCase):
    """Collection of tests for :view:`users.UserProfileUpdateView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:userprofile_update", kwargs={"username": cls.user.username})
        cls.redirect_uri = reverse("users:redirect")
        cls.success_uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

        image_data = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        image_file = ContentFile(image_data, "fake.png")
        cls.uploaded_image_file = SimpleUploadedFile(image_file.name, image_file.read(), content_type="image/png")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.other_client_auth = Client()
        self.other_client_auth.login(username=self.other_user.username, password=PASSWORD)
        self.assertTrue(self.other_client_auth.login(username=self.other_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "users/profile_form.html")

    def test_view_blocks_improper_access(self):
        response = self.other_client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_successfull_redirect(self):
        response = self.client_auth.post(self.uri, {"avatar": self.uploaded_image_file})
        self.assertRedirects(response, self.success_uri)


class UserRedirectViewTests(TestCase):
    """Collection of tests for :view:`users.UserRedirectView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:redirect")
        cls.redirect_uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class GhostwriterPasswordChangeViewTests(TestCase):
    """Collection of tests for :view:`users.GhostwriterPasswordChangeView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("account_change_password")
        cls.success_uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_successfull_redirect(self):
        response = self.client_auth.post(
            self.uri,
            {"oldpassword": PASSWORD, "password1": "IxIGx58vy79hS&sju#Ea", "password2": "IxIGx58vy79hS&sju#Ea"},
        )
        self.assertRedirects(response, self.success_uri)
        self.user.password = PASSWORD
        self.user.save()


class UserLoginViewTests(TestCase):
    """Collection of tests for :view:`allauth.Login`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("account_login")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_redirects_if_authenticated(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")

    def test_valid_credentials(self):
        response = self.client.post(self.uri, {"login": self.user.username, "password": PASSWORD})
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed(response, "account/messages/logged_in.txt")

    def test_invalid_credentials(self):
        response = self.client.post(self.uri, {"login": self.user.username, "password": "invalid"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")


class RequireMFAMiddlewareTests(TestCase):
    """Collection of tests for `RequireMFAMiddleware` authentication middleware."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("home:dashboard")
        cls.setup_uri = reverse("mfa_activate_totp")
        cls.change_pwd_uri = reverse("account_change_password")
        cls.logout_uri = reverse("account_logout")
        cls.reset_pwd_uri = reverse("account_reset_password")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_mfa_required(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        self.user.require_mfa = True
        self.user.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(response, self.setup_uri, fetch_redirect_response=False, target_status_code=302)

        response = self.client_auth.get(self.setup_uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_auth.get(self.change_pwd_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_auth.get(self.reset_pwd_uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_auth.get(self.logout_uri)
        self.assertEqual(response.status_code, 200)

        self.user.require_mfa = False
        self.user.save()


class AvatarDownloadTest(TestCase):
    """Collection of tests for :view:`users.AvatarDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.username_with_period = UserFactory(username="first.last", password=PASSWORD)
        cls.uri = reverse("users:avatar_download", kwargs={"slug": cls.user.username})
        cls.user_profile = UserProfile.objects.get(user=cls.user)
        cls.missing_user_uri = reverse("users:avatar_download", kwargs={"slug": "missing_user"})
        cls.period_uri = reverse("users:avatar_download", kwargs={"slug": cls.username_with_period.username})

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

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.get("Content-Disposition"), 'attachment; filename="default_avatar.png"')

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_non_existent_user(self):
        response = self.client_auth.get(self.missing_user_uri)
        self.assertEqual(response.status_code, 404)

    def test_username_with_period(self):
        response = self.client_auth.get(self.period_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_returns_correct_image(self):
        self.user_profile.avatar = self.uploaded_image_file
        self.user_profile.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertRegexpMatches(response.get("Content-Disposition"), r'^attachment; filename="fake[_0-9]*\.png"$')

        if os.path.exists(self.user_profile.avatar.path):
            os.remove(self.user_profile.avatar.path)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.get("Content-Disposition"), 'attachment; filename="default_avatar.png"')

        self.user_profile.avatar = None
        self.user_profile.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(response.get("Content-Disposition"), 'attachment; filename="default_avatar.png"')


class HideQuickStartViewTests(TestCase):
    """Collection of tests for :view:`users.HideQuickStart`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:hide_quickstart", kwargs={"slug": cls.user.username})
        cls.other_user_uri = reverse("users:hide_quickstart", kwargs={"slug": cls.other_user.username})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_requires_login(self):
        user_profile = UserProfile.objects.get(user=self.user)
        user_profile.hide_quickstart = False
        user_profile.save()
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.other_user_uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        user_profile.refresh_from_db()
        self.assertTrue(user_profile.hide_quickstart)


class SignupViewTests(TestCase):
    """Collection of tests for :view:`allauth.account_signup`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("account_signup")

    def setUp(self):
        self.client = Client()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        settings.ACCOUNT_ALLOW_REGISTRATION = True
        self.assertTrue(settings.ACCOUNT_ALLOW_REGISTRATION)
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup.html")

        settings.ACCOUNT_ALLOW_REGISTRATION = False
        self.assertFalse(settings.ACCOUNT_ALLOW_REGISTRATION)
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/signup_closed.html")
