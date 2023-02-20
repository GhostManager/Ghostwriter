"""This contains custom validators for the Rolodex application."""

# Standard Libraries
import ipaddress

# Django Imports
from django.core.exceptions import ValidationError


def validate_ip_range(value):
    """
    Check if the value is a valid IP address or IP range.
    """
    try:
        ipaddress.ip_address(value)
    except ValueError:
        try:
            ipaddress.ip_network(value)
        except ValueError:
            raise ValidationError(f"{value} is not a valid IP address or IP range.")
    return value
