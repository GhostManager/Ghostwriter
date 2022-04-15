# Standard Libraries
import logging
from datetime import datetime

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

    def test_generate_jwt_with_expiration(self):
        expiration = datetime(2099, 1, 1).timestamp()
        payload, encoded_payload = utils.generate_jwt(
            self.user, exp=expiration
        )
        self.assertTrue(payload["exp"], expiration)

    def test_verify_jwt(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        try:
            self.assertTrue(utils.verify_jwt_user(payload["https://hasura.io/jwt/claims"]))
        except AttributeError:
            self.fail("verify_jwt_user() raised an AttributeError unexpectedly!")

    def test_verify_jwt_with_invalid_user(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Id"] = "999"
        try:
            self.assertFalse(utils.verify_jwt_user(payload["https://hasura.io/jwt/claims"]))
        except AttributeError:
            self.fail("verify_jwt_user() raised an AttributeError unexpectedly!")

    def test_get_jwt_payload(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        try:
            self.assertTrue(utils.get_jwt_payload(encoded_payload))
        except AttributeError:
            self.fail("get_jwt_payload() raised an AttributeError unexpectedly!")

    def test_get_jwt_payload_with_invalid_token(self):
        token = (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxIiwic3Vi"
            "X25hbWUiOiJCZW5ueSB0aGUgR2hvc3QiLCJzdWJfZW1haWwiOiJiZW5ue"
            "UBnaG9zdHdyaXRlci53aWtpIiwidXNlcm5hbWUiOiJiZW5ueSIsImlhdC"
            "I6MTUxNjIzOTAyMn0.DZSXsRRAr3sS2fIOmhxFxzdzjoMGG-JzKLB2QGGFhFk"
        )
        try:
            self.assertFalse(utils.get_jwt_payload(token))
        except AttributeError:
            self.fail("get_jwt_payload() raised an AttributeError unexpectedly!")

    def test_verify_hasura_claims(self):
        payload, encoded_payload = utils.generate_jwt(self.user)
        try:
            self.assertTrue(utils.verify_hasura_claims(payload))
        except AttributeError:
            self.fail("verify_hasura_claims() raised an AttributeError unexpectedly!")

    def test_verify_hasura_claims_without_claims(self):
        payload, token = utils.generate_jwt(self.user)
        del payload["https://hasura.io/jwt/claims"]
        result = utils.verify_hasura_claims(payload)
        self.assertFalse(result)


class HasuraWebhookTests(TestCase):
    """Collection of tests for the `users:graphql_webhook`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("graphql_webhook")
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

    def test_graphql_webhook_with_valid_jwt(self):
        payload, token = utils.generate_jwt(self.user)
        data = {
            "X-Hasura-Role": f"{self.user.role}",
            "X-Hasura-User-Id": f"{self.user.id}",
            "X-Hasura-User-Name": f"{self.user.username}",
        }
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_graphql_webhook_with_valid_jwt_and_inactive_user(self):
        payload, token = utils.generate_jwt(self.user)
        self.user.is_active = False
        self.user.save()
        response = self.client.get(
            self.uri,
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
            self.uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), self.public_data)

    def test_graphql_webhook_without_claims(self):
        payload, token = utils.generate_jwt(self.user, exclude_hasura=True)
        response = self.client.get(
            self.uri,
            content_type="application/json",
            **{"HTTP_AUTHORIZATION": f"Bearer {token}", },
        )
        self.assertEqual(response.status_code, 401)


class HasuraLoginTests(TestCase):
    """Collection of tests for the `users:graphql_login`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("graphql_login")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_graphql_login(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["login"]`` keys are not present
        self.assertTrue(response.json()["token"])

    def test_graphql_login_with_invalid_credentials(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": "Not the Password"}
        }
        result = {
            "message": "Invalid credentials",
            "extensions": {"code": "InvalidCredentials", },
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 401)
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_login_requires_secret(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

    def test_graphql_login_rejects_bad_request(self):
        data = {
            "bad_input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 400)

    def test_graphql_login_without_secret(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        result = {
            "message": "Unauthorized access method",
            "extensions": {"code": "Unauthorized", },
        }
        self.assertJSONEqual(force_str(response.content), result)

    def test_graphql_login_with_invalid_secret(self):
        data = {
            "input": {"username": f"{self.user.username}", "password": f"{PASSWORD}"}
        }
        response = self.client.post(
            self.uri,
            data=data,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "wrong", },
        )
        self.assertEqual(response.status_code, 403)

        result = {
            "message": "Unauthorized access method",
            "extensions": {"code": "Unauthorized", },
        }
        self.assertJSONEqual(force_str(response.content), result)


class HasuraWhoamiTests(TestCase):
    """Collection of tests for the `users:graphql_whoami`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("graphql_whoami")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_graphql_whoami(self):
        payload, token = utils.generate_jwt(self.user)
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 200)
        # Test bypasses Hasura so the ``["data"]["whoami"]`` keys are not present
        self.assertEqual(response.json()["username"], self.user.username)

    def test_graphql_whoami_rejects_missing_jwt(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", },
        )
        self.assertEqual(response.status_code, 400)

    def test_graphql_whoami_requires_valid_jwt(self):
        token = "GARBAGE!"
        response = self.client.post(
            self.uri,
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": "changeme", "HTTP_AUTHORIZATION": f"Bearer {token}"},
        )
        self.assertEqual(response.status_code, 401)

    def test_graphql_whoami_without_secret(self):
        response = self.client.post(
            self.uri,
            content_type="application/json",
        )
        self.assertEqual(response.status_code, 403)

        result = {
            "message": "Unauthorized access method",
            "extensions": {"code": "Unauthorized", },
        }
        self.assertJSONEqual(force_str(response.content), result)
