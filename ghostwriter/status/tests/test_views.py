# Standard Libraries
import json
from asgiref.sync import async_to_sync
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch
from uuid import uuid4

# Django Imports
from django.test import Client, TestCase, override_settings, tag
from django.urls import reverse
from django.utils import timezone
from django.utils.feedgenerator import rfc2822_date

# 3rd Party Libraries
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
from ghostwriter.status.health import get_dashboard_health_summary
from ghostwriter.status.models import DashboardHealthSnapshot
from ghostwriter.status.tasks import refresh_dashboard_health
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

    def test_html_rejects_regular_and_anonymous_users(self):
        formats = ("", "html", "unknown")
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

    def test_html_content_negotiation_and_head_reject_regular_users(self):
        self.client.force_login(self.user)
        for accept in ("text/html", "application/xhtml+xml", "text/*", "*/*"):
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

    def test_manager_can_view_public_monitoring_formats(self):
        for response_format in ("json", "text", "atom", "rss", "openmetrics"):
            with self.subTest(response_format=response_format):
                response = self.client.get(self.uri, {"format": response_format})
                self.assertEqual(response.status_code, 200)

    def test_inactive_admin_cannot_view_detailed_status(self):
        self.client.force_login(UserFactory(role="admin", is_active=False))

        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 403)
        self.get_checks.assert_not_called()


class PublicHealthStatusTests(TestCase):
    """Public monitoring exposes status without diagnostics or configuration."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(role="user")
        cls.admin = UserFactory(role="admin")
        cls.uri = reverse("status:healthcheck")

    def setUp(self):
        self.results = [
            SimpleNamespace(check=HasuraBackend(), error=None, time_taken=0.01),
            SimpleNamespace(
                check=ConfiguredDisk(),
                error=ServiceWarning("private disk path /srv/private-volume"),
                time_taken=0.02,
            ),
            SimpleNamespace(
                check=SimpleNamespace(
                    endpoint="http://private-host:8080",
                    labels={"credential": "private-service-secret"},
                ),
                error=ServiceUnavailable("private connection error and traceback"),
                time_taken=0.03,
            ),
        ]
        self.checks = [
            Mock(get_result=AsyncMock(return_value=result)) for result in self.results
        ]
        patcher = patch.object(
            HealthCheckCustomView, "get_checks", return_value=self.checks
        )
        patcher.start()
        self.addCleanup(patcher.stop)

    def assert_basic_response(self, response):
        for private_value in (
            "/srv/private-volume",
            "private-host",
            "private-service-secret",
            "private connection error",
            "traceback",
            "credential",
        ):
            self.assertNotIn(private_value, response.content.decode())

    def test_machine_formats_are_public_and_hide_diagnostics_for_all_roles(self):
        for user in (None, self.user, self.admin):
            if user is None:
                self.client.logout()
            else:
                self.client.force_login(user)
            for response_format in ("json", "text", "atom", "rss", "openmetrics"):
                with self.subTest(user=user, response_format=response_format):
                    response = self.client.get(self.uri, {"format": response_format})

                    expected_status = (
                        500 if response_format in ("json", "text") else 200
                    )
                    self.assertEqual(response.status_code, expected_status)
                    self.assert_basic_response(response)
                    self.assertIn("Accept", response.headers["Vary"])
                    self.assertIn("no-store", response.headers["Cache-Control"])

    def test_json_contains_only_basic_service_statuses(self):
        response = self.client.get(self.uri, HTTP_ACCEPT="application/json")

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            response.json(),
            {
                "Hasura GraphQL Engine": "working",
                "Disk": "warning",
                "SimpleNamespace": "error",
            },
        )

    def test_healthy_json_returns_working_and_http_200(self):
        for result in self.results:
            result.error = None

        response = self.client.get(self.uri, {"format": "json"})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.json().values()), {"working"})

    def test_machine_content_negotiation_and_query_overrides_are_public(self):
        for accept in (
            "application/json",
            "application/*",
            "text/plain",
            "application/atom+xml",
            "application/rss+xml",
            "application/openmetrics-text; version=1.0.0",
            "text/html;q=0.1, application/json;q=0.9",
        ):
            with self.subTest(accept=accept):
                response = self.client.get(self.uri, HTTP_ACCEPT=accept)
                self.assertIn(response.status_code, (200, 500))
                self.assert_basic_response(response)
        response = self.client.get(
            self.uri, {"format": "json"}, HTTP_ACCEPT="text/html"
        )
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.headers["Content-Type"], "application/json")

    def test_html_preference_stays_restricted_before_running_checks(self):
        for accept in (
            "application/json;q=0.1, text/html;q=0.9",
            "text/html, application/json",
        ):
            with self.subTest(accept=accept):
                response = self.client.get(self.uri, HTTP_ACCEPT=accept)
                self.assertEqual(response.status_code, 403)
        for check in self.checks:
            check.get_result.assert_not_called()

    def test_unknown_media_types_are_not_public(self):
        response = self.client.get(self.uri, HTTP_ACCEPT="application/yaml")

        self.assertEqual(response.status_code, 403)
        for check in self.checks:
            check.get_result.assert_not_called()

    @patch("ghostwriter.status.views.is_public_status_request", return_value=True)
    def test_html_renderer_stays_restricted_if_format_selection_changes(
        self, public_request
    ):
        response = self.client.get(self.uri, HTTP_ACCEPT="text/html")

        self.assertEqual(response.status_code, 403)
        self.assert_basic_response(response)

    def test_openmetrics_preserves_health_metrics_without_configuration_labels(self):
        response = self.client.get(self.uri, {"format": "openmetrics"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(
            response, 'django_health_check_status{check="HasuraBackend"} 1'
        )
        self.assertContains(
            response, 'django_health_check_status{check="ConfiguredDisk"} 0'
        )
        self.assertContains(response, "django_health_check_overall_status 0")
        self.assertContains(
            response,
            'django_health_check_response_time_seconds{check="ConfiguredDisk"} 0.020000',
        )
        self.assert_basic_response(response)

    def test_feeds_keep_only_basic_status_descriptions(self):
        for response_format in ("atom", "rss"):
            with self.subTest(response_format=response_format):
                response = self.client.get(self.uri, {"format": response_format})
                for status in ("working", "warning", "error"):
                    self.assertContains(response, status)
                self.assert_basic_response(response)

    def test_rss_preserves_existing_failure_timestamps_and_categories(self):
        response = self.client.get(self.uri, {"format": "rss"})

        self.assertContains(response, "<category>error</category>")
        self.assertContains(response, "<category>unhealthy</category>")
        self.assertContains(
            response, "<pubDate>Thu, 01 Jan 1970 00:00:00 +0000</pubDate>"
        )
        self.assertContains(
            response,
            f"<pubDate>{rfc2822_date(self.results[1].error.timestamp)}</pubDate>",
        )

    def test_public_monitoring_does_not_query_failed_job_notifications(self):
        with patch(
            "ghostwriter.status.views.get_uncleared_failed_tasks"
        ) as failed_tasks:
            response = self.client.get(self.uri, {"format": "json"})

        self.assertEqual(response.status_code, 500)
        failed_tasks.assert_not_called()

    def test_head_supports_public_monitoring_without_response_body(self):
        response = self.client.head(self.uri, {"format": "json"})

        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"")

    def test_machine_formats_remain_public_during_mfa_enrollment(self):
        self.user.require_mfa = True
        self.user.save(update_fields=["require_mfa"])
        self.client.force_login(self.user)

        response = self.client.get(self.uri, {"format": "json"})

        self.assertEqual(response.status_code, 500)
        self.assert_basic_response(response)
        response = self.client.get(self.uri)
        self.assertRedirects(
            response, reverse("mfa_activate_totp"), fetch_redirect_response=False
        )

    def test_privileged_html_retains_diagnostic_messages(self):
        self.client.force_login(self.admin)

        response = self.client.get(self.uri)

        self.assertContains(response, "/srv/private-volume", status_code=500)
        self.assertContains(
            response, "private connection error and traceback", status_code=500
        )


class DashboardHealthSummaryTests(TestCase):
    """Dashboard health includes configured capacity warnings and service failures."""

    def setUp(self):
        DashboardHealthSnapshot.objects.all().delete()

    @patch("health_check.contrib.psutil.psutil.disk_usage")
    def test_disk_threshold_controls_dashboard_warning(self, disk_usage):
        disk_usage.return_value = SimpleNamespace(percent=94.5)
        for threshold, expected_state in ((90, "WARNING"), (95, "OK")):
            with self.subTest(threshold=threshold), override_settings(
                HEALTH_CHECK={"DISK_USAGE_MAX": threshold, "MEMORY_MIN": 0}
            ):
                view = HealthCheckCustomView()
                with patch.object(view, "get_checks", return_value=[ConfiguredDisk()]):
                    summary = async_to_sync(view.collect_health_summary)()

                self.assertEqual(summary["state"], expected_state)
                if expected_state == "WARNING":
                    self.assertEqual(summary["issues"][0]["display_name"], "Disk")
                    self.assertTrue(summary["issues"][0]["is_warning"])
                    self.assertIn("94.5", summary["issues"][0]["result"]["error"])
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
            summary = async_to_sync(view.collect_health_summary)()

        self.assertEqual(summary["state"], "ERROR")
        self.assertEqual(len(summary["issues"]), 2)
        self.assertEqual(summary["issues"][1]["display_name"], "Hasura GraphQL Engine")
        self.assertFalse(summary["issues"][1]["is_warning"])

    def test_background_failure_is_shared_and_next_run_records_recovery(self):
        result = SimpleNamespace(
            check=HasuraBackend(), error=ServiceUnavailable("GraphQL unavailable")
        )
        check = Mock(get_result=AsyncMock(return_value=result))
        with patch.object(HealthCheckCustomView, "get_checks", return_value=[check]):
            refresh_dashboard_health()
            with self.assertNumQueries(1):
                summary = get_dashboard_health_summary()
            self.assertEqual(get_dashboard_health_summary(), summary)
            check.get_result.assert_awaited_once()
            self.assertEqual(summary["state"], "ERROR")
            self.assertIn(
                "GraphQL unavailable", summary["issues"][0]["result"]["error"]
            )
            self.assertEqual(json.loads(json.dumps(summary)), summary)
            result.error = None
            refresh_dashboard_health()

        self.assertEqual(check.get_result.await_count, 2)
        self.assertEqual(get_dashboard_health_summary(), {"state": "OK", "issues": []})
        self.assertEqual(DashboardHealthSnapshot.objects.count(), 1)

    def test_unexpected_monitor_error_records_unknown_instead_of_ready(self):
        DashboardHealthSnapshot.objects.create(
            checked_at=timezone.now(), summary={"state": "OK", "issues": []}
        )
        with patch.object(
            HealthCheckCustomView,
            "collect_health_summary",
            side_effect=RuntimeError("Unavailable"),
        ):
            refresh_dashboard_health()

        self.assertEqual(
            get_dashboard_health_summary(), {"state": "UNKNOWN", "issues": []}
        )

    def test_status_page_runs_fresh_checks_without_replacing_background_snapshot(self):
        DashboardHealthSnapshot.objects.create(
            checked_at=timezone.now(), summary={"state": "ERROR", "issues": []}
        )
        self.client.force_login(UserFactory(role="admin"))
        with patch.object(
            HealthCheckCustomView, "get_checks", return_value=[]
        ) as checks:
            response = self.client.get(reverse("status:healthcheck"))

        checks.assert_called_once()
        self.assertFalse(response.context["has_check_failures"])
        self.assertContains(response, "All monitored services are operational")
        self.assertEqual(get_dashboard_health_summary()["state"], "ERROR")

    def test_older_monitor_run_cannot_overwrite_a_newer_result(self):
        now = timezone.now()
        DashboardHealthSnapshot.objects.create(
            checked_at=now, summary={"state": "ERROR", "issues": []}
        )
        with patch(
            "ghostwriter.status.tasks.timezone.now",
            return_value=now - timedelta(seconds=1),
        ), patch.object(
            HealthCheckCustomView,
            "collect_health_summary",
            return_value={"state": "OK", "issues": []},
        ):
            refresh_dashboard_health()

        self.assertEqual(get_dashboard_health_summary()["state"], "ERROR")
        self.assertEqual(DashboardHealthSnapshot.objects.get(pk=1).checked_at, now)


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

        mock_get.assert_called_once_with(
            "http://graphql_engine:8080/healthz", timeout=5
        )

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_raises_warning_for_warn_response(self, mock_get):
        mock_get.return_value = Mock(ok=True, text="WARN: inconsistent metadata")

        with self.assertRaises(ServiceWarning):
            HasuraBackend().run()

    @patch("ghostwriter.modules.health_utils.requests.get")
    def test_run_raises_unexpected_result_for_unrecognized_success_response(
        self, mock_get
    ):
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

    def test_basic_status_stays_public_for_anonymous_and_regular_users(self):
        user = UserFactory(role="user", require_mfa=True)
        for current_user in (None, user):
            if current_user is not None:
                self.client.force_login(current_user)
            with self.subTest(user=current_user):
                response = self.client.get(self.uri)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(response.content, b"OK")

    @patch("ghostwriter.status.views.DjangoHealthChecks")
    def test_warning_and_error_responses_never_include_diagnostics(self, health_checks):
        checks = health_checks.return_value
        checks.get_database_status.return_value = {"default": False}
        checks.get_cache_status.return_value = {"default": True}
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.content, b"WARNING")

        checks.get_database_status.side_effect = RuntimeError(
            "private connection error"
        )
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 500)
        self.assertEqual(response.content, b"ERROR")
