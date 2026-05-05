# Standard Libraries
import logging

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.api.models import ServicePrincipal, ServiceToken
from ghostwriter.factories import AdminFactory, OplogFactory, UserFactory

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


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
