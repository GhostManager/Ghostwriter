"""This contains the custom template tags used by he Rolodex application."""

# Standard Libraries
import datetime

# Django & Other 3rd Party Libraries
from django import template

# Ghostwriter Libraries
from ghostwriter.shepherd.models import AuxServerAddress

register = template.Library()


@register.simple_tag
def get_primary_address(value):
    """
    Get the primary IP address for an individual :model:`shepherd.StaticServer`
    from :model:`shepherd.AuxServerAddress`.
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
    """
    return "\n".join(value.split("\r\n")[0:n])


@register.filter
def plus_days(value, days):
    """
    Add some number of days to a ``datetime`` value within a template.

    **Parameters**

    ``days``
        A whole integer to add to the day value of a ``datetime`` value.
    """
    return value + datetime.timedelta(days=days)
