"""This contains the custom template tags used by the Home application."""

# Django Imports
from django import template
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q

# 3rd Party Libraries
from allauth_2fa.utils import user_has_valid_totp_device
from bs4 import BeautifulSoup

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    verify_access,
    verify_finding_access,
    verify_user_is_privileged,
)
from ghostwriter.reporting.models import Report, ReportFindingLink
from ghostwriter.rolodex.models import ProjectAssignment

register = template.Library()


@register.filter(name="has_group")
def has_group(user, group_name):
    """
    Check if individual :model:`users.User` is linked to an individual
    :model:`django.contrib.auth.Group`.
    """
    # Get the group from the Group auth model
    group = Group.objects.get(name=group_name)
    # Check if the logged-in user a member of the returned group object
    return bool(group in user.groups.all())


@register.filter(name="get_groups")
def get_groups(user):
    """
    Collect a list of all memberships in :model:`django.contrib.auth.Group` for
    an individual :model:`users.User`.
    """
    groups = Group.objects.filter(user=user)
    group_list = []
    for group in groups:
        group_list.append(group.name)
    return ", ".join(group_list)


@register.simple_tag
def count_assignments(request):
    """
    Count number of incomplete :model:`reporting.ReportFindingLink` entries associated
    with an individual :model:`users.User`.
    """
    user_tasks = (
        ReportFindingLink.objects.select_related("report", "report__project")
        .filter(Q(assigned_to=request.user) & Q(report__complete=False) & Q(complete=False))
        .order_by("report__project__end_date")
    )
    return user_tasks.count()


@register.simple_tag
def get_reports(request):
    """
    Get a list of all :model:`reporting.Report` entries associated with
    an individual :model:`users.User` via :model:`rolodex.Project` and
    :model:`rolodex.ProjectAssignment`.
    """
    active_reports = []
    active_projects = (
        ProjectAssignment.objects.select_related("project")
        .filter(Q(operator=request.user) & Q(project__complete=False))
        .order_by("project__end_date")
    )
    for active_project in active_projects:
        reports = Report.objects.filter(Q(project=active_project.project) & Q(complete=False))
        for report in reports:
            active_reports.append(report)

    return active_reports


@register.simple_tag
def settings_value(name):
    """Return the specified setting value."""
    return getattr(settings, name, "")


@register.filter(name="count_incomplete_objectives")
def count_incomplete_objectives(queryset):
    """Return the number of incomplete objectives"""
    return queryset.filter(complete=False).count()


@register.filter(name="strip_empty_tags")
def strip_empty_tags(content):
    """Strip empty tags from HTML content."""
    soup = BeautifulSoup(content, "lxml")
    for x in soup.find_all():
        if len(x.get_text(strip=True)) == 0:
            x.extract()
    return soup.prettify()


@register.filter
def divide(value, arg):
    """Divide the value by the argument."""
    try:
        return int(value) / int(arg)
    except (ValueError, ZeroDivisionError):
        return None


@register.filter
def has_access(project, user):
    """Check if the user has access to the project."""
    return verify_access(user, project)


@register.filter
def can_create_finding(user):
    """Check if the user has the permission to create a finding."""
    return verify_finding_access(user, "create")


@register.filter
def is_privileged(user):
    """Check if the user has the permission to create a finding."""
    return verify_user_is_privileged(user)


@register.filter
def has_2fa(user):
    """Check if the user has a valid TOTP method configured."""
    return user_has_valid_totp_device(user)
