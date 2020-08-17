"""This contains all of the views used by the Home application."""

# Standard Libraries
import datetime
import logging

# Django & Other 3rd Party Libraries
from django.conf import settings
from django.contrib import messages
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.http import HttpResponseRedirect
from django.shortcuts import redirect, render
from django.urls import reverse
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
def dashboard(request):
    """
    Display the home page.

    **Context**

    ``user_projects``
        Active :model:`reporting.ProjectAssignment` for current :model:`users.User`.
    ``upcoming_projects``
        Future :model:`reporting.ProjectAssignment` for current :model:`users.User`.
    ``recent_tasks``
        Five most recent :model:`django_q.Task` entries.
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
    ).filter(Q(operator=request.user) & Q(start_date__lte=datetime.datetime.now()))
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
    return render(request, "home/upload_avatar.html", {"form": form})


@login_required
@staff_member_required
def management(request):
    """
    Display the current Ghostwriter settings.

    **Context**

    ``company_name ``
        The current value of ``settings.COMPANY_NAME``.
    ``company_twitter``
        The current value of ``settings.COMPANY_TWITTER``.
    ``company_email``
        The current value of ``settings.COMPANY_EMAIL``.
    ``timezone``
        The current value of ``settings.TIME_ZONE``.
    ``sleep_time``
        The associated value from ``settings.DOMAINCHECK_CONFIG``.
    ``virustotal_api_key``
        The associated value from ``settings.DOMAINCHECK_CONFIG``.
    ``slack_emoji``
        The associated value from ``settings.SLACK_CONFIG``.
    ``enable_slack``
        The associated value from ``settings.SLACK_CONFIG``.
    ``slack_channel``
        The associated value from ``settings.SLACK_CONFIG``.
    ``slack_username``
        The associated value from ``settings.SLACK_CONFIG``.
    ``slack_webhook_url``
        The associated value from ``settings.SLACK_CONFIG``.
    ``slack_alert_target``
        The associated value from ``settings.SLACK_CONFIG``.
    ``namecheap_client_ip``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``enable_namecheap``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``namecheap_api_key``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``namecheap_username``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``namecheap_page_size``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``namecheap_api_username``
        The associated value from ``settings.NAMECHEAP_CONFIG``.
    ``enable_cloud_monitor``
        The associated value from ``settings.CLOUD_SERVICE_CONFIG``.
    ``aws_key``
        The associated value from ``settings.CLOUD_SERVICE_CONFIG``.
    ``aws_secret``
        The associated value from ``settings.CLOUD_SERVICE_CONFIG``.
    ``do_api_key``
        The associated value from ``settings.CLOUD_SERVICE_CONFIG``.

    **Template**

    :template:`home/management.html`
    """

    """View function to display the current settings configured for
    Ghostwriter.
    """
    # Get the *_CONFIG dictionaries from settings.py
    config = {}
    config.update(settings.SLACK_CONFIG)
    config.update(settings.NAMECHEAP_CONFIG)
    config.update(settings.DOMAINCHECK_CONFIG)
    config.update(settings.CLOUD_SERVICE_CONFIG)

    def sanitize(sensitive_thing):
        """
        Sanitize the provided input and return for display in the template.
        """
        sanitized_string = sensitive_thing
        length = len(sensitive_thing)
        if sensitive_thing:
            if "http" in sensitive_thing:
                # Split the URL – expecting a Slack (or other) webhook
                sensitive_thing = sensitive_thing.split("/")
                # Get just the last part for sanitization
                webhook_tail = "".join(sensitive_thing[-1:])
                length = len(webhook_tail)
                # Construct a sanitized string
                sanitized_string = (
                    "/".join(sensitive_thing[:-1])
                    + "/"
                    + webhook_tail[0:4]
                    + "\u2717" * (length - 8)
                    + webhook_tail[length - 5 : length - 1]
                )
            # Handle anything else that's long enough to be a key
            elif length > 15:
                sanitized_string = (
                    sensitive_thing[0:4]
                    + "\u2717" * (length - 8)
                    + sensitive_thing[length - 5 : length - 1]
                )
        return sanitized_string

    # Pass the relevant settings to management.html
    context = {
        "company_name": settings.COMPANY_NAME,
        "company_twitter": settings.COMPANY_TWITTER,
        "company_email": settings.COMPANY_EMAIL,
        "timezone": settings.TIME_ZONE,
        "sleep_time": config["sleep_time"],
        "slack_emoji": config["slack_emoji"],
        "enable_slack": config["enable_slack"],
        "slack_channel": config["slack_channel"],
        "slack_username": config["slack_username"],
        "slack_webhook_url": sanitize(config["slack_webhook_url"]),
        "virustotal_api_key": sanitize(config["virustotal_api_key"]),
        "slack_alert_target": config["slack_alert_target"],
        "namecheap_client_ip": config["client_ip"],
        "enable_namecheap": config["enable_namecheap"],
        "namecheap_api_key": sanitize(config["namecheap_api_key"]),
        "namecheap_username": config["namecheap_username"],
        "namecheap_page_size": config["namecheap_page_size"],
        "namecheap_api_username": config["namecheap_api_username"],
        "enable_cloud_monitor": config["sleep_time"],
        "aws_key": sanitize(config["aws_key"]),
        "aws_secret": sanitize(config["aws_secret"]),
        "do_api_key": sanitize(config["do_api_key"]),
    }
    return render(request, "home/management.html", context=context)


@login_required
@staff_member_required
def send_slack_test_msg(request):
    """
    Create an individual :model:`django_q.Task` to test sending Slack messages.

    **Template**

    :template:`home/management.html`
    """
    # Check if the request is a POST and proceed with the task
    if request.method == "POST":
        # Add an async task grouped as `Test Slack Message`
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.send_slack_test_msg",
                group="Test Slack Message",
            )
            messages.success(
                request,
                "Test Slack message has been successfully queued.",
                extra_tags="alert-success",
            )
        except Exception:
            messages.error(
                request,
                "Test Slack message task could not be queued. Is the AMQP server running?",
                extra_tags="alert-danger",
            )
    return HttpResponseRedirect(reverse("home:management"))
