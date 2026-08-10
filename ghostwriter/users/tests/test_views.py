# Standard Libraries
import logging
import os
import time
from base64 import b64decode
from io import BytesIO
from unittest.mock import patch

# Django Imports
from django.conf import settings
from django.contrib.auth import SESSION_KEY
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.core.files.uploadedfile import InMemoryUploadedFile, SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse

# 3rd Party Libraries
from allauth.account.models import EmailAddress
from allauth.account.authentication import AUTHENTICATION_METHODS_SESSION_KEY
from allauth.mfa import app_settings as mfa_app_settings
from allauth.mfa.internal.flows.add import validate_can_add_authenticator
from allauth.mfa.models import Authenticator
from allauth.mfa.recovery_codes.internal.auth import RecoveryCodes
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

# Ghostwriter Libraries
from ghostwriter.factories import ProjectAssignmentFactory, ProjectFactory, UserFactory
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
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

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
        self.assertContains(response, 'class="page-content"')
        self.assertContains(response, 'class="profile-dashboard"')
        self.assertContains(response, 'class="profile-identity-panel"')
        self.assertContains(response, 'id="account-actions"')
        self.assertContains(response, "Settings and security")
        self.assertContains(response, "Personal access tokens")

    def test_active_project_uses_shared_table_link_style(self):
        project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)

        response = self.client_auth.get(self.uri)

        self.assertContains(
            response,
            f'class="table-primary-link" href="{project.get_absolute_url()}"',
        )


class UserUpdateViewTests(TestCase):
    """Collection of tests for :view:`users.UserUpdateView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:user_update", kwargs={"username": cls.user.username})
        cls.success_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.other_client_auth = Client()
        self.other_client_auth.login(
            username=self.other_user.username, password=PASSWORD
        )
        self.assertTrue(
            self.other_client_auth.login(
                username=self.other_user.username, password=PASSWORD
            )
        )

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
        self.assertContains(response, "Operator identity")
        self.assertContains(
            response,
            "Edit the contact details and timezone used for assignments and reports.",
        )
        self.assertContains(response, 'data-timezone-search="true"')
        self.assertContains(response, 'id="profile-timezone-options"')
        self.assertContains(response, "America/Los_Angeles")
        self.assertContains(
            response,
            'class="resource-form-actions resource-form-actions-compact"',
        )
        self.assertNotContains(response, "Editing your profile")
        self.assertNotContains(response, "Edit operator profile")
        self.assertNotContains(response, '<span class="detail-eyebrow">Profile</span>')

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

    def test_invalid_timezone_is_rejected(self):
        response = self.client_auth.post(
            self.uri,
            {
                "name": self.user.name,
                "timezone": "Not/A_Timezone",
                "phone": self.user.phone,
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFormError(
            response.context["form"],
            "timezone",
            "Select a valid choice. Not/A_Timezone is not one of the available choices.",
        )


class UserProfileUpdateViewTests(TestCase):
    """Collection of tests for :view:`users.UserProfileUpdateView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse(
            "users:userprofile_update", kwargs={"username": cls.user.username}
        )
        cls.redirect_uri = reverse("users:redirect")
        cls.success_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

        image_data = b64decode(
            "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg=="
        )
        image_file = ContentFile(image_data, "fake.png")
        cls.uploaded_image_file = SimpleUploadedFile(
            image_file.name, image_file.read(), content_type="image/png"
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.other_client_auth = Client()
        self.other_client_auth.login(
            username=self.other_user.username, password=PASSWORD
        )
        self.assertTrue(
            self.other_client_auth.login(
                username=self.other_user.username, password=PASSWORD
            )
        )

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
        self.assertContains(response, 'class="profile-avatar-current"')
        self.assertContains(response, "Choose a new image")
        self.assertContains(response, "profile-avatar-submit")
        self.assertContains(response, "disabled")
        self.assertContains(
            response,
            'class="resource-form-actions resource-form-actions-compact"',
        )
        self.assertNotContains(response, "Updating your profile image")
        self.assertNotContains(response, "Avatar Upload")
        self.assertNotContains(response, "Update profile image")
        self.assertNotContains(response, '<span class="detail-eyebrow">Profile</span>')

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
        cls.redirect_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

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
        cls.success_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "password-change-form")

    def test_view_uses_refreshed_account_security_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-security-page"',
        )
        self.assertContains(
            response, 'class="resource-form-card account-security-card"'
        )
        self.assertContains(response, 'class="resource-form-actions-buttons"')
        self.assertNotContains(response, 'class="col-md-6 offset-md-3"')

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_successfull_redirect(self):
        response = self.client_auth.post(
            self.uri,
            {
                "oldpassword": PASSWORD,
                "password1": "IxIGx58vy79hS&sju#Ea",
                "password2": "IxIGx58vy79hS&sju#Ea",
            },
        )
        self.assertRedirects(response, self.success_uri)
        self.user.password = PASSWORD
        self.user.save()


class GhostwriterEmailAddressViewTests(TestCase):
    """Collection of tests for the account email-address management view."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, email="operator@example.com")
        cls.uri = reverse("account_email")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uses_refreshed_account_email_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-email-editor"',
        )
        self.assertContains(response, 'class="account-email-option"')
        self.assertContains(response, "Verified")
        self.assertContains(response, "Primary")
        self.assertContains(response, "Add an email address")
        self.assertContains(response, "window.confirm")
        self.assertNotContains(response, 'class="col-md-6 offset-md-3"')

    def test_view_requires_login(self):
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 302)


class MFAIndexViewTests(TestCase):
    """Collection of tests for the multi-factor authentication settings page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("mfa_index")

    def setUp(self):
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_actions_are_centered_with_footer_spacing(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="card-footer mfa-actions"', count=2)
        self.assertNotContains(response, "card-footer pt-0 mfa-actions")


class MFALoginChallengeViewTests(TestCase):
    """Collection of tests for the MFA challenge during sign-in."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            password=PASSWORD,
            email="mfa-login@example.com",
        )
        cls.uri = reverse("mfa_authenticate")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )
        TOTP.activate(cls.user, generate_totp_secret())

    def setUp(self):
        self.client_auth = Client()
        response = self.client_auth.post(
            reverse("account_login"),
            {"login": self.user.username, "password": PASSWORD},
        )
        self.assertRedirects(
            response,
            self.uri,
            fetch_redirect_response=False,
        )

    def test_view_uses_refreshed_login_challenge_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/authenticate.html")
        self.assertContains(response, 'class="auth-challenge-page"')
        self.assertContains(response, 'class="auth-challenge-card"')
        self.assertContains(response, "Confirm your sign-in")
        self.assertContains(response, "Verify and continue")
        self.assertContains(response, "Use passkey")
        self.assertContains(response, "Authentication or recovery code")
        self.assertContains(response, 'autocomplete="one-time-code"')
        self.assertContains(response, 'autocapitalize="off"')
        self.assertNotContains(response, 'class="form-group col-4 offset-4')


class MFAActivationViewTests(TestCase):
    """Collection of tests for the authenticator-app activation page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            password=PASSWORD,
            email="mfa-activation@example.com",
        )
        cls.uri = reverse("mfa_activate_totp")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)
        session = self.client_auth.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

    def test_view_uses_refreshed_activation_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/totp/activate_form.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-mfa-activation"',
        )
        self.assertContains(response, 'class="account-mfa-step"', count=2)
        self.assertContains(response, "Connect your app")
        self.assertContains(response, "Confirm the connection")
        self.assertContains(response, "Verify and enable")
        self.assertContains(response, 'autocomplete="one-time-code"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertContains(response, 'pattern="[0-9]{6}"')
        self.assertNotContains(response, 'class="col-4 offset-4')

    def test_view_does_not_schedule_working_report_redirect(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "redirectToShortcutAfterMessage: true")


class MFADeactivationViewTests(TestCase):
    """Collection of tests for authenticator-app deactivation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            password=PASSWORD,
            email="mfa-deactivation@example.com",
        )
        cls.uri = reverse("mfa_deactivate_totp")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )
        TOTP.activate(cls.user, generate_totp_secret())

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)
        session = self.client_auth.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

    def test_view_uses_refreshed_deactivation_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/totp/deactivate_form.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-mfa-deactivation"',
        )
        self.assertContains(response, "What changes when you disable it")
        self.assertContains(response, "Confirm this change")
        self.assertContains(response, "Current authenticator code")
        self.assertContains(response, 'autocomplete="one-time-code"')
        self.assertContains(response, 'inputmode="numeric"')
        self.assertNotContains(response, "This field is required")
        self.assertNotContains(response, 'class="form-group col-4 offset-4')

    def test_invalid_code_is_reported_inline_without_removing_authenticator(self):
        response = self.client_auth.post(self.uri, {"code": "123"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Authenticator app not disabled")
        self.assertContains(response, "Ensure this value has at least 6 characters")
        self.assertTrue(
            Authenticator.objects.filter(
                user=self.user,
                type=Authenticator.Type.TOTP,
            ).exists()
        )


class MFAWebAuthnAddViewTests(TestCase):
    """Collection of tests for security-key enrollment."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            password=PASSWORD,
            email="mfa-security-key@example.com",
        )
        cls.uri = reverse("mfa_add_webauthn")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )
        TOTP.activate(cls.user, generate_totp_secret())

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)
        session = self.client_auth.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

    def test_view_uses_refreshed_security_key_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/webauthn/add_form.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-webauthn-add"',
        )
        self.assertContains(response, "What to expect")
        self.assertContains(response, "Allow passwordless sign-in")
        self.assertContains(response, 'id="id_passwordless_helptext"')
        self.assertContains(response, 'name="name"')
        self.assertContains(response, 'name="credential"')
        self.assertContains(response, 'id="mfa_webauthn_add" type="button"')
        self.assertContains(
            response, 'data-allauth-onload="allauth.webauthn.forms.addForm"'
        )
        self.assertNotContains(response, "redirectToShortcutAfterMessage: true")
        self.assertNotContains(response, 'class="row justify-content-center"')


class MFAWebAuthnListViewTests(TestCase):
    """Collection of tests for registered security-key management."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("mfa_list_webauthn")
        cls.passkey = Authenticator.objects.create(
            user=cls.user,
            type=Authenticator.Type.WEBAUTHN,
            data={
                "name": "Laptop passkey",
                "credential": {"clientExtensionResults": {"credProps": {"rk": True}}},
            },
        )
        cls.security_key = Authenticator.objects.create(
            user=cls.user,
            type=Authenticator.Type.WEBAUTHN,
            data={
                "name": "Office key",
                "credential": {"clientExtensionResults": {"credProps": {"rk": False}}},
            },
        )

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)

    def test_view_uses_refreshed_key_management_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/webauthn/authenticator_list.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-webauthn-management"',
        )
        self.assertContains(response, 'class="account-webauthn-device"', count=2)
        self.assertContains(response, "Laptop passkey")
        self.assertContains(response, "Office key")
        self.assertContains(response, "Passkey")
        self.assertContains(response, "Security key")
        self.assertContains(
            response,
            f'href="{reverse("mfa_edit_webauthn", args=[self.passkey.pk])}"',
        )
        self.assertContains(
            response,
            f'href="{reverse("mfa_remove_webauthn", args=[self.passkey.pk])}"',
        )
        self.assertNotContains(response, '<table id="token-table"')
        self.assertNotContains(
            response,
            f'<form method="post" action="{reverse("mfa_edit_webauthn", args=[self.passkey.pk])}"',
        )
        self.assertNotContains(
            response,
            f'<form method="post" action="{reverse("mfa_remove_webauthn", args=[self.passkey.pk])}"',
        )

    def test_view_has_actionable_empty_state(self):
        Authenticator.objects.filter(
            user=self.user,
            type=Authenticator.Type.WEBAUTHN,
        ).delete()

        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No security keys registered")
        self.assertContains(response, reverse("mfa_add_webauthn"))


class MFAWebAuthnKeyActionViewTests(TestCase):
    """Collection of tests for renaming and removing security keys."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.authenticator = Authenticator.objects.create(
            user=cls.user,
            type=Authenticator.Type.WEBAUTHN,
            data={
                "name": "Office key",
                "credential": {"clientExtensionResults": {"credProps": {"rk": False}}},
            },
        )
        cls.edit_uri = reverse(
            "mfa_edit_webauthn",
            args=[cls.authenticator.pk],
        )
        cls.remove_uri = reverse(
            "mfa_remove_webauthn",
            args=[cls.authenticator.pk],
        )

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)
        session = self.client_auth.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

    def test_edit_view_uses_refreshed_layout(self):
        response = self.client_auth.get(self.edit_uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/webauthn/edit_form.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-webauthn-edit"',
        )
        self.assertContains(response, "Rename security key")
        self.assertContains(response, "Office key")
        self.assertContains(response, "Save name")
        self.assertContains(response, f'action="{self.edit_uri}"')
        self.assertNotContains(response, 'class="row justify-content-center"')

    def test_edit_post_renames_security_key(self):
        response = self.client_auth.post(
            self.edit_uri,
            {"name": "Travel key"},
        )

        self.assertRedirects(
            response,
            reverse("mfa_list_webauthn"),
            fetch_redirect_response=False,
        )
        self.authenticator.refresh_from_db()
        self.assertEqual(self.authenticator.data["name"], "Travel key")

    def test_remove_view_uses_custom_confirmation_layout(self):
        response = self.client_auth.get(self.remove_uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(
            response,
            "mfa/webauthn/authenticator_confirm_delete.html",
        )
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-webauthn-remove"',
        )
        self.assertContains(response, "This action cannot be undone")
        self.assertContains(response, "Office key")
        self.assertContains(response, f'action="{self.remove_uri}"')
        self.assertTrue(Authenticator.objects.filter(pk=self.authenticator.pk).exists())

    def test_remove_post_deletes_security_key(self):
        response = self.client_auth.post(self.remove_uri)

        self.assertRedirects(
            response,
            reverse("mfa_list_webauthn"),
            fetch_redirect_response=False,
        )
        self.assertFalse(
            Authenticator.objects.filter(pk=self.authenticator.pk).exists()
        )


@override_settings(MFA_REVEAL_TOKENS=True)
class MFARecoveryCodesViewTests(TestCase):
    """Collection of tests for the recovery-code management page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(
            password=PASSWORD,
            email="mfa-recovery@example.com",
        )
        cls.uri = reverse("mfa_view_recovery_codes")
        EmailAddress.objects.create(
            user=cls.user,
            email=cls.user.email,
            primary=True,
            verified=True,
        )
        TOTP.activate(cls.user, generate_totp_secret())
        cls.recovery_codes = RecoveryCodes.activate(cls.user).get_unused_codes()

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)
        session = self.client_auth.session
        session[AUTHENTICATION_METHODS_SESSION_KEY] = [
            {"method": "password", "at": time.time()}
        ]
        session.save()

    def test_view_uses_refreshed_recovery_code_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "mfa/recovery_codes/index.html")
        self.assertContains(
            response,
            'class="resource-form-shell account-profile-editor account-recovery-codes"',
        )
        self.assertContains(
            response, 'class="account-recovery-code"', count=len(self.recovery_codes)
        )
        self.assertContains(response, self.recovery_codes[0])
        self.assertContains(
            response,
            f'action="{reverse("mfa_view_recovery_codes")}"',
        )
        self.assertContains(response, "Replace codes")
        self.assertContains(response, "data-confirm-replacement")
        self.assertContains(response, "window.confirm")
        self.assertNotContains(response, 'class="offset-4 col-4"')

    def test_recovery_codes_are_not_rendered_when_viewing_is_disabled(self):
        with patch(
            "allauth.mfa.recovery_codes.internal.flows.view_recovery_codes"
        ) as mock_view_codes:
            recovery_wrapper = Authenticator.objects.get(
                user=self.user,
                type=Authenticator.Type.RECOVERY_CODES,
            ).wrap()
            mock_view_codes.return_value = (recovery_wrapper, False)
            response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Recovery codes are hidden")
        self.assertNotContains(response, self.recovery_codes[0])

    @override_settings(MFA_REVEAL_TOKENS=False)
    def test_view_respects_administrator_code_reveal_policy(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, "Your administrator has disabled displaying recovery codes here"
        )
        self.assertNotContains(response, self.recovery_codes[0])


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
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

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

    def test_view_uses_refreshed_authentication_layout(self):
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response,
            'class="auth-challenge-page auth-login-page"',
        )
        self.assertContains(
            response,
            'class="auth-challenge-card auth-login-card"',
        )
        self.assertContains(response, "Sign in to Ghostwriter")
        self.assertContains(response, "Operator access")
        self.assertContains(response, 'name="login"')
        self.assertContains(response, 'name="password"')
        self.assertContains(
            response,
            reverse("account_reset_password"),
            count=1,
        )
        self.assertContains(response, f'action="{self.uri}"')
        self.assertContains(response, 'id="passkey_login"')
        self.assertContains(response, 'id="mfa_login"')
        self.assertNotContains(response, 'class="col-md-6 offset-md-3"')

    @patch("ghostwriter.context_processors.get_editor_shortcuts_date_config")
    def test_anonymous_view_does_not_load_editor_shortcuts(self, mock_date_config):
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 200)
        mock_date_config.assert_not_called()
        self.assertNotContains(response, 'id="gw-current-date"')
        self.assertNotContains(response, "js/editor_shortcuts.js")

    def test_valid_credentials(self):
        response = self.client.post(
            self.uri, {"login": self.user.username, "password": PASSWORD}
        )
        self.assertEqual(response.status_code, 302)
        self.assertTemplateUsed(response, "account/messages/logged_in.txt")

    def test_invalid_credentials(self):
        response = self.client.post(
            self.uri, {"login": self.user.username, "password": "invalid"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/login.html")
        self.assertContains(response, "We could not sign you in")


class UserLogoutViewTests(TestCase):
    """Collection of tests for :view:`allauth.Logout` and its confirmation."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("account_logout")

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.force_login(self.user)

    def test_view_uses_refreshed_session_confirmation_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "account/logout.html")
        self.assertContains(
            response,
            'class="auth-challenge-page auth-signout-page"',
        )
        self.assertContains(
            response,
            'class="auth-challenge-card auth-signout-card"',
        )
        self.assertContains(response, "Sign out of Ghostwriter")
        self.assertContains(response, self.user.username)
        self.assertContains(response, f'action="{self.uri}"')
        self.assertContains(response, reverse("home:dashboard"))
        self.assertNotContains(response, 'class="col-md-6 offset-md-3"')

    def test_post_ends_authenticated_session(self):
        response = self.client_auth.post(self.uri)

        self.assertEqual(response.status_code, 302)
        self.assertNotIn(SESSION_KEY, self.client_auth.session)


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
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_mfa_required(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        self.user.require_mfa = True
        self.user.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        self.assertRedirects(
            response,
            self.setup_uri,
            fetch_redirect_response=False,
            target_status_code=302,
        )

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

    def test_mfa_setup_allows_unverified_email(self):
        EmailAddress.objects.filter(user=self.user).delete()
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=False,
            primary=True,
        )

        try:
            validate_can_add_authenticator(self.user)
        except ValidationError as exc:
            self.fail(f"MFA setup should not require email verification: {exc}")

    @override_settings(MFA_ALLOW_UNVERIFIED_EMAIL=False)
    def test_allauth_mfa_guard_blocks_unverified_email_when_disabled(self):
        EmailAddress.objects.filter(user=self.user).delete()
        EmailAddress.objects.create(
            user=self.user,
            email=self.user.email,
            verified=False,
            primary=True,
        )

        self.assertFalse(mfa_app_settings.ALLOW_UNVERIFIED_EMAIL)
        with self.assertRaises(ValidationError):
            validate_can_add_authenticator(self.user)


class AvatarDownloadTest(TestCase):
    """Collection of tests for :view:`users.AvatarDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.username_with_period = UserFactory(username="first.last", password=PASSWORD)
        cls.uri = reverse("users:avatar_download", kwargs={"slug": cls.user.username})
        cls.user_profile = UserProfile.objects.get(user=cls.user)
        cls.missing_user_uri = reverse(
            "users:avatar_download", kwargs={"slug": "missing_user"}
        )
        cls.period_uri = reverse(
            "users:avatar_download", kwargs={"slug": cls.username_with_period.username}
        )

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

        cls.uploaded_image_file = SimpleUploadedFile(
            image_file.name, image_file.read(), content_type="image/png"
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        """Test default behavior downloads file (as_attachment=True)."""
        response = self.client_auth.get(f"{self.uri}")
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            'attachment; filename="default_avatar.png"',
        )
        # Verify security header is present
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

    def test_view_inline_with_view_parameter(self):
        """Test inline viewing with ?view=true parameter."""
        response = self.client_auth.get(f"{self.uri}?view=true")
        self.assertEqual(response.status_code, 200)
        # Should NOT have attachment disposition for inline viewing
        content_disposition = response.get("Content-Disposition")
        if content_disposition:
            self.assertNotIn("attachment", content_disposition)
        # Verify security headers
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")
        self.assertIn("Content-Security-Policy", response)

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
        self.assertRegexpMatches(
            response.get("Content-Disposition"),
            r'^attachment; filename="fake[_0-9a-zA-Z]*\.png"$',
        )
        # Verify security header
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

        if os.path.exists(self.user_profile.avatar.path):
            os.remove(self.user_profile.avatar.path)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            'attachment; filename="default_avatar.png"',
        )

        self.user_profile.avatar = None
        self.user_profile.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            'attachment; filename="default_avatar.png"',
        )


class HideQuickStartViewTests(TestCase):
    """Collection of tests for :view:`users.HideQuickStart`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:hide_quickstart", kwargs={"slug": cls.user.username})
        cls.other_user_uri = reverse(
            "users:hide_quickstart", kwargs={"slug": cls.other_user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

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
