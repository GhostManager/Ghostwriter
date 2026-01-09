"""Tests for passive voice API endpoint."""

# Django Imports
from django.conf import settings
from django.test import TestCase, override_settings
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory


class PassiveVoiceAPITests(TestCase):
    """Test suite for passive voice detection API."""

    @classmethod
    def setUpTestData(cls):
        """Set up test user."""
        cls.user = UserFactory(password="testpass")
        cls.url = reverse("api:passive_voice_detect")

    def setUp(self):
        """Authenticate for each test."""
        self.client.login(username=self.user.username, password="testpass")

    def test_requires_authentication(self):
        """Test that endpoint requires authentication."""
        self.client.logout()
        response = self.client.post(
            self.url, {"text": "Test text."}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 403)

    def test_detects_passive_voice(self):
        """Test successful passive voice detection."""
        response = self.client.post(
            self.url,
            {"text": "The report was written by the team."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("ranges", data)
        self.assertIn("count", data)
        self.assertEqual(data["count"], 1)
        self.assertIsInstance(data["ranges"], list)
        self.assertEqual(len(data["ranges"]), 1)

    def test_returns_multiple_ranges(self):
        """Test detection of multiple passive sentences."""
        response = self.client.post(
            self.url,
            {"text": "The system was tested. The vulnerabilities were found."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 2)
        self.assertEqual(len(data["ranges"]), 2)

    def test_returns_empty_for_active_voice(self):
        """Test that active voice returns empty results."""
        response = self.client.post(
            self.url,
            {"text": "We tested the system."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data["count"], 0)
        self.assertEqual(len(data["ranges"]), 0)

    def test_rejects_empty_text(self):
        """Test that empty text returns error."""
        response = self.client.post(
            self.url, {"text": ""}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    def test_rejects_missing_text_field(self):
        """Test that missing text field returns error."""
        response = self.client.post(self.url, {}, content_type="application/json")

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    @override_settings(SPACY_MAX_TEXT_LENGTH=100)
    def test_respects_max_length_setting(self):
        """Test that max length from settings is enforced."""
        large_text = "x" * 150
        response = self.client.post(
            self.url, {"text": large_text}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 413)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("maximum length", data["error"])

    def test_range_format_is_correct(self):
        """Test that ranges are in correct format [start, end]."""
        response = self.client.post(
            self.url,
            {"text": "The report was written."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(len(data["ranges"]), 1)

        # Each range should be a list of two integers
        range_item = data["ranges"][0]
        self.assertIsInstance(range_item, list)
        self.assertEqual(len(range_item), 2)
        self.assertIsInstance(range_item[0], int)
        self.assertIsInstance(range_item[1], int)
        # End should be greater than start
        self.assertGreater(range_item[1], range_item[0])

    def test_handles_unicode_text(self):
        """Test handling of unicode characters."""
        response = self.client.post(
            self.url,
            {"text": "The café was closed by the owner. 😊"},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        data = response.json()
        # Should detect the passive sentence despite unicode
        self.assertGreaterEqual(data["count"], 1)

    def test_only_accepts_post_method(self):
        """Test that only POST method is accepted."""
        response = self.client.get(self.url)
        self.assertEqual(response.status_code, 405)  # Method Not Allowed
