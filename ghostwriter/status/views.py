"""This contains all the views used by the Status application."""

# Standard Libraries
import logging

# Django Imports
from django.contrib.auth import get_user_model
from django.http import HttpResponse
from django.utils.decorators import method_decorator
from django.views.decorators.cache import never_cache
from django.views.generic.edit import View

# 3rd Party Libraries
from health_check.views import MainView, MediaType

# Ghostwriter Libraries
from ghostwriter.modules.health_utils import DjangoHealthChecks

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)


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


class HealthCheckCustomView(MainView):
    """
    Custom health check view to check Ghostwriter services.

    **Template**

    :template:`status/index.html`
    """

    template_name = "health_check.html"

    @method_decorator(never_cache)
    def get(self, request, *args, **kwargs):  # pragma: no cover
        status_code = 500 if self.errors else 200

        format_override = request.GET.get("format")

        if format_override == "json":
            return self.render_to_response_json(self.plugins, status_code)

        accept_header = request.META.get("HTTP_ACCEPT", "*/*")
        for media in MediaType.parse_header(accept_header):
            if media.mime_type in (
                "text/html",
                "application/xhtml+xml",
                "text/*",
                "*/*",
            ):
                context = self.get_context_data(**kwargs)
                return self.render_to_response(context, status=status_code)
            if media.mime_type in ("application/json", "application/*"):
                return self.render_to_response_json(self.plugins, status_code)
        return HttpResponse(
            "Not Acceptable: Supported content types: text/html, application/json",
            status=406,
            content_type="text/plain",
        )  # pragma: no cover
