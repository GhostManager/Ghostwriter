"""This contains all the views used by the Status application."""

# Standard Libraries
import asyncio
import logging

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.views.generic.edit import View

# 3rd Party Libraries
from health_check.exceptions import ServiceWarning
from health_check.views import HealthCheckView
from redis.asyncio import Redis as RedisClient

# Ghostwriter Libraries
from ghostwriter.modules.health_utils import DjangoHealthChecks

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)


def get_redis_client():
    """Create a Redis client for the health check request."""
    return RedisClient.from_url(settings.REDIS_URL)


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
                "result": result,
            }
            for result in self.results
        ]

    async def get_dashboard_summary(self):
        """Run the status page's checks and summarize warnings and failures."""
        with self.get_executor() as executor:
            self.results = await asyncio.gather(
                *(check.get_result(executor) for check in self.get_checks())
            )
        issues = [
            result for result in self.get_status_results() if not result["is_healthy"]
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
        return context
