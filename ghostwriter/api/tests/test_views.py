# Standard Libraries
import base64
import logging
import os
from datetime import date, datetime, timedelta

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str

# 3rd Party Libraries
import factory
from django_otp.plugins.otp_static.models import StaticToken

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.models import APIKey
from ghostwriter.factories import (
    ActivityTypeFactory,
    BlankReportFindingLinkFactory,
    ClientFactory,
    EvidenceOnReportFactory,
    DomainFactory,
    DomainStatusFactory,
    EvidenceOnFindingFactory,
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
    FindingFactory,
    HistoryFactory,
    OplogEntryFactory,
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
from ghostwriter.reporting.models import Evidence

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"

ACTION_SECRET = settings.HASURA_ACTION_SECRET

User = get_user_model()


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
        cls.user_token_obj, cls.user_token = APIKey.objects.create_token(user=cls.user, name="Valid Token")
        cls.inactive_token_obj, cls.inactive_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Inactive User Token"
        )
        cls.expired_token_obj, cls.expired_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Expired Token", expiry_date=yesterday
        )
        cls.revoked_token_obj, cls.revoked_token = APIKey.objects.create_token(
            user=cls.inactive_user, name="Revoked Token", revoked=True
        )
        # Test data set as required inputs for the test view
        cls.data = {"input": {"id": 1, "function": "test_func", "args": {"arg1": "test"}}}

    def setUp(self):
        self.client = Client()

    def test_action_with_valid_jwt(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_action_requires_correct_secret(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "wrong", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 403)

    def test_action_requires_secret(self):
        _, token = utils.generate_jwt(self.user)
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
        _, token = utils.generate_jwt(self.user)
        # Test with no data
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data="Not JSON",
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
                "code": "JWTMissing",
            },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_action_with_valid_jwt_and_inactive_user(self):
        _, token = utils.generate_jwt(self.user)
        self.user.is_active = False
        self.user.save()
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_valid_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {self.user_token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_action_with_valid_tracked_token_and_inactive_user(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {self.inactive_token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_expired_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {self.expired_token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_revoked_tracked_token(self):
        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {self.revoked_token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_action_with_incomplete_header(self):
        result = {
            "message": "No ``Authorization`` header found",
            "extensions": {
                "code": "JWTMissing",
            },
        }

        response = self.client.post(
            self.uri,
            data=self.data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": ""},
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
        _, token = utils.generate_jwt(self.user)
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

        cls.user_2fa = UserFactory(password=PASSWORD)
        cls.user_2fa_required = UserFactory(password=PASSWORD, require_2fa=True)
        cls.user_2fa.totpdevice_set.create()
        static_model = cls.user_2fa.staticdevice_set.create()
        static_model.token_set.create(token=StaticToken.random_token())

        cls.uri = reverse("api:graphql_login")

    def setUp(self):
        self.client = Client()

    def test_graphql_login(self):
        data = {"input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}}
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
        self.assertTrue(response.json()["token"])

    def test_graphql_login_with_invalid_credentials(self):
        data = {"input": {"username": f"{self.user.username}", "password": "Not the Password"}}
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

    def test_graphql_login_with_2fa(self):
        result = {
            "message": "Login and generate a token from your user profile",
            "extensions": {
                "code": "2FARequired",
            },
        }

        data = {"input": {"username": f"{self.user_2fa.username}", "password": f"{PASSWORD}"}}
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

        data = {"input": {"username": f"{self.user_2fa_required.username}", "password": f"{PASSWORD}"}}
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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_graphql_whoami(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["whoami"]`` keys are not present
        self.assertEqual(response.json()["username"], self.user.username)

    def test_graphql_whoami_with_tracked_token(self):
        user_token_obj, user_token = APIKey.objects.create_token(user=self.user, name="Valid Token")
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {user_token}"},
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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_graphql_generate_report(self):
        _, token = utils.generate_jwt(self.user)
        data = {"input": {"id": self.report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_graphql_generate_report_with_invalid_report(self):
        _, token = utils.generate_jwt(self.user)
        data = {"input": {"id": 999}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = {"input": {"id": self.other_report.pk}}
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        cls.assignment = ProjectAssignmentFactory(operator=cls.user, project=cls.project)

        cls.domain_unavailable = DomainStatusFactory(domain_status="Unavailable")
        cls.domain = DomainFactory()
        cls.unavailable_domain = DomainFactory(domain_status=cls.domain_unavailable)
        cls.expired_domain = DomainFactory(expiration=timezone.now() - timedelta(days=1))

        cls.server_unavailable = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory()
        cls.unavailable_server = StaticServerFactory(server_status=cls.server_unavailable)
        cls.server_role = ServerRoleFactory()

        cls.domain_uri = reverse("api:graphql_checkout_domain")
        cls.server_uri = reverse("api:graphql_checkout_server")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def generate_domain_data(
        self,
        project,
        domain,
        activity,
        start_date=date.today() - timedelta(days=1),
        end_date=date.today() + timedelta(days=1),
        note=None,
    ):
        return {
            "input": {
                "projectId": project,
                "domainId": domain,
                "activityTypeId": activity,
                "startDate": start_date,
                "endDate": end_date,
                "note": note,
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
        note=None,
    ):
        return {
            "input": {
                "projectId": project,
                "serverId": server,
                "activityTypeId": activity,
                "serverRoleId": server_role,
                "startDate": start_date,
                "endDate": end_date,
                "note": note,
            }
        }

    def test_graphql_checkout_domain(self):
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, self.domain.pk, self.activity.pk)
        del data["input"]["note"]
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_server_data(self.project.pk, self.server.pk, self.activity.pk, self.server_role.pk)
        del data["input"]["note"]
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_server_data(self.project.pk, self.server.pk, self.activity.pk, 999, note="Test note")
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, 999, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, self.domain.pk, 999)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(999, self.domain.pk, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, self.unavailable_domain.pk, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_server_data(
            self.project.pk, self.unavailable_server.pk, self.activity.pk, self.server_role.pk
        )
        response = self.client.post(
            self.server_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.project.pk, self.expired_domain.pk, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        data = self.generate_domain_data(self.other_project.pk, self.domain.pk, self.activity.pk)
        response = self.client.post(
            self.domain_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        cls.other_checkout = HistoryFactory(domain=cls.other_domain, project=cls.other_project)

        cls.server_available = ServerStatusFactory(server_status="Available")
        cls.server_unavailable = ServerStatusFactory(server_status="Unavailable")
        cls.server = StaticServerFactory(server_status=cls.server_unavailable)
        cls.server_checkout = ServerHistoryFactory(server=cls.server, project=cls.project)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def generate_data(self, checkout_id):
        return {
            "input": {
                "checkoutId": checkout_id,
            }
        }

    def test_deleting_domain_checkout(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(self.domain_checkout.pk),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.domain.refresh_from_db()
        self.assertEqual(self.domain.domain_status, self.domain_available)

    def test_deleting_server_checkout(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.server_uri,
            data=self.generate_data(self.server_checkout.pk),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.server.refresh_from_db()
        self.assertEqual(self.server.server_status, self.server_available)

    def test_deleting_domain_checkout_without_access(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(self.other_checkout.pk),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.domain_uri,
            data=self.generate_data(checkout_id=999),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.template.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.ReportTemplate.objects.filter(id=self.template.id).exists())

    def test_deleting_template_with_invalid_id(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(999),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_deleting_protected_template_with_access(self):
        _, token = utils.generate_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.protected_template.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_deleting_protected_template_without_access(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.protected_template.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 401)

        response = self.client.post(
            self.uri,
            data=self.generate_data(self.client_template.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        new_finding = response.json()["id"]
        self.assertTrue(self.ReportFindingLink.objects.filter(id=new_finding).exists())
        self.assertEqual(len(self.finding.tags.similar_objects()), 1)
        self.assertEqual(
            len(self.ReportFindingLink.objects.get(id=new_finding).tags.similar_objects()),
            len(self.finding.tags.similar_objects()),
        )
        self.assertEqual(list(self.finding.tags.names()), self.tags)

    def test_attaching_finding_with_invalid_report(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, 999),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)
        data = {"message": "Report does not exist", "extensions": {"code": "ReportDoesNotExist"}}
        self.assertJSONEqual(force_str(response.content), data)

    def test_attaching_finding_with_invalid_finding(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(999, self.report.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)
        data = {"message": "Finding does not exist", "extensions": {"code": "FindingDoesNotExist"}}
        self.assertJSONEqual(force_str(response.content), data)

    def test_attaching_finding_with_mgr_access(self):
        _, token = utils.generate_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

    def test_attaching_finding_without_access(self):
        _, token = utils.generate_jwt(self.other_user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.finding.id, self.report.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        cls.assignment = ProjectAssignmentFactory(project=cls.project, operator=cls.user)
        cls.report = ReportFactory(project=cls.project)
        cls.finding = ReportFindingLinkFactory(report=cls.report)

    def setUp(self):
        self.client = Client()

    def test_upload_report(self):
        _, token = utils.generate_jwt(self.user)
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        id = response.json()["id"]
        evidence = Evidence.objects.get(pk=id)
        self.assertEqual(evidence.caption, data["caption"])
        self.assertEqual(evidence.document.read(), "Hello, world!".encode("utf-8"))
        self.assertEqual(evidence.pk, self.report.evidence_set.all().get().pk)

    def test_upload_report_forbidden(self):
        _, token = utils.generate_jwt(self.disallowed_user)
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertNotEqual(response.status_code, 201, response.content)

    def test_upload_finding(self):
        _, token = utils.generate_jwt(self.user)
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 201, response.content)
        id = response.json()["id"]
        evidence = Evidence.objects.get(pk=id)
        self.assertEqual(evidence.caption, data["caption"])
        self.assertEqual(evidence.document.read(), "Hello, world!".encode("utf-8"))
        self.assertEqual(evidence.pk, self.finding.evidence_set.all().get().pk)

    def test_upload_finding_forbidden(self):
        _, token = utils.generate_jwt(self.disallowed_user)
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertNotEqual(response.status_code, 201, response.content)


class GraphqlGenerateCodenameActionTests(TestCase):
    """Collection of tests for :view:`GraphqlGenerateCodenameAction`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_generate_codename")

    def setUp(self):
        self.client = Client()

    def test_generating_codename(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_graphql_get_extra_field_spec(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "finding"}},
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "Finding"}},
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "Reporting.Finding"}},
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["extraFieldSpec"]["test_field"]["internalName"], "test_field")

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data={"input": {"model": "bad_model_name"}},
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()["message"], "Model does not exist")


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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def generate_data(self, name, email, username, role, **kwargs):
        return {
            "input": {
                "name": name,
                "email": email,
                "username": username,
                "role": role,
                "password": PASSWORD,
                **kwargs
            }
        }

    def test_graphql_create_user(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data(
                "validuser", "validuser@specterops.io", "validuser", "user",
                require2fa=True,
                timezone="America/New_York",
                enableFindingCreate=False,
                enableFindingEdit=False,
                enableFindingDelete=False,
                enableObservationCreate=False,
                enableObservationEdit=False,
                enableObservationDelete=False,
                phone="123-456-7890",
            ),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)

        created_user = User.objects.get(username="validuser")
        self.assertEqual(created_user.email, "validuser@specterops.io")
        self.assertEqual(created_user.require_2fa, True)

        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data("validuser", "validuser@specterops.io", "validuser", "user"),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data("badtimezone", "badtimezone@specterops.io", "badtimezone", "user", timezone="PST"),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data("badrole", "badrole@specterops.io", "badrole", "invalid"),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.mgr_user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data("mgruser", "mgruser@specterops.io", "mgruser", "manager"),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        _, token = utils.generate_jwt(self.unprivileged_user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            data=self.generate_data("unprivileged", "unprivileged@specterops.io", "unprivileged", "manager"),
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
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
        cls.domain = DomainFactory(name="chrismaddalena.com", domain_status=cls.expired_status)
        cls.sample_data = {
            "event": {
                "data": {
                    "new": {
                        "expired": False,
                        "registrar": "Hover",
                        "note": "<p>The personal website and blog of Christopher Maddalena</p>",
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

        self.sample_data["event"]["data"]["new"]["domain_status_id"] = self.available_status.id
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
        first_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=1)
        second_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=2)
        third_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=3)

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
        new_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity)
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
        finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=0)

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
        finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=100)

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
        total_findings = self.ReportFindingLink.objects.filter(report=self.report).count()
        self.assertEqual(finding.position, total_findings)

    def test_position_change_on_delete(self):
        self.ReportFindingLink.objects.all().delete()

        first_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=1)
        second_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=2)
        third_finding = ReportFindingLinkFactory(report=self.report, severity=self.critical_severity, position=3)

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
                        "note": cls.other_contact.note,
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
                        "note": cls.other_contact.note,
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
                    "new": {"id": cls.objective.id, "complete": False, "deadline": cls.objective.deadline},
                    "old": {"id": cls.objective.id, "complete": True, "deadline": cls.objective.deadline},
                },
            }
        }
        cls.incomplete_data = {
            "event": {
                "data": {
                    "new": {"id": cls.objective.id, "complete": True, "deadline": cls.objective.deadline},
                    "old": {"id": cls.objective.id, "complete": False, "deadline": cls.objective.deadline},
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
                    "new": {"id": cls.task.id, "complete": False, "deadline": cls.task.deadline},
                    "old": {"id": cls.task.id, "complete": True, "deadline": cls.task.deadline},
                },
            }
        }
        cls.incomplete_data = {
            "event": {
                "data": {
                    "new": {"id": cls.task.id, "complete": True, "deadline": cls.task.deadline},
                    "old": {"id": cls.task.id, "complete": False, "deadline": cls.task.deadline},
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
            document=factory.django.FileField(filename="finding_evidence.txt", data=b"lorem ipsum"),
        )
        cls.report_evidence = EvidenceOnReportFactory(
            friendly_name="Test Report Evidence",
            report=cls.finding.report,
            document=factory.django.FileField(filename="finding_evidence.txt", data=b"lorem ipsum"),
        )
        cls.deleted_evidence = EvidenceOnFindingFactory(finding=cls.finding, friendly_name="Deleted Evidence")

        # Add a blank finding to the report for regression testing updates on findings with blank fields
        BlankReportFindingLinkFactory(report=cls.report_evidence.report)
        EvidenceOnReportFactory(report=cls.report_evidence.report, friendly_name="Blank Test")

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
            self.finding.description, "<p>Here is some evidence:</p><p>{{.New Name}}</p><p>{{.ref New Name}}</p>"
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
            self.finding.impact, "<p>Here is some evidence:</p><p>{{.New Name}}</p><p>{{.ref New Name}}</p>"
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
        self.assertEqual(self.finding.mitigation, "<p>Here is some evidence:</p><p></p>")


# Tests related to CBVs for :model:`api:APIKey`


class ApiKeyRevokeTests(TestCase):
    """Collection of tests for :view:`api:ApiKeyRevoke`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.token_obj, cls.token = APIKey.objects.create_token(user=cls.user, name="User's Token")
        cls.other_token_obj, cls.other_token = APIKey.objects.create_token(
            user=cls.other_user, name="Other User's Token"
        )
        cls.uri = reverse("api:ajax_revoke_token", kwargs={"pk": cls.token_obj.pk})
        cls.other_uri = reverse("api:ajax_revoke_token", kwargs={"pk": cls.other_token_obj.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

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


class ApiKeyCreateTests(TestCase):
    """Collection of tests for :view:`api:ApiKeyCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:ajax_create_token")
        cls.redirect_uri = reverse("users:user_detail", kwargs={"username": cls.user.username})

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
        self.assertTemplateUsed(response, "token_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], self.redirect_uri)

    def test_post_data(self):
        response = self.client_auth.post(
            self.uri, data={"name": "CreateView Test", "expiry_date": datetime.now() + timedelta(days=1)}
        )
        self.assertRedirects(response, self.redirect_uri)
        obj = APIKey.objects.get(name="CreateView Test")
        self.assertEqual(obj.user, self.user)


class CheckEditPermissionsTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("api:check_permissions")

    def setUp(self):
        self.client = Client()

    def headers(self, user):
        _, token = utils.generate_jwt(user)
        return {
            "Hasura-Action-Secret": ACTION_SECRET,
            "Authorization": f"Bearer {token}"
        }

    def data(self, hasura_role="user"):
        return {
            "input": {"model": "finding", "id": self.finding.id},
            "session_variables": {"x-hasura-role": hasura_role}
        }

    def test_no_access_without_action_secret(self):
        headers = self.headers(self.manager)
        del headers["Hasura-Action-Secret"]
        response = self.client.post(self.uri, content_type="application/json", headers=headers, data=self.data())
        self.assertEqual(response.status_code, 403)

        response = self.client.post(self.uri, content_type="application/json", headers=headers, data=self.data("admin"))
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

    def test_access_finding_not_found(self):
        data = self.data()
        data["input"]["id"] += 1024
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
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
            _, token = utils.generate_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, hasura_role="user"):
        return {
            "input": {"model": "report_finding_link", "id": self.report_finding.id},
            "session_variables": {"x-hasura-role": hasura_role}
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
            _, token = utils.generate_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, tags, hasura_role="user"):
        v = {
            "input": {"model": "report_finding_link", "id": self.report_finding.id, "tags": list(tags)},
            "session_variables": {"x-hasura-role": hasura_role}
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
        self.assertEqual(set(self.report_finding.tags.names()), self.tags, response.content)

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
            _, token = utils.generate_jwt(user)
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def data(self, tag, hasura_role="user"):
        v = {
            "input": {"tag": tag},
            "session_variables": {"x-hasura-role": hasura_role}
        }
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
        self.assertJSONEqual(response.content, [
            {"id": self.report_finding.pk}
        ])

    def test_get_manager_results(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            headers=self.headers(self.manager),
            data=self.data("severity:high"),
        )
        self.assertEquals(response.status_code, 200)
        self.assertJSONEqual(response.content, [
            {"id": self.report_finding.pk}
        ])

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
        self.assertJSONEqual(response.content, [
            {"id": self.report_finding.pk}
        ])
