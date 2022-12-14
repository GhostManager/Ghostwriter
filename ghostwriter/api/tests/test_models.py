# Standard Libraries
import logging
from datetime import timedelta

# Django Imports
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.models import APIKey
from ghostwriter.factories import UserFactory

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
        token_obj, token = APIKey.objects.create_token(user=self.user, name="Valid Token")
        self.assertTrue(token_obj)

        # Read
        read = APIKey.objects.get_from_token(token)
        self.assertEqual(read.token, token)

        # Update
        token_obj.name = "Updated Token"
        token_obj.save()
        updated = APIKey.objects.get(token=token)
        self.assertEqual(updated.name, "Updated Token")

        # Delete
        token_obj.delete()
        self.assertFalse(APIKey.objects.all().exists())

    def test_get_usable_keys(self):
        APIKey.objects.all().exists()
        APIKey.objects.create_token(user=self.user, name="Valid Token")
        APIKey.objects.create_token(user=self.user, name="Revoked Token", revoked=True)
        APIKey.objects.create_token(user=self.user, name="Expired Token", expiry_date=self.yesterday)

        self.assertEqual(APIKey.objects.all().count(), 3)
        self.assertEqual(APIKey.objects.get_usable_keys().count(), 2)

    def test_token_revocation(self):
        token_obj, _ = APIKey.objects.create_token(user=self.user, name="Valid Token", revoked=True)
        token_obj.revoked = False
        with self.assertRaises(ValidationError):
            token_obj.clean()
            token_obj.save()

    def test_token_expiration(self):
        valid_obj, _ = APIKey.objects.create_token(user=self.user, name="Valid Token")
        exp_obj, _ = APIKey.objects.create_token(user=self.user, name="Expired Token", expiry_date=self.yesterday)

        self.assertTrue(exp_obj.has_expired)
        self.assertFalse(valid_obj.has_expired)

    def test_is_valid(self):
        _, valid_token = APIKey.objects.create_token(user=self.user, name="Valid Token")
        _, inactive_token = APIKey.objects.create_token(user=self.inactive_user, name="Inactive Token")
        _, revoked_token = APIKey.objects.create_token(
            user=self.user, name="Revoked Token", revoked=True, expiry_date=timezone.now() + timedelta(days=5)
        )
        _, expired_token = APIKey.objects.create_token(user=self.user, name="Expired Token", expiry_date=self.yesterday)

        self.assertTrue(APIKey.objects.is_valid(valid_token))
        self.assertFalse(APIKey.objects.is_valid(inactive_token))
        self.assertFalse(APIKey.objects.is_valid(revoked_token))
        self.assertFalse(APIKey.objects.is_valid(expired_token))
        self.assertFalse(APIKey.objects.is_valid("GARBAGE"))
