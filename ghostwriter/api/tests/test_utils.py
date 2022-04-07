# Standard Libraries
import logging
from datetime import datetime

# Django Imports
from django.test import Client, TestCase

# Ghostwriter Libraries
from ghostwriter.api import utils
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
