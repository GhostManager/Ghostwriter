# Standard Libraries
import json
import logging

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.api.models import APIKey
from ghostwriter.factories import AcronymFactory, UserFactory
from ghostwriter.reporting.models import Acronym

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"

ACTION_SECRET = settings.HASURA_ACTION_SECRET

User = get_user_model()


class GraphqlGetAcronymsActionTests(TestCase):
    """Collection of tests for :view:`api:GraphqlGetAcronymsAction`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("api:graphql_get_acronyms")
        cls.user_token_obj, cls.user_token = APIKey.objects.create_token(
            user=cls.user, name="Test Token"
        )

        # Create test acronyms
        cls.acronym1 = AcronymFactory(
            acronym="CIA",
            expansion="Central Intelligence Agency",
            is_active=True,
            priority=10,
        )
        cls.acronym2 = AcronymFactory(
            acronym="NSA",
            expansion="National Security Agency",
            is_active=True,
            priority=5,
        )
        cls.acronym3 = AcronymFactory(
            acronym="API",
            expansion="Application Programming Interface",
            is_active=True,
            priority=8,
        )
        cls.acronym4 = AcronymFactory(
            acronym="API",
            expansion="Advanced Persistent Infrastructure",
            is_active=False,
            priority=3,
        )

    def test_view_requires_authentication(self):
        """Test that the view requires authentication."""
        data = {"input": {}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{"HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}"},
        )
        self.assertEqual(response.status_code, 400)

    def test_view_requires_valid_token(self):
        """Test that the view requires a valid token."""
        data = {"input": {}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": "Bearer invalid_token",
            },
        )
        self.assertEqual(response.status_code, 401)

    def test_get_all_acronyms(self):
        """Test retrieving all active acronyms."""
        data = {"input": {}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertIn("acronyms", response_data)
        # Should only return active acronyms by default
        self.assertEqual(len(response_data["acronyms"]), 3)

    def test_filter_by_acronym(self):
        """Test filtering by acronym text."""
        data = {"input": {"acronym": "CIA"}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 1)
        self.assertEqual(response_data["acronyms"][0]["acronym"], "CIA")
        self.assertEqual(
            response_data["acronyms"][0]["expansion"], "Central Intelligence Agency"
        )

    def test_filter_by_acronym_case_insensitive(self):
        """Test filtering by acronym is case-insensitive."""
        data = {"input": {"acronym": "cia"}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 1)
        self.assertEqual(response_data["acronyms"][0]["acronym"], "CIA")

    def test_filter_by_is_active_true(self):
        """Test filtering by is_active=True."""
        data = {"input": {"is_active": True}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 3)
        for acronym in response_data["acronyms"]:
            self.assertTrue(acronym["is_active"])

    def test_filter_by_is_active_false(self):
        """Test filtering by is_active=False."""
        data = {"input": {"is_active": False}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 1)
        self.assertFalse(response_data["acronyms"][0]["is_active"])

    def test_filter_multiple_expansions_same_acronym(self):
        """Test filtering returns multiple expansions for same acronym."""
        data = {"input": {"acronym": "API"}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # Should return only active API expansion
        self.assertEqual(len(response_data["acronyms"]), 1)
        self.assertEqual(
            response_data["acronyms"][0]["expansion"],
            "Application Programming Interface",
        )

    def test_pagination_limit(self):
        """Test limiting number of results."""
        data = {"input": {"limit": 2}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 2)

    def test_ordering_by_priority(self):
        """Test results are ordered by priority descending."""
        data = {"input": {}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # Should be ordered: CIA (10), API (8), NSA (5)
        priorities = [a["priority"] for a in response_data["acronyms"]]
        self.assertEqual(priorities, sorted(priorities, reverse=True))

    def test_empty_results(self):
        """Test query with no matching results."""
        data = {"input": {"acronym": "NONEXISTENT"}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 0)

    def test_response_includes_all_fields(self):
        """Test response includes all expected fields."""
        data = {"input": {"acronym": "CIA"}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        acronym = response_data["acronyms"][0]
        self.assertIn("id", acronym)
        self.assertIn("acronym", acronym)
        self.assertIn("expansion", acronym)
        self.assertIn("is_active", acronym)
        self.assertIn("priority", acronym)
        self.assertIn("override_builtin", acronym)
        self.assertIn("created_at", acronym)
        self.assertIn("updated_at", acronym)

    def test_invalid_limit_handled(self):
        """Test that invalid limit values are handled gracefully."""
        data = {"input": {"limit": -1}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        # Should ignore negative limit or return all results
        self.assertGreater(len(response_data["acronyms"]), 0)

    def test_limit_zero_returns_all(self):
        """Test that limit=0 returns all results."""
        data = {"input": {"limit": 0}}
        response = self.client.post(
            self.uri,
            data=json.dumps(data),
            content_type="application/json",
            **{
                "HTTP_HASURA_ACTION_SECRET": f"{ACTION_SECRET}",
                "HTTP_AUTHORIZATION": f"Bearer {self.user_token}",
            },
        )
        self.assertEqual(response.status_code, 200)
        response_data = response.json()
        self.assertEqual(len(response_data["acronyms"]), 3)
