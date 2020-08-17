"""This contains the custom template tags used by he Rolodex application."""

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
