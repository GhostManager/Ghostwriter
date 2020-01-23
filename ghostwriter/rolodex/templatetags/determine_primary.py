from django import template

from ghostwriter.shepherd.models import AuxServerAddress

register = template.Library()

@register.simple_tag
def get_primary_address(value):
    """Gets the primary IP address for this server."""
    primary_address = value.ip_address
    aux_addresses = AuxServerAddress.objects.filter(static_server=value)
    for address in aux_addresses:
        if address.primary:
            primary_address = address.ip_address
    return primary_address
