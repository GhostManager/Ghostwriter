"""This contains all the views used by the Home application."""

# Standard Libraries
import logging

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.views.generic.edit import View
from django.views.static import serve

# 3rd Party Libraries
from django_q.models import Task
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.api.utils import RoleBasedAccessControlMixin, verify_user_is_privileged
from ghostwriter.modules.health_utils import DjangoHealthChecks
from ghostwriter.reporting.models import ReportFindingLink
from ghostwriter.rolodex.models import ProjectAssignment

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)


##################
# View Functions #
##################


@login_required
def update_session(request):
    """Update the requesting user's session variable based on ``session_data`` in POST."""
    if request.method == "POST":
        req_data = request.POST.get("session_data", None)
        if req_data:
            if req_data == "sidebar":
                if "sidebar" in request.session.keys():
                    request.session["sidebar"]["sticky"] ^= True
                else:
                    request.session["sidebar"] = {}
                    request.session["sidebar"]["sticky"] = True
            if req_data == "filter":
                if "filter" in request.session.keys():
                    request.session["filter"]["sticky"] ^= True
                else:
                    request.session["filter"] = {}
                    request.session["filter"]["sticky"] = True
            request.session.save()
        data = {
            "result": "success",
            "message": "Session updated",
        }
        return JsonResponse(data)

    return HttpResponseNotAllowed(["POST"])


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    """Serve static files from ``MEDIA_ROOT`` for authenticated requests."""
    return serve(request, path, document_root, show_indexes)


class Dashboard(RoleBasedAccessControlMixin, View):
    """
    Display the home page.

    **Context**

    ``user_projects``
        All :model:`reporting.ProjectAssignment` for current :model:`users.User`
    ``active_projects``
        All :model:`reporting.ProjectAssignment` for active :model:`rolodex.Project` and current :model:`users.User`
    ``recent_tasks``
        Five most recent :model:`django_q.Task` entries
    ``user_tasks``
        Incomplete :model:`reporting.ReportFindingLink` for current :model:`users.User`
    ``system_health``
        Current system health based on :func:`ghostwriter.modules.health_utils.DjangoHealthChecks`

    **Template**

    :template:`index.html`
    """

    def get(self, request, *args, **kwargs):
        # Get the most recent :model:`django_q.Task` entries
        recent_tasks = Task.objects.all()[:5]
        # Get incomplete :model:`reporting.ReportFindingLink` for current :model:`users.User`
        user_tasks = (
            ReportFindingLink.objects.select_related("report", "report__project")
            .filter(Q(assigned_to=request.user) & Q(report__complete=False) & Q(complete=False))
            .order_by("report__project__end_date")[:10]
        )
        # Get active :model:`reporting.ProjectAssignment` for current :model:`users.User`
        user_projects = ProjectAssignment.objects.select_related("project", "project__client", "role").filter(
            operator=request.user
        )
        # Get future :model:`reporting.ProjectAssignment` for current :model:`users.User`
        active_project = ProjectAssignment.objects.select_related("project", "project__client", "role").filter(
            Q(operator=request.user) & Q(project__complete=False)
        )
        # Get system status
        system_health = "OK"
        try:
            healthcheck = DjangoHealthChecks()
            db_status = healthcheck.get_database_status()
            cache_status = healthcheck.get_cache_status()
            if not db_status["default"] or not cache_status["default"]:
                system_health = "WARNING"
        except Exception:  # pragma: no cover
            system_health = "ERROR"

        # Assemble the context dictionary to pass to the dashboard
        context = {
            "user_projects": user_projects,
            "active_projects": active_project,
            "recent_tasks": recent_tasks,
            "user_tasks": user_tasks,
            "system_health": system_health,
        }
        # Render the HTML template index.html with the data in the context variable
        return render(request, "index.html", context=context)


class Management(RoleBasedAccessControlMixin, View):
    """
    Display the current Ghostwriter settings.

    **Context**

    ``timezone``
        The current value of ``settings.TIME_ZONE``

    **Template**

    :template:`home/management.html`
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, request, *args, **kwargs):
        context = {
            "timezone": settings.TIME_ZONE,
        }
        return render(request, "home/management.html", context=context)


class TestAWSConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``AWS Test`` with
    :task:`shepherd.tasks.test_aws_keys` to test AWS keys in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``AWS Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_aws_keys",
                self.request.user,
                group="AWS Test",
            )
            message = "AWS access key test has been successfully queued."
        except Exception:  # pragma: no cover
            result = "error"
            message = "AWS access key test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestDOConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Digital Ocean Test`` with
    :task:`shepherd.tasks.test_digital_ocean` to test the Digital Ocean API key stored in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Digital Ocean Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_digital_ocean",
                self.request.user,
                group="Digital Ocean Test",
            )
            message = "Digital Ocean API key test has been successfully queued."
        except Exception:  # pragma: no cover
            result = "error"
            message = "Digital Ocean API key test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestNamecheapConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Namecheap Test`` with
    :task:`shepherd.tasks.test_namecheap` to test the Namecheap API configuration stored
    in :model:`commandcenter.NamecheapConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Namecheap Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_namecheap",
                self.request.user,
                group="Namecheap Test",
            )
            message = "Namecheap API test has been successfully queued."
        except Exception:  # pragma: no cover
            result = "error"
            message = "Namecheap API test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestSlackConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Slack Test`` with
    :task:`shepherd.tasks.test_slack_webhook` to test the Slack Webhook configuration
    stored in :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Slack Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_slack_webhook",
                self.request.user,
                group="Slack Test",
            )
            message = "Slack Webhook test has been successfully queued."
        except Exception:  # pragma: no cover
            result = "error"
            message = "Slack Webhook test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestVirusTotalConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``VirusTotal Test`` with
    :task:`shepherd.tasks.test_virustotal` to test the VirusTotal API key stored in
    :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``VirusTotal Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_virustotal",
                self.request.user,
                group="Slack Test",
            )
            message = "VirusTotal API test has been successfully queued."
        except Exception:  # pragma: no cover
            result = "error"
            message = "VirusTotal API test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)
