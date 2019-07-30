from django import template
from django.contrib.auth.models import Group

register = template.Library()

@register.filter(name='has_group')
def has_group(user, group_name):
    """Custom template tag to check the current user's group membership."""
    # Get the group from the Group auth model
    group = Group.objects.get(name=group_name)
    # Check if the logged-in user a member of the returned group object
    return True if group in user.groups.all() else False
