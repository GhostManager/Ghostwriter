# Standard Libraries
from types import SimpleNamespace
from unittest.mock import patch

# Django Imports
from django.test import RequestFactory, TestCase

# Ghostwriter Libraries
from ghostwriter.users.adapters import SocialAccountAdapter


class SocialAccountAdapterTests(TestCase):
    """Collection of tests for :class:`users.adapters.SocialAccountAdapter`."""

    def test_on_authentication_error_logs_and_returns(self):
        adapter = SocialAccountAdapter()
        request = RequestFactory().get("/accounts/microsoft/login/callback/")
        provider = SimpleNamespace(id="microsoft")
        exception = Exception("invalid_client")

        self.assertFalse(hasattr(adapter, "authentication_error"))
        with patch("ghostwriter.users.adapters.logger.error") as mock_logger_error:
            response = adapter.on_authentication_error(
                request,
                provider,
                error="unknown",
                exception=exception,
                extra_context={"provider": "microsoft"},
            )

        self.assertIsNone(response)
        mock_logger_error.assert_called_once_with(
            "Error authenticating with social account: %s %s %s",
            "unknown",
            exception,
            {"provider": "microsoft"},
        )
