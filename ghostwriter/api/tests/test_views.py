# Standard Libraries
import base64
import json
import logging
import os
from datetime import date, datetime, timedelta
from http import HTTPStatus

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.contrib.messages import get_messages
from django.core.files.base import ContentFile
from django.http import JsonResponse
from django.test import Client, RequestFactory, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str

# 3rd Party Libraries
import factory
from allauth.mfa.models import Authenticator
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.models import (
    APIKey,
    ServicePrincipal,
    ServiceToken,
    ServiceTokenPermission,
    ServiceTokenPreset,
    ServiceTokenProjectScope,
    UserSession,
)
from ghostwriter.api.views import HasuraActionView, JwtRequiredMixin
from ghostwriter.factories import (
    ActivityTypeFactory,
    BlankReportFindingLinkFactory,
    ClientFactory,
    DomainFactory,
    DomainStatusFactory,
    EvidenceOnFindingFactory,
    EvidenceOnReportFactory,
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
    FindingFactory,
    HistoryFactory,
    OplogEntryFactory,
    OplogEntryRecordingFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectContactFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ProjectSubtaskFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportTemplateFactory,
    ServerHistoryFactory,
    ServerRoleFactory,
    ServerStatusFactory,
    SeverityFactory,
    StaticServerFactory,
    UserFactory,
)
from ghostwriter.oplog.utils import (
    CAST_GZIP_TOO_LARGE_UPLOAD_MESSAGE,
    get_cast_decompressed_bytes,
)
from ghostwriter.reporting.models import Evidence

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"

ACTION_SECRET = settings.HASURA_ACTION_SECRET

User = get_user_model()


def generate_user_jwt(user):
    return UserSession.objects.create_token(user)[1:]


def create_project_read_service_token(user, project):
    ProjectAssignmentFactory(project=project, operator=user)
    service_principal = ServicePrincipal.objects.create(
        name=f"Project Reader {project.pk}",
        created_by=user,
    )
    _, token = ServiceToken.objects.create_token(
        name=f"Project Read {project.pk}",
        created_by=user,
        service_principal=service_principal,
        permissions=ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.PROJECT_READ,
            project_id=project.id,
        ),
    )
    return token


def create_oplog_read_service_token(user, oplog):
    ProjectAssignmentFactory(project=oplog.project, operator=user)
    service_principal = ServicePrincipal.objects.create(
        name=f"Oplog Reader {oplog.pk}",
        created_by=user,
    )
    _, token = ServiceToken.objects.create_token(
        name=f"Oplog Read {oplog.pk}",
        created_by=user,
        service_principal=service_principal,
        permissions=[
            {
                "resource_type": ServiceTokenPermission.ResourceType.OPLOG,
                "resource_id": oplog.id,
                "action": ServiceTokenPermission.Action.READ,
            }
        ],
    )
    return token


def create_oplog_rw_service_token(user, oplog):
    ProjectAssignmentFactory(project=oplog.project, operator=user)
    service_principal = ServicePrincipal.objects.create(
        name=f"Oplog Writer {oplog.pk}",
        created_by=user,
    )
    _, token = ServiceToken.objects.create_token(
        name=f"Oplog Read/Write {oplog.pk}",
        created_by=user,
        service_principal=service_principal,
        permissions=ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.OPLOG_RW,
            oplog_id=oplog.id,
        ),
    )
    return token


# Tests related to authentication in custom CBVs


class HasuraViewTests(TestCase):
    """
    Collection of tests for :view:`api:HasuraView` and
    :view:`api:HasuraActionView` custom CBVs.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)
        cls.uri = reverse("api:graphql_test")
        # Create valid and invalid JWTs for testing
        yesterday = timezone.now() - timedelta(days=1)
        cls.user_token_obj, cls.user_token = APIKey.objects.create_token(
            user=cls.user, name="Valid Token"
        )
        cls.inactive_token_obj, cls.inactive_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Inactive User Token"
        )
        cls.expired_token_obj, cls.expired_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Expired Token", expiry_date=yesterday
        )
        cls.revoked_token_obj, cls.revoked_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Revoked Token", revoked=True
        )
        cls.project = ProjectFactory()
        cls.other_project = ProjectFactory()
        ProjectAssignmentFactory(project=cls.project, operator=cls.user)
        ProjectAssignmentFactory(project=cls.other_project, operator=cls.user)
        cls.service_principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=cls.user
        )
        cls.service_token_obj, cls.service_token = ServiceToken.objects.create_token(
            name="Project Read Service Token",
            created_by=cls.user,
            service_principal=cls.service_principal,
            permissions=[
                {
                    "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
                    "resource_id": cls.project.id,
                    "action": ServiceTokenPermission.Action.READ,
                }
            ],
        )
        # Test data set as required inputs for the test view
        cls.data = {
            "input": {"id": 1, "function": "test_func", "args": {"arg1": "test"}}
        }

    def setUp(self):
        self.client = Client()
        self.request_factory = RequestFactory()

    def test_action_with_valid_jwt(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_action_rejects_revoked_user_session_jwt(self):
        session, _, token = UserSession.objects.create_token(self.user)
        session.revoke(revoked_by=self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_rejects_legacy_short_lived_user_jwt(self):
        _, token = utils.generate_jwt(self.user, token_type=utils.LEGACY_JWT_TYPE)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_rejects_collab_jwt(self):
        _, token = utils.generate_jwt(self.user, token_type=utils.COLLAB_JWT_TYPE)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_rejects_untracked_long_lived_legacy_jwt(self):
        _, token = utils.generate_jwt(
            self.user,
            exp=timezone.now() + timedelta(days=7),
            token_type=utils.LEGACY_JWT_TYPE,
        )
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_rejects_legacy_stored_api_token(self):
        token_obj, _ = APIKey.objects.create_token(
            user=self.user,
            name="Legacy API Token",
            expiry_date=timezone.now() + timedelta(days=7),
        )
        _, token = utils.generate_jwt(
            self.user,
            exp=timezone.now() + timedelta(days=7),
            token_type=utils.LEGACY_JWT_TYPE,
        )
        token_obj.token = token
        token_obj.save(update_fields=["token"])

        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_expired_api_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.expired_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_revoked_api_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.revoked_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_inactive_user_api_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.inactive_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_requires_correct_secret(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": "wrong",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_action_requires_secret(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 403)
        result = {
            "message": "Unauthorized access method",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_action_requires_all_input(self):
        _, token = generate_user_jwt(self.user)
        # Test with no data
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Missing all required inputs",
            "extensions": {
                "code": "InvalidRequestBody",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)
        # Test with incomplete data
        response = self.client.post(
            self.uri,
            data={
                "input": {
                    "id": 1,
                }
            },
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Missing one or more required inputs",
            "extensions": {
                "code": "InvalidRequestBody",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_action_with_invalid_json_input(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data="Not JSON",
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_action_requires_jwt(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "No ``Authorization`` header found",
            "extensions": {
                "code": "AuthenticationMissing",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_action_with_valid_jwt_and_inactive_user(self):
        _, token = generate_user_jwt(self.user)
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.user.is_active = True
        self.user.save()

    def test_action_with_invalid_jwt(self):
        token = "GARBAGE!"
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_valid_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_action_with_valid_tracked_token_and_inactive_user(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.inactive_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_expired_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.expired_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_revoked_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.revoked_token}",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_service_token_is_denied_by_default(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.service_token}",
            },
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        result = {
            "message": "This service token is not authorized for this action",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_service_token_action_authorization_uses_token_permissions(self):
        class ProjectReadServiceAction(JwtRequiredMixin, HasuraActionView):
            required_inputs = ["projectId"]

            def get_service_token_permission_requirements(self):
                return (
                    {
                        "resource_type": ServiceTokenPermission.ResourceType.PROJECT,
                        "resource_id": self.input["projectId"],
                        "action": ServiceTokenPermission.Action.READ,
                    },
                )

            def post(self, request, *args, **kwargs):
                return JsonResponse({"result": "success"}, status=self.status)

        view = ProjectReadServiceAction.as_view()
        request = self.request_factory.post(
            "/project-read-service-action",
            data=json.dumps({"input": {"projectId": self.project.id}}),
            content_type="application/json",
            HTTP_HASURA_ACTION_SECRET=f"{ACTION_SECRET}",
            HTTP_AUTHORIZATION=f"Bearer {self.service_token}",
        )
        response = view(request)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), {"result": "success"})

        request = self.request_factory.post(
            "/project-read-service-action",
            data=json.dumps({"input": {"projectId": self.other_project.id}}),
            content_type="application/json",
            HTTP_HASURA_ACTION_SECRET=f"{ACTION_SECRET}",
            HTTP_AUTHORIZATION=f"Bearer {self.service_token}",
        )
        response = view(request)
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_service_token_any_project_read_requirement_uses_current_access(self):
        project = ProjectFactory()
        assignment = ProjectAssignmentFactory(project=project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader Current Access", created_by=self.user
        )
        token_obj, _ = ServiceToken.objects.create_token(
            name="Project Read Current Access Token",
            created_by=self.user,
            service_principal=principal,
            permissions=ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=project.id,
            ),
        )
        view = HasuraActionView()
        view.service_token_obj = token_obj

        self.assertTrue(view.service_token_has_project_read_grant())

        assignment.delete()
        view = HasuraActionView()
        view.service_token_obj = token_obj

        self.assertFalse(view.service_token_has_project_read_grant())

    def test_action_with_incomplete_header(self):
        result = {
            "message": "No ``Authorization`` header found",
            "extensions": {
                "code": "AuthenticationMissing",
            },
        }

        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": "",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(force_str(response.content), result)

        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(force_str(response.content), result)


class HasuraEventViewTests(TestCase):
    """Collection of tests for the :view:`api:HasuraEventView` custom CBV."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_event_test")
        cls.data = {
            "event": {
                "data": {
                    "new": {},
                    "old": {},
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_event_with_valid_input(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_action_requires_secret(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)
        result = {
            "message": "Unauthorized access method",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_requires_correct_secret(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": "wrong",
            },
        )
        self.assertEqual(response.status_code, 403)

    def test_with_invalid_json(self):
        response = self.client.post(
            self.uri,
            data="Not JSON",
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Missing event data",
            "extensions": {
                "code": "InvalidRequestBody",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)


# Tests related to the authentication webhook


class HasuraWebhookTests(TestCase):
    """Collection of tests for :view:`api:GraphqlAuthenticationWebhook`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_webhook")
        cls.public_data = {
            "X-Hasura-Role": "public",
            "X-Hasura-User-Id": "-1",
            "X-Hasura-User-Name": "anonymous",
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_webhook_with_valid_jwt(self):
        _, token = generate_user_jwt(self.user)
        data = {
            "X-Hasura-Role": f"{self.user.role}",
            "X-Hasura-User-Id": f"{self.user.id}",
            "X-Hasura-User-Name": f"{self.user.username}",
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_collab_jwt_uses_collab_role(self):
        _, token = utils.generate_jwt(
            self.user,
            token_type=utils.COLLAB_JWT_TYPE,
            extra_claims={
                utils.COLLAB_MODEL_CLAIM: "report_finding_link",
                utils.COLLAB_OBJECT_ID_CLAIM: 101,
                utils.COLLAB_REPORT_ID_CLAIM: 202,
                utils.COLLAB_FINDING_ID_CLAIM: 101,
            },
        )
        data = {
            "X-Hasura-Role": "collab",
            "X-Hasura-User-Id": f"{self.user.id}",
            "X-Hasura-User-Name": f"{self.user.username}",
            "X-Hasura-Collab-Model": "report_finding_link",
            "X-Hasura-Collab-Object-Id": "101",
            "X-Hasura-Collab-Report-Id": "202",
            "X-Hasura-Collab-Finding-Id": "101",
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_defaults_missing_collab_ids_to_negative_one(self):
        _, token = utils.generate_jwt(self.user, token_type=utils.COLLAB_JWT_TYPE)
        data = {
            "X-Hasura-Role": "collab",
            "X-Hasura-User-Id": f"{self.user.id}",
            "X-Hasura-User-Name": f"{self.user.username}",
            "X-Hasura-Collab-Model": "",
            "X-Hasura-Collab-Object-Id": "-1",
            "X-Hasura-Collab-Report-Id": "-1",
            "X-Hasura-Collab-Finding-Id": "-1",
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_valid_service_token(self):
        oplog = OplogFactory()
        ProjectAssignmentFactory(project=oplog.project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Service Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": oplog.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": oplog.id,
                    "action": ServiceTokenPermission.Action.CREATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": oplog.id,
                    "action": ServiceTokenPermission.Action.UPDATE,
                },
                {
                    "resource_type": "oplog",
                    "resource_id": oplog.id,
                    "action": ServiceTokenPermission.Action.DELETE,
                },
            ],
        )
        data = {
            "X-Hasura-Role": "service",
            "X-Hasura-User-Name": principal.name,
            "X-Hasura-Service-Principal-Id": f"{principal.id}",
            "X-Hasura-Service-Token-Id": f"{token_obj.id}",
            "X-Hasura-Read-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Create-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Update-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Delete-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Principal-Type": "service",
            "X-Hasura-Service-Token-Preset": ServiceTokenPreset.OPLOG_RW,
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_throttles_api_token_last_used_at(self):
        token_obj, token = APIKey.objects.create_token(
            user=self.user, name="Usage Token"
        )

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        token_obj.refresh_from_db()
        first_used_at = token_obj.last_used_at
        self.assertIsNotNone(first_used_at)

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

    def test_graphql_webhook_with_project_read_service_token(self):
        project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
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
                    "resource_id": project.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
            ],
        )
        data = {
            "X-Hasura-Role": "service",
            "X-Hasura-User-Name": principal.name,
            "X-Hasura-Service-Principal-Id": f"{principal.id}",
            "X-Hasura-Service-Token-Id": f"{token_obj.id}",
            "X-Hasura-Read-Oplog-Id": "-1",
            "X-Hasura-Create-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Update-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Delete-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Principal-Type": "service",
            "X-Hasura-Service-Token-Preset": ServiceTokenPreset.PROJECT_READ,
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_multi_project_read_service_token(self):
        project = ProjectFactory()
        other_project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
        ProjectAssignmentFactory(project=other_project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Project Reader", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.PROJECT_READ,
            project_ids=[project.id, other_project.id],
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Multi-Project Read Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )
        data = {
            "X-Hasura-Role": "service",
            "X-Hasura-User-Name": principal.name,
            "X-Hasura-Service-Principal-Id": f"{principal.id}",
            "X-Hasura-Service-Token-Id": f"{token_obj.id}",
            "X-Hasura-Read-Oplog-Id": "-1",
            "X-Hasura-Create-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Update-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Delete-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Principal-Type": "service",
            "X-Hasura-Service-Token-Preset": ServiceTokenPreset.PROJECT_READ,
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_all_accessible_project_read_service_token(self):
        project = ProjectFactory()
        future_project = ProjectFactory()
        inaccessible_project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
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

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        first_response_data = json.loads(force_str(response.content))
        self.assertEqual(first_response_data["X-Hasura-Role"], "service")
        self.assertNotIn("X-Hasura-Read-Project-Ids", first_response_data)
        self.assertEqual(token_obj.get_current_project_read_ids(), [project.id])

        ProjectAssignmentFactory(project=future_project, operator=self.user)
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        second_response_data = json.loads(force_str(response.content))
        self.assertNotIn("X-Hasura-Read-Project-Ids", second_response_data)
        self.assertEqual(
            token_obj.get_current_project_read_ids(),
            sorted([project.id, future_project.id]),
        )
        self.assertNotIn(
            inaccessible_project.id,
            token_obj.get_current_project_read_ids(),
        )

    def test_graphql_webhook_throttles_service_token_last_used_at(self):
        project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
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
                    "resource_id": project.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
            ],
        )

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        token_obj.refresh_from_db()
        first_used_at = token_obj.last_used_at
        self.assertIsNotNone(first_used_at)

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        token_obj.refresh_from_db()
        self.assertEqual(token_obj.last_used_at, first_used_at)

    def test_graphql_webhook_revokes_service_token_for_inactive_creator(self):
        project = ProjectFactory()
        ProjectAssignmentFactory(project=project, operator=self.user)
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
        self.user.is_active = False
        self.user.save()

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        token_obj.refresh_from_db()
        principal.refresh_from_db()
        self.assertTrue(token_obj.revoked)
        self.assertFalse(principal.active)

    def test_graphql_webhook_revokes_service_token_for_stale_project_scope(self):
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
        assignment.delete()

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        token_obj.refresh_from_db()
        self.assertTrue(token_obj.revoked)

    def test_graphql_webhook_prunes_stale_project_from_multi_project_scope(self):
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
        stale_assignment.delete()

        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(force_str(response.content))
        self.assertNotIn("X-Hasura-Read-Project-Ids", response_data)
        token_obj.refresh_from_db()
        self.assertFalse(token_obj.revoked)
        self.assertEqual(token_obj.get_allowed_project_ids(), [project.id])

    def test_graphql_webhook_with_oplog_read_service_token_only_emits_read_scope(self):
        oplog = OplogFactory()
        ProjectAssignmentFactory(project=oplog.project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Custom Service", created_by=self.user
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Read-Only Oplog Token",
            created_by=self.user,
            service_principal=principal,
            permissions=[
                {
                    "resource_type": "oplog",
                    "resource_id": oplog.id,
                    "action": ServiceTokenPermission.Action.READ,
                },
            ],
        )
        data = {
            "X-Hasura-Role": "service",
            "X-Hasura-User-Name": principal.name,
            "X-Hasura-Service-Principal-Id": f"{principal.id}",
            "X-Hasura-Service-Token-Id": f"{token_obj.id}",
            "X-Hasura-Read-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Create-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Update-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Delete-OplogEntry-Oplog-Id": "-1",
            "X-Hasura-Principal-Type": "service",
            "X-Hasura-Service-Token-Preset": ServiceTokenPreset.CUSTOM,
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_mixed_service_token_emits_action_specific_scope(self):
        oplog = OplogFactory()
        project = ProjectFactory()
        ProjectAssignmentFactory(project=oplog.project, operator=self.user)
        ProjectAssignmentFactory(project=project, operator=self.user)
        principal = ServicePrincipal.objects.create(
            name="Mixed Service", created_by=self.user
        )
        permissions = ServiceToken.build_permissions_for_preset(
            ServiceTokenPreset.OPLOG_RW,
            oplog_id=oplog.id,
        )
        permissions.extend(
            ServiceToken.build_permissions_for_preset(
                ServiceTokenPreset.PROJECT_READ,
                project_id=project.id,
            )
        )
        token_obj, token = ServiceToken.objects.create_token(
            name="Mixed Service Token",
            created_by=self.user,
            service_principal=principal,
            permissions=permissions,
        )
        data = {
            "X-Hasura-Role": "service",
            "X-Hasura-User-Name": principal.name,
            "X-Hasura-Service-Principal-Id": f"{principal.id}",
            "X-Hasura-Service-Token-Id": f"{token_obj.id}",
            "X-Hasura-Read-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Create-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Update-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Delete-OplogEntry-Oplog-Id": f"{oplog.id}",
            "X-Hasura-Principal-Type": "service",
            "X-Hasura-Service-Token-Preset": ServiceTokenPreset.CUSTOM,
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_without_jwt(self):
        response = self.client.get(
            self.uri,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), self.public_data)


# Tests related to Hasura Actions


class HasuraLoginTests(TestCase):
    """Collection of tests for :view:`api:graphql_login`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.user_mfa = UserFactory(password=PASSWORD)
        cls.user_webauthn = UserFactory(password=PASSWORD)
        cls.user_mfa_required = UserFactory(password=PASSWORD, require_mfa=True)
        secret = generate_totp_secret()
        TOTP.activate(cls.user_mfa, secret)
        Authenticator.objects.create(
            user=cls.user_webauthn,
            type=Authenticator.Type.WEBAUTHN,
            data={"credential_id": "test_credential_id"},
        )

        cls.uri = reverse("api:graphql_login")

    def setUp(self):
        self.client = Client()

    def test_graphql_login(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["login"]`` keys are not present
        token = response.json()["token"]
        payload = utils.jwt_decode_no_verification(token)
        self.assertTrue(token)
        self.assertEqual(utils.get_jwt_type(token), utils.USER_JWT_TYPE)
        self.assertIsInstance(response.json()["expires"], int)
        self.assertTrue(UserSession.objects.filter(identifier=payload["jti"]).exists())

    def test_graphql_login_with_invalid_credentials(self):
        data = {
            "input": {
                "username": f"{self.user.username}",
                "password": "Not the Password",
            }
        }
        result = {
            "message": "Invalid credentials",
            "extensions": {
                "code": "InvalidCredentials",
            },
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_login_with_mfa(self):
        result = {
            "message": "Login and generate a token from your user profile",
            "extensions": {
                "code": "MFARequired",
            },
        }

        data = {
            "input": {
                "username": f"{self.user_mfa.username}",
                "password": f"{PASSWORD}",
            }
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), result)

        data = {
            "input": {
                "username": f"{self.user_webauthn.username}",
                "password": f"{PASSWORD}",
            }
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), result)

        data = {
            "input": {
                "username": f"{self.user_mfa_required.username}",
                "password": f"{PASSWORD}",
            }
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), result)


class HasuraWhoamiTests(TestCase):
    """Collection of tests for :view:`api:GraphqlWhoami`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_whoami")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_graphql_whoami(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["whoami"]`` keys are not present
        self.assertEqual(response.json()["username"], self.user.username)

    def test_graphql_whoami_with_tracked_token(self):
        user_token_obj, user_token = APIKey.objects.create_token(
            user=self.user, name="Valid Token"
        )
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["whoami"]`` keys are not present
        self.assertEqual(response.json()["username"], self.user.username)


class HasuraGenerateReportTests(TestCase):
    """Collection of tests for :view:`api:GraphqlGenerateReport`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.assignment = ProjectAssignmentFactory(operator=cls.user)
        cls.report = ReportFactory(project=cls.assignment.project)
        cls.other_report = ReportFactory()
        cls.uri = reverse("api:graphql_generate_report")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_graphql_generate_report(self):
        _, token = generate_user_jwt(self.user)
        data = {"input": {"id": self.report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_graphql_generate_report_with_project_service_token(self):
        token = create_project_read_service_token(self.user, self.report.project)
        data = {"input": {"id": self.report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )

        self.assertEqual(response.status_code, 200)

    def test_graphql_generate_report_with_project_service_token_without_scope(self):
        token = create_project_read_service_token(self.user, self.report.project)
        data = {"input": {"id": self.other_report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )

        self.assertEqual(response.status_code, 401)

    def test_graphql_generate_report_with_invalid_report(self):
        _, token = generate_user_jwt(self.user)
        data = {"input": {"id": 999}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_generate_report_without_access(self):
        _, token = generate_user_jwt(self.user)
        data = {"input": {"id": self.other_report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)


class HasuraCheckoutTests(TestCase):
    """
    Collection of tests for the ``HasuraCheckoutView`` class and the related
    :view:`api:GraphqlCheckoutDomain` and :view:`api:GraphqlCheckoutServer`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.activity = ActivityTypeFactory()
        cls.project = ProjectFactory()
        cls.other_project = ProjectFactory()
        cls.assignment = ProjectAssignmentFactory(
            operator=cls.user, project=cls.project
        )

        cls.domain_available = DomainStatusFactory(domain_status="Available")
        cls.domain_unavailable = DomainStatusFactory(domain_status="Unavailable")
        cls.domain = DomainFactory(domain_status=cls.domain_available)
        cls.unavailable_domain = DomainFactory(domain_status=cls.domain_unavailable)
        cls.expired_domain = DomainFactory(
            expiration=timezone.now() - timedelta(days=1),
            domain_status=cls.domain_available,
        )

        cls.server_unavailable = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory()
        cls.unavailable_server = StaticServerFactory(
            server_status=cls.server_unavailable
        )
        cls.server_role = ServerRoleFactory()

        cls.domain_uri = reverse("api:graphql_checkout_domain")
        cls.server_uri = reverse("api:graphql_checkout_server")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def generate_domain_data(
        self,
        project,
        domain,
        activity,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        description=None,
    ):
        return {
            "input": {
                "projectId": project,
                "domainId": domain,
                "activityTypeId": activity,
                "startDate": start_date,
                "endDate": end_date,
                "description": description,
            }
        }

    def generate_server_data(
        self,
        project,
        server,
        activity,
        server_role,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        description=None,
    ):
        return {
            "input": {
                "projectId": project,
                "serverId": server,
                "activityTypeId": activity,
                "serverRoleId": server_role,
                "startDate": start_date,
                "endDate": end_date,
                "description": description,
            }
        }

    def test_graphql_checkout_domain(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(
            self.project.pk, self.domain.pk, self.activity.pk
        )
        del data["input"]["description"]
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "result": "success",
            },
        )
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.domain_status, self.domain_unavailable)

    def test_graphql_checkout_server(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_server_data(
            self.project.pk, self.server.pk, self.activity.pk, self.server_role.pk
        )
        del data["input"]["description"]
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "result": "success",
            },
        )
        self.server.refresh_from_db()
        self.assertEqual(self.server.server_status, self.server_unavailable)

    def test_graphql_checkout_server_with_invalid_role(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_server_data(
            self.project.pk,
            self.server.pk,
            self.activity.pk,
            999,
            description="Test note",
        )
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Server Role Type does not exist",
            "extensions": {
                "code": "ServerRoleDoesNotExist",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_object_with_invalid_dates(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(
            self.project.pk,
            self.domain.pk,
            self.activity.pk,
            start_date=date.today() + timedelta(days=1),
            end_date=date.today() - timedelta(days=1),
        )
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "End date is before start date",
            "extensions": {
                "code": "InvalidDates",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

        data = self.generate_domain_data(
            self.project.pk,
            self.domain.pk,
            self.activity.pk,
            start_date="2022-0325",
            end_date=date.today() - timedelta(days=1),
        )
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Invalid date values (must be YYYY-MM-DD)",
            "extensions": {
                "code": "InvalidDates",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_invalid_object(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, 999, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Domain does not exist",
            "extensions": {
                "code": "DomainDoesNotExist",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_invalid_activity(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, self.domain.pk, 999)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Activity Type does not exist",
            "extensions": {
                "code": "ActivityTypeDoesNotExist",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_invalid_project(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(999, self.domain.pk, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_unavailable_domain(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(
            self.project.pk, self.unavailable_domain.pk, self.activity.pk
        )
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Domain is unavailable",
            "extensions": {
                "code": "DomainUnavailable",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_unavailable_server(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_server_data(
            self.project.pk,
            self.unavailable_server.pk,
            self.activity.pk,
            self.server_role.pk,
        )
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Server is unavailable",
            "extensions": {
                "code": "ServerUnavailable",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_expired_domain(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(
            self.project.pk, self.expired_domain.pk, self.activity.pk
        )
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

        result = {
            "message": "Domain is expired",
            "extensions": {
                "code": "DomainExpired",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_checkout_without_project_access(self):
        _, token = generate_user_jwt(self.user)
        data = self.generate_domain_data(
            self.other_project.pk, self.domain.pk, self.activity.pk
        )
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)


class CheckoutDeleteViewTests(TestCase):
    """
    Collection of tests for ``CheckoutDeleteView`` class and related
    :view:`api.GraphqlDomainReleaseAction` and :view:`api.GraphqlServerReleaseAction`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.domain_uri = reverse("api:graphql_domain_checkout_delete")
        cls.server_uri = reverse("api:graphql_server_checkout_delete")

        cls.project = ProjectFactory()
        cls.other_project = ProjectFactory()
        ProjectAssignmentFactory(operator=cls.user, project=cls.project)

        cls.domain_available = DomainStatusFactory(domain_status="Available")
        cls.domain_unavailable = DomainStatusFactory(domain_status="Unavailable")
        cls.domain = DomainFactory(domain_status=cls.domain_unavailable)
        cls.domain_checkout = HistoryFactory(domain=cls.domain, project=cls.project)

        cls.other_domain = DomainFactory(domain_status=cls.domain_unavailable)
        cls.other_checkout = HistoryFactory(
            domain=cls.other_domain, project=cls.other_project
        )

        cls.server_available = ServerStatusFactory(server_status="Available")
        cls.server_unavailable = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory(server_status=cls.server_unavailable)
        cls.server_checkout = ServerHistoryFactory(
            server=cls.server, project=cls.project
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def generate_data(self, checkout_id):
        return {
            "input": {
                "checkoutId": checkout_id,
            }
        }

    def test_deleting_domain_checkout(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(self.domain_checkout.pk),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.domain_status, self.domain_available)

    def test_deleting_server_checkout(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.server_uri,
            data=self.generate_data(self.server_checkout.pk),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.server.refresh_from_db()
        self.assertEqual(self.server.server_status, self.server_available)

    def test_deleting_domain_checkout_without_access(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(self.other_checkout.pk),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_deleting_invalid_checkout(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(checkout_id=999),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Checkout does not exist",
            "extensions": {
                "code": "HistoryDoesNotExist",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)


class GraphqlDeleteReportTemplateAction(TestCase):
    """Collection of tests for :view:`GraphqlDeleteReportTemplateAction`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportTemplate = ReportTemplateFactory._meta.model

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:graphql_delete_template")

        cls.template = ReportTemplateFactory()
        cls.protected_template = ReportTemplateFactory(protected=True)
        cls.client = ClientFactory()
        cls.client_template = ReportTemplateFactory(client=cls.client)

    def setUp(self):
        self.client = Client()

    def generate_data(self, template_id):
        return {
            "input": {
                "templateId": template_id,
            }
        }

    def test_deleting_template(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.template.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(
            self.ReportTemplate.objects.filter(id=self.template.id).exists()
        )

    def test_deleting_template_with_invalid_id(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(999),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)

    def test_deleting_protected_template_with_access(self):
        _, token = generate_user_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.protected_template.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_deleting_protected_template_without_access(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.protected_template.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            self.uri,
            data=self.generate_data(self.client_template.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)


class GraphqlAttachFindingAction(TestCase):
    """Collection of tests for :view:`GraphqlAttachFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model

        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:graphql_attach_finding")

        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.tags = ["severity:high, att&ck:t1159"]
        cls.finding = FindingFactory(tags=cls.tags)
        _ = ProjectAssignmentFactory(project=cls.project, operator=cls.user)

    def setUp(self):
        self.client = Client()

    def generate_data(self, finding_id, report_id):
        return {
            "input": {
                "findingId": finding_id,
                "reportId": report_id,
            }
        }

    def test_attaching_finding(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        new_finding = response.json()["id"]
        self.assertTrue(self.ReportFindingLink.objects.filter(id=new_finding).exists())
        self.assertEqual(len(self.finding.tags.similar_objects()), 1)
        self.assertEqual(
            len(
                self.ReportFindingLink.objects.get(
                    id=new_finding
                ).tags.similar_objects()
            ),
            len(self.finding.tags.similar_objects()),
        )
        self.assertEqual(list(self.finding.tags.names()), self.tags)

    def test_attaching_finding_with_invalid_report(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, 999),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        data = {
            "message": "Report does not exist",
            "extensions": {"code": "ReportDoesNotExist"},
        }
        self.assertJSONEqual(force_str(response.content), data)

    def test_attaching_finding_with_invalid_finding(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(999, self.report.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        data = {
            "message": "Finding does not exist",
            "extensions": {"code": "FindingDoesNotExist"},
        }
        self.assertJSONEqual(force_str(response.content), data)

    def test_attaching_finding_with_mgr_access(self):
        _, token = generate_user_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_attaching_finding_without_access(self):
        _, token = generate_user_jwt(self.other_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)


class GraphqlUploadEvidenceViewTests(TestCase):
    """Collection of tests for :view:`api:GraphqlUploadEvidenceView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.disallowed_user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_upload_evidence")
        cls.project = ProjectFactory()
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )
        cls.report = ReportFactory(project=cls.project)
        cls.finding = ReportFindingLinkFactory(report=cls.report)

    def setUp(self):
        self.client = Client()

    def test_upload_report(self):
        _, token = generate_user_jwt(self.user)
        data = {
            "filename": "test.txt",
            "file_base64": base64.b64encode(b"Hello, world!").decode("ascii"),
            "friendly_name": "test_evidence",
            "description": "This was added via graphql",
            "caption": "Graphql Evidence",
            "tags": "foo,bar,baz",
            "report": str(self.report.pk),
        }
        response = self.client.post(
            self.uri,
            data={"input": data},
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        id = response.json()["id"]
        evidence = Evidence.objects.get(pk=id)
        self.assertEqual(evidence.caption, data["caption"])
        self.assertEqual(evidence.document.read(), "Hello, world!".encode("utf-8"))
        self.assertEqual(evidence.pk, self.report.evidence_set.all().get().pk)

    def test_upload_report_forbidden(self):
        _, token = generate_user_jwt(self.disallowed_user)
        data = {
            "filename": "test.txt",
            "file_base64": base64.b64encode(b"Hello, world!").decode("ascii"),
            "friendly_name": "test_evidence",
            "description": "This was added via graphql",
            "caption": "Graphql Evidence",
            "tags": "foo,bar,baz",
            "report": str(self.report.pk),
        }
        response = self.client.post(
            self.uri,
            data={"input": data},
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertNotEqual(response.status_code, 201, response.content)

    def test_upload_finding(self):
        _, token = generate_user_jwt(self.user)
        data = {
            "filename": "test.txt",
            "file_base64": base64.b64encode(b"Hello, world!").decode("ascii"),
            "friendly_name": "test_evidence",
            "description": "This was added via graphql",
            "caption": "Graphql Evidence",
            "tags": "foo,bar,baz",
            "finding": str(self.finding.pk),
        }
        response = self.client.post(
            self.uri,
            data={"input": data},
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 201, response.content)
        id = response.json()["id"]
        evidence = Evidence.objects.get(pk=id)
        self.assertEqual(evidence.caption, data["caption"])
        self.assertEqual(evidence.document.read(), "Hello, world!".encode("utf-8"))
        self.assertEqual(evidence.pk, self.finding.evidence_set.all().get().pk)

    def test_upload_finding_forbidden(self):
        _, token = generate_user_jwt(self.disallowed_user)
        data = {
            "filename": "test.txt",
            "file_base64": base64.b64encode(b"Hello, world!").decode("ascii"),
            "friendly_name": "test_evidence",
            "description": "This was added via graphql",
            "caption": "Graphql Evidence",
            "tags": "foo,bar,baz",
            "finding": str(self.finding.pk),
        }
        response = self.client.post(
            self.uri,
            data={"input": data},
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertNotEqual(response.status_code, 201, response.content)

    def test_upload_evidence_oversized_payload_rejected(self):
        """Regression test: payloads exceeding GHOSTWRITER_MAX_FILE_SIZE must return 413, not exhaust memory."""
        _, token = generate_user_jwt(self.user)
        # Build a body one byte over the transport envelope cap for large-input uploads
        oversized_body = b"x" * ((settings.GHOSTWRITER_MAX_FILE_SIZE * 2) + 1)
        response = self.client.post(
            self.uri,
            data=oversized_body,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["extensions"]["code"], "PayloadTooLarge")

    def test_upload_evidence_accepts_valid_file_when_encoded_body_exceeds_file_limit(
        self,
    ):
        """Base64+JSON overhead should not cause a valid sub-limit file upload to be rejected."""
        _, token = generate_user_jwt(self.user)
        file_bytes = b"x" * 90
        data = {
            "filename": "test.txt",
            "file_base64": base64.b64encode(file_bytes).decode("ascii"),
            "friendly_name": "test_evidence",
            "description": "This was added via graphql",
            "caption": "Graphql Evidence",
            "tags": "foo,bar,baz",
            "report": str(self.report.pk),
        }
        request_body = json.dumps({"input": data}).encode("utf-8")
        max_file_size = (len(file_bytes) + len(request_body)) // 2

        with override_settings(GHOSTWRITER_MAX_FILE_SIZE=max_file_size):
            self.assertGreater(len(request_body), settings.GHOSTWRITER_MAX_FILE_SIZE)
            self.assertLessEqual(len(file_bytes), settings.GHOSTWRITER_MAX_FILE_SIZE)

            response = self.client.post(
                self.uri,
                data=request_body,
                content_type="application/json",
                **{
                    "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                    "HTTP_AUTHORIZATION": f"Bearer {token}",
                },
            )
        self.assertEqual(response.status_code, 201, response.content)


class GraphqlGenerateCodenameActionTests(TestCase):
    """Collection of tests for :view:`GraphqlGenerateCodenameAction`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_generate_codename")

    def setUp(self):
        self.client = Client()

    def test_generating_codename(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)


class GraphqlGetExtraFieldSpecActionTests(TestCase):
    """Collection of tests for :view:`api:GraphqlGetExtraFieldSpecAction`."""

    fixtures = ["ghostwriter/commandcenter/fixtures/initial.json"]

    @classmethod
    def setUpTestData(cls):
        cls.ExtraFieldModel = ExtraFieldModelFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_get_extra_field_spec")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_graphql_get_extra_field_spec(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "Finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "Reporting.Finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

        extra_field_model = self.ExtraFieldModel.objects.get(pk="reporting.Finding")
        ExtraFieldSpecFactory(
            internal_name="test_field",
            display_name="Test Field",
            type="single_line_text",
            target_model=extra_field_model,
        )

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json()["extraFieldSpec"]["test_field"]["internalName"],
            "test_field",
        )

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "bad_model_name"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Model does not exist")

    def test_graphql_get_extra_field_spec_preserves_position_order(self):
        _, token = generate_user_jwt(self.user)
        extra_field_model = self.ExtraFieldModel.objects.get(pk="reporting.Finding")
        third = ExtraFieldSpecFactory(
            internal_name="third_field",
            display_name="Third Field",
            type="single_line_text",
            target_model=extra_field_model,
            position=3,
        )
        first = ExtraFieldSpecFactory(
            internal_name="first_field",
            display_name="First Field",
            type="single_line_text",
            target_model=extra_field_model,
            position=1,
        )
        second = ExtraFieldSpecFactory(
            internal_name="second_field",
            display_name="Second Field",
            type="single_line_text",
            target_model=extra_field_model,
            position=2,
        )

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            list(response.json()["extraFieldSpec"].keys()),
            [first.internal_name, second.internal_name, third.internal_name],
        )

    def test_graphql_get_extra_field_spec_with_project_service_token(self):
        project = ProjectFactory()
        token = create_project_read_service_token(self.user, project)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "finding"}},
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )

        self.assertEqual(response.status_code, 200)


class HasuraCreateUserTests(TestCase):
    """Collection of tests for :view:`api:GraphqlUserCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, role="admin")
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.unprivileged_user = UserFactory(password=PASSWORD, role="user")
        cls.uri = reverse("api:graphql_create_user")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def generate_data(self, name, email, username, role, **kwargs):
        return {
            "input": {
                "name": name,
                "email": email,
                "username": username,
                "role": role,
                "password": PASSWORD,
                **kwargs,
            }
        }

    def test_graphql_create_user(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "validuser",
                "validuser@specterops.io",
                "validuser",
                "user",
                requiremfa=True,
                timezone="America/New_York",
                enableFindingCreate=False,
                enableFindingEdit=False,
                enableFindingDelete=False,
                enableObservationCreate=False,
                enableObservationEdit=False,
                enableObservationDelete=False,
                phone="123-456-7890",
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 200)

        created_user = User.objects.get(username="validuser")
        self.assertEqual(created_user.email, "validuser@specterops.io")
        self.assertEqual(created_user.require_mfa, True)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "validuser", "validuser@specterops.io", "validuser", "user"
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "A user with that username already exists",
            "extensions": {
                "code": "UserAlreadyExists",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_create_user_with_bad_timezone(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "badtimezone",
                "badtimezone@specterops.io",
                "badtimezone",
                "user",
                timezone="PST",
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Invalid timezone",
            "extensions": {
                "code": "InvalidTimezone",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_create_user_with_bad_role(self):
        _, token = generate_user_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "badrole", "badrole@specterops.io", "badrole", "invalid"
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 400)
        result = {
            "message": "Invalid user role",
            "extensions": {
                "code": "InvalidUserRole",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_create_user_with_manager_user(self):
        _, token = generate_user_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "mgruser", "mgruser@specterops.io", "mgruser", "manager"
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        result = {
            "message": "Unauthorized to create user with this role",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_create_user_with_unprivileged_user(self):
        _, token = generate_user_jwt(self.unprivileged_user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "unprivileged", "unprivileged@specterops.io", "unprivileged", "manager"
            ),
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {token}",
            },
        )
        self.assertEqual(response.status_code, 401)
        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)


# Tests related to Hasura Event Triggers


class GraphqlDomainUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlDomainUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_domain_update_event")
        cls.available_status = DomainStatusFactory(domain_status="Available")
        cls.expired_status = DomainStatusFactory(domain_status="Expired")
        cls.domain = DomainFactory(
            name="chrismaddalena.com", domain_status=cls.expired_status
        )
        cls.sample_data = {
            "event": {
                "data": {
                    "new": {
                        "expired": False,
                        "registrar": "Hover",
                        "description": "<p>The personal website and blog of Christopher Maddalena</p>",
                        "last_health_check": "",
                        "auto_renew": True,
                        "expiration": "2023-03-25",
                        "reset_dns": False,
                        "vt_permalink": "",
                        "burned_explanation": "",
                        "creation": "2010-03-25",
                        "domain_status_id": cls.expired_status.id,
                        "last_used_by_id": "",
                        "name": "Chrismaddalena.com",
                        "categorization": "",
                        "health_status_id": cls.domain.health_status.id,
                        "id": cls.domain.id,
                        "whois_status_id": 1,
                        "dns": {},
                    },
                    "old": {},
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_domain_update_event(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.name, "chrismaddalena.com")
        self.assertEqual(self.domain.domain_status, self.expired_status)
        self.assertTrue(self.domain.expired)

        self.domain.domain_status = self.available_status
        self.domain.save()

        self.sample_data["event"]["data"]["new"][
            "domain_status_id"
        ] = self.available_status.id
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.domain.refresh_from_db()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.domain.domain_status, self.available_status)
        self.assertFalse(self.domain.expired)


class GraphqlOplogEntryEventTests(TestCase):
    """
    Collection of tests for :view:`api:GraphqlOplogEntryCreateEvent`,
    :view:`api:GraphqlOplogEntryUpdateEvent`, and :view:`api:GraphqlOplogEntryDeleteEvent`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.create_uri = reverse("api:graphql_oplogentry_create_event")
        cls.update_uri = reverse("api:graphql_oplogentry_update_event")
        cls.delete_uri = reverse("api:graphql_oplogentry_delete_event")
        cls.oplog_entry = OplogEntryFactory()
        cls.sample_data = {
            "event": {
                "session_variables": None,
                "op": "INSERT",
                "data": {
                    "old": None,
                    "new": {
                        "end_date": "2022-08-02T16:37:49.768288+00:00",
                        "command": None,
                        "tool": None,
                        "operator_name": None,
                        "dest_ip": None,
                        "start_date": "2022-08-02T16:37:49.768257+00:00",
                        "user_context": None,
                        "output": None,
                        "id": cls.oplog_entry.id,
                        "comments": None,
                        "oplog_id_id": cls.oplog_entry.oplog_id.id,
                        "source_ip": None,
                        "description": None,
                    },
                },
                "trace_context": None,
            },
            "created_at": "2022-08-02T16:37:49.773219Z",
            "id": "162a8485-97f4-49a3-9914-82e0f18549e8",
            "delivery_info": {"max_retries": 0, "current_retry": 0},
            "trigger": {"name": "CreateOplogEntry"},
            "table": {"schema": "public", "name": "oplog_oplogentry"},
        }
        cls.sample_delete_data = {
            "event": {
                "session_variables": None,
                "op": "DELETE",
                "data": {
                    "old": {
                        "end_date": "2022-08-02T16:37:49.768288+00:00",
                        "command": None,
                        "tool": "",
                        "operator_name": None,
                        "dest_ip": None,
                        "start_date": "2022-08-02T16:37:49.768257+00:00",
                        "user_context": None,
                        "output": "",
                        "id": cls.oplog_entry.id,
                        "comments": None,
                        "oplog_id_id": cls.oplog_entry.oplog_id.id,
                        "source_ip": None,
                        "description": None,
                    },
                    "new": None,
                },
                "trace_context": None,
            },
            "created_at": "2022-08-02T16:49:10.912756Z",
            "id": "359ddc5c-1f53-44f5-889a-ef1e438632d0",
            "delivery_info": {"max_retries": 0, "current_retry": 0},
            "trigger": {"name": "DeleteOplogEntry"},
            "table": {"schema": "public", "name": "oplog_oplogentry"},
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_oplogentry_create_event(self):
        response = self.client.post(
            self.create_uri,
            content_type="application/json",
            data=self.sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_graphql_oplogentry_update_event(self):
        response = self.client.post(
            self.update_uri,
            content_type="application/json",
            data=self.sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)

    def test_graphql_oplogentry_delete_event(self):
        response = self.client.post(
            self.delete_uri,
            content_type="application/json",
            data=self.sample_delete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)


class GraphqlReportFindingEventTests(TestCase):
    """
    Collection of tests for :view:`api:GraphqlReportFindingChangeEvent` and
    :view:`api:GraphqlReportFindingDeleteEvent`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

        cls.critical_severity = SeverityFactory(severity="Critical", weight=0)
        cls.high_severity = SeverityFactory(severity="High", weight=1)

        cls.report = ReportFactory()

        cls.change_uri = reverse("api:graphql_reportfinding_change_event")
        cls.delete_uri = reverse("api:graphql_reportfinding_delete_event")

    def setUp(self):
        self.client = Client()

    def test_model_cleaning_position(self):
        self.ReportFindingLink.objects.all().delete()
        first_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=1
        )
        second_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=2
        )
        third_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=3
        )

        # Simulate an event changing the position of the first finding to `3`
        first_finding.position = 3
        first_finding.save()
        sample_data = {
            "event": {
                "op": "UPDATE",
                "data": {
                    "old": {
                        "id": first_finding.id,
                        "position": 1,
                        "severity_id": first_finding.severity.id,
                    },
                    "new": {
                        "id": first_finding.id,
                        "position": 3,
                        "severity_id": first_finding.severity.id,
                    },
                },
            },
        }

        # Submit the POST request to the event webhook
        response = self.client.post(
            self.change_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        first_finding.refresh_from_db()
        self.assertEqual(first_finding.position, 3)
        second_finding.refresh_from_db()
        self.assertEqual(second_finding.position, 1)
        third_finding.refresh_from_db()
        self.assertEqual(third_finding.position, 2)

        # Repeat for an `UPDATE` event with a severity change
        second_finding.severity = self.high_severity
        second_finding.save()
        sample_data = {
            "event": {
                "op": "UPDATE",
                "data": {
                    "old": {
                        "id": second_finding.id,
                        "position": second_finding.position,
                        "severity_id": self.critical_severity.id,
                    },
                    "new": {
                        "id": second_finding.id,
                        "position": second_finding.position,
                        "severity_id": self.high_severity.id,
                    },
                },
            },
        }

        response = self.client.post(
            self.change_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        first_finding.refresh_from_db()
        second_finding.refresh_from_db()
        third_finding.refresh_from_db()
        self.assertEqual(second_finding.position, 1)
        self.assertEqual(first_finding.position, 2)
        self.assertEqual(third_finding.position, 1)

        # Repeat for an `INSERT` event
        new_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity
        )
        sample_data = {
            "event": {
                "op": "INSERT",
                "data": {
                    "old": None,
                    "new": {
                        "id": new_finding.id,
                        "position": 1,
                        "severity_id": new_finding.severity.id,
                    },
                },
            },
        }

        response = self.client.post(
            self.change_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        new_finding.refresh_from_db()
        self.assertEqual(new_finding.position, 3)

    def test_position_set_to_zero(self):
        self.ReportFindingLink.objects.all().delete()
        finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=0
        )

        # Simulate an event changing the position of the first finding to `0`
        sample_data = {
            "event": {
                "op": "INSERT",
                "data": {
                    "old": None,
                    "new": {
                        "id": finding.id,
                        "position": 0,
                        "severity_id": finding.severity.id,
                    },
                },
            },
        }

        # Submit the POST request to the event webhook
        response = self.client.post(
            self.change_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        finding.refresh_from_db()
        self.assertEqual(finding.position, 1)

    def test_position_set_higher_than_count(self):
        self.ReportFindingLink.objects.all().delete()
        finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=100
        )

        # Simulate an event changing the position of the first finding to `100`
        sample_data = {
            "event": {
                "op": "INSERT",
                "data": {
                    "old": None,
                    "new": {
                        "id": finding.id,
                        "position": 100,
                        "severity_id": finding.severity.id,
                    },
                },
            },
        }

        # Submit the POST request to the event webhook
        response = self.client.post(
            self.change_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        finding.refresh_from_db()
        total_findings = self.ReportFindingLink.objects.filter(
            report=self.report
        ).count()
        self.assertEqual(finding.position, total_findings)

    def test_position_change_on_delete(self):
        self.ReportFindingLink.objects.all().delete()

        first_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=1
        )
        second_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=2
        )
        third_finding = ReportFindingLinkFactory(
            report=self.report, severity=self.critical_severity, position=3
        )

        # Simulate an event deleting the second finding
        second_finding.delete()
        sample_data = {
            "event": {
                "op": "DELETE",
                "data": {
                    "old": {
                        "id": second_finding.id,
                        "position": 2,
                        "severity_id": second_finding.severity.id,
                        "report_id": second_finding.report.id,
                    },
                    "new": None,
                },
            },
        }

        # Submit the POST request to the event webhook
        response = self.client.post(
            self.delete_uri,
            content_type="application/json",
            data=sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        first_finding.refresh_from_db()
        third_finding.refresh_from_db()
        self.assertEqual(first_finding.position, 1)
        self.assertEqual(third_finding.position, 2)


class GraphqlProjectContactUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlProjectContactUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_projectcontact_update_event")

        cls.project = ProjectFactory()
        cls.primary_contact = ProjectContactFactory(primary=True, project=cls.project)
        cls.other_contact = ProjectContactFactory(primary=False, project=cls.project)
        cls.sample_data = {
            "event": {
                "data": {
                    "new": {
                        "id": cls.other_contact.id,
                        "name": cls.other_contact.name,
                        "job_title": cls.other_contact.job_title,
                        "email": cls.other_contact.email,
                        "phone": cls.other_contact.phone,
                        "description": cls.other_contact.description,
                        "timezone": cls.other_contact.timezone.key,
                        "project": cls.project.id,
                        "primary": True,
                    },
                    "old": {
                        "id": cls.other_contact.id,
                        "name": cls.other_contact.name,
                        "job_title": cls.other_contact.job_title,
                        "email": cls.other_contact.email,
                        "phone": cls.other_contact.phone,
                        "description": cls.other_contact.description,
                        "timezone": cls.other_contact.timezone.key,
                        "project": cls.project.id,
                        "primary": cls.other_contact.primary,
                    },
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_projectcontact_update_event(self):
        self.assertTrue(self.primary_contact.primary)
        self.assertFalse(self.other_contact.primary)

        self.other_contact.primary = True
        self.other_contact.save()

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.sample_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)

        self.primary_contact.refresh_from_db()
        self.assertFalse(self.primary_contact.primary)
        self.other_contact.refresh_from_db()
        self.assertTrue(self.other_contact.primary)


class GraphqlProjectObjectiveUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlProjectObjectiveUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_projectobjective_update_event")

        cls.project = ProjectFactory()
        cls.objective = ProjectObjectiveFactory(project=cls.project, complete=False)
        cls.complete_data = {
            "event": {
                "data": {
                    "new": {
                        "id": cls.objective.id,
                        "complete": False,
                        "deadline": cls.objective.deadline,
                    },
                    "old": {
                        "id": cls.objective.id,
                        "complete": True,
                        "deadline": cls.objective.deadline,
                    },
                },
            }
        }
        cls.incomplete_data = {
            "event": {
                "data": {
                    "new": {
                        "id": cls.objective.id,
                        "complete": True,
                        "deadline": cls.objective.deadline,
                    },
                    "old": {
                        "id": cls.objective.id,
                        "complete": False,
                        "deadline": cls.objective.deadline,
                    },
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_projectobjective_update_event(self):
        self.objective.complete = True
        self.objective.save()

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.complete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.objective.refresh_from_db()
        self.assertTrue(self.objective.complete)
        self.assertEqual(self.objective.marked_complete, date.today())

        self.objective.complete = False
        self.objective.save()

        subtask = ProjectSubtaskFactory(
            complete=False,
            parent=self.objective,
            deadline=self.objective.deadline + timedelta(days=1),
        )
        self.assertEqual(subtask.deadline, self.objective.deadline + timedelta(days=1))

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.incomplete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.objective.refresh_from_db()
        self.assertFalse(self.objective.complete)
        self.assertFalse(self.objective.marked_complete)

        subtask.refresh_from_db()
        self.assertEqual(subtask.deadline, self.objective.deadline)


class GraphqlProjectSubTaskUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlProjectSubTaskUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_projectsubtaske_update_event")

        cls.task = ProjectSubtaskFactory(complete=False)
        cls.complete_data = {
            "event": {
                "data": {
                    "new": {
                        "id": cls.task.id,
                        "complete": False,
                        "deadline": cls.task.deadline,
                    },
                    "old": {
                        "id": cls.task.id,
                        "complete": True,
                        "deadline": cls.task.deadline,
                    },
                },
            }
        }
        cls.incomplete_data = {
            "event": {
                "data": {
                    "new": {
                        "id": cls.task.id,
                        "complete": True,
                        "deadline": cls.task.deadline,
                    },
                    "old": {
                        "id": cls.task.id,
                        "complete": False,
                        "deadline": cls.task.deadline,
                    },
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_projectsubtask_update_event(self):
        self.task.complete = True
        self.task.deadline = self.task.parent.deadline + timedelta(days=1)
        self.task.save()

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.complete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.task.refresh_from_db()
        self.assertTrue(self.task.complete)
        self.assertEqual(self.task.marked_complete, date.today())
        self.assertEqual(self.task.deadline, self.task.parent.deadline)

        self.task.complete = False
        self.task.save()

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.incomplete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)

        self.task.refresh_from_db()
        self.assertFalse(self.task.complete)
        self.assertFalse(self.task.marked_complete)


class GraphqlEvidenceUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlEvidenceUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_evidence_update_event")

        cls.finding = ReportFindingLinkFactory(
            description="<p>Here is some evidence:</p><p>{{.Test Finding Evidence}}</p><p>{{.ref Test Finding Evidence}}</p>",
            impact="<p>Here is some evidence:</p><p>{{.Test Report Evidence}}</p><p>{{.ref Test Report Evidence}}</p>",
            mitigation="<p>Here is some evidence:</p><p>{{.Deleted Evidence}}</p><p>{{.ref Deleted Evidence}}</p>",
        )
        cls.finding_evidence = EvidenceOnFindingFactory(
            friendly_name="Test Finding Evidence",
            finding=cls.finding,
            report=None,
            document=factory.django.FileField(
                filename="finding_evidence.txt", data=b"lorem ipsum"
            ),
        )
        cls.report_evidence = EvidenceOnReportFactory(
            friendly_name="Test Report Evidence",
            report=cls.finding.report,
            document=factory.django.FileField(
                filename="finding_evidence.txt", data=b"lorem ipsum"
            ),
        )
        cls.deleted_evidence = EvidenceOnFindingFactory(
            finding=cls.finding, friendly_name="Deleted Evidence"
        )

        # Add a blank finding to the report for regression testing updates on findings with blank fields
        BlankReportFindingLinkFactory(report=cls.report_evidence.report)
        EvidenceOnReportFactory(
            report=cls.report_evidence.report, friendly_name="Blank Test"
        )

        # Sample data for an update that changes the friendly name and document on finding evidence
        cls.update_data_finding = {
            "event": {
                "op": "UPDATE",
                "data": {
                    "new": {
                        "id": cls.finding_evidence.id,
                        "document": "evidence/some_new_file.txt",
                        "friendly_name": "New Name",
                        "finding_id": cls.finding.id,
                        "report_id": "",
                    },
                    "old": {
                        "id": cls.finding_evidence.id,
                        "document": str(cls.finding_evidence.document),
                        "friendly_name": cls.finding_evidence.friendly_name,
                        "finding_id": cls.finding.id,
                        "report_id": "",
                    },
                },
            }
        }
        # Sample data for an update that changes the friendly name and document on report evidence
        cls.update_data_report = {
            "event": {
                "op": "UPDATE",
                "data": {
                    "new": {
                        "id": cls.report_evidence.id,
                        "document": str(cls.report_evidence.document),
                        "friendly_name": "New Name",
                        "finding_id": "",
                        "report_id": cls.report_evidence.report.id,
                    },
                    "old": {
                        "id": cls.report_evidence.id,
                        "document": str(cls.report_evidence.document),
                        "friendly_name": cls.report_evidence.friendly_name,
                        "finding_id": "",
                        "report_id": cls.report_evidence.report.id,
                    },
                },
            }
        }
        # Sample data for a delete event
        cls.delete_data = {
            "event": {
                "op": "DELETE",
                "data": {
                    "new": {},
                    "old": {
                        "id": cls.deleted_evidence.id,
                        "document": str(cls.deleted_evidence.document),
                        "friendly_name": cls.deleted_evidence.friendly_name,
                        "finding_id": cls.finding.id,
                        "report_id": "",
                    },
                },
            }
        }

    def setUp(self):
        self.client = Client()

    def test_graphql_evidence_update_event(self):
        # Test updating finding evidence
        self.assertTrue(os.path.exists(self.finding_evidence.document.path))
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.update_data_finding,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        # The document should no longer exist
        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(self.finding_evidence.document.path))

        # The friendly name references should be changed
        self.finding.refresh_from_db()
        self.assertEqual(
            self.finding.description,
            "<p>Here is some evidence:</p><p>{{.New Name}}</p><p>{{.ref New Name}}</p>",
        )

        # Test updating report evidence
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.update_data_report,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )
        self.assertEqual(response.status_code, 200)
        self.finding.refresh_from_db()
        self.assertEqual(
            self.finding.impact,
            "<p>Here is some evidence:</p><p>{{.New Name}}</p><p>{{.ref New Name}}</p>",
        )

    def test_graphql_evidence_delete_event(self):
        self.assertTrue(os.path.exists(self.deleted_evidence.document.path))
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.delete_data,
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertFalse(os.path.exists(self.deleted_evidence.document.path))
        self.finding.refresh_from_db()
        self.assertEqual(
            self.finding.mitigation, "<p>Here is some evidence:</p><p></p>"
        )


# Tests related to CBVs for :model:`api:APIKey`


class ApiKeyRevokeTests(TestCase):
    """Collection of tests for :view:`api:ApiKeyRevoke`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.token_obj, cls.token = APIKey.objects.create_token(
            user=cls.user, name="User's Token"
        )
        cls.other_token_obj, cls.other_token = APIKey.objects.create_token(
            user=cls.other_user, name="Other User's Token"
        )
        cls.uri = reverse("api:ajax_revoke_token", kwargs={"pk": cls.token_obj.pk})
        cls.other_uri = reverse(
            "api:ajax_revoke_token", kwargs={"pk": cls.other_token_obj.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        data = {"result": "success", "message": "Token successfully revoked!"}
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        self.token_obj.refresh_from_db()
        self.assertEqual(self.token_obj.revoked, True)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_revoking_another_users_token(self):
        response = self.client_auth.post(self.other_uri)
        self.assertEqual(response.status_code, 302)


class ApiKeyExpiryUpdateTests(TestCase):
    """Collection of tests for :view:`api:ApiKeyExpiryUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.expired_at = timezone.now() - timedelta(days=1)
        cls.token_obj, cls.token = APIKey.objects.create_token(
            user=cls.user, name="User's Token", expiry_date=cls.expired_at
        )
        cls.other_token_obj, cls.other_token = APIKey.objects.create_token(
            user=cls.other_user, name="Other User's Token", expiry_date=cls.expired_at
        )
        cls.revoked_token_obj, cls.revoked_token = APIKey.objects.create_token(
            user=cls.user,
            name="Revoked Token",
            expiry_date=cls.expired_at,
            revoked=True,
        )
        cls.uri = reverse("api:update_token_expiry", kwargs={"pk": cls.token_obj.pk})
        cls.other_uri = reverse(
            "api:update_token_expiry", kwargs={"pk": cls.other_token_obj.pk}
        )
        cls.revoked_uri = reverse(
            "api:update_token_expiry", kwargs={"pk": cls.revoked_token_obj.pk}
        )
        cls.redirect_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_updates_expired_token_to_future_expiry(self):
        future_expiry = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
            microsecond=0
        )
        old_token = self.token
        old_identifier = self.token_obj.identifier
        old_prefix = self.token_obj.token_prefix
        response = self.client_auth.post(
            self.uri,
            data={"expiry_date": future_expiry.strftime("%Y-%m-%dT%H:%M:%S")},
        )

        self.assertRedirects(response, self.redirect_uri)
        self.token_obj.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.token_obj.expiry_date).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            future_expiry.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self.assertNotEqual(self.token_obj.identifier, old_identifier)
        self.assertNotEqual(self.token_obj.token_prefix, old_prefix)
        self.assertFalse(APIKey.objects.is_valid(old_token))
        replacement_messages = [
            message
            for message in get_messages(response.wsgi_request)
            if "api-token" in message.tags and "replacement-token" in message.tags
        ]
        self.assertEqual(len(replacement_messages), 1)
        replacement_token = str(replacement_messages[0])
        self.assertTrue(replacement_token.startswith(f"{APIKey.objects.token_prefix}_"))
        self.assertTrue(APIKey.objects.is_valid(replacement_token))

    def test_updates_active_token_replaces_current_token(self):
        current_expiry = timezone.localtime(timezone.now() + timedelta(days=7)).replace(
            microsecond=0
        )
        token_obj, old_token = APIKey.objects.create_token(
            user=self.user,
            name="Active Token",
            expiry_date=current_expiry,
        )
        token_obj.last_used_at = timezone.now() - timedelta(days=1)
        token_obj.save(update_fields=["last_used_at"])
        old_identifier = token_obj.identifier
        old_prefix = token_obj.token_prefix
        future_expiry = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
            microsecond=0
        )
        response = self.client_auth.post(
            reverse("api:update_token_expiry", kwargs={"pk": token_obj.pk}),
            data={"expiry_date": future_expiry.strftime("%Y-%m-%dT%H:%M:%S")},
        )

        self.assertRedirects(response, self.redirect_uri)
        token_obj.refresh_from_db()
        self.assertNotEqual(token_obj.identifier, old_identifier)
        self.assertNotEqual(token_obj.token_prefix, old_prefix)
        self.assertIsNone(token_obj.last_used_at)
        self.assertFalse(APIKey.objects.is_valid(old_token))
        replacement_messages = [
            message
            for message in get_messages(response.wsgi_request)
            if "api-token" in message.tags and "replacement-token" in message.tags
        ]
        self.assertEqual(len(replacement_messages), 1)
        self.assertTrue(APIKey.objects.is_valid(str(replacement_messages[0])))

    def test_updates_active_token_rejects_previous_token_for_authentication(self):
        current_expiry = timezone.localtime(timezone.now() + timedelta(days=7)).replace(
            microsecond=0
        )
        token_obj, old_token = APIKey.objects.create_token(
            user=self.user,
            name="Active Token",
            expiry_date=current_expiry,
        )
        old_identifier = token_obj.identifier
        old_prefix = token_obj.token_prefix
        future_expiry = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
            microsecond=0
        )

        self.client_auth.post(
            reverse("api:update_token_expiry", kwargs={"pk": token_obj.pk}),
            data={"expiry_date": future_expiry.strftime("%Y-%m-%dT%H:%M:%S")},
        )
        response = self.client.post(
            reverse("api:graphql_test"),
            data={
                "input": {
                    "id": 1,
                    "function": "test_func",
                    "args": {},
                }
            },
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {old_token}",
            },
        )
        token_obj.refresh_from_db()

        self.assertNotEqual(token_obj.identifier, old_identifier)
        self.assertNotEqual(token_obj.token_prefix, old_prefix)
        self.assertEqual(response.status_code, 401)

    def test_rejects_past_expiry(self):
        old_prefix = self.token_obj.token_prefix
        old_secret_hash = self.token_obj.secret_hash
        response = self.client_auth.post(
            self.uri,
            data={"expiry_date": self.expired_at.strftime("%Y-%m-%dT%H:%M:%S")},
        )

        self.assertRedirects(response, self.redirect_uri)
        self.token_obj.refresh_from_db()
        self.assertEqual(self.token_obj.expiry_date, self.expired_at)
        self.assertEqual(self.token_obj.token_prefix, old_prefix)
        self.assertEqual(self.token_obj.secret_hash, old_secret_hash)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_rejects_another_users_token(self):
        response = self.client_auth.post(
            self.other_uri,
            data={
                "expiry_date": (
                    timezone.localtime(timezone.now() + timedelta(days=14)).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        self.other_token_obj.refresh_from_db()
        self.assertEqual(self.other_token_obj.expiry_date, self.expired_at)
        self.assertEqual(
            self.other_token_obj.token_prefix, self.other_token.split("_", 2)[1]
        )

    def test_rejects_revoked_token(self):
        response = self.client_auth.post(
            self.revoked_uri,
            data={
                "expiry_date": (
                    timezone.localtime(timezone.now() + timedelta(days=14)).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                )
            },
        )

        self.assertRedirects(response, self.redirect_uri)
        self.revoked_token_obj.refresh_from_db()
        self.assertTrue(self.revoked_token_obj.revoked)
        self.assertEqual(self.revoked_token_obj.expiry_date, self.expired_at)
        self.assertEqual(
            self.revoked_token_obj.token_prefix, self.revoked_token.split("_", 2)[1]
        )


class ApiKeyCreateTests(TestCase):
    """Collection of tests for :view:`api:ApiKeyCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:ajax_create_token")
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
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "token_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], self.redirect_uri)

    def test_post_data(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "name": "CreateView Test",
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = APIKey.objects.get(name="CreateView Test")
        self.assertEqual(obj.user, self.user)


class ServiceTokenRevokeTests(TestCase):
    """Collection of tests for :view:`api:ServiceTokenRevoke`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=cls.user
        )
        cls.token_obj, cls.token = ServiceToken.objects.create_token(
            name="User's Service Token",
            created_by=cls.user,
            service_principal=cls.principal,
        )
        cls.other_principal = ServicePrincipal.objects.create(
            name="Other Mythic Sync", created_by=cls.other_user
        )
        cls.other_token_obj, cls.other_token = ServiceToken.objects.create_token(
            name="Other User's Service Token",
            created_by=cls.other_user,
            service_principal=cls.other_principal,
        )
        cls.uri = reverse(
            "api:ajax_revoke_service_token", kwargs={"pk": cls.token_obj.pk}
        )
        cls.other_uri = reverse(
            "api:ajax_revoke_service_token", kwargs={"pk": cls.other_token_obj.pk}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        data = {"result": "success", "message": "Service token successfully revoked!"}
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)
        self.token_obj.refresh_from_db()
        self.assertTrue(self.token_obj.revoked)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_revoking_another_users_service_token(self):
        response = self.client_auth.post(self.other_uri)
        self.assertEqual(response.status_code, 302)


class ServiceTokenExpiryUpdateTests(TestCase):
    """Collection of tests for :view:`api:ServiceTokenExpiryUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.expired_at = timezone.now() - timedelta(days=1)
        cls.principal = ServicePrincipal.objects.create(
            name="External Integration", created_by=cls.user
        )
        cls.token_obj, cls.token = ServiceToken.objects.create_token(
            name="User's Service Token",
            created_by=cls.user,
            service_principal=cls.principal,
            expiry_date=cls.expired_at,
        )
        cls.other_principal = ServicePrincipal.objects.create(
            name="Other External Integration", created_by=cls.other_user
        )
        cls.other_token_obj, cls.other_token = ServiceToken.objects.create_token(
            name="Other User's Service Token",
            created_by=cls.other_user,
            service_principal=cls.other_principal,
            expiry_date=cls.expired_at,
        )
        cls.revoked_token_obj, cls.revoked_token = ServiceToken.objects.create_token(
            name="Revoked Service Token",
            created_by=cls.user,
            service_principal=cls.principal,
            expiry_date=cls.expired_at,
            revoked=True,
        )
        cls.uri = reverse(
            "api:update_service_token_expiry", kwargs={"pk": cls.token_obj.pk}
        )
        cls.other_uri = reverse(
            "api:update_service_token_expiry", kwargs={"pk": cls.other_token_obj.pk}
        )
        cls.revoked_uri = reverse(
            "api:update_service_token_expiry", kwargs={"pk": cls.revoked_token_obj.pk}
        )
        cls.redirect_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_updates_expired_service_token_to_future_expiry(self):
        future_expiry = timezone.localtime(timezone.now() + timedelta(days=14)).replace(
            microsecond=0
        )
        response = self.client_auth.post(
            self.uri,
            data={"expiry_date": future_expiry.strftime("%Y-%m-%dT%H:%M:%S")},
        )

        self.assertRedirects(response, self.redirect_uri)
        self.token_obj.refresh_from_db()
        self.assertEqual(
            timezone.localtime(self.token_obj.expiry_date).strftime(
                "%Y-%m-%dT%H:%M:%S"
            ),
            future_expiry.strftime("%Y-%m-%dT%H:%M:%S"),
        )
        self.assertTrue(ServiceToken.objects.is_valid(self.token))

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_rejects_another_users_service_token(self):
        response = self.client_auth.post(
            self.other_uri,
            data={
                "expiry_date": (
                    timezone.localtime(timezone.now() + timedelta(days=14)).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                )
            },
        )
        self.assertEqual(response.status_code, 302)
        self.other_token_obj.refresh_from_db()
        self.assertEqual(self.other_token_obj.expiry_date, self.expired_at)

    def test_rejects_revoked_service_token(self):
        response = self.client_auth.post(
            self.revoked_uri,
            data={
                "expiry_date": (
                    timezone.localtime(timezone.now() + timedelta(days=14)).strftime(
                        "%Y-%m-%dT%H:%M:%S"
                    )
                )
            },
        )

        self.assertRedirects(response, self.redirect_uri)
        self.revoked_token_obj.refresh_from_db()
        self.assertTrue(self.revoked_token_obj.revoked)
        self.assertEqual(self.revoked_token_obj.expiry_date, self.expired_at)


class ServiceTokenCreateTests(TestCase):
    """Collection of tests for :view:`api:ServiceTokenCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.oplog = OplogFactory()
        cls.second_oplog = OplogFactory()
        ProjectAssignmentFactory(project=cls.oplog.project, operator=cls.user)
        ProjectAssignmentFactory(project=cls.second_oplog.project, operator=cls.user)
        cls.existing_principal = ServicePrincipal.objects.create(
            name="Mythic Sync", created_by=cls.user
        )
        cls.uri = reverse("api:ajax_create_service_token")
        cls.redirect_uri = reverse(
            "users:user_detail", kwargs={"username": cls.user.username}
        )

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_get_renders_create_form(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "service_token_form.html")
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], self.redirect_uri)

    def test_get_excludes_inactive_service_principals(self):
        inactive_principal = ServicePrincipal.objects.create(
            name="Retired Integration",
            active=False,
            created_by=self.user,
        )

        response = self.client_auth.get(self.uri)

        queryset = response.context["form"].fields["service_principal"].queryset
        self.assertIn(self.existing_principal, queryset)
        self.assertNotIn(inactive_principal, queryset)

    def test_post_data(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Create Service Token",
                "new_service_principal_name": "Mythic Sync Prod",
                "oplog": self.oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Create Service Token")
        self.assertEqual(obj.created_by, self.user)
        self.assertEqual(obj.get_allowed_oplog_id(), self.oplog.id)
        self.assertEqual(obj.service_principal.name, "Mythic Sync Prod")
        self.assertEqual(
            obj.service_principal.service_type, ServicePrincipal.ServiceType.INTEGRATION
        )

    def test_post_data_with_existing_service_principal(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Acme Assessment",
                "service_principal": self.existing_principal.id,
                "oplog": self.second_oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Acme Assessment")
        self.assertEqual(obj.created_by, self.user)
        self.assertEqual(obj.service_principal, self.existing_principal)
        self.assertEqual(obj.get_allowed_oplog_id(), self.second_oplog.id)

    def test_post_data_reuses_existing_principal_name(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Beta Assessment",
                "new_service_principal_name": "mythic sync",
                "oplog": self.second_oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Beta Assessment")
        self.assertEqual(obj.service_principal, self.existing_principal)

    def test_post_data_does_not_reuse_inactive_principal_name(self):
        inactive_principal = ServicePrincipal.objects.create(
            name="Retired Integration",
            active=False,
            created_by=self.user,
        )

        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Retired Integration Token",
                "new_service_principal_name": "retired integration",
                "oplog": self.second_oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )

        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Retired Integration Token")
        self.assertNotEqual(obj.service_principal, inactive_principal)
        self.assertEqual(obj.service_principal.name, "retired integration")
        self.assertTrue(obj.service_principal.active)

    def test_post_data_for_project_read_token(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.PROJECT_READ,
                "name": "Project Reader",
                "service_principal": self.existing_principal.id,
                "projects": [self.oplog.project.id],
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Project Reader")
        self.assertEqual(obj.service_principal, self.existing_principal)
        self.assertEqual(obj.get_allowed_project_id(), self.oplog.project.id)
        self.assertEqual(obj.get_allowed_project_ids(), [self.oplog.project.id])
        self.assertIsNone(obj.get_allowed_oplog_id())
        self.assertEqual(obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)

    def test_post_data_for_multi_project_read_token(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.PROJECT_READ,
                "name": "Multi-Project Reader",
                "service_principal": self.existing_principal.id,
                "projects": [self.oplog.project.id, self.second_oplog.project.id],
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="Multi-Project Reader")
        self.assertEqual(obj.service_principal, self.existing_principal)
        self.assertIsNone(obj.get_allowed_project_id())
        self.assertEqual(
            obj.get_allowed_project_ids(),
            sorted([self.oplog.project.id, self.second_oplog.project.id]),
        )
        self.assertIsNone(obj.get_allowed_oplog_id())
        self.assertEqual(obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)

    def test_post_data_rejects_inaccessible_project_ids(self):
        inaccessible_project = ProjectFactory()

        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.PROJECT_READ,
                "name": "Unauthorized Project Reader",
                "service_principal": self.existing_principal.id,
                "projects": [self.oplog.project.id, inaccessible_project.id],
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("projects", response.context["form"].errors)
        self.assertFalse(
            ServiceToken.objects.filter(name="Unauthorized Project Reader").exists()
        )

    def test_post_data_rejects_other_users_service_principal(self):
        other_user = UserFactory(password=PASSWORD)
        other_principal = ServicePrincipal.objects.create(
            name="Other User Principal",
            created_by=other_user,
        )

        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Unauthorized Principal Token",
                "service_principal": other_principal.id,
                "oplog": self.oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("service_principal", response.context["form"].errors)
        self.assertFalse(
            ServiceToken.objects.filter(name="Unauthorized Principal Token").exists()
        )

    def test_post_data_rejects_inactive_service_principal(self):
        inactive_principal = ServicePrincipal.objects.create(
            name="Retired Integration",
            active=False,
            created_by=self.user,
        )

        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.OPLOG_RW,
                "name": "Inactive Principal Token",
                "service_principal": inactive_principal.id,
                "oplog": self.oplog.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertIn("service_principal", response.context["form"].errors)
        self.assertFalse(
            ServiceToken.objects.filter(name="Inactive Principal Token").exists()
        )

    def test_post_data_for_all_accessible_project_read_token(self):
        response = self.client_auth.post(
            self.uri,
            data={
                "token_preset": ServiceTokenPreset.PROJECT_READ,
                "project_scope": ServiceTokenProjectScope.ALL_ACCESSIBLE,
                "name": "All Accessible Project Reader",
                "service_principal": self.existing_principal.id,
                "expiry_date": datetime.now() + timedelta(days=1),
            },
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = ServiceToken.objects.get(name="All Accessible Project Reader")
        self.assertEqual(obj.service_principal, self.existing_principal)
        self.assertEqual(obj.get_allowed_project_ids(), [])
        self.assertTrue(obj.has_all_accessible_project_scope())
        self.assertIsNone(obj.get_allowed_oplog_id())
        self.assertEqual(obj.get_token_preset(), ServiceTokenPreset.PROJECT_READ)
        self.assertEqual(
            obj.get_scope_display(),
            "All Accessible Projects (Read-Only)",
        )


class CheckEditPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:check_permissions")

    def setUp(self):
        self.client = Client()

    def collab_claims(self, *, model="finding", object_id=None):
        return {
            utils.COLLAB_MODEL_CLAIM: model,
            utils.COLLAB_OBJECT_ID_CLAIM: object_id or self.finding.id,
            utils.COLLAB_REPORT_ID_CLAIM: utils.COLLAB_NO_ID,
            utils.COLLAB_FINDING_ID_CLAIM: utils.COLLAB_NO_ID,
        }

    def headers(
        self,
        user,
        *,
        token_type=utils.COLLAB_JWT_TYPE,
        exp=None,
        collab_claims=None,
    ):
        extra_claims = collab_claims if token_type == utils.COLLAB_JWT_TYPE else None
        if extra_claims is None and token_type == utils.COLLAB_JWT_TYPE:
            extra_claims = self.collab_claims()
        _, token = utils.generate_jwt(
            user,
            exp=exp,
            token_type=token_type,
            extra_claims=extra_claims,
        )
        return {
            "Hasura-Action-Secret": ACTION_SECRET,
            "Authorization": f"Bearer {token}",
        }

    def login_headers(self, user):
        _, token = generate_user_jwt(user)
        return {
            "Hasura-Action-Secret": ACTION_SECRET,
            "Authorization": f"Bearer {token}",
        }

    def data(self, hasura_role="user"):
        return {
            "input": {"model": "finding", "id": self.finding.id},
            "session_variables": {"x-hasura-role": hasura_role},
        }

    def test_no_access_without_action_secret(self):
        headers = self.headers(self.manager)
        del headers["Hasura-Action-Secret"]
        response = self.client.post(
            self.uri, content_type="application/json", headers=headers, data=self.data()
        )
        self.assertEqual(response.status_code, 403)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=headers,
            data=self.data("admin"),
        )
        self.assertEqual(response.status_code, 403)

    def test_access_finding_disallowed(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.user),
            data=self.data(),
        )
        self.assertEquals(response.status_code, 403, response.content)

    def test_access_finding_allowed(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data(),
        )
        self.assertEquals(response.status_code, 200, response.content)

    def test_rejects_collab_jwt_for_different_object_scope(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(
                self.manager,
                collab_claims=self.collab_claims(object_id=self.finding.id + 1),
            ),
            data=self.data(),
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_rejects_collab_jwt_without_object_scope(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager, collab_claims={}),
            data=self.data(),
        )
        self.assertEqual(response.status_code, 403, response.content)

    def test_rejects_login_jwt(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.login_headers(self.manager),
            data=self.data(),
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_rejects_expired_collab_jwt(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(
                self.manager,
                exp=timezone.now() - timedelta(hours=1),
            ),
            data=self.data(),
        )
        self.assertEqual(response.status_code, 401, response.content)

    def test_rejects_inactive_collab_jwt_user(self):
        self.manager.is_active = False
        self.manager.save(update_fields=["is_active"])
        try:
            response = self.client.post(
                self.uri,
                content_type="application/json",
                headers=self.headers(self.manager),
                data=self.data(),
            )
        finally:
            self.manager.is_active = True
            self.manager.save(update_fields=["is_active"])
        self.assertEqual(response.status_code, 401, response.content)

    def test_access_finding_not_found(self):
        data = self.data()
        data["input"]["id"] += 1024
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(
                self.manager,
                collab_claims=self.collab_claims(object_id=data["input"]["id"]),
            ),
            data=data,
        )
        self.assertEquals(response.status_code, 404, response.content)


class GetTagsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tags = {"severity:high", "att&ck:t1159"}
        cls.report_finding = ReportFindingLinkFactory(tags=list(cls.tags))
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:graphql_get_tags")

    def setUp(self):
        self.client = Client()

    def headers(self, user):
        headers = {
            "Hasura-Action-Secret": ACTION_SECRET,
        }
        if user is not None:
            _, token = generate_user_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, hasura_role="user"):
        return {
            "input": {"model": "report_finding_link", "id": self.report_finding.id},
            "session_variables": {"x-hasura-role": hasura_role},
        }

    def test_get_report_finding_tags_allowed_manager(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data(),
        )
        self.assertEquals(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(set(body["tags"]), self.tags)

    def test_get_report_finding_tags_not_allowed(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.user),
            data=self.data(),
        )
        self.assertFalse(self.report_finding.user_can_view(self.user))
        self.assertEquals(response.status_code, 403, response.content)
        body = response.json()
        self.assertFalse("tags" in body, body)

    def test_get_report_finding_tags_allowed_admin(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(None),
            data=self.data("admin"),
        )
        self.assertEquals(response.status_code, 200)
        body = response.json()
        self.assertEqual(set(body["tags"]), self.tags)

    def test_get_report_finding_tags_allowed_project_service_token(self):
        token = create_project_read_service_token(
            self.user, self.report_finding.report.project
        )
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers={
                "Hasura-Action-Secret": ACTION_SECRET,
                "Authorization": f"Bearer {token}",
            },
            data=self.data("service"),
        )

        self.assertEquals(response.status_code, 200, response.content)
        body = response.json()
        self.assertEqual(set(body["tags"]), self.tags)


class SetTagsTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.tags = {"severity:high", "att&ck:t1159"}
        cls.report_finding = ReportFindingLinkFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:graphql_set_tags")

    def setUp(self):
        self.client = Client()

    def headers(self, user):
        headers = {
            "Hasura-Action-Secret": ACTION_SECRET,
        }
        if user is not None:
            _, token = generate_user_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, tags, hasura_role="user"):
        v = {
            "input": {
                "model": "report_finding_link",
                "id": self.report_finding.id,
                "tags": list(tags),
            },
            "session_variables": {"x-hasura-role": hasura_role},
        }
        return v

    def test_set_report_finding_tags_allowed_manager(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data(self.tags),
        )
        self.assertEquals(response.status_code, 200)
        self.report_finding.refresh_from_db()
        self.assertEqual(
            set(self.report_finding.tags.names()), self.tags, response.content
        )

    def test_set_report_finding_tags_not_allowed(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.user),
            data=self.data(self.tags),
        )
        self.assertEquals(response.status_code, 403, response.content)
        self.report_finding.refresh_from_db()
        self.assertEqual(set(self.report_finding.tags.names()), set())

    def test_set_report_finding_tags_allowed_admin(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(None),
            data=self.data(self.tags, "admin"),
        )
        self.assertEquals(response.status_code, 200)
        self.report_finding.refresh_from_db()
        self.assertEqual(set(self.report_finding.tags.names()), self.tags)


class ObjectsByTagTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.report_finding = ReportFindingLinkFactory()
        cls.report_finding.tags.set({"severity:high", "att&ck:t1159"})
        cls.report_finding.save()

        cls.user = UserFactory(password=PASSWORD)
        cls.user_with_access = UserFactory(password=PASSWORD)
        cls.user_with_access_assignment = ProjectAssignmentFactory(
            project=cls.report_finding.report.project,
            operator=cls.user_with_access,
        )
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:graphql_objects_by_tag", args=["report_finding_link"])

    def setUp(self):
        self.client = Client()

    def headers(self, user):
        headers = {
            "Hasura-Action-Secret": ACTION_SECRET,
        }
        if user is not None:
            _, token = generate_user_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, tag, hasura_role="user"):
        v = {"input": {"tag": tag}, "session_variables": {"x-hasura-role": hasura_role}}
        return v

    def test_get_anonymous_no_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(None),
            data=self.data("severity:high", hasura_role="public"),
        )
        self.assertEquals(response.status_code, 400)

    def test_get_user_no_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.user),
            data=self.data("severity:high"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [])

    def test_get_user_with_access_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.user_with_access),
            data=self.data("severity:high"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [{"id": self.report_finding.pk}])

    def test_get_project_service_token_results_are_project_scoped(self):
        other_report_finding = ReportFindingLinkFactory(tags=["severity:high"])
        token = create_project_read_service_token(
            self.user, self.report_finding.report.project
        )
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers={
                "Hasura-Action-Secret": ACTION_SECRET,
                "Authorization": f"Bearer {token}",
            },
            data=self.data("severity:high", hasura_role="service"),
        )

        self.assertEquals(response.status_code, 200)
        self.assertEqual(response.json(), [{"id": self.report_finding.pk}])
        self.assertNotIn({"id": other_report_finding.pk}, response.json())

    def test_get_project_service_token_can_query_library_findings_by_tag(self):
        finding = FindingFactory(tags=["library:useful"])
        token = create_project_read_service_token(
            self.user, self.report_finding.report.project
        )
        response = self.client.post(
            reverse("api:graphql_objects_by_tag", args=["finding"]),
            content_type="application/json",
            headers={
                "Hasura-Action-Secret": ACTION_SECRET,
                "Authorization": f"Bearer {token}",
            },
            data=self.data("library:useful", hasura_role="service"),
        )

        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [{"id": finding.pk}])

    def test_get_oplog_service_token_can_query_own_oplog_entries_by_tag(self):
        oplog = OplogFactory()
        entry = OplogEntryFactory(oplog_id=oplog, tags=["activity:interesting"])
        other_entry = OplogEntryFactory(tags=["activity:interesting"])
        token = create_oplog_read_service_token(self.user, oplog)

        response = self.client.post(
            reverse("api:graphql_objects_by_tag", args=["oplog_entry"]),
            content_type="application/json",
            headers={
                "Hasura-Action-Secret": ACTION_SECRET,
                "Authorization": f"Bearer {token}",
            },
            data=self.data("activity:interesting", hasura_role="service"),
        )

        self.assertEquals(response.status_code, 200)
        self.assertEqual(response.json(), [{"id": entry.pk}])
        self.assertNotIn({"id": other_entry.pk}, response.json())

    def test_get_oplog_service_token_cannot_query_project_objects_by_tag(self):
        token = create_oplog_read_service_token(self.user, OplogFactory())

        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers={
                "Hasura-Action-Secret": ACTION_SECRET,
                "Authorization": f"Bearer {token}",
            },
            data=self.data("severity:high", hasura_role="service"),
        )

        self.assertEquals(response.status_code, HTTPStatus.FORBIDDEN)

    def test_get_manager_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data("severity:high"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [{"id": self.report_finding.pk}])

    def test_get_manager_no_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data("thistagdoesnotexist!"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [])

    def test_get_admin_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(None),
            data=self.data("severity:high", hasura_role="admin"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [{"id": self.report_finding.pk}])


class GraphqlDownloadEvidenceViewTests(TestCase):
    """Collection of tests for :view:`api.GraphqlDownloadEvidence`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, role="user", is_active=True)
        cls.manager = UserFactory(password=PASSWORD, role="manager", is_active=True)
        cls.other_user = UserFactory(password=PASSWORD, role="user", is_active=True)

        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.finding = ReportFindingLinkFactory(report=cls.report)

        # Create evidence with finding
        cls.evidence_with_finding = EvidenceOnFindingFactory(finding=cls.finding)

        # Create evidence without finding but with report
        cls.evidence_with_report = EvidenceOnReportFactory(report=cls.report)

        # Create project assignment for user (not for manager - they don't need it)
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )

        cls.uri = reverse("api:graphql_download_evidence")

    def setUp(self):
        self.client = Client()

        # Generate JWT tokens using utils.generate_jwt
        _, self.user_token = generate_user_jwt(self.user)
        _, self.manager_token = generate_user_jwt(self.manager)
        _, self.other_user_token = generate_user_jwt(self.other_user)

    def test_download_evidence_unauthorized_no_secret(self):
        """Test that request without action secret is rejected."""
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        result = {
            "message": "Unauthorized access method",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_unauthorized_wrong_secret(self):
        """Test that request with wrong action secret is rejected."""
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET="wrong_secret",
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        result = {
            "message": "Unauthorized access method",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_no_token(self):
        """Test that request without JWT token is rejected."""
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        result = {
            "message": "No ``Authorization`` header found",
            "extensions": {
                "code": "AuthenticationMissing",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_invalid_token(self):
        """Test that request with invalid JWT token is rejected."""
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer invalid_token",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.UNAUTHORIZED)
        result = {
            "message": "Received invalid authentication token",
            "extensions": {
                "code": "AuthenticationInvalid",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_missing_id(self):
        """Test that request without evidence ID is rejected."""
        data = {"input": {}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)
        result = {
            "message": "Missing all required inputs",
            "extensions": {
                "code": "InvalidRequestBody",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_not_found(self):
        """Test that request for non-existent evidence returns 404."""
        data = {"input": {"evidenceId": 99999}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        result = {
            "message": "Evidence not found",
            "extensions": {
                "code": "EvidenceNotFound",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_forbidden_no_project_access(self):
        """Test that user without project access cannot download evidence."""
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.other_user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        result = {
            "message": "Unauthorized access",
            "extensions": {
                "code": "Unauthorized",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_success_returns_both_url_and_base64(self):
        """Test successful evidence download returns both URL and base64."""
        test_content = b"Test evidence content"

        self.evidence_with_finding.document.save(
            "test_evidence.txt", ContentFile(test_content), save=True
        )

        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        result = response.json()
        self.assertEqual(result["evidenceId"], self.evidence_with_finding.id)
        self.assertEqual(result["filename"], self.evidence_with_finding.filename)
        self.assertEqual(
            result["friendlyName"], self.evidence_with_finding.friendly_name
        )
        self.assertIn("downloadUrl", result)
        self.assertIn(str(self.evidence_with_finding.id), result["downloadUrl"])
        self.assertIn("fileBase64", result)

        # Verify base64 content
        decoded_content = base64.b64decode(result["fileBase64"])
        self.assertEqual(decoded_content, test_content)

    def test_download_evidence_with_project_service_token(self):
        """Test that a project-scoped service token can download in-scope evidence."""
        test_content = b"Service token evidence content"
        self.evidence_with_finding.document.save(
            "service_token_evidence.txt", ContentFile(test_content), save=True
        )
        token = create_project_read_service_token(self.user, self.project)
        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        decoded_content = base64.b64decode(response.json()["fileBase64"])
        self.assertEqual(decoded_content, test_content)

    def test_download_evidence_success_with_report(self):
        """Test successful evidence download for evidence with report only."""
        test_content = b"Report evidence content"

        self.evidence_with_report.document.save(
            "report_evidence.txt", ContentFile(test_content), save=True
        )

        data = {"input": {"evidenceId": self.evidence_with_report.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)

        result = response.json()
        self.assertEqual(result["evidenceId"], self.evidence_with_report.id)
        self.assertIn("downloadUrl", result)
        self.assertIn("fileBase64", result)

    def test_download_evidence_manager_access(self):
        """Test that manager can download evidence from any project."""
        test_content = b"Manager test content"

        self.evidence_with_finding.document.save(
            "manager_test.txt", ContentFile(test_content), save=True
        )

        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.manager_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = response.json()
        self.assertEqual(result["evidenceId"], self.evidence_with_finding.id)
        self.assertIn("downloadUrl", result)
        self.assertIn("fileBase64", result)

    def test_download_evidence_file_not_found(self):
        """Test that missing file returns 404."""
        # Create evidence with a file that we'll delete
        evidence = EvidenceOnFindingFactory(finding=self.finding)
        evidence.document.save(
            "temp_file.txt", ContentFile(b"temporary content"), save=True
        )

        # Get the file path and delete the physical file (but keep the DB record)
        file_path = evidence.document.path
        if os.path.exists(file_path):
            os.remove(file_path)

        data = {"input": {"evidenceId": evidence.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        result = {
            "message": "Evidence file not found on server",
            "extensions": {
                "code": "EvidenceFileNotFound",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_download_evidence_oversized_file_rejected(self):
        """Test that evidence files exceeding GHOSTWRITER_MAX_FILE_SIZE are rejected with 413."""
        # Django Imports
        from django.test import override_settings

        evidence = EvidenceOnFindingFactory(finding=self.finding)
        evidence.document.save(
            "oversize_evidence.txt", ContentFile(b"some content"), save=True
        )

        data = {"input": {"evidenceId": evidence.id}}

        # Set the limit to 1 byte so any real file exceeds it
        with override_settings(GHOSTWRITER_MAX_FILE_SIZE=1):
            response = self.client.post(
                self.uri,
                json.dumps(data),
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
                HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
            )

        self.assertEqual(response.status_code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(response.json()["extensions"]["code"], "FileTooLargeForInline")

    def test_download_evidence_with_forwarded_ip(self):
        """Test that request with forwarded IP header is handled correctly."""
        test_content = b"Forwarded IP test content"

        self.evidence_with_finding.document.save(
            "forwarded_test.txt", ContentFile(test_content), save=True
        )

        data = {"input": {"evidenceId": self.evidence_with_finding.id}}

        response = self.client.post(
            self.uri,
            json.dumps(data),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
            HTTP_X_FORWARDED_FOR="192.168.1.1",
        )

        self.assertEqual(response.status_code, HTTPStatus.OK)
        result = response.json()
        self.assertEqual(result["evidenceId"], self.evidence_with_finding.id)
        self.assertIn("downloadUrl", result)
        self.assertIn("fileBase64", result)


class GraphqlLinkOplogEvidenceTests(TestCase):
    """Collection of tests for :view:`api.GraphqlLinkOplogEvidence`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, role="user", is_active=True)
        cls.manager = UserFactory(password=PASSWORD, role="manager", is_active=True)
        cls.other_user = UserFactory(password=PASSWORD, role="user", is_active=True)

        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )

        cls.oplog_entry = OplogEntryFactory(oplog_id__project=cls.project)
        cls.evidence = EvidenceOnReportFactory(report=cls.report)

        cls.other_project = ProjectFactory()
        cls.other_report = ReportFactory(project=cls.other_project)
        cls.other_evidence = EvidenceOnReportFactory(report=cls.other_report)

        cls.uri = reverse("api:graphql_link_oplog_evidence")

    def setUp(self):
        self.client = Client()
        _, self.user_token = generate_user_jwt(self.user)
        _, self.manager_token = generate_user_jwt(self.manager)
        _, self.other_user_token = generate_user_jwt(self.other_user)

    def _post(self, data, token):
        return self.client.post(
            self.uri,
            json.dumps({"input": data}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

    def test_link_oplog_evidence_success(self):
        """Test that a user with project access can link evidence to an oplog entry."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.evidence.id},
            self.user_token,
        )
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertIn("id", result)
        self.oplog_entry.refresh_from_db()
        self.assertIn("evidence", list(self.oplog_entry.tags.names()))

    def test_link_oplog_evidence_idempotent(self):
        """Test that linking the same evidence twice returns the existing link ID."""
        r1 = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.evidence.id},
            self.user_token,
        )
        r2 = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.evidence.id},
            self.user_token,
        )
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        self.assertEqual(r1.json()["id"], r2.json()["id"])

    def test_link_oplog_evidence_manager_access(self):
        """Test that a manager can link evidence without a project assignment."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.evidence.id},
            self.manager_token,
        )
        self.assertEqual(response.status_code, 200)

    def test_link_oplog_evidence_without_access(self):
        """Test that a user without project access is rejected."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.evidence.id},
            self.other_user_token,
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(
            force_str(response.content),
            {"message": "Unauthorized access", "extensions": {"code": "Unauthorized"}},
        )

    def test_link_oplog_evidence_invalid_entry(self):
        """Test that a non-existent oplog entry returns 400."""
        response = self._post(
            {"oplogEntryId": 99999, "evidenceId": self.evidence.id},
            self.user_token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Oplog entry does not exist",
                "extensions": {"code": "OplogEntryDoesNotExist"},
            },
        )

    def test_link_oplog_evidence_invalid_evidence(self):
        """Test that a non-existent evidence ID returns 400."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": 99999},
            self.user_token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Evidence does not exist",
                "extensions": {"code": "EvidenceDoesNotExist"},
            },
        )

    def test_link_oplog_evidence_project_mismatch(self):
        """Test that evidence from a different project is rejected."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id, "evidenceId": self.other_evidence.id},
            self.user_token,
        )
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Evidence does not belong to the same project",
                "extensions": {"code": "ProjectMismatch"},
            },
        )

    def test_link_oplog_evidence_no_secret(self):
        """Test that request without action secret is rejected."""
        response = self.client.post(
            self.uri,
            json.dumps(
                {
                    "input": {
                        "oplogEntryId": self.oplog_entry.id,
                        "evidenceId": self.evidence.id,
                    }
                }
            ),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_link_oplog_evidence_missing_inputs(self):
        """Test that missing required inputs returns 400."""
        response = self.client.post(
            self.uri,
            json.dumps({"input": {}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)


class GraphqlUploadOplogRecordingTests(TestCase):
    """Collection of tests for :view:`api.GraphqlUploadOplogRecording`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, role="user", is_active=True)
        cls.manager = UserFactory(password=PASSWORD, role="manager", is_active=True)
        cls.other_user = UserFactory(password=PASSWORD, role="user", is_active=True)

        cls.project = ProjectFactory()
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )
        cls.oplog_entry = OplogEntryFactory(oplog_id__project=cls.project)

        cls.uri = reverse("api:graphql_upload_oplog_recording")

    def setUp(self):
        self.client = Client()
        _, self.user_token = generate_user_jwt(self.user)
        _, self.manager_token = generate_user_jwt(self.manager)
        _, self.other_user_token = generate_user_jwt(self.other_user)

    def _cast_b64(self):
        raw = b'{"version": 2, "width": 80, "height": 24}\n[0.5, "o", "test"]\n'
        return base64.b64encode(raw).decode()

    def _post(self, data, token):
        return self.client.post(
            self.uri,
            json.dumps({"input": data}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

    def test_upload_recording_success(self):
        """Test that a user with project access can upload a recording."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "session.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 201)
        self.assertIn("id", response.json())
        self.oplog_entry.refresh_from_db()
        self.assertIn("recording", list(self.oplog_entry.tags.names()))

    def test_upload_recording_replaces_existing(self):
        """Test that uploading a second recording replaces the first."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "first.cast",
        }
        r1 = self._post(data, self.user_token)
        self.assertEqual(r1.status_code, 201)
        first_id = r1.json()["id"]

        data["filename"] = "second.cast"
        r2 = self._post(data, self.user_token)
        self.assertEqual(r2.status_code, 201)
        second_id = r2.json()["id"]

        # IDs differ — a new recording object was created
        self.assertNotEqual(first_id, second_id)
        # Only one recording exists for the entry
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import OplogEntryRecording

        self.assertEqual(
            OplogEntryRecording.objects.filter(oplog_entry=self.oplog_entry).count(), 1
        )
        # Tag survives the delete-and-replace cycle
        self.oplog_entry.refresh_from_db()
        self.assertIn("recording", list(self.oplog_entry.tags.names()))

    def test_upload_recording_manager_access(self):
        """Test that a manager can upload a recording without a project assignment."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "manager.cast",
        }
        response = self._post(data, self.manager_token)
        self.assertEqual(response.status_code, 201)
        self.oplog_entry.refresh_from_db()
        self.assertIn("recording", list(self.oplog_entry.tags.names()))

    def test_upload_recording_without_access(self):
        """Test that a user without project access is rejected."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "unauth.cast",
        }
        response = self._post(data, self.other_user_token)
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(
            force_str(response.content),
            {"message": "Unauthorized access", "extensions": {"code": "Unauthorized"}},
        )

    def test_upload_recording_invalid_entry(self):
        """Test that a non-existent oplog entry returns 400."""
        data = {
            "oplogEntryId": 99999,
            "file_base64": self._cast_b64(),
            "filename": "missing.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Oplog entry does not exist",
                "extensions": {"code": "OplogEntryDoesNotExist"},
            },
        )

    def test_upload_recording_wrong_extension(self):
        """Test that a non-.cast file extension is rejected."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "session.mp4",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 400)

    def test_upload_recording_cast_gz_accepted(self):
        """Test that .cast.gz files are accepted."""
        # Standard Libraries
        import gzip
        from base64 import b64encode

        cast_content = (
            b'{"version": 2, "width": 80, "height": 24}\n[0.5, "o", "test"]\n'
        )
        gz_content = gzip.compress(cast_content)
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": b64encode(gz_content).decode("utf-8"),
            "filename": "session.cast.gz",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 201)

    def test_upload_recording_invalid_cast_gz_rejected(self):
        """Malformed .cast.gz files are rejected instead of crashing during parsing."""
        # Standard Libraries
        from base64 import b64encode

        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": b64encode(b"\x1f\x8b\x08\x00truncated").decode("utf-8"),
            "filename": "session.cast.gz",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["extensions"]["code"], "Invalid")

    @override_settings(GHOSTWRITER_MAX_FILE_SIZE=128)
    def test_upload_recording_gzip_bomb_like_cast_gz_rejected(self):
        """Compressed recordings that expand beyond the playback safety limit are rejected."""
        # Standard Libraries
        import gzip
        from base64 import b64encode

        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": b64encode(
                gzip.compress(b"a" * (get_cast_decompressed_bytes() + 1))
            ).decode("utf-8"),
            "filename": "session.cast.gz",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["message"], CAST_GZIP_TOO_LARGE_UPLOAD_MESSAGE)

    def test_upload_recording_invalid_base64(self):
        """Test that invalid base64 content is rejected."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": "not-valid-base64!!!",
            "filename": "session.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 400)

    def test_upload_recording_oversized_payload_rejected(self):
        """Regression test: payloads exceeding GHOSTWRITER_MAX_FILE_SIZE must return 413, not exhaust memory."""
        oversized_body = b"x" * ((settings.GHOSTWRITER_MAX_FILE_SIZE * 2) + 1)
        response = self.client.post(
            self.uri,
            oversized_body,
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )
        self.assertEqual(response.status_code, 413)
        self.assertEqual(response.json()["extensions"]["code"], "PayloadTooLarge")

    def test_upload_recording_accepts_valid_file_when_encoded_body_exceeds_file_limit(
        self,
    ):
        """Base64+JSON overhead should not cause a valid sub-limit recording upload to be rejected."""
        cast_bytes = (
            b'{"version": 2, "width": 80, "height": 24}\n'
            + b'[0.5, "o", "'
            + (b"x" * 30)
            + b'"]\n'
        )
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": base64.b64encode(cast_bytes).decode("utf-8"),
            "filename": "session.cast",
        }
        request_body = json.dumps({"input": data}).encode("utf-8")
        max_file_size = (len(cast_bytes) + len(request_body)) // 2

        with override_settings(GHOSTWRITER_MAX_FILE_SIZE=max_file_size):
            self.assertGreater(len(request_body), settings.GHOSTWRITER_MAX_FILE_SIZE)
            self.assertLessEqual(len(cast_bytes), settings.GHOSTWRITER_MAX_FILE_SIZE)

            response = self.client.post(
                self.uri,
                request_body,
                content_type="application/json",
                HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
                HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
            )
        self.assertEqual(response.status_code, 201, response.content)

    def test_upload_recording_no_secret(self):
        """Test that request without action secret is rejected."""
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": self._cast_b64(),
            "filename": "session.cast",
        }
        response = self.client.post(
            self.uri,
            json.dumps({"input": data}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_upload_recording_missing_inputs(self):
        """Test that missing required inputs returns 400."""
        response = self.client.post(
            self.uri,
            json.dumps({"input": {}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_upload_v2_populates_recording_text(self):
        """An asciicast v2 file extracts 'o' event data into recording_text."""
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import OplogEntryRecording

        raw = b'{"version": 2, "width": 80, "height": 24}\n[0.5, "o", "v2 output"]\n'
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": base64.b64encode(raw).decode(),
            "filename": "v2session.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 201)
        recording = OplogEntryRecording.objects.get(oplog_entry=self.oplog_entry)
        self.assertIn("v2 output", recording.recording_text)

    def test_upload_v3_populates_recording_text(self):
        """An asciicast v3 file extracts both 'o' and 'i' event data into recording_text."""
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import OplogEntryRecording

        raw = (
            b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n'
            b'[0.5, "o", "v3 command output"]\n'
            b'[1.0, "i", "user input"]\n'
        )
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": base64.b64encode(raw).decode(),
            "filename": "v3session.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 201)
        recording = OplogEntryRecording.objects.get(oplog_entry=self.oplog_entry)
        self.assertIn("v3 command output", recording.recording_text)
        self.assertIn("user input", recording.recording_text)

    def test_upload_v1_triggers_warning(self):
        """An asciicast v1 file (unsupported format) uploads successfully but returns a 'warning' key.

        asciicast v1 uses a single JSON object for the entire recording (not newline-delimited
        JSON), so the header will have version=1 and the parser will reject it.
        """
        # v1 format: single JSON object with a 'stdout' array — version key is 1
        raw = b'{"version": 1, "width": 80, "height": 24, "stdout": [[0.5, "hello"]]}\n'
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": base64.b64encode(raw).decode(),
            "filename": "v1session.cast",
        }
        response = self._post(data, self.user_token)
        self.assertEqual(response.status_code, 201)
        result = response.json()
        self.assertIn("warning", result)

    def test_upload_unsupported_version_recording_text_empty(self):
        """When parsing fails the recording still saves, but recording_text is empty."""
        # Ghostwriter Libraries
        from ghostwriter.oplog.models import OplogEntryRecording

        raw = b'{"version": 1, "width": 80, "height": 24, "stdout": [[0.5, "hello"]]}\n'
        data = {
            "oplogEntryId": self.oplog_entry.id,
            "file_base64": base64.b64encode(raw).decode(),
            "filename": "v1empty.cast",
        }
        self._post(data, self.user_token)
        recording = OplogEntryRecording.objects.get(oplog_entry=self.oplog_entry)
        self.assertEqual(recording.recording_text, "")


class GraphqlDownloadRecordingTests(TestCase):
    """Collection of tests for :view:`api.GraphqlDownloadRecording`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD, role="user", is_active=True)
        cls.manager = UserFactory(password=PASSWORD, role="manager", is_active=True)
        cls.other_user = UserFactory(password=PASSWORD, role="user", is_active=True)

        cls.project = ProjectFactory()
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )
        cls.oplog_entry = OplogEntryFactory(oplog_id__project=cls.project)
        cls.recording = OplogEntryRecordingFactory(oplog_entry=cls.oplog_entry)

        cls.entry_no_recording = OplogEntryFactory(oplog_id__project=cls.project)

        cls.uri = reverse("api:graphql_download_oplog_recording")

    def setUp(self):
        self.client = Client()
        _, self.user_token = generate_user_jwt(self.user)
        _, self.manager_token = generate_user_jwt(self.manager)
        _, self.other_user_token = generate_user_jwt(self.other_user)

    def _post(self, data, token):
        return self.client.post(
            self.uri,
            json.dumps({"input": data}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )

    def test_download_recording_success(self):
        """Test that a user with project access can download a recording."""
        response = self._post({"oplogEntryId": self.oplog_entry.id}, self.user_token)
        self.assertEqual(response.status_code, 200)
        result = response.json()
        self.assertEqual(result["recordingId"], self.recording.id)
        self.assertEqual(result["oplogEntryId"], self.oplog_entry.id)
        self.assertIn("filename", result)
        self.assertIn("downloadUrl", result)
        self.assertIn("fileBase64", result)
        # Verify the base64 decodes to the original file content
        decoded = base64.b64decode(result["fileBase64"])
        self.recording.recording_file.seek(0)
        self.assertEqual(decoded, self.recording.recording_file.read())

    def test_download_recording_with_project_service_token(self):
        """Test that a project-scoped service token can download in-scope recordings."""
        token = create_project_read_service_token(self.user, self.project)
        response = self._post({"oplogEntryId": self.oplog_entry.id}, token)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["recordingId"], self.recording.id)

    def test_download_recording_with_oplog_rw_service_token(self):
        """Test that an oplog-scoped service token can download its oplog's recordings."""
        token = create_oplog_rw_service_token(self.user, self.oplog_entry.oplog_id)
        response = self._post({"oplogEntryId": self.oplog_entry.id}, token)

        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.json()["recordingId"], self.recording.id)

    def test_download_recording_with_oplog_rw_service_token_rejects_other_oplog(self):
        """Test that an oplog-scoped service token cannot download other oplog recordings."""
        other_entry = OplogEntryFactory()
        OplogEntryRecordingFactory(oplog_entry=other_entry)
        token = create_oplog_rw_service_token(self.user, self.oplog_entry.oplog_id)

        response = self._post({"oplogEntryId": other_entry.id}, token)

        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertJSONEqual(
            force_str(response.content),
            {"message": "Unauthorized access", "extensions": {"code": "Unauthorized"}},
        )

    def test_download_recording_manager_access(self):
        """Test that a manager can download a recording without a project assignment."""
        response = self._post({"oplogEntryId": self.oplog_entry.id}, self.manager_token)
        self.assertEqual(response.status_code, 200)

    def test_download_recording_without_access(self):
        """Test that a user without project access is rejected."""
        response = self._post(
            {"oplogEntryId": self.oplog_entry.id}, self.other_user_token
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)
        self.assertJSONEqual(
            force_str(response.content),
            {"message": "Unauthorized access", "extensions": {"code": "Unauthorized"}},
        )

    def test_download_recording_invalid_entry(self):
        """Test that a non-existent oplog entry returns 404."""
        response = self._post({"oplogEntryId": 99999}, self.user_token)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Oplog entry not found",
                "extensions": {"code": "OplogEntryNotFound"},
            },
        )

    def test_download_recording_no_recording(self):
        """Test that an oplog entry without a recording returns 404."""
        response = self._post(
            {"oplogEntryId": self.entry_no_recording.id}, self.user_token
        )
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "No recording found for this oplog entry",
                "extensions": {"code": "RecordingNotFound"},
            },
        )

    def test_download_recording_file_not_found(self):
        """Test that a missing physical file returns 404."""
        entry = OplogEntryFactory(oplog_id__project=self.project)
        recording = OplogEntryRecordingFactory(oplog_entry=entry)
        file_path = recording.recording_file.path
        if os.path.exists(file_path):
            os.remove(file_path)

        response = self._post({"oplogEntryId": entry.id}, self.user_token)
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "message": "Recording file not found on server",
                "extensions": {"code": "RecordingFileNotFound"},
            },
        )

    def test_download_recording_no_secret(self):
        """Test that request without action secret is rejected."""
        response = self.client.post(
            self.uri,
            json.dumps({"input": {"oplogEntryId": self.oplog_entry.id}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
        )
        self.assertEqual(response.status_code, HTTPStatus.FORBIDDEN)

    def test_download_recording_missing_inputs(self):
        """Test that missing required inputs returns 400."""
        response = self.client.post(
            self.uri,
            json.dumps({"input": {}}),
            content_type="application/json",
            HTTP_AUTHORIZATION=f"Bearer {self.user_token}",
            HTTP_HASURA_ACTION_SECRET=ACTION_SECRET,
        )
        self.assertEqual(response.status_code, HTTPStatus.BAD_REQUEST)

    def test_download_recording_oversized_file_rejected(self):
        """Test that recording files exceeding GHOSTWRITER_MAX_FILE_SIZE are rejected with 413."""
        # Django Imports
        from django.test import override_settings

        # Set the limit to 1 byte so any real file exceeds it
        with override_settings(GHOSTWRITER_MAX_FILE_SIZE=1):
            response = self._post(
                {"oplogEntryId": self.oplog_entry.id}, self.user_token
            )

        self.assertEqual(response.status_code, HTTPStatus.REQUEST_ENTITY_TOO_LARGE)
        self.assertEqual(response.json()["extensions"]["code"], "FileTooLargeForInline")
