# Standard Libraries
import logging

# Django Imports
from django.contrib import admin
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.api.models import APIKey, ServicePrincipal, ServiceToken, UserSession
from ghostwriter.factories import AdminFactory, OplogFactory, UserFactory

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class APIKeyAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = AdminFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.assertTrue(
            self.client.login(username=self.admin_user.username, password=PASSWORD)
        )

    def test_admin_does_not_expose_legacy_token_field(self):
        model_admin = admin.site._registry[APIKey]

        self.assertNotIn("token", model_admin.readonly_fields)

    def test_admin_cannot_create_api_tokens(self):
        model_admin = admin.site._registry[APIKey]

        self.assertFalse(model_admin.has_add_permission(None))

        response = self.client.get(reverse("admin:api_apikey_add"))

        self.assertEqual(response.status_code, 403)


class ServiceTokenAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = AdminFactory(password=PASSWORD)
        cls.creator = UserFactory(password=PASSWORD)
        cls.oplog = OplogFactory()
        cls.principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=cls.creator
        )
        cls.token_obj, cls.token = ServiceToken.objects.create_token(
            name="Admin Managed Service Token",
            created_by=cls.creator,
            service_principal=cls.principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": cls.oplog.id,
                    "action": "read",
                },
                {
                    "resource_type": "oplog",
                    "resource_id": cls.oplog.id,
                    "action": "create",
                },
                {
                    "resource_type": "oplog",
                    "resource_id": cls.oplog.id,
                    "action": "update",
                },
                {
                    "resource_type": "oplog",
                    "resource_id": cls.oplog.id,
                    "action": "delete",
                },
            ],
        )
        cls.changelist_uri = reverse("admin:api_servicetoken_changelist")

    def setUp(self):
        self.client = Client()
        self.assertTrue(
            self.client.login(username=self.admin_user.username, password=PASSWORD)
        )

    def test_admin_action_revokes_service_token(self):
        response = self.client.post(
            self.changelist_uri,
            {
                "action": "revoke_tokens",
                "_selected_action": [self.token_obj.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.token_obj.refresh_from_db()
        self.assertTrue(self.token_obj.revoked)

    def test_admin_cannot_create_service_principals(self):
        model_admin = admin.site._registry[ServicePrincipal]

        self.assertFalse(model_admin.has_add_permission(None))

        response = self.client.get(reverse("admin:api_serviceprincipal_add"))

        self.assertEqual(response.status_code, 403)

    def test_admin_cannot_create_service_tokens(self):
        model_admin = admin.site._registry[ServiceToken]

        self.assertFalse(model_admin.has_add_permission(None))

        response = self.client.get(reverse("admin:api_servicetoken_add"))

        self.assertEqual(response.status_code, 403)


class UserSessionAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin_user = AdminFactory(password=PASSWORD)
        cls.user = UserFactory(password=PASSWORD)
        cls.session, _, _ = UserSession.objects.create_token(cls.user)
        cls.changelist_uri = reverse("admin:api_usersession_changelist")

    def setUp(self):
        self.client = Client()
        self.assertTrue(
            self.client.login(username=self.admin_user.username, password=PASSWORD)
        )

    def test_admin_action_revokes_user_session(self):
        response = self.client.post(
            self.changelist_uri,
            {
                "action": "revoke_sessions",
                "_selected_action": [self.session.pk],
            },
            follow=True,
        )
        self.assertEqual(response.status_code, 200)
        self.session.refresh_from_db()
        self.assertTrue(self.session.revoked_at)
        self.assertEqual(self.session.revoked_by, self.admin_user)
