# Standard Libraries
import re
from pathlib import Path

# Django Imports
from django.conf import settings
from django.contrib.auth.models import AnonymousUser
from django.http import HttpResponse
from django.test import RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse
from django.views import defaults as default_views

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory
from ghostwriter.middleware import ContentSecurityPolicyMiddleware

REPO_ROOT = Path(__file__).resolve().parents[3]
CSP_REPORT_ONLY_HEADER = "Content-Security-Policy-Report-Only"
PASSWORD = "SuperNaturalReporting!"


def parse_directives(policy):
    """Return a policy as a mapping of directive names to source lists."""
    directives = {}
    for value in policy.split(";"):
        parts = value.split()
        if parts:
            directives[parts[0]] = parts[1:]
    return directives


class ContentSecurityPolicyMiddlewareTests(SimpleTestCase):
    """Validate the Django report-only CSP middleware and policy baseline."""

    def setUp(self):
        self.request = RequestFactory().get("/")

    def test_policy_contains_required_restrictions(self):
        directives = parse_directives(settings.CONTENT_SECURITY_POLICY_REPORT_ONLY)

        self.assertEqual(directives["default-src"], ["'self'"])
        self.assertEqual(directives["base-uri"], ["'self'"])
        self.assertEqual(directives["frame-ancestors"], ["'self'"])
        self.assertEqual(directives["form-action"], ["'self'"])
        self.assertEqual(directives["object-src"], ["'none'"])
        self.assertEqual(directives["script-src"], ["'self'"])
        self.assertEqual(directives["style-src"], ["'self'"])
        self.assertIn("ws:", directives["connect-src"])
        self.assertIn("wss:", directives["connect-src"])
        self.assertNotIn("'unsafe-inline'", settings.CONTENT_SECURITY_POLICY_REPORT_ONLY)
        self.assertNotIn("'unsafe-eval'", settings.CONTENT_SECURITY_POLICY_REPORT_ONLY)

    def test_middleware_adds_policy_to_normal_and_error_responses(self):
        for status in (200, 400, 403, 404, 500):
            middleware = ContentSecurityPolicyMiddleware(
                lambda request, response_status=status: HttpResponse(
                    status=response_status
                )
            )

            response = middleware(self.request)

            self.assertEqual(
                response.headers[CSP_REPORT_ONLY_HEADER],
                settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
                status,
            )

    def test_middleware_preserves_route_specific_policy(self):
        route_policy = "default-src 'none'"

        def get_response(request):
            response = HttpResponse()
            response.headers[CSP_REPORT_ONLY_HEADER] = route_policy
            return response

        response = ContentSecurityPolicyMiddleware(get_response)(self.request)

        self.assertEqual(response.headers[CSP_REPORT_ONLY_HEADER], route_policy)

    def test_report_only_policy_coexists_with_enforced_file_preview_policy(self):
        enforced_policy = "default-src 'none'; img-src 'self'"

        def get_response(request):
            response = HttpResponse()
            response.headers["Content-Security-Policy"] = enforced_policy
            return response

        response = ContentSecurityPolicyMiddleware(get_response)(self.request)

        self.assertEqual(
            response.headers[CSP_REPORT_ONLY_HEADER],
            settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
        )
        self.assertEqual(
            response.headers["Content-Security-Policy"],
            enforced_policy,
        )


class ContentSecurityPolicyResponseTests(TestCase):
    """Confirm representative Django responses receive the global policy."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.admin = UserFactory(password=PASSWORD, role="admin")

    def test_authenticated_page_has_report_only_policy(self):
        self.client.login(username=self.user.username, password=PASSWORD)

        response = self.client.get(reverse("home:dashboard"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers[CSP_REPORT_ONLY_HEADER],
            settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
        )


    def test_admin_page_has_report_only_policy(self):
        self.client.login(username=self.admin.username, password=PASSWORD)

        response = self.client.get(reverse("admin:index"))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.headers[CSP_REPORT_ONLY_HEADER],
            settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
        )

    def test_not_found_response_has_report_only_policy(self):
        response = self.client.get("/not-a-real-ghostwriter-route/")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(
            response.headers[CSP_REPORT_ONLY_HEADER],
            settings.CONTENT_SECURITY_POLICY_REPORT_ONLY,
        )


class ErrorStateTemplateTests(TestCase):
    """Confirm production-style error handlers use the shared recovery card."""

    @override_settings(DEBUG=False)
    def test_error_handlers_render_refreshed_recovery_cards(self):
        request_factory = RequestFactory()
        error_views = {
            400: default_views.bad_request,
            403: default_views.permission_denied,
            404: default_views.page_not_found,
            500: default_views.server_error,
        }

        for status_code, view in error_views.items():
            request = request_factory.get(f"/{status_code}/")
            request.user = AnonymousUser()
            if status_code == 500:
                response = view(request)
            else:
                response = view(request, Exception("Test error"))

            self.assertEqual(response.status_code, status_code)
            self.assertContains(
                response,
                'class="error-state-card"',
                status_code=status_code,
            )
            self.assertContains(
                response,
                f'aria-label="Status code {status_code}"',
                status_code=status_code,
            )
            self.assertContains(
                response,
                "Return to dashboard",
                status_code=status_code,
            )


class NginxContentSecurityPolicyTests(SimpleTestCase):
    """Keep Nginx proxy coverage aligned with Django's CSP baseline."""

    def test_nginx_applies_matching_policy_to_all_responses(self):
        config_path = (
            REPO_ROOT / "compose" / "production" / "nginx" / "nginx_common.conf"
        )
        config = config_path.read_text()
        match = re.search(
            r'add_header\s+Content-Security-Policy-Report-Only\s+"([^"]+)"\s+always;',
            config,
        )

        self.assertIsNotNone(match)
        self.assertEqual(match.group(1), settings.CONTENT_SECURITY_POLICY_REPORT_ONLY)
        self.assertIn(
            "proxy_hide_header     Content-Security-Policy-Report-Only;",
            config,
        )
