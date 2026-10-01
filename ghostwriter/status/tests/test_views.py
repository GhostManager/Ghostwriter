# Standard Libraries
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Django Imports
from django.test import Client, TestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone

# 3rd Party Libraries
from asgiref.sync import async_to_sync
from django_q.models import Task
from health_check.contrib.psutil import Disk, Memory
from health_check.exceptions import (
    HealthCheckException,
    ServiceReturnedUnexpectedResult,
    ServiceUnavailable,
    ServiceWarning,
)

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.home.models import DashboardExceptionDismissal
from ghostwriter.modules.health_utils import ConfiguredDisk, HasuraBackend
from ghostwriter.status.views import HealthCheckCustomView


class StatusNotificationSummaryTests(TestCase):
    """The status page explains failed-job warnings without exposing job details."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(role="user")
        cls.manager = UserFactory(role="manager")
        cls.uri = reverse("status:healthcheck")
        cls.task = Task.objects.create(
            id=uuid4().hex,
            name="private-failed-job",
            func="ghostwriter.shepherd.tasks.check_domains",
            hook="",
            args=(),
            kwargs={},
            result="Private traceback",
            group="Private background job",
            started=timezone.now(),
            stopped=timezone.now(),
            success=False,
        )

    def setUp(self):
        checks_patcher = patch.object(
            HealthCheckCustomView, "get_checks", return_value=[]
        )
        self.get_checks = checks_patcher.start()
        self.addCleanup(checks_patcher.stop)
        self.client.force_login(self.manager)

    def test_privileged_user_sees_failed_job_summary(self):
        response = self.client.get(self.uri)

        self.assertTrue(response.context["has_failed_tasks"])
        self.assertTrue(response.context["has_system_warning"])
        self.assertFalse(response.context["has_check_failures"])
        self.assertContains(response, "Background jobs need attention")
        self.assertContains(response, "Attention required")
        self.assertContains(response, "Review the failed-job notifications")
        self.assertContains(response, reverse("home:dashboard"))
        self.assertNotContains(response, "All monitored services are operational")
        self.assertNotContains(response, self.task.group)
        self.assertNotContains(response, self.task.result)
        self.assertNotContains(response, "Clear all")

    def test_cleared_failed_jobs_do_not_warn(self):
        DashboardExceptionDismissal.objects.create(
            task_id=self.task.id, dismissed_by=self.manager
        )

        response = self.client.get(self.uri)

        self.assertFalse(response.context["has_system_warning"])
        self.assertContains(response, "All monitored services are operational")
        self.assertNotContains(response, "Contact a manager or admin")

    def test_successful_jobs_do_not_warn(self):
        self.task.success = True
        self.task.save(update_fields=["success"])

        response = self.client.get(self.uri)

        self.assertFalse(response.context["has_system_warning"])
        self.assertContains(response, "All monitored services are operational")

    def test_diagnostic_formats_reject_regular_and_anonymous_users(self):
        formats = ("", "json", "text", "atom", "rss", "openmetrics")
        for user in (self.user, None):
            if user is None:
                self.client.logout()
            else:
                self.client.force_login(user)
            for response_format in formats:
                with self.subTest(user=user, response_format=response_format):
                    response = self.client.get(self.uri, {"format": response_format})

                    self.assertEqual(response.status_code, 403)
                    self.assertNotIn(self.task.group, response.content.decode())
                    self.assertNotIn(self.task.result, response.content.decode())
        self.get_checks.assert_not_called()

    def test_content_negotiation_and_head_reject_regular_users(self):
        self.client.force_login(self.user)
        for accept in ("text/html", "application/json", "text/plain"):
            with self.subTest(accept=accept):
                response = self.client.get(self.uri, HTTP_ACCEPT=accept)
                self.assertEqual(response.status_code, 403)
        self.assertEqual(self.client.head(self.uri).status_code, 403)
        self.get_checks.assert_not_called()

    def test_admin_can_view_detailed_status(self):
        self.client.force_login(UserFactory(role="admin"))

        response = self.client.get(self.uri)

        self.assertContains(response, "Service checks")
        self.assertContains(response, "Background jobs need attention")

    def test_manager_can_view_diagnostic_formats(self):
        for response_format in ("json", "text", "atom", "rss", "openmetrics"):
            with self.subTest(response_format=response_format):
                response = self.client.get(self.uri, {"format": response_format})
                self.assertEqual(response.status_code, 200)

    def test_inactive_admin_cannot_view_detailed_status(self):
        self.client.force_login(UserFactory(role="admin", is_active=False))

        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 403)
        self.get_checks.assert_not_called()


class DashboardHealthSummaryTests(TestCase):
    """Dashboard health includes configured capacity warnings and service failures."""

    @patch("health_check.contrib.psutil.psutil.disk_usage")
    def test_disk_threshold_controls_dashboard_warning(self, disk_usage):
        disk_usage.return_value = SimpleNamespace(percent=94.5)
        for threshold, expected_state in ((90, "WARNING"), (95, "OK")):
            with self.subTest(threshold=threshold), override_settings(
                HEALTH_CHECK={"DISK_USAGE_MAX": threshold, "MEMORY_MIN": 0}
            ):
                view = HealthCheckCustomView()
                with patch.object(view, "get_checks", return_value=[ConfiguredDisk()]):
                    summary = async_to_sync(view.get_dashboard_summary)()

                self.assertEqual(summary["state"], expected_state)
                if expected_state == "WARNING":
                    self.assertEqual(summary["issues"][0]["display_name"], "Disk")
                    self.assertTrue(summary["issues"][0]["is_warning"])
                    self.assertIn("94.5", str(summary["issues"][0]["result"].error))
                else:
                    self.assertEqual(summary["issues"], [])
                context = view.get_context_data()
                self.assertEqual(context["has_check_failures"], expected_state != "OK")

    def test_service_failure_takes_precedence_over_capacity_warning(self):
        results = [
            SimpleNamespace(
                check=ConfiguredDisk(), error=ServiceWarning("94.5% disk usage")
            ),
            SimpleNamespace(
                check=HasuraBackend(), error=ServiceUnavailable("GraphQL unavailable")
            ),
        ]
        checks = [Mock(get_result=AsyncMock(return_value=result)) for result in results]
        view = HealthCheckCustomView()
        with patch.object(view, "get_checks", return_value=checks):
            summary = async_to_sync(view.get_dashboard_summary)()

        self.assertEqual(summary["state"], "ERROR")
        self.assertEqual(len(summary["issues"]), 2)
        self.assertEqual(summary["issues"][1]["display_name"], "Hasura GraphQL Engine")
        self.assertFalse(summary["issues"][1]["is_warning"])


# Health checks for RAM and disk cannot be completed successfully in the GitHub CI/CD pipeline
@tag("GitHub")
class HealthCheckCustomViewTests(TestCase):  # pragma: no cover
    """Collection of tests for :view:`status.HealthCheckCustomView`."""

    @classmethod
    def setUpTestData(cls):
        cls.uri = reverse("status:healthcheck")
        cls.admin = UserFactory(role="admin")

    def setUp(self):
        self.client = Client()
        self.client.force_login(self.admin)

    def test_view_uri_exists_at_desired_location(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200, response.context)

    def test_view_uses_correct_template(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "health_check.html")

    def test_authenticated_view_hides_inherited_top_bar(self):
        response = self.client.get(self.uri)

        self.assertNotContains(response, 'class="top-bar')
        self.assertNotContains(response, 'class="navbar-avatar"')
        self.assertContains(response, "Return home")

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

        self.assertContains(response, 'class="status-page"')
        self.assertContains(response, 'class="status-section"')
        self.assertContains(response, 'class="status-section status-service-section"')
        self.assertNotContains(response, 'class="card status-section')
        self.assertContains(response, "Current readout")
        self.assertContains(response, "Return home")
        self.assertContains(response, "Refresh checks")
        self.assertContains(response, "Monitoring thresholds")
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
