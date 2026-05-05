# Standard Libraries
import logging
from datetime import timedelta

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.models import APIKey, ServicePrincipal, ServiceToken
from ghostwriter.factories import UserFactory

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class UserProfileTokenDisplayTests(TestCase):
    """Tests for token display behavior on the user profile page."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

    def setUp(self):
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_token_tables_style_expiry_dates_and_filter_expired_rows(self):
        soon = timezone.now() + timedelta(days=1)
        later = timezone.now() + timedelta(days=8)
        expired = timezone.now() - timedelta(days=1)
        principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=self.user
        )

        APIKey.objects.create_token(
            user=self.user,
            name="Expiring API Token",
            expiry_date=soon,
        )
        APIKey.objects.create_token(
            user=self.user,
            name="Later API Token",
            expiry_date=later,
        )
        APIKey.objects.create_token(
            user=self.user,
            name="Expired API Token",
            expiry_date=expired,
        )
        ServiceToken.objects.create_token(
            name="Expiring Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=soon,
        )
        ServiceToken.objects.create_token(
            name="Later Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=later,
        )
        ServiceToken.objects.create_token(
            name="Expired Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=expired,
        )

        response = self.client_auth.get(self.uri)

        self.assertContains(response, 'id="api-token-card"')
        self.assertContains(response, 'id="service-token-card"')
        self.assertContains(
            response,
            "API tokens authenticate as your user account and inherit your current Ghostwriter permissions.",
        )
        self.assertContains(
            response,
            "Service tokens authenticate as non-human service principals",
        )
        self.assertContains(response, "use only the permissions assigned to the token")
        self.assertContains(response, 'id="js-hide-expired"')
        self.assertContains(response, 'id="js-hide-expired-service-tokens"')
        self.assertContains(
            response, 'data-expired-token-selector=".js-expired-api-token"'
        )
        self.assertContains(
            response, 'data-expired-token-selector=".js-expired-service-token"'
        )
        self.assertContains(response, 'data-storage-key="profileHideExpiredApiTokens"')
        self.assertContains(
            response, 'data-storage-key="profileHideExpiredServiceTokens"'
        )
        self.assertContains(response, "localStorage.getItem(storageKey)")
        self.assertContains(response, "localStorage.setItem(storageKey")
        self.assertContains(
            response,
            'class="align-middle text-left warning"',
            count=2,
        )
        self.assertContains(response, "Later API Token")
        self.assertContains(response, "Later Service Token")
        self.assertContains(
            response,
            'class="align-middle text-left burned js-expired-token js-expired-api-token"',
        )
        self.assertContains(
            response,
            'class="align-middle text-left burned js-expired-token js-expired-service-token"',
        )
        self.assertContains(response, 'data-revoke-target-preview="Expired API Token"')
        self.assertContains(
            response, 'data-revoke-target-preview="Expired Service Token"'
        )
        self.assertContains(
            response,
            'data-revoke-target-url="/api/ajax/token/revoke/',
        )
        self.assertContains(
            response,
            'data-revoke-target-url="/api/ajax/service-token/revoke/',
        )
        self.assertContains(response, "$(event.relatedTarget)")
        self.assertContains(response, "$modal.data('revoke-target', $target)")
