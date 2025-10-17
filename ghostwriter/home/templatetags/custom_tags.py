"""This contains the custom template tags used by the Home application."""

# Standard Libraries
from datetime import datetime, timedelta

# Django Imports
from django import template
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils import timezone

# 3rd Party Libraries
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_datetime
from dateutil.parser._parser import ParserError

# Ghostwriter Libraries
from ghostwriter.api.utils import verify_user_is_privileged, user_has_valid_totp_device
from ghostwriter.home.models import UserProfile
from ghostwriter.reporting.models import Finding, Observation, Report, ReportFindingLink
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
def get_assignment_data(request):
    """
    Get a list of :model:`rolodex.ProjectAssignment` entries associated
    with an individual :model:`users.User` and return a list of unique
    :model:`rolodex.Project` entries and a list of unique :model:`reporting.Report` entries.
    """
    active_projects = []
    active_reports = []

    user_assignments = (
        ProjectAssignment.objects.select_related("project")
        .filter(Q(operator=request.user) & Q(project__complete=False))
        .order_by("project__end_date")
    )
    for assignment in user_assignments:
        if assignment.project not in active_projects:
            active_projects.append(assignment.project)

    for active_project in active_projects:
        reports = Report.objects.filter(Q(project=active_project) & Q(complete=False))
        for report in reports:
            if report not in active_reports:
                active_reports.append(report)
    return active_projects, active_reports


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
    return project.user_can_view(user)


@register.filter
def can_create_finding(user):
    """Check if the user has the permission to create a finding."""
    return Finding.user_can_create(user)


@register.filter
def can_create_observation(user):
    """Check if the user has the permission to create a finding."""
    return Observation.user_can_create(user)


@register.filter
def is_privileged(user):
    """Check if the user has the permission to create a finding."""
    return verify_user_is_privileged(user)


@register.filter
def has_mfa(user):
    """Check if the user has a valid TOTP method configured."""
    return user_has_valid_totp_device(user)


@register.filter
def add_days(date, days):
    """Add business days to a date. Days can be negative to subtract."""
    new_date = date
    try:
        date_obj = parse_datetime(str(date))
        # Loop until all days added
        if days > 0:
            while days > 0:
                # Add one day to the date
                date_obj += timedelta(days=1)
                # Check if the day is a business day
                weekday = date_obj.weekday()
                if weekday >= 5:
                    # Return to the top (Sunday is 6)
                    continue
                # Decrement the number of days to add
                days -= 1
        else:
            # Same as above but in reverse for negative days
            while days < 0:
                date_obj -= timedelta(days=1)
                weekday = date_obj.weekday()
                if weekday >= 5:
                    continue
                days += 1
        new_date = date_obj
    except ParserError:
        pass
    return new_date


@register.filter
def split_and_join(value, delimiter):
    """Split a string with the delimiter and return a comma-separated string."""
    return ", ".join(value.split(delimiter))


@register.filter
def get_tags_list(value):
    """Return a list of tags from an object's `tags.names` value."""
    return ", ".join(value)


@register.simple_tag
def hide_quickstart(request):
    """
    Return a boolean value indicating if the quickstart card should be hidden.
    """
    user_profile = UserProfile.objects.get(user=request.user)
    return user_profile.hide_quickstart


@register.filter(name="is_past")
def is_past(value):
    """
    Return True if the given datetime is in the past.
    """
    if not value or not isinstance(value, datetime):
        return False
    now = timezone.now()
    # Ensure both are timezone-aware for comparison
    if timezone.is_naive(value):
        value = timezone.make_aware(value, timezone.get_current_timezone())
    return value < now
