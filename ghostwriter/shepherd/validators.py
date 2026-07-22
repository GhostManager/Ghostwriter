"""Validators for user-controlled inventory identifiers."""

# Django Imports
from django.core.validators import RegexValidator
from django.utils.translation import gettext_lazy as _

DOMAIN_NAME_PATTERN = (
    r"\A(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.?\Z"
)
SERVER_NAME_PATTERN = r"\A(?:[A-Za-z0-9](?:[A-Za-z0-9._-]{0,253}[A-Za-z0-9])?)?\Z"

validate_inventory_domain_name = RegexValidator(
    regex=DOMAIN_NAME_PATTERN,
    message=_(
        "Enter a valid domain name using letters, numbers, periods, and hyphens."
    ),
    code="invalid_domain_name",
)

validate_inventory_server_name = RegexValidator(
    regex=SERVER_NAME_PATTERN,
    message=_(
        "Enter a valid server name using letters, numbers, periods, underscores, and hyphens."
    ),
    code="invalid_server_name",
)
