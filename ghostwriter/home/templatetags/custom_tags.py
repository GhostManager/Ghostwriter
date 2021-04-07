"""This contains the custom template tags used by he Home application."""

# Django Imports
from django import template
from django.contrib.auth.models import Group
from django.db.models import Q

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink

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
    return True if group in user.groups.all() else False


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
        .filter(
            Q(assigned_to=request.user) & Q(report__complete=False) & Q(complete=False)
        )
        .order_by("report__project__end_date")
    )
    return user_tasks.count()
