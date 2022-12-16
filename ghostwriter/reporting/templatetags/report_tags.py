"""Custom template tags for the reporting app."""

# Standard Libraries
import logging
from collections import defaultdict

# Django Imports
from django import template

# Ghostwriter Libraries
from ghostwriter.reporting.models import Severity

register = template.Library()

# Using __name__ resolves to ghostwriter.reporting.template_tags.report_tags
logger = logging.getLogger(__name__)


@register.filter
def get_item(dictionary, key):
    """
    Return a key value from a dictionary object.

    **Parameters**

    ``dictionary``
        Python dictionary object to parse
    ``key``
        Key name to retrieve from the dictionary
    """
    # Use `get` to return `None` if not found
    return dictionary.get(key)


@register.simple_tag
def group_by_severity(queryset):
    """
    Group a queryset by the ``Severity`` field.

    **Parameters**

    ``queryset``
        Instance of :model:`reporting.Report` or :model:`reporting.Finding`
    """
    all_severity = Severity.objects.all().order_by("weight")
    severity_dict = defaultdict(list)
    for severity in all_severity:
        severity_dict[str(severity)] = {
            "tpl_name": f"severity_{severity.weight}",
            "findings": [],
            "weight": severity.weight,
        }
    for finding in queryset:
        severity_dict[str(finding.severity)]["findings"].append(finding)
    # Return a basic dict because templates can't handle defaultdict
    return dict(severity_dict)
