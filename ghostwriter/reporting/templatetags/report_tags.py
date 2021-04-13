"""Custom template tags for the reporting app."""

# Standard Libraries
import json
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

    ``dictonary``
        Python dictionary object to parse
    ``key``
        Key name tor etrieve from the dictionary
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
        severity_dict[str(severity)] = []
    for finding in queryset:
        severity_dict[str(finding.severity)].append(finding)
    # Return a basic dict because templates can't handle defaultdict
    return dict(severity_dict)


@register.filter
def load_json(data):
    """
    Parse a string as JSON and return JSON suitable for iterating.

    **Parameters**

    ``data``
        String to parse as JSON
    """
    try:
        return json.loads(data)
    except json.decoder.JSONDecodeError:
        logger.exception("Could not decode the string in the string: %s", data)
    except Exception:
        logger.exception("Encountered an error while trying to decode data as JSON")
