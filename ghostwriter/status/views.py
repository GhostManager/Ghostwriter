"""This contains all the views used by the Status application."""

# Standard Libraries
import asyncio
import datetime
import logging

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse, HttpResponseForbidden, JsonResponse
from django.views.generic.edit import View

# 3rd Party Libraries
from health_check.exceptions import ServiceWarning
from health_check.views import HealthCheckView, MediaType
from redis.asyncio import Redis as RedisClient

# Ghostwriter Libraries
from ghostwriter.home.notifications import get_uncleared_failed_tasks
from ghostwriter.modules.health_utils import DjangoHealthChecks

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)


PUBLIC_STATUS_FORMATS = {"json", "text", "atom", "rss", "openmetrics"}
PUBLIC_STATUS_MEDIA_TYPES = {
    "application/json",
    "application/*",
    "text/plain",
    "application/atom+xml",
    "application/rss+xml",
    "application/openmetrics-text",
}
HTML_STATUS_MEDIA_TYPES = {"text/html", "application/xhtml+xml", "text/*", "*/*"}


def get_redis_client():
    """Create a Redis client for the health check request."""
    return RedisClient.from_url(settings.REDIS_URL)


def is_public_status_request(request):
    """Allow only supported monitoring formats, following health-check's ordering."""
    if request.GET.get("format") in PUBLIC_STATUS_FORMATS:
        return True
    for media in MediaType.parse_header(request.headers.get("accept", "*/*")):
        if media.mime_type in PUBLIC_STATUS_MEDIA_TYPES:
            return True
        if media.mime_type in HTML_STATUS_MEDIA_TYPES:
            return False
    return False


##################
# View Functions #
##################


class HealthCheckSimpleView(View):
    """
    A simplified health check view that returns a status message. The response is "OK"
    with a 200 status code if the database and cache are available. Otherwise, the
    response is "WARNING" with a 200 status code. If the database or cache checks fail,
    the response is "ERROR" with a 500 status code.
    """

    def get(self, request):
        status = "OK"
        code = 200
        try:
            healthcheck = DjangoHealthChecks()
            db_status = healthcheck.get_database_status()
            cache_status = healthcheck.get_cache_status()
            if not db_status["default"] or not cache_status["default"]:  # pragma: no cover
                status = "WARNING"
        except Exception:  # pragma: no cover
            logger.exception("Health check failed")
            status = "ERROR"
            code = 500
        return HttpResponse(status, status=code)


class HealthCheckCustomView(HealthCheckView):
    """
    Custom health check view to check Ghostwriter services.

    **Template**

    :template:`status/index.html`
    """

    template_name = "health_check.html"
    permission_denied_message = "Only managers and admins may view detailed system status."
    display_names = {
        "Cache": "Cache",
        "ConfiguredDisk": "Disk",
        "ConfiguredMemory": "Memory",
        "Database": "Database",
        "Disk": "Disk",
        "HasuraBackend": "Hasura GraphQL Engine",
        "Memory": "Memory",
        "Redis": "Redis",
        "Storage": "Storage",
    }
    checks = [
        "health_check.Cache",
        "health_check.Database",
        "health_check.Storage",
        "ghostwriter.modules.health_utils.ConfiguredDisk",
        "ghostwriter.modules.health_utils.ConfiguredMemory",
        ("health_check.contrib.redis.Redis", {"client_factory": get_redis_client}),
        "ghostwriter.modules.health_utils.HasuraBackend",
    ]

    async def get(self, request, *args, **kwargs):
        """Keep HTML diagnostics privileged and expose basic monitoring formats."""
        self.can_view_diagnostics = False
        if not is_public_status_request(request):
            user = await request.auser()
            if (
                not user.is_authenticated
                or not user.is_active
                or not user.is_privileged
            ):
                return HttpResponseForbidden(self.permission_denied_message)
            self.can_view_diagnostics = True
            self.has_failed_tasks = await get_uncleared_failed_tasks().aexists()
        return await super().get(request, *args, **kwargs)

    def render_to_response(self, context, **response_kwargs):
        """Guard HTML rendering even if upstream format negotiation changes."""
        if not getattr(self, "can_view_diagnostics", False):
            return HttpResponseForbidden(self.permission_denied_message)
        return super().render_to_response(context, **response_kwargs)

    def render_to_response_json(self, status):
        """Return public service statuses, preserving monitoring HTTP codes."""
        return JsonResponse(
            {
                result["display_name"]: result["status"]
                for result in self.get_status_results()
            },
            status=status,
        )

    def render_to_response_text(self, status):
        """Return public service statuses without diagnostic messages."""
        lines = (
            f"{result['display_name']}: {result['status']}"
            for result in self.get_status_results()
        )
        return HttpResponse(
            "\n".join(lines) + "\n",
            content_type="text/plain; charset=utf-8",
            status=status,
        )

    def _render_feed(self, feed_class):
        """Keep Atom and RSS feeds public without exposing errors or check reprs."""
        feed = feed_class(
            title="Health Check Status",
            link=self.request.build_absolute_uri(self.request.path),
            description="Current status of system health checks",
            feed_url=self.request.build_absolute_uri(),
        )
        for result in self.get_status_results():
            error = result["result"].error
            published_at = (
                error.timestamp
                if error
                else datetime.datetime(1970, 1, 1, tzinfo=datetime.timezone.utc)
            )
            feed.add_item(
                title=result["display_name"],
                link=self.request.build_absolute_uri(self.request.path),
                description=result["status"],
                pubdate=published_at,
                updateddate=published_at,
                author_name=self.feed_author,
                categories=["error", "unhealthy"] if error else ["healthy"],
            )
        return HttpResponse(feed.writeString("utf-8"), content_type=feed.content_type)

    def render_to_response_openmetrics(self):
        """Expose health and timing metrics using only public service labels."""
        results = self.get_status_results()
        lines = [
            "# HELP django_health_check_status Health check status (1 = healthy, 0 = unhealthy)",
            "# TYPE django_health_check_status gauge",
        ]
        for result in results:
            check_name = result["result"].check.__class__.__name__
            labels = self.abnf_dumps({"check": check_name})
            lines.append(
                f"django_health_check_status{{{labels}}} {result['is_healthy']:d}"
            )
        lines += [
            "",
            "# HELP django_health_check_response_time_seconds Health check response time in seconds",
            "# TYPE django_health_check_response_time_seconds gauge",
        ]
        for result in results:
            check_name = result["result"].check.__class__.__name__
            labels = self.abnf_dumps({"check": check_name})
            lines.append(
                f"django_health_check_response_time_seconds{{{labels}}} {result['result'].time_taken:.6f}"
            )
        lines += [
            "",
            "# HELP django_health_check_overall_status Overall health check status (1 = all healthy, 0 = at least one unhealthy)",
            "# TYPE django_health_check_overall_status gauge",
            f"django_health_check_overall_status {all(result['is_healthy'] for result in results):d}",
            "# EOF",
        ]
        return HttpResponse(
            "\n".join(lines) + "\n",
            content_type="application/openmetrics-text; version=1.0.0; charset=utf-8",
        )

    def get_status_results(self):
        """Describe each check consistently for status and dashboard displays."""
        return [
            {
                "display_name": self.display_names.get(
                    result.check.__class__.__name__,
                    result.check.__class__.__name__,
                ),
                "is_healthy": not bool(result.error),
                "is_warning": isinstance(result.error, ServiceWarning),
                "status": (
                    "warning"
                    if isinstance(result.error, ServiceWarning)
                    else "error"
                    if result.error
                    else "working"
                ),
                "result": result,
            }
            for result in self.results
        ]

    async def collect_health_summary(self):
        """Run diagnostics for the background monitor and return only display data."""
        with self.get_executor() as executor:
            self.results = await asyncio.gather(
                *(check.get_result(executor) for check in self.get_checks())
            )
        # Persist display data only; health check objects can hold live connections.
        issues = [
            {
                "display_name": result["display_name"],
                "is_warning": result["is_warning"],
                "result": {"error": str(result["result"].error)},
            }
            for result in self.get_status_results()
            if not result["is_healthy"]
        ]
        if any(not issue["is_warning"] for issue in issues):
            state = "ERROR"
        elif issues:
            state = "WARNING"
        else:
            state = "OK"
        return {"state": state, "issues": issues}

    def get_context_data(self, **kwargs):
        """Add display-friendly service names for the HTML status page."""
        context = super().get_context_data(**kwargs)
        context["health_check_thresholds"] = [
            {
                "name": "Disk Usage Warning Threshold",
                "value": f"{settings.HEALTH_CHECK['DISK_USAGE_MAX']:g}%",
            },
            {
                "name": "Minimum Available Memory",
                "value": f"{settings.HEALTH_CHECK['MEMORY_MIN']:g} MB",
            },
        ]
        context["status_results"] = self.get_status_results()
        context["healthy_check_count"] = sum(
            status_result["is_healthy"] for status_result in context["status_results"]
        )
        context["has_check_failures"] = any(
            not status_result["is_healthy"]
            for status_result in context["status_results"]
        )
        context["has_failed_tasks"] = getattr(self, "has_failed_tasks", False)
        context["has_system_warning"] = (
            context["has_check_failures"] or context["has_failed_tasks"]
        )
        return context
