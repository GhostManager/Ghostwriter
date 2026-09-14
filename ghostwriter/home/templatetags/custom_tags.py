"""This contains the custom template tags used by the Home application."""

# Standard Libraries
import logging
from datetime import datetime, timedelta

# Django Imports
from django import template
from django.conf import settings
from django.contrib.auth.models import Group
from django.db.models import Q
from django.utils import timezone
from django.utils.text import slugify

# 3rd Party Libraries
from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_datetime
from dateutil.parser._parser import ParserError

# Ghostwriter Libraries
from ghostwriter.api.utils import verify_user_is_privileged, user_has_valid_totp_device, user_has_valid_webauthn_device
from ghostwriter.home.models import UserProfile
from ghostwriter.reporting.models import Finding, Observation, Report, ReportFindingLink
from ghostwriter.rolodex.models import ProjectAssignment

register = template.Library()
logger = logging.getLogger(__name__)


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
    user_assignments = (
        ProjectAssignment.objects.select_related("project")
        .filter(Q(operator=request.user) & Q(project__complete=False))
        .order_by("project__end_date")
    )
    active_projects = []
    project_ids = []
    for assignment in user_assignments:
        if assignment.project not in active_projects:
            active_projects.append(assignment.project)
            project_ids.append(assignment.project_id)

    active_reports = list(
        Report.objects.select_related("project")
        .filter(project_id__in=project_ids, complete=False)
        .order_by("project__end_date", "title", "id")
    )
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
def multiply(value, arg):
    """Multiply the value by the argument."""
    try:
        return round(float(value) * float(arg), 2)
    except (ValueError, TypeError):
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
def can_edit_report_template(user, report_template):
    """Check if the user has permission to edit a report template."""
    return report_template.user_can_edit(user)


@register.filter
def can_delete_report_template(user, report_template):
    """Check if the user has permission to delete a report template."""
    return report_template.user_can_delete(user)


@register.filter
def has_mfa(user):
    """Check if the user has a valid TOTP method configured."""
    return user_has_valid_totp_device(user)


@register.filter
def has_webauthn(user):
    """Check if the user has a valid WebAuthn authenticator configured."""
    return user_has_valid_webauthn_device(user)


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
        logger.debug("Unable to parse date value for business-day calculation.", exc_info=True)
    return new_date


@register.filter
def split_and_join(value, delimiter):
    """Split a string with the delimiter and return a comma-separated string."""
    return ", ".join(value.split(delimiter))


@register.filter
def humanize_comma_list(value, delimiter=","):
    """Split a delimited string and return a human-readable list with ``and``."""
    items = [item.strip() for item in value.split(delimiter) if item.strip()]
    if not items:
        return ""
    if len(items) == 1:
        return items[0]
    if len(items) == 2:
        return " and ".join(items)
    return f"{', '.join(items[:-1])}, and {items[-1]}"


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


@register.filter(name="translate_domain_sid")
def translate_domain_sid(sid: str, domains: dict):
    """
    Translate a domain SID to its corresponding domain name.
    """
    for domain in domains:
        if "domain_sid" in domain:
            if sid == domain["domain_sid"]:
                return domain["name"]
    return sid


@register.simple_tag
def prepare_bhe_findings(findings, domains):
    """Prepare BloodHound Enterprise findings for the project dashboard."""
    severity_weights = {
        "critical": 1,
        "high": 2,
        "moderate": 3,
        "medium": 3,
        "low": 4,
        "informational": 5,
        "info": 5,
    }
    domain_names = {
        domain.get("domain_sid"): domain.get("name")
        for domain in (domains or [])
        if isinstance(domain, dict) and domain.get("domain_sid")
    }
    groups = {}
    environments = {}
    categories = set()
    principal_count = 0
    tier_zero_count = 0

    for index, finding in enumerate(findings or [], start=1):
        if not isinstance(finding, dict):
            continue

        assets = (
            finding.get("assets") if isinstance(finding.get("assets"), dict) else {}
        )
        severity = str(finding.get("severity") or "Unknown").strip()
        severity_key = slugify(severity) or "unknown"
        environment_id = finding.get("environment_id")
        environment = (
            domain_names.get(environment_id) or environment_id or "Unknown environment"
        )
        title = assets.get("title") or finding.get("finding_name") or "Untitled finding"
        category = assets.get("type") or "Uncategorized"
        principals = (
            finding.get("principals")
            if isinstance(finding.get("principals"), list)
            else []
        )
        is_tier_zero = bool(finding.get("is_tier_zero"))
        impact_values = []
        exposure_values = []
        for principal in principals:
            if not isinstance(principal, dict):
                continue
            for key, values in (
                ("impact_percentage", impact_values),
                ("exposure_percentage", exposure_values),
            ):
                try:
                    values.append(float(principal[key]))
                except (KeyError, TypeError, ValueError):
                    continue
        identifier = slugify(str(finding.get("id") or index)) or str(index)
        item = {
            "finding": finding,
            "title": title,
            "category": category,
            "environment": environment,
            "environment_key": slugify(str(environment)) or "unknown-environment",
            "category_key": slugify(str(category)) or "uncategorized",
            "severity": severity,
            "severity_key": severity_key,
            "principal_count": len(principals),
            "peak_impact": max(impact_values, default=None),
            "peak_exposure": max(exposure_values, default=None),
            "is_tier_zero": is_tier_zero,
            "modal_id": f"bhe-finding-{identifier}-{index}",
            "search_text": " ".join(
                str(value)
                for value in (
                    title,
                    category,
                    environment,
                    finding.get("finding_name"),
                )
                if value
            ),
        }

        if severity_key not in groups:
            groups[severity_key] = {
                "label": severity,
                "key": severity_key,
                "weight": severity_weights.get(severity_key, 99),
                "items": [],
            }
        groups[severity_key]["items"].append(item)
        environments[item["environment_key"]] = environment
        categories.add(str(category))
        principal_count += len(principals)
        tier_zero_count += int(is_tier_zero)

    ordered_groups = sorted(
        groups.values(),
        key=lambda group: (group["weight"], group["label"].lower()),
    )
    return {
        "total": sum(len(group["items"]) for group in ordered_groups),
        "critical": len(groups.get("critical", {}).get("items", [])),
        "environment_count": len(environments),
        "principal_count": principal_count,
        "tier_zero_count": tier_zero_count,
        "groups": ordered_groups,
        "environments": [
            {"key": key, "label": label}
            for key, label in sorted(
                environments.items(), key=lambda item: str(item[1]).lower()
            )
        ],
        "categories": [
            {"key": slugify(category) or "uncategorized", "label": category}
            for category in sorted(categories, key=str.lower)
        ],
    }


@register.filter(name="bhe_percent")
def bhe_percent(value):
    """Format a BloodHound decimal ratio as a compact percentage."""
    try:
        percentage = float(value)
    except (TypeError, ValueError):
        return "--"
    if -1 <= percentage <= 1:
        percentage *= 100
    percentage = round(percentage, 1)
    if percentage.is_integer():
        return str(int(percentage))
    return str(percentage)
