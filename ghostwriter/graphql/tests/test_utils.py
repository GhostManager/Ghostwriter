# Standard Libraries
import logging

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter import utils
from ghostwriter.factories import UserFactory

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class JwtUtilsTests(TestCase):
    """Collection of tests for JWT utilities and GraphQL Action endpoints."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.webhook_uri = reverse("graphql_webhook")
        cls.login_uri = reverse("graphql_login")
        cls.whoami_uri = reverse("graphql_whoami")
        cls.public_data = {
            "X-Hasura-Role": "public",
            "X-Hasura-User-Id": "-1",
            "X-Hasura-User-Name": "anonymous",
        }

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_generate_jwt(self):
        try:
            payload, encoded_payload = utils.generate_jwt(self.user)
        except AttributeError:
            self.fail("generate_jwt() raised an AttributeError unexpectedly!")
        try:
            self.assertTrue(utils.verify_jwt_user(payload["https://hasura.io/jwt/claims"]))
        except AttributeError:
            self.fail("verify_jwt_user() raised an AttributeError unexpectedly!")
        try:
            self.assertTrue(utils.get_jwt_payload(encoded_payload))
        except AttributeError:
            self.fail("get_jwt_payload() raised an AttributeError unexpectedly!")
        try:
            self.assertTrue(utils.verify_hasura_claims(payload))
        except AttributeError:
            self.fail("verify_hasura_claims() raised an AttributeError unexpectedly!")

    def test_graphql_login(self):
        data = {
            "input": {"username": F"{self.user.username}", "password": F"{PASSWORD}"}
        }
        response = self.client.post(
            self.login_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["login"]`` keys are not present
        self.assertTrue(response.json()["token"])

    def test_graphql_login_requires_secret(self):
        data = {
            "input": {"username": F"{self.user.username}", "password": F"{PASSWORD}"}
        }
        response = self.client.post(
            self.login_uri,
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_graphql_login_rejects_bad_request(self):
        data = {
            "bad_input": {"username": F"{self.user.username}", "password": F"{PASSWORD}"}
        }
        response = self.client.post(
            self.login_uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 400)

    def test_graphql_whoami(self):
        payload, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.whoami_uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["whoami"]`` keys are not present
        self.assertEqual(response.json()["username"], self.user.username)

    def test_graphql_whoami_rejects_missing_jwt(self):
        response = self.client.post(
            self.whoami_uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 400)

    def test_graphql_whoami_requires_valid_jwt(self):
        token = "GARBAGE!"
        response = self.client.post(
            self.whoami_uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_graphql_webhookwith_valid_jwt(self):
        payload, token = utils.generate_jwt(self.user)
        data = {
            "X-Hasura-Role": f"{self.user.role}",
            "X-Hasura-User-Id": f"{self.user.id}",
            "X-Hasura-User-Name": f"{self.user.username}",
        }
        response = self.client.get(
            self.webhook_uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhookwith_valid_jwt_and_inactive_user(self):
        payload, token = utils.generate_jwt(self.user)
        self.user.is_active = False
        self.user.save()
        response = self.client.get(
            self.webhook_uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), self.public_data)
        self.user.is_active = True
        self.user.save()

    def test_graphql_webhook_with_invalid_jwt(self):
        token = "GARBAGE!"
        response = self.client.get(
            self.webhook_uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), self.public_data)
