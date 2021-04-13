"""This contains the custom template tags used by he Rolodex application."""

# Standard Libraries
from collections import defaultdict
import datetime


from django import template

# Ghostwriter Libraries
from ghostwriter.rolodex.models import ObjectivePriority
from ghostwriter.shepherd.models import AuxServerAddress

register = template.Library()


@register.simple_tag
def get_primary_address(value):
    """
    Get the primary IP address for an individual :model:`shepherd.StaticServer`
    from :model:`shepherd.AuxServerAddress`.

    **Parameters**

    ``value``
        Individual :model:`shepherd.StaticServer` entry
    """
    primary_address = value.ip_address
    aux_addresses = AuxServerAddress.objects.filter(static_server=value)
    for address in aux_addresses:
        if address.primary:
            primary_address = address.ip_address
    return primary_address


@register.filter
def get_scope_preview(value, n):
    """
    Get the top N lines of a ``scope`` list for an individual :model:`rolodex.ProjectScope`.

    **Parameters**

    ``value``
        The ``scope`` value of an individual :model:`rolodex.ProjectScope` entry
    ``value``
        Number of lines to return
    """
    return "\n".join(value.split("\r\n")[0:n])


@register.filter
def plus_days(value, days):
    """
    Add some number of days to a ``datetime`` value within a template.

    **Parameters**

    ``days``
        A whole integer to add to the day value of a ``datetime`` value
    """
    return value + datetime.timedelta(days=days)


@register.filter
def days_left(value):
    """
    Calculate how many days between the current date and a provide ``datetime`` value.

    **Parameters**

    ``value``
        A ``datetime`` value
    """
    today = datetime.date.today()
    delta = value - today
    return delta.days


@register.filter
def get_item(dictionary, key):
    """
    Return a key value from a dictionary object.

    **Parameters**

    ``dictonary``
        Python dictionary object to parse
    ``key``
        Key name tor etrieve from the dictionary
    """
    # Use `get` to return `None` if not found
    return dictionary.get(key)


@register.simple_tag
def group_by_priority(queryset):
    """
    Group a queryset by the ``Priority`` field.

    **Parameters**

    ``queryset``
        Instance of :model:`rolodex.ProjectObjective`
    """
    all_priorities = ObjectivePriority.objects.all().order_by("weight")
    priority_dict = defaultdict(list)
    for priority in all_priorities:
        priority_dict[str(priority)] = []
    for objective in queryset:
        priority_dict[str(objective.priority)].append(objective)
    # Return a basic dict because templates can't handle defaultdict
    return dict(priority_dict)
