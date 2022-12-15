# Standard Libraries
import logging
from datetime import date, datetime, timedelta

# Django Imports
from django.conf import settings
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.models import APIKey
from ghostwriter.factories import (
    ActivityTypeFactory,
    DomainFactory,
    DomainStatusFactory,
    EvidenceFactory,
    FindingFactory,
    HistoryFactory,
    OplogEntryFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportTemplateFactory,
    ServerHistoryFactory,
    ServerRoleFactory,
    ServerStatusFactory,
    StaticServerFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"

ACTION_SECRET = settings.HASURA_ACTION_SECRET


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
        data = self.generate_domain_data(self.project.pk, self.domain.pk, self.activity.pk, note="Test note")
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
        data = self.generate_server_data(
            self.project.pk, self.server.pk, self.activity.pk, self.server_role.pk, note="Test note"
        )
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


class GraphqlDeleteEvidenceActionTests(TestCase):
    """Collection of tests for :view:`GraphqlDeleteEvidenceAction`."""

    @classmethod
    def setUpTestData(cls):
        cls.Evidence = EvidenceFactory._meta.model

        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_delete_evidence")

        cls.project = ProjectFactory()
        cls.other_project = ProjectFactory()
        ProjectAssignmentFactory(operator=cls.user, project=cls.project)

        cls.report = ReportFactory(project=cls.project)
        cls.other_report = ReportFactory(project=cls.other_project)

        cls.finding = ReportFindingLinkFactory(report=cls.report)
        cls.other_finding = ReportFindingLinkFactory(report=cls.other_report)

        cls.evidence = EvidenceFactory(finding=cls.finding)
        cls.other_evidence = EvidenceFactory(finding=cls.other_finding)

    def setUp(self):
        self.client = Client()

    def generate_data(self, evidence_id):
        return {
            "input": {
                "evidenceId": evidence_id,
            }
        }

    def test_deleting_evidence(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.evidence.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(self.Evidence.objects.filter(id=self.evidence.id).exists())

    def test_deleting_evidence_with_invalid_id(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(999),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_deleting_evidence_without_access(self):
        _, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            data=self.generate_data(self.other_evidence.id),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 401)


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


# Tests related to Hasura Event Triggers


class GraphqlDomainUpdateEventTests(TestCase):
    """Collection of tests for :view:`api:GraphqlDomainUpdateEvent`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_domain_update_event")
        cls.domain = DomainFactory(name="chrismaddalena.com")
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
                        "domain_status_id": cls.domain.domain_status.id,
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
        response = self.client.post(self.other_uri)
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
