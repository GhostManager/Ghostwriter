"""Tests for passive voice API endpoint."""

# Standard Libraries
from unittest.mock import MagicMock, patch

# Django Imports
from django.test import TestCase, RequestFactory, override_settings
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.api.views import _validate_passive_voice_request
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

        # API returns JSON 401 for unauthenticated requests (not redirect)
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["error"], "Authentication required")

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

    def test_rejects_whitespace_only_text(self):
        """Test that whitespace-only text returns error."""
        response = self.client.post(
            self.url, {"text": "   \n\t  "}, content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertEqual(data["error"], "Text field is required")

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

    def test_handles_invalid_json(self):
        """Test handling of malformed JSON."""
        response = self.client.post(
            self.url, "invalid json", content_type="application/json"
        )

        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)

    @patch("ghostwriter.api.views.get_detector")
    def test_handles_detector_failure(self, mock_get_detector):
        """Test handling of detector failures."""
        # Mock detector to raise an exception during processing
        mock_detector = mock_get_detector.return_value
        mock_detector.detect_passive_sentences.side_effect = RuntimeError(
            "spaCy processing error"
        )

        response = self.client.post(
            self.url,
            {"text": "The report was written."},
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 500)
        data = response.json()
        self.assertIn("error", data)
        self.assertEqual(data["error"], "Failed to analyze text")


class ValidatePassiveVoiceRequestTests(TestCase):
    """Tests for _validate_passive_voice_request helper function."""

    def setUp(self):
        """Set up request factory and test user."""
        self.factory = RequestFactory()
        self.user = UserFactory()

    def _make_request(self, method="POST", body=b'{"text": "Test."}', user=None):
        """Create a mock request for testing."""
        if method == "POST":
            request = self.factory.post(
                "/api/v1/passive-voice/detect",
                data=body,
                content_type="application/json",
            )
        else:
            request = self.factory.get("/api/v1/passive-voice/detect")
        request.user = user if user else self.user
        request._body = body
        return request

    def test_returns_text_on_valid_request(self):
        """Test that valid request returns (text, None)."""
        request = self._make_request(body=b'{"text": "The report was written."}')

        text, error = _validate_passive_voice_request(request)

        self.assertEqual(text, "The report was written.")
        self.assertIsNone(error)

    def test_returns_error_for_unauthenticated_request(self):
        """Test that unauthenticated request returns 401 error response."""
        anon_user = MagicMock()
        anon_user.is_authenticated = False
        request = self._make_request(user=anon_user)

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 401)

    def test_returns_error_for_get_method(self):
        """Test that GET request returns 405 error response."""
        request = self._make_request(method="GET")

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 405)

    def test_returns_error_for_invalid_json(self):
        """Test that invalid JSON returns 400 error response."""
        request = self._make_request(body=b"not valid json")

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    def test_returns_error_for_empty_text(self):
        """Test that empty text returns 400 error response."""
        request = self._make_request(body=b'{"text": ""}')

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    def test_returns_error_for_whitespace_only_text(self):
        """Test that whitespace-only text returns 400 error response."""
        request = self._make_request(body=b'{"text": "   \\n\\t  "}')

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 400)

    @override_settings(SPACY_MAX_TEXT_LENGTH=10)
    def test_returns_error_for_text_exceeding_max_length(self):
        """Test that text exceeding max length returns 413 error response."""
        request = self._make_request(body=b'{"text": "This is a very long text."}')

        text, error = _validate_passive_voice_request(request)

        self.assertIsNone(text)
        self.assertIsNotNone(error)
        self.assertEqual(error.status_code, 413)
