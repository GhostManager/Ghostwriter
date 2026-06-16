# Standard Libraries
from unittest.mock import Mock, patch

# Django Imports
from django.test import Client, TestCase, override_settings, tag
from django.urls import reverse

# 3rd Party Libraries
from health_check.contrib.psutil import Disk, Memory
from health_check.exceptions import HealthCheckException, ServiceReturnedUnexpectedResult, ServiceWarning

# Ghostwriter Libraries
from ghostwriter.modules.health_utils import HasuraBackend
from ghostwriter.status.views import HealthCheckCustomView


# Health checks for RAM and disk cannot be completed successfully in the GitHub CI/CD pipeline
@tag("GitHub")
class HealthCheckCustomViewTests(TestCase):  # pragma: no cover
    """Collection of tests for :view:`status.HealthCheckCustomView`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("status:healthcheck")

    def setUp(self):
        self.client = Client()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200, response.context)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "health_check.html")

    def test_format_options(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)

        response = self.client.get(f"{self.uri}?format=json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["content-type"], "application/json")

        response = self.client.get(self.uri, HTTP_ACCEPT="application/json")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["content-type"], "application/json")

        response = self.client.get(self.uri, HTTP_ACCEPT="text/html")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(response["content-type"], "text/html")

    @override_settings(HEALTH_CHECK={"DISK_USAGE_MAX": 75, "MEMORY_MIN": 512})
    def test_psutil_checks_use_configured_thresholds(self):
        checks = list(HealthCheckCustomView().get_checks())

        disk_check = next(check for check in checks if isinstance(check, Disk))
        memory_check = next(check for check in checks if isinstance(check, Memory))

        self.assertEqual(disk_check.max_disk_usage_percent, 75)
        self.assertEqual(memory_check.min_gibibytes_available, 0.5)

    @override_settings(HEALTH_CHECK={"DISK_USAGE_MAX": 100, "MEMORY_MIN": 0})
    def test_view_displays_configured_thresholds(self):
        response = self.client.get(self.uri)

        self.assertContains(response, "Monitoring Thresholds")
        self.assertContains(response, "Disk Usage Warning Threshold")
        self.assertContains(response, "100%")
        self.assertContains(response, "Minimum Available Memory")
        self.assertContains(response, "0 MB")


class HasuraBackendTests(TestCase):
    """Collection of tests for :class:`modules.health_utils.HasuraBackend`."""

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_passes_for_ok_response(self, mock_get):
        mock_get.return_value = Mock(ok=True, text="OK")

        HasuraBackend().run()

        mock_get.assert_called_once_with("http://graphql_engine:8080/healthz", timeout=5)

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_raises_warning_for_warn_response(self, mock_get):
        mock_get.return_value = Mock(ok=True, text="WARN: inconsistent metadata")

        with self.assertRaises(ServiceWarning):
            HasuraBackend().run()

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_raises_unexpected_result_for_unrecognized_success_response(self, mock_get):
        mock_get.return_value = Mock(ok=True, text="STARTING")

        with self.assertRaises(ServiceReturnedUnexpectedResult):
            HasuraBackend().run()

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_raises_error_for_non_success_response(self, mock_get):
        mock_get.return_value = Mock(ok=False, text="ERROR")

        with self.assertRaises(HealthCheckException):
            HasuraBackend().run()


class HealthCheckSimpleViewTests(TestCase):
    """Collection of tests for :view:`status.HealthCheckSimpleView`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("status:healthcheck_simple")

    def setUp(self):
        self.uri = reverse("status:healthcheck_simple")
        self.client = Client()

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"OK", response.content)
