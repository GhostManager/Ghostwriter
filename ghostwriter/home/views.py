"""This contains all of the views used by the Home application."""

# Standard Libraries
import datetime
import logging

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.db.models import Q
from django.http import JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.views.generic.edit import View
from django.views.static import serve

# 3rd Party Libraries
from django_q.models import Task
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink
from ghostwriter.rolodex.models import ProjectAssignment

from .forms import UserProfileForm

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)


##################
# View Functions #
##################


@login_required
def protected_serve(request, path, document_root=None, show_indexes=False):
    """
    Serve static files from ``MEDIA_ROOT`` for authenticated requests.
    """
    return serve(request, path, document_root, show_indexes)


@login_required
def dashboard(request):
    """
    Display the home page.

    **Context**

    ``user_projects``
        Active :model:`reporting.ProjectAssignment` for current :model:`users.User`
    ``upcoming_projects``
        Future :model:`reporting.ProjectAssignment` for current :model:`users.User`
    ``recent_tasks``
        Five most recent :model:`django_q.Task` entries
    ``user_tasks``
        Incomplete :model:`reporting.ReportFindingLink` for current :model:`users.User`

    **Template**

    :template:`index.html`
    """
    # Get the most recent :model:`django_q.Task` entries
    recent_tasks = Task.objects.all()[:5]
    # Get incomplete :model:`reporting.ReportFindingLink` for current :model:`users.User`
    user_tasks = (
        ReportFindingLink.objects.select_related("report", "report__project")
        .filter(
            Q(assigned_to=request.user) & Q(report__complete=False) & Q(complete=False)
        )
        .order_by("report__project__end_date")[:10]
    )
    # Get active :model:`reporting.ProjectAssignment` for current :model:`users.User`
    user_projects = ProjectAssignment.objects.select_related(
        "project", "project__client", "role"
    ).filter(
        Q(operator=request.user)
        & Q(start_date__lte=datetime.datetime.now())
        & Q(end_date__gte=datetime.datetime.now())
    )
    # Get future :model:`reporting.ProjectAssignment` for current :model:`users.User`
    upcoming_project = ProjectAssignment.objects.select_related(
        "project", "project__client", "role"
    ).filter(Q(operator=request.user) & Q(start_date__gt=datetime.datetime.now()))
    # Assemble the context dictionary to pass to the dashboard
    context = {
        "user_projects": user_projects,
        "upcoming_project": upcoming_project,
        "recent_tasks": recent_tasks,
        "user_tasks": user_tasks,
    }
    # Render the HTML template index.html with the data in the context variable
    return render(request, "index.html", context=context)


@login_required
def profile(request):
    """
    Display an individual :model:`home.UserProfile`.

    **Template**

    :template:`home/profile.html`
    """
    return render(request, "home/profile.html")


@login_required
def upload_avatar(request):
    """
    Upload an avatar image for an individual :model:`home.UserProfile`.

    **Context**

    ``form``
        A single ``UserProfileForm`` form.
    ``cancel_link``
        Link for the form's Cancel button to return to user's profile page

    **Template**

    :template:`hom/upload_avatar.html`
    """

    if request.method == "POST":
        form = UserProfileForm(
            request.POST, request.FILES, instance=request.user.userprofile
        )
        if form.is_valid():
            form.save()
            return redirect("home:profile")
    else:
        form = UserProfileForm()
    cancel_link = reverse("home:profile")
    return render(
        request, "home/upload_avatar.html", {"form": form, "cancel_link": cancel_link}
    )


class Management(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Display the current Ghostwriter settings.

    **Context**

    ``timezone``
        The current value of ``settings.TIME_ZONE``

    **Template**

    :template:`home/management.html`
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def get(self, request, *args, **kwargs):
        context = {
            "timezone": settings.TIME_ZONE,
        }
        return render(request, "home/management.html", context=context)


class TestAWSConnection(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``AWS Test`` with
    :task:`shepherd.tasks.test_aws_keys` to test AWS keys in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``AWS Test``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.test_aws_keys",
                self.request.user,
                group="AWS Test",
            )
            message = "AWS access key test has been successfully queued"
        except Exception:
            result = "error"
            message = "AWS access key test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestDOConnection(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Digital Ocean Test`` with
    :task:`shepherd.tasks.test_digital_ocean` to test the Digital Ocean API key stored in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Digital Ocean Test``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.test_digital_ocean",
                self.request.user,
                group="Digital Ocean Test",
            )
            message = "Digital Ocean API key test has been successfully queued"
        except Exception:
            result = "error"
            message = "Digital Ocean API key test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestNamecheapConnection(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Namecheap Test`` with
    :task:`shepherd.tasks.test_namecheap` to test the Namecheap API configuration stored
    in :model:`commandcenter.NamecheapConfiguration`.
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Namecheap Test``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.test_namecheap",
                self.request.user,
                group="Namecheap Test",
            )
            message = "Namecheap API test has been successfully queued"
        except Exception:
            result = "error"
            message = "Namecheap API test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestSlackConnection(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Slack Test`` with
    :task:`shepherd.tasks.test_slack_webhook` to test the Slack Webhook configuration
    stored in :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Slack Test``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.test_slack_webhook",
                self.request.user,
                group="Slack Test",
            )
            message = "Slack Webhook test has been successfully queued"
        except Exception:
            result = "error"
            message = "Slack Webhook test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestVirusTotalConnection(LoginRequiredMixin, UserPassesTestMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``VirusTotal Test`` with
    :task:`shepherd.tasks.test_virustotal` to test the VirusTotal API key stored in
    :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return self.request.user.is_staff

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``VirusTotal Test``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.test_virustotal",
                self.request.user,
                group="Slack Test",
            )
            message = "VirusTotal API test has been successfully queued"
        except Exception:
            result = "error"
            message = "VirusTotal API test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)
