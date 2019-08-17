from django import template
from django.contrib.auth.models import Group

from django.db.models import Q

from ghostwriter.reporting.models import ReportFindingLink


register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """Custom template tag to check the current user's group membership."""
    # Get the group from the Group auth model
    group = Group.objects.get(name=group_name)
    # Check if the logged-in user a member of the returned group object
    return True if group in user.groups.all() else False


@register.simple_tag
def count_assignments(request):
    user_tasks = ReportFindingLink.objects.\
        select_related('report', 'report__project').\
        filter(Q(assigned_to=request.user) & Q(report__complete=False) &
              Q(complete=False)).order_by('report__project__end_date')
    return user_tasks.count()
