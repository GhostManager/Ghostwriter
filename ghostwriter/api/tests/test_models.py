# Standard Libraries
import logging
from datetime import timedelta

# Django Imports
from django.contrib.auth.hashers import check_password
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connection, transaction
from django.test import TestCase
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.models import (
    APIKey,
    ServicePrincipal,
    ServiceToken,
    ServiceTokenPermission,
    ServiceTokenPreset,
    UserSession,
)
from ghostwriter.factories import (
    ClientFactory,
    ClientInviteFactory,
    DomainServerConnectionFactory,
    EvidenceFactory,
    HistoryFactory,
    LocalFindingNoteFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectInviteFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportObservationLinkFactory,
    ServerHistoryFactory,
    ServiceTokenFactory,
    UserFactory,
)
from ghostwriter.rolodex.models import Client, Project

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class ApiKeyModelTests(TestCase):
    """Collection of tests for :model:`api.APIKey`."""

    @classmethod
    def setUpTestData(cls):
        cls.yesterday = timezone.now() - timedelta(days=1)
        cls.user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)

    def test_crud(self):
        # Create
        token_obj, token = APIKey.objects.create_token(
            user=self.user, name="Valid Token"
        )
        self.assertTrue(token_obj)
        self.assertTrue(token_obj.identifier)
        self.assertTrue(token.startswith(f"{APIKey.objects.token_prefix}_"))
        self.assertEqual(token_obj.token, "")
        self.assertTrue(token_obj.token_prefix)
        self.assertTrue(token_obj.secret_hash)
        self.assertNotIn(token.split("_", 2)[2], token_obj.secret_hash)
        self.assertTrue(token_obj.is_valid(token))

        # Read
        read = APIKey.objects.get_from_token(token)
        self.assertEqual(read, token_obj)

        # Update
        token_obj.name = "Updated Token"
        token_obj.save()
        updated = APIKey.objects.get(id=token_obj.id)
        self.assertEqual(updated.name, "Updated Token")

        # Delete
        token_obj.delete()
        self.assertFalse(APIKey.objects.all().exists())

    def test_get_usable_keys(self):
        APIKey.objects.all().exists()
        APIKey.objects.create_token(user=self.user, name="Valid Token")
        APIKey.objects.create_token(user=self.user, name="Revoked Token", revoked=True)
        APIKey.objects.create_token(
            user=self.user, name="Expired Token", expiry_date=self.yesterday
        )

        self.assertEqual(APIKey.objects.all().count(), 3)
        self.assertEqual(APIKey.objects.get_usable_keys().count(), 2)

    def test_token_revocation(self):
        token_obj, _ = APIKey.objects.create_token(
            user=self.user, name="Valid Token", revoked=True
        )
        token_obj.revoked = False
        with self.assertRaises(ValidationError):
            token_obj.clean()
            token_obj.save()

    def test_token_expiration(self):
        valid_obj, _ = APIKey.objects.create_token(user=self.user, name="Valid Token")
        expiring_obj, _ = APIKey.objects.create_token(
            user=self.user,
            name="Expiring Token",
            expiry_date=timezone.now() + timedelta(days=1),
        )
        future_obj, _ = APIKey.objects.create_token(
            user=self.user,
            name="Future Token",
            expiry_date=timezone.now() + timedelta(days=8),
        )
        exp_obj, _ = APIKey.objects.create_token(
            user=self.user, name="Expired Token", expiry_date=self.yesterday
        )

        self.assertTrue(exp_obj.has_expired)
        self.assertFalse(valid_obj.has_expired)
        self.assertTrue(expiring_obj.expires_soon)
        self.assertFalse(future_obj.expires_soon)
        self.assertFalse(exp_obj.expires_soon)
        self.assertFalse(valid_obj.expires_soon)

    def test_is_valid(self):
        valid_obj, valid_token = APIKey.objects.create_token(
            user=self.user, name="Valid Token"
        )
        inactive_obj, inactive_token = APIKey.objects.create_token(
            user=self.inactive_user, name="Inactive Token"
        )
        revoked_obj, revoked_token = APIKey.objects.create_token(
            user=self.user,
            name="Revoked Token",
            revoked=True,
            expiry_date=timezone.now() + timedelta(days=5),
        )
        expired_obj, expired_token = APIKey.objects.create_token(
            user=self.user, name="Expired Token", expiry_date=self.yesterday
        )

        self.assertTrue(APIKey.objects.is_valid(valid_token))
        self.assertFalse(APIKey.objects.is_valid(inactive_token))
        self.assertFalse(APIKey.objects.is_valid(revoked_token))
        self.assertFalse(APIKey.objects.is_valid(expired_token))
        self.assertFalse(APIKey.objects.is_valid("GARBAGE"))
        self.assertTrue(valid_obj.is_valid(valid_token))
        self.assertFalse(inactive_obj.is_valid(inactive_token))
        self.assertFalse(revoked_obj.is_valid(revoked_token))
        self.assertFalse(expired_obj.is_valid(expired_token))

    def test_is_valid_rejects_legacy_jwt_even_if_stored_on_token_field(self):
        token_obj, _ = APIKey.objects.create_token(
            user=self.user,
            name="Legacy Token",
            expiry_date=timezone.now() + timedelta(days=5),
        )
        _, legacy_token = utils.generate_jwt(
            self.user,
            exp=timezone.now() + timedelta(days=5),
            token_type=utils.LEGACY_JWT_TYPE,
        )
        token_obj.token = legacy_token
        token_obj.save(update_fields=["token"])

        self.assertEqual(utils.get_jwt_type(legacy_token), utils.LEGACY_JWT_TYPE)
        self.assertFalse(APIKey.objects.is_valid(legacy_token))

    def test_is_valid_rejects_unknown_opaque_token(self):
        self.assertFalse(APIKey.objects.is_valid("gwat_unknown_secret"))

    def test_record_usage_throttles_recent_updates(self):
        token_obj, _ = APIKey.objects.create_token(user=self.user, name="Usage Token")
        first_used_at = timezone.now()
        recent_used_at = first_used_at + timedelta(minutes=1)
        stale_used_at = (
            first_used_at
            + APIKey.objects.last_used_update_interval
            + timedelta(seconds=1)
        )

        self.assertTrue(APIKey.objects.record_usage(token_obj, used_at=first_used_at))
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

        self.assertFalse(APIKey.objects.record_usage(token_obj, used_at=recent_used_at))
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

        self.assertTrue(APIKey.objects.record_usage(token_obj, used_at=stale_used_at))
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, stale_used_at)

    def test_create_token_escapes_control_characters_in_log_name(self):
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("ghostwriter.api.models", level="INFO") as logs:
                APIKey.objects.create_token(
                    user=self.user,
                    name="Unsafe\nToken",
                )
        finally:
            logging.disable(logging.CRITICAL)

        self.assertIn(r"Unsafe\x0aToken", logs.output[0])
        self.assertNotIn("Unsafe\nToken", logs.output[0])


class UserSessionModelTests(TestCase):
    """Collection of tests for revocable login sessions."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

    def test_create_token_tracks_session_identifier(self):
        session, payload, token = UserSession.objects.create_token(self.user)

        self.assertEqual(payload["jti"], str(session.identifier))
        self.assertEqual(utils.get_jwt_type(token), utils.USER_JWT_TYPE)
        self.assertTrue(UserSession.objects.get_valid_from_payload(payload))

    def test_revoked_session_is_not_valid(self):
        session, payload, _ = UserSession.objects.create_token(self.user)

        session.revoke(revoked_by=self.user)

        with self.assertRaises(UserSession.DoesNotExist):
            UserSession.objects.get_valid_from_payload(payload)


class ServiceTokenModelTests(TestCase):
    """Collection of tests for service token models."""

    @classmethod
    def setUpTestData(cls):
        cls.yesterday = timezone.now() - timedelta(days=1)
        cls.user = UserFactory(password=PASSWORD)
        cls.oplog = OplogFactory()
        cls.project = ProjectFactory()
        ProjectAssignmentFactory(project=cls.oplog.project, operator=cls.user)
        ProjectAssignmentFactory(project=cls.project, operator=cls.user)

    def _service_token_project_access_ids(self, token: ServiceToken) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT project_id
                FROM api_service_token_project_access
                WHERE token_id = %s
                ORDER BY project_id
                """,
                [token.id],
            )
            return [row[0] for row in cursor.fetchall()]

    def _service_token_domain_access_ids(self, token: ServiceToken) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT domain_id
                FROM api_service_token_domain_access
                WHERE token_id = %s
                ORDER BY domain_id
                """,
                [token.id],
            )
            return [row[0] for row in cursor.fetchall()]

    def _service_token_static_server_access_ids(
        self, token: ServiceToken
    ) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT server_id
                FROM api_service_token_static_server_access
                WHERE token_id = %s
                ORDER BY server_id
                """,
                [token.id],
            )
            return [row[0] for row in cursor.fetchall()]

    def _service_token_user_access_ids(self, token: ServiceToken) -> list[int]:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT user_id
                FROM api_service_token_user_access
                WHERE token_id = %s
                ORDER BY user_id
                """,
                [token.id],
            )
            return [row[0] for row in cursor.fetchall()]

    def test_create_token(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Oplog Service Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.CREATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.UPDATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.DELETE,
                },
            ],
        )

        self.assertTrue(token.startswith("gwst_"))
        self.assertEqual(token_obj.get_allowed_oplog_id(), self.oplog.id)
        self.assertEqual(token_obj.permissions.count(), 4)
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.OPLOG_RW)
        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertTrue(token_obj.check_secret(token.split("_", 2)[2]))
        self.assertFalse(token_obj.check_secret("incorrect-secret"))

    def test_create_token_escapes_control_characters_in_log_name(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )

        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("ghostwriter.api.models", level="INFO") as logs:
                ServiceToken.objects.create_token(
                    name="Unsafe\r\nToken",
                    created_by=self.user,
                    service_principal=principal,
                )
        finally:
            logging.disable(logging.CRITICAL)

        self.assertIn(r"Unsafe\x0d\x0aToken", logs.output[0])
        self.assertNotIn("Unsafe\r\nToken", logs.output[0])

    def test_service_token_factory_hashes_secret_per_instance(self):
        first_token = ServiceTokenFactory()
        second_token = ServiceTokenFactory()

        self.assertNotEqual(first_token.secret_hash, second_token.secret_hash)
        self.assertTrue(check_password("service-secret", first_token.secret_hash))
        self.assertTrue(check_password("service-secret", second_token.secret_hash))

    def test_oplog_rw_preset_emits_hasura_oplog_scope(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.OPLOG_RW,
            oplog_id=self.oplog.id,
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Oplog Service Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )

        self.assertEqual(token_obj.get_allowed_oplog_id(), self.oplog.id)
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.OPLOG_RW)
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.OPLOG_RW,
                "read_oplog_id": self.oplog.id,
                "create_oplogentry_oplog_id": self.oplog.id,
                "update_oplogentry_oplog_id": self.oplog.id,
                "delete_oplogentry_oplog_id": self.oplog.id,
            },
        )

    def test_permission_builder_requires_scope(self):
        with self.assertRaises(ValueError):
            ServiceToken.build_permissions_for_preset(ServiceTokenPreset.OPLOG_RW)

        with self.assertRaises(ValueError):
            ServiceToken.build_permissions_for_preset(ServiceTokenPreset.PROJECT_READ)

    def test_service_token_permission_validation(self):
        principal = ServicePrincipal.objects.create(
            name="Validation Service", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Validation Token",
            created_by=self.user,
            service_principal=principal,
        )

        invalid_resource = ServiceTokenPermission(
            token=token_obj,
            resource_type="finding",
            resource_id=1,
            action=ServiceTokenPermission.Action.READ,
        )
        with self.assertRaises(ValidationError):
            invalid_resource.full_clean()

        invalid_action = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            resource_id=self.project.id,
            action=ServiceTokenPermission.Action.UPDATE,
        )
        with self.assertRaises(ValidationError):
            invalid_action.full_clean()

        missing_resource_id = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            action=ServiceTokenPermission.Action.READ,
        )
        with self.assertRaises(ValidationError):
            missing_resource_id.full_clean()

        invalid_constraints = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            resource_id=self.project.id,
            action=ServiceTokenPermission.Action.READ,
            constraints=[],
        )
        with self.assertRaises(ValidationError):
            invalid_constraints.full_clean()

        concrete_permission_with_constraints = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            resource_id=self.project.id,
            action=ServiceTokenPermission.Action.READ,
            constraints={"unexpected": True},
        )
        with self.assertRaises(ValidationError):
            concrete_permission_with_constraints.full_clean()

        invalid_scope_value = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            action=ServiceTokenPermission.Action.READ,
            constraints={ServiceTokenPermission.ConstraintKey.SCOPE: "future_scope"},
        )
        with self.assertRaises(ValidationError):
            invalid_scope_value.full_clean()

        all_accessible_projects_with_extra_constraint = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            action=ServiceTokenPermission.Action.READ,
            constraints={
                ServiceTokenPermission.ConstraintKey.SCOPE: (
                    ServiceTokenPermission.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
                ),
                "unexpected": True,
            },
        )
        with self.assertRaises(ValidationError):
            all_accessible_projects_with_extra_constraint.full_clean()

        all_accessible_projects_with_resource_id = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            resource_id=self.project.id,
            action=ServiceTokenPermission.Action.READ,
            constraints={
                ServiceTokenPermission.ConstraintKey.SCOPE: (
                    ServiceTokenPermission.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
                )
            },
        )
        with self.assertRaises(ValidationError):
            all_accessible_projects_with_resource_id.full_clean()

        all_accessible_projects_on_oplog = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.OPLOG,
            action=ServiceTokenPermission.Action.READ,
            constraints={
                ServiceTokenPermission.ConstraintKey.SCOPE: (
                    ServiceTokenPermission.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
                )
            },
        )
        with self.assertRaises(ValidationError):
            all_accessible_projects_on_oplog.full_clean()

        all_accessible_projects = ServiceTokenPermission(
            token=token_obj,
            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
            action=ServiceTokenPermission.Action.READ,
            constraints={
                ServiceTokenPermission.ConstraintKey.SCOPE: (
                    ServiceTokenPermission.ConstraintScope.ALL_ACCESSIBLE_PROJECTS
                )
            },
        )
        all_accessible_projects.full_clean()

    def test_service_token_permission_save_validates(self):
        principal = ServicePrincipal.objects.create(
            name="Validation Service", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Validation Token",
            created_by=self.user,
            service_principal=principal,
        )
        with self.assertRaises(ValidationError):
            ServiceTokenPermission.objects.create(
                token=token_obj,
                resource_type=ServiceTokenPermission.ResourceType.PROJECT,
                resource_id=self.project.id,
                action=ServiceTokenPermission.Action.DELETE,
            )
        self.assertEqual(token_obj.permissions.count(), 0)

    def test_service_token_permission_db_constraints_reject_invalid_dynamic_scope(self):
        principal = ServicePrincipal.objects.create(
            name="Validation Service", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Validation Token",
            created_by=self.user,
            service_principal=principal,
        )

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceTokenPermission.objects.bulk_create(
                    [
                        ServiceTokenPermission(
                            token=token_obj,
                            resource_type=ServiceTokenPermission.ResourceType.PROJECT,
                            action=ServiceTokenPermission.Action.READ,
                            constraints={},
                        )
                    ]
                )

    def test_service_token_permission_db_constraints_reject_duplicate_dynamic_scope(
        self,
    ):
        principal = ServicePrincipal.objects.create(
            name="Validation Service", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Validation Token",
            created_by=self.user,
            service_principal=principal,
        )
        permission_kwargs = {
            "token": token_obj,
            "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
            "action": ServiceTokenPermission.Action.READ,
            "constraints": ServiceTokenPermission.ALL_ACCESSIBLE_PROJECT_CONSTRAINTS,
        }

        ServiceTokenPermission.objects.bulk_create(
            [ServiceTokenPermission(**permission_kwargs)]
        )
        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                ServiceTokenPermission.objects.bulk_create(
                    [ServiceTokenPermission(**permission_kwargs)]
                )

    def test_create_token_validates_permissions(self):
        principal = ServicePrincipal.objects.create(
            name="Validation Service", created_by=self.user
        )
        with self.assertRaises(ValidationError):
            ServiceToken.objects.create_token(
                name="Invalid Permission Token",
                created_by=self.user,
                service_principal=principal,
                permissions=[
                    {
                        "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
                        "resource_id": self.project.id,
                        "action": ServiceTokenPermission.Action.DELETE,
                    }
                ],
            )
        self.assertFalse(
            ServiceToken.objects.filter(name="Invalid Permission Token").exists()
        )

    def test_create_project_read_token(self):
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "project",
                    "resource_id": self.project.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
            ],
        )

        self.assertTrue(token.startswith("gwst_"))
        self.assertEqual(token_obj.get_allowed_project_id(), self.project.id)
        self.assertEqual(token_obj.get_allowed_project_ids(), [self.project.id])
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)
        self.assertEqual(
            token_obj.get_scope_display(), f"Project #{self.project.id} (Read-Only)"
        )
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                self.project.id,
            )
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                self.oplog.project.id,
            )
        )
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.PROJECT_READ,
                "read_oplog_id": None,
                "create_oplogentry_oplog_id": None,
                "update_oplogentry_oplog_id": None,
                "delete_oplogentry_oplog_id": None,
            },
        )

    def test_create_multi_project_read_token(self):
        other_project = ProjectFactory()
        ProjectAssignmentFactory(project=other_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.PROJECT_READ,
            project_ids=[self.project.id, other_project.id],
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Multi-Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )

        self.assertTrue(token.startswith("gwst_"))
        self.assertIsNone(token_obj.get_allowed_project_id())
        self.assertEqual(
            token_obj.get_allowed_project_ids(),
            sorted([self.project.id, other_project.id]),
        )
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)
        self.assertEqual(token_obj.get_scope_display(), "2 Projects (Read-Only)")
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                self.project.id,
            )
        )
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                other_project.id,
            )
        )
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.PROJECT_READ,
                "read_oplog_id": None,
                "create_oplogentry_oplog_id": None,
                "update_oplogentry_oplog_id": None,
                "delete_oplogentry_oplog_id": None,
            },
        )

    def test_create_all_accessible_projects_read_token(self):
        other_project = ProjectFactory()
        ProjectAssignmentFactory(project=other_project, operator=self.user)
        inaccessible_project = ProjectFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.PROJECT_READ,
            all_accessible_projects=True,
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="All Accessible Projects Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )

        self.assertTrue(token.startswith("gwst_"))
        self.assertEqual(token_obj.get_allowed_project_ids(), [])
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)
        self.assertEqual(
            token_obj.get_scope_display(), "All Accessible Projects (Read-Only)"
        )
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                self.project.id,
            )
        )
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                other_project.id,
            )
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                inaccessible_project.id,
            )
        )
        self.assertEqual(
            token_obj.get_current_project_read_ids(),
            sorted([self.oplog.project.id, self.project.id, other_project.id]),
        )
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.PROJECT_READ,
                "read_oplog_id": None,
                "create_oplogentry_oplog_id": None,
                "update_oplogentry_oplog_id": None,
                "delete_oplogentry_oplog_id": None,
            },
        )

    def test_create_client_project_read_token(self):
        client = ClientFactory()
        assigned_project = ProjectFactory(client=client)
        inaccessible_project = ProjectFactory(client=client)
        other_client_project = ProjectFactory()
        ProjectAssignmentFactory(project=assigned_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Client Project Reader", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.PROJECT_READ,
            client_ids=[client.id],
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Client Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )

        self.assertTrue(token.startswith("gwst_"))
        self.assertEqual(token_obj.get_allowed_project_ids(), [])
        self.assertEqual(token_obj.get_allowed_client_ids(), [client.id])
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)
        self.assertEqual(
            token_obj.get_scope_display(), "1 Client's Projects (Read-Only)"
        )
        self.assertEqual(
            token_obj.get_current_project_read_ids(), [assigned_project.id]
        )
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                assigned_project.id,
            )
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                inaccessible_project.id,
            )
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                other_client_project.id,
            )
        )

    def test_all_accessible_projects_read_token_tracks_future_assignments(self):
        future_project = ProjectFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="All Accessible Projects Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                all_accessible_projects=True,
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertNotIn(future_project.id, token_obj.get_current_project_read_ids())

        assignment = ProjectAssignmentFactory(
            project=future_project, operator=self.user
        )
        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertIn(future_project.id, token_obj.get_current_project_read_ids())
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                future_project.id,
            )
        )

        assignment.delete()
        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertNotIn(future_project.id, token_obj.get_current_project_read_ids())
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                future_project.id,
            )
        )

    def test_client_project_read_token_tracks_future_client_invite_projects(self):
        client = ClientFactory()
        current_project = ProjectFactory(client=client)
        outside_project = ProjectFactory()
        ClientInviteFactory(client=client, user=self.user)
        principal = ServicePrincipal.objects.create(
            name="Client Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Client Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                client_ids=[client.id],
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertEqual(token_obj.get_current_project_read_ids(), [current_project.id])
        self.assertNotIn(outside_project.id, token_obj.get_current_project_read_ids())

        future_project = ProjectFactory(client=client)
        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertEqual(
            token_obj.get_current_project_read_ids(),
            sorted([current_project.id, future_project.id]),
        )

    def test_client_project_read_token_does_not_escalate_project_assignment_to_client(
        self,
    ):
        client = ClientFactory()
        assigned_project = ProjectFactory(client=client)
        unassigned_project = ProjectFactory(client=client)
        ProjectAssignmentFactory(project=assigned_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Client Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Client Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                client_ids=[client.id],
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertEqual(
            token_obj.get_current_project_read_ids(), [assigned_project.id]
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                unassigned_project.id,
            )
        )

        ProjectInviteFactory(project=unassigned_project, user=self.user)
        self.assertTrue(ServiceToken.objects.is_valid(token))
        self.assertEqual(
            token_obj.get_current_project_read_ids(),
            sorted([assigned_project.id, unassigned_project.id]),
        )

    def test_selected_client_scope_access_matrix(self):
        client = ClientFactory(name="ClientA")
        projects = [
            ProjectFactory(client=client, codename=f"ClientA Project{index}")
            for index in range(1, 6)
        ]

        def create_client_scope_token(user, name):
            principal = ServicePrincipal.objects.create(name=name, created_by=user)
            return ServiceToken.objects.create_token(
                name=name,
                created_by=user,
                service_principal=principal,
                permissions=ServiceToken.build_permissions_for_preset(
                    ServiceTokenPreset.PROJECT_READ,
                    client_ids=[client.id],
                ),
            )

        assigned_user = UserFactory(password=PASSWORD)
        ProjectAssignmentFactory(project=projects[1], operator=assigned_user)
        assigned_token, _ = create_client_scope_token(
            assigned_user, "Assigned User Client Token"
        )
        self.assertIn(client, Client.for_user(assigned_user))
        self.assertEqual(
            list(Project.for_user(assigned_user)),
            [projects[1]],
        )
        self.assertEqual(
            self._service_token_project_access_ids(assigned_token),
            [projects[1].id],
        )

        client_invited_user = UserFactory(password=PASSWORD)
        ClientInviteFactory(client=client, user=client_invited_user)
        client_invited_token, _ = create_client_scope_token(
            client_invited_user, "Client Invited User Client Token"
        )
        self.assertIn(client, Client.for_user(client_invited_user))
        self.assertEqual(
            self._service_token_project_access_ids(client_invited_token),
            sorted(project.id for project in projects),
        )

        project_invited_user = UserFactory(password=PASSWORD)
        project_invite = ProjectInviteFactory(
            project=projects[1], user=project_invited_user
        )
        project_invited_token, project_invited_token_value = create_client_scope_token(
            project_invited_user, "Project Invited User Client Token"
        )
        self.assertIn(client, Client.for_user(project_invited_user))
        self.assertEqual(
            list(Project.for_user(project_invited_user)),
            [projects[1]],
        )
        self.assertEqual(
            self._service_token_project_access_ids(project_invited_token),
            [projects[1].id],
        )

        project_invite.delete()
        self.assertEqual(
            list(Client.for_user(project_invited_user)),
            [],
        )
        self.assertEqual(
            self._service_token_project_access_ids(project_invited_token),
            [],
        )
        self.assertFalse(ServiceToken.objects.is_valid(project_invited_token_value))
        project_invited_token.refresh_from_db()
        self.assertTrue(project_invited_token.revoked)

    def test_project_read_scope_types_follow_user_project_access_matrix(self):
        client = ClientFactory(name="ClientA")
        projects = [
            ProjectFactory(client=client, codename=f"ClientA Project{index}")
            for index in range(1, 6)
        ]
        project_ids = [project.id for project in projects]
        project_two = projects[1]

        def create_token(user, name, permissions):
            principal = ServicePrincipal.objects.create(name=name, created_by=user)
            token_obj, token = ServiceToken.objects.create_token(
                name=name,
                created_by=user,
                service_principal=principal,
                permissions=permissions,
            )
            return token_obj, token

        def create_selected_projects_token(user, name):
            return create_token(
                user,
                name,
                ServiceToken.build_permissions_for_preset(
                    ServiceTokenPreset.PROJECT_READ,
                    project_ids=project_ids,
                ),
            )

        def create_selected_client_token(user, name):
            return create_token(
                user,
                name,
                ServiceToken.build_permissions_for_preset(
                    ServiceTokenPreset.PROJECT_READ,
                    client_ids=[client.id],
                ),
            )

        def create_all_accessible_token(user, name):
            return create_token(
                user,
                name,
                ServiceToken.build_permissions_for_preset(
                    ServiceTokenPreset.PROJECT_READ,
                    all_accessible_projects=True,
                ),
            )

        scenarios = []

        assigned_user = UserFactory(password=PASSWORD)
        ProjectAssignmentFactory(project=project_two, operator=assigned_user)
        scenarios.append((assigned_user, [project_two.id], "assigned"))

        project_invited_user = UserFactory(password=PASSWORD)
        project_invite = ProjectInviteFactory(
            project=project_two, user=project_invited_user
        )
        scenarios.append((project_invited_user, [project_two.id], "project-invited"))

        client_invited_user = UserFactory(password=PASSWORD)
        ClientInviteFactory(client=client, user=client_invited_user)
        scenarios.append((client_invited_user, sorted(project_ids), "client-invited"))

        for user, expected_project_ids, label in scenarios:
            with self.subTest(access=label):
                selected_projects_token, _ = create_selected_projects_token(
                    user, f"{label} Selected Projects"
                )
                selected_client_token, _ = create_selected_client_token(
                    user, f"{label} Selected Client"
                )
                all_accessible_token, _ = create_all_accessible_token(
                    user, f"{label} All Accessible"
                )

                self.assertEqual(
                    self._service_token_project_access_ids(selected_projects_token),
                    expected_project_ids,
                )
                self.assertEqual(
                    self._service_token_project_access_ids(selected_client_token),
                    expected_project_ids,
                )
                self.assertEqual(
                    self._service_token_project_access_ids(all_accessible_token),
                    expected_project_ids,
                )
                self.assertEqual(
                    selected_projects_token.get_current_project_read_ids(),
                    expected_project_ids,
                )
                self.assertEqual(
                    selected_client_token.get_current_project_read_ids(),
                    expected_project_ids,
                )
                self.assertEqual(
                    all_accessible_token.get_current_project_read_ids(),
                    expected_project_ids,
                )

        project_invite.delete()
        (
            no_access_selected_projects_token,
            no_access_selected_projects_value,
        ) = create_selected_projects_token(
            project_invited_user, "No Access Selected Projects"
        )
        (
            no_access_selected_client_token,
            no_access_selected_client_value,
        ) = create_selected_client_token(
            project_invited_user, "No Access Selected Client"
        )
        (
            no_access_all_accessible_token,
            no_access_all_accessible_value,
        ) = create_all_accessible_token(
            project_invited_user, "No Access All Accessible"
        )

        self.assertEqual(
            self._service_token_project_access_ids(no_access_selected_projects_token),
            [],
        )
        self.assertEqual(
            self._service_token_project_access_ids(no_access_selected_client_token),
            [],
        )
        self.assertEqual(
            self._service_token_project_access_ids(no_access_all_accessible_token),
            [],
        )
        self.assertFalse(
            ServiceToken.objects.is_valid(no_access_selected_projects_value)
        )
        self.assertFalse(ServiceToken.objects.is_valid(no_access_selected_client_value))
        self.assertTrue(ServiceToken.objects.is_valid(no_access_all_accessible_value))

    def test_selected_project_helpers_deny_stale_project_without_validation(self):
        project = ProjectFactory()
        assignment = ProjectAssignmentFactory(project=project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=project.id,
            ),
        )

        self.assertEqual(token_obj.get_current_project_read_ids(), [project.id])
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                project.id,
            )
        )

        assignment.delete()

        self.assertEqual(token_obj.get_allowed_project_ids(), [project.id])
        self.assertEqual(token_obj.get_current_project_read_ids(), [])
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                project.id,
            )
        )
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.revoked)

    def test_multi_project_helpers_deny_only_stale_project_without_validation(self):
        project = ProjectFactory()
        stale_project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
        stale_assignment = ProjectAssignmentFactory(
            project=stale_project, operator=self.user
        )
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Multi-Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[project.id, stale_project.id],
            ),
        )

        stale_assignment.delete()

        self.assertEqual(
            token_obj.get_allowed_project_ids(),
            sorted([project.id, stale_project.id]),
        )
        self.assertEqual(token_obj.get_current_project_read_ids(), [project.id])
        self.assertTrue(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                project.id,
            )
        )
        self.assertFalse(
            token_obj.has_permission(
                ServiceTokenPermission.ResourceType.PROJECT,
                ServiceTokenPermission.Action.READ,
                stale_project.id,
            )
        )
        self.assertTrue(
            token_obj.permissions.filter(
                resource_type=ServiceTokenPermission.ResourceType.PROJECT,
                action=ServiceTokenPermission.Action.READ,
                resource_id=stale_project.id,
            ).exists()
        )

    def test_service_token_project_access_view_filters_selected_projects_by_current_creator_access(
        self,
    ):
        stale_project = ProjectFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Selected Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[self.project.id, stale_project.id],
            ),
        )

        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            [self.project.id],
        )

    def test_service_token_project_access_view_tracks_all_accessible_projects(self):
        future_project = ProjectFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="All Accessible Projects Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                all_accessible_projects=True,
            ),
        )

        self.assertNotIn(
            future_project.id,
            self._service_token_project_access_ids(token_obj),
        )

        ProjectAssignmentFactory(project=future_project, operator=self.user)
        self.assertIn(
            future_project.id,
            self._service_token_project_access_ids(token_obj),
        )

    def test_service_token_project_access_view_tracks_selected_clients(self):
        client = ClientFactory()
        assigned_project = ProjectFactory(client=client)
        unassigned_project = ProjectFactory(client=client)
        other_client_project = ProjectFactory()
        ProjectAssignmentFactory(project=assigned_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Client Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Selected Client Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                client_ids=[client.id],
            ),
        )

        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            [assigned_project.id],
        )
        self.assertNotIn(
            unassigned_project.id,
            self._service_token_project_access_ids(token_obj),
        )
        self.assertNotIn(
            other_client_project.id,
            self._service_token_project_access_ids(token_obj),
        )

    def test_service_token_project_access_view_tracks_selected_client_future_access(
        self,
    ):
        client = ClientFactory()
        current_project = ProjectFactory(client=client)
        ClientInviteFactory(client=client, user=self.user)
        principal = ServicePrincipal.objects.create(
            name="Client Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Selected Client Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                client_ids=[client.id],
            ),
        )

        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            [current_project.id],
        )

        future_project = ProjectFactory(client=client)
        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            sorted([current_project.id, future_project.id]),
        )

    def test_service_token_project_access_view_tracks_client_invite_access(self):
        invited_project = ProjectFactory()
        ClientInviteFactory(client=invited_project.client, user=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Client Invite Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=invited_project.id,
            ),
        )

        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            [invited_project.id],
        )

    def test_service_token_project_access_view_tracks_privileged_user_access(self):
        manager = UserFactory(password=PASSWORD, role="manager")
        visible_project = ProjectFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=manager
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Privileged Project Read Token",
            created_by=manager,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                all_accessible_projects=True,
            ),
        )

        self.assertIn(
            visible_project.id,
            self._service_token_project_access_ids(token_obj),
        )

    def test_service_token_domain_access_view_tracks_scoped_infrastructure(self):
        direct_checkout = HistoryFactory(project=self.project)
        connected_checkout = HistoryFactory()
        DomainServerConnectionFactory(project=self.project, domain=connected_checkout)
        out_of_scope_checkout = HistoryFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Selected Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[self.project.id],
            ),
        )

        self.assertEqual(
            self._service_token_domain_access_ids(token_obj),
            sorted([direct_checkout.domain_id, connected_checkout.domain_id]),
        )
        self.assertNotIn(
            out_of_scope_checkout.domain_id,
            self._service_token_domain_access_ids(token_obj),
        )

    def test_service_token_static_server_access_view_tracks_scoped_infrastructure(
        self,
    ):
        direct_checkout = ServerHistoryFactory(project=self.project)
        connected_checkout = ServerHistoryFactory()
        DomainServerConnectionFactory(
            project=self.project,
            static_server=connected_checkout,
        )
        out_of_scope_checkout = ServerHistoryFactory()
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Selected Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[self.project.id],
            ),
        )

        self.assertEqual(
            self._service_token_static_server_access_ids(token_obj),
            sorted([direct_checkout.server_id, connected_checkout.server_id]),
        )
        self.assertNotIn(
            out_of_scope_checkout.server_id,
            self._service_token_static_server_access_ids(token_obj),
        )

    def test_service_token_project_access_view_excludes_inactive_creator_tokens(self):
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            ),
        )

        self.assertEqual(
            self._service_token_project_access_ids(token_obj),
            [self.project.id],
        )
        self.user.is_active = False
        self.user.save()

        self.assertEqual(self._service_token_project_access_ids(token_obj), [])

    def test_service_token_user_access_view_tracks_project_read_access(self):
        assigned_user = UserFactory(password=PASSWORD)
        invited_user = UserFactory(password=PASSWORD)
        client_invited_user = UserFactory(password=PASSWORD)
        inaccessible_user = UserFactory(password=PASSWORD)
        ProjectAssignmentFactory(project=self.project, operator=assigned_user)
        ProjectInviteFactory(project=self.project, user=invited_user)
        ClientInviteFactory(client=self.project.client, user=client_invited_user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            ),
        )

        user_access_ids = self._service_token_user_access_ids(token_obj)

        self.assertIn(self.user.id, user_access_ids)
        self.assertIn(self.project.operator_id, user_access_ids)
        self.assertIn(assigned_user.id, user_access_ids)
        self.assertNotIn(invited_user.id, user_access_ids)
        self.assertNotIn(client_invited_user.id, user_access_ids)
        self.assertNotIn(inaccessible_user.id, user_access_ids)

    def test_service_token_user_access_view_tracks_report_user_relationships(self):
        report_creator = UserFactory(password=PASSWORD)
        evidence_uploader = UserFactory(password=PASSWORD)
        finding_assignee = UserFactory(password=PASSWORD)
        finding_note_operator = UserFactory(password=PASSWORD)
        observation_assignee = UserFactory(password=PASSWORD)
        inaccessible_user = UserFactory(password=PASSWORD)
        report = ReportFactory(project=self.project, created_by=report_creator)
        EvidenceFactory(report=report, uploaded_by=evidence_uploader)
        finding = ReportFindingLinkFactory(
            report=report,
            assigned_to=finding_assignee,
        )
        LocalFindingNoteFactory(finding=finding, operator=finding_note_operator)
        ReportObservationLinkFactory(
            report=report,
            assigned_to=observation_assignee,
        )
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            ),
        )

        user_access_ids = self._service_token_user_access_ids(token_obj)

        self.assertIn(report_creator.id, user_access_ids)
        self.assertIn(evidence_uploader.id, user_access_ids)
        self.assertIn(finding_assignee.id, user_access_ids)
        self.assertIn(finding_note_operator.id, user_access_ids)
        self.assertIn(observation_assignee.id, user_access_ids)
        self.assertNotIn(inaccessible_user.id, user_access_ids)

    def test_service_token_user_access_view_does_not_expand_to_privileged_users(self):
        manager = UserFactory(password=PASSWORD, role="manager")
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            ),
        )

        self.assertNotIn(manager.id, self._service_token_user_access_ids(token_obj))

    def test_oplog_service_token_has_no_project_user_access(self):
        principal = ServicePrincipal.objects.create(
            name="Oplog Reader", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Oplog Service Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.OPLOG_RW,
                oplog_id=self.oplog.id,
            ),
        )

        self.assertEqual(self._service_token_user_access_ids(token_obj), [])

    def test_inactive_creator_revokes_service_tokens_and_deactivates_principals(self):
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            ),
        )

        self.user.is_active = False
        self.user.save()

        self.assertFalse(ServiceToken.objects.is_valid(token))
        token_obj.refresh_from_db()
        principal.refresh_from_db()
        self.assertTrue(token_obj.revoked)
        self.assertFalse(principal.active)

    def test_selected_project_access_loss_revokes_service_token(self):
        project = ProjectFactory()
        assignment = ProjectAssignmentFactory(project=project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=project.id,
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        assignment.delete()

        self.assertFalse(ServiceToken.objects.is_valid(token))
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.revoked)

    def test_multi_project_access_loss_prunes_inaccessible_project(self):
        project = ProjectFactory()
        stale_project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
        stale_assignment = ProjectAssignmentFactory(
            project=stale_project, operator=self.user
        )
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Multi-Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_ids=[project.id, stale_project.id],
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        stale_assignment.delete()

        self.assertTrue(ServiceToken.objects.is_valid(token))
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.revoked)
        self.assertEqual(token_obj.get_allowed_project_ids(), [project.id])
        self.assertFalse(
            token_obj.permissions.filter(
                resource_type=ServiceTokenPermission.ResourceType.PROJECT,
                action=ServiceTokenPermission.Action.READ,
                resource_id=stale_project.id,
            ).exists()
        )

    def test_retracted_project_invite_revokes_selected_project_token(self):
        project = ProjectFactory()
        invite = ProjectInviteFactory(project=project, user=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=project.id,
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        invite.delete()

        self.assertFalse(ServiceToken.objects.is_valid(token))
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.revoked)

    def test_oplog_access_loss_revokes_service_token(self):
        oplog = OplogFactory()
        assignment = ProjectAssignmentFactory(project=oplog.project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Activity Log Service", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Activity Log Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.OPLOG_RW,
                oplog_id=oplog.id,
            ),
        )

        self.assertTrue(ServiceToken.objects.is_valid(token))
        assignment.delete()

        self.assertFalse(ServiceToken.objects.is_valid(token))
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.revoked)

    def test_oplog_read_permission_only_emits_read_hasura_scope(self):
        principal = ServicePrincipal.objects.create(
            name="Read-Only Oplog", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Read-Only Oplog Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
            ],
        )

        self.assertEqual(token_obj.get_allowed_oplog_id(), self.oplog.id)
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.CUSTOM)
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.CUSTOM,
                "read_oplog_id": self.oplog.id,
                "create_oplogentry_oplog_id": None,
                "update_oplogentry_oplog_id": None,
                "delete_oplogentry_oplog_id": None,
            },
        )

    def test_mixed_single_resource_permissions_emit_action_specific_hasura_scope(self):
        principal = ServicePrincipal.objects.create(
            name="Mixed Scope Service", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.OPLOG_RW,
            oplog_id=self.oplog.id,
        )
        permissions.extend(
            ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=self.project.id,
            )
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Mixed Scope Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )

        self.assertEqual(token_obj.get_allowed_oplog_id(), self.oplog.id)
        self.assertEqual(token_obj.get_allowed_project_id(), self.project.id)
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.CUSTOM)
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.CUSTOM,
                "read_oplog_id": self.oplog.id,
                "create_oplogentry_oplog_id": self.oplog.id,
                "update_oplogentry_oplog_id": self.oplog.id,
                "delete_oplogentry_oplog_id": self.oplog.id,
            },
        )

    def test_split_scope_does_not_match_oplog_rw_preset(self):
        other_oplog = OplogFactory()
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Split Oplog Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": self.oplog.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": other_oplog.id,
                    "action": ServiceTokenPermission.Action.CREATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": other_oplog.id,
                    "action": ServiceTokenPermission.Action.UPDATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": other_oplog.id,
                    "action": ServiceTokenPermission.Action.DELETE,
                },
            ],
        )

        self.assertIsNone(token_obj.get_allowed_oplog_id())
        self.assertEqual(token_obj.get_token_preset(), ServiceTokenPreset.CUSTOM)
        self.assertEqual(
            token_obj.get_hasura_scope(),
            {
                "preset": ServiceTokenPreset.CUSTOM,
                "read_oplog_id": self.oplog.id,
                "create_oplogentry_oplog_id": other_oplog.id,
                "update_oplogentry_oplog_id": other_oplog.id,
                "delete_oplogentry_oplog_id": other_oplog.id,
            },
        )

    def test_service_token_revocation(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Oplog Service Token",
            created_by=self.user,
            service_principal=principal,
            revoked=True,
        )
        token_obj.revoked = False
        with self.assertRaises(ValidationError):
            token_obj.clean()
            token_obj.save()

    def test_revoke_token_log_sanitizes_reason_control_characters(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Oplog Service Token",
            created_by=self.user,
            service_principal=principal,
        )

        previous_disable_level = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("ghostwriter.api.models", level="WARNING") as logs:
                ServiceToken.objects.revoke_token(
                    token_obj,
                    reason="scope failed\nforged line\rwith tab\tand null\x00",
                )
        finally:
            logging.disable(previous_disable_level)

        message = logs.output[0]
        self.assertIn(
            r"scope failed\x0aforged line\x0dwith tab\x09and null\x00",
            message,
        )
        self.assertNotIn("\nforged line", message)
        self.assertNotIn("\rwith tab", message)

    def test_service_token_management_logs_sanitize_reason_control_characters(self):
        inactive_user = UserFactory(password=PASSWORD)
        inactive_user_principal = ServicePrincipal.objects.create(
            name="Inactive User Principal", created_by=inactive_user
        )
        ServiceToken.objects.create_token(
            name="Inactive User Token",
            created_by=inactive_user,
            service_principal=inactive_user_principal,
        )
        revoke_principal = ServicePrincipal.objects.create(
            name="Revoke Principal", created_by=self.user
        )
        ServiceToken.objects.create_token(
            name="Principal Token",
            created_by=self.user,
            service_principal=revoke_principal,
        )
        deactivate_principal = ServicePrincipal.objects.create(
            name="Deactivate Principal", created_by=self.user
        )
        reason = "owner disabled\nforged line\rwith tab\tand null\x00"

        previous_disable_level = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("ghostwriter.api.models", level="WARNING") as logs:
                ServiceToken.objects.revoke_tokens_for_inactive_user(
                    inactive_user,
                    reason=reason,
                )
                ServiceToken.objects.revoke_tokens_for_service_principal(
                    revoke_principal,
                    reason=reason,
                )
                ServiceToken.objects.deactivate_service_principal(
                    deactivate_principal,
                    reason=reason,
                )
        finally:
            logging.disable(previous_disable_level)

        self.assertGreaterEqual(len(logs.output), 3)
        for message in logs.output:
            self.assertIn(
                r"owner disabled\x0aforged line\x0dwith tab\x09and null\x00",
                message,
            )
            self.assertNotIn("\nforged line", message)
            self.assertNotIn("\rwith tab", message)

    def test_service_token_expiration(self):
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        valid_obj, valid_token = ServiceToken.objects.create_token(
            name="Valid Service Token",
            created_by=self.user,
            service_principal=principal,
        )
        expiring_obj, _ = ServiceToken.objects.create_token(
            name="Expiring Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=timezone.now() + timedelta(days=1),
        )
        future_obj, _ = ServiceToken.objects.create_token(
            name="Future Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=timezone.now() + timedelta(days=8),
        )
        expired_obj, expired_token = ServiceToken.objects.create_token(
            name="Expired Service Token",
            created_by=self.user,
            service_principal=principal,
            expiry_date=self.yesterday,
        )

        self.assertTrue(ServiceToken.objects.is_valid(valid_token))
        self.assertFalse(ServiceToken.objects.is_valid(expired_token))
        self.assertTrue(expired_obj.has_expired)
        self.assertFalse(valid_obj.has_expired)
        self.assertTrue(expiring_obj.expires_soon)
        self.assertFalse(future_obj.expires_soon)
        self.assertFalse(expired_obj.expires_soon)
        self.assertFalse(valid_obj.expires_soon)

    def test_record_usage_throttles_recent_updates(self):
        principal = ServicePrincipal.objects.create(
            name="Usage Service", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Usage Token",
            created_by=self.user,
            service_principal=principal,
        )
        first_used_at = timezone.now()
        recent_used_at = first_used_at + timedelta(minutes=1)
        stale_used_at = (
            first_used_at
            + ServiceToken.objects.last_used_update_interval
            + timedelta(seconds=1)
        )

        self.assertTrue(
            ServiceToken.objects.record_usage(token_obj, used_at=first_used_at)
        )
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

        self.assertFalse(
            ServiceToken.objects.record_usage(token_obj, used_at=recent_used_at)
        )
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

        self.assertTrue(
            ServiceToken.objects.record_usage(token_obj, used_at=stale_used_at)
        )
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, stale_used_at)
