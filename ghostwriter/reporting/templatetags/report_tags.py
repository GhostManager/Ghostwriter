"""Custom template tags for the reporting app."""

# Import Django libraries
from django import template
from django.db.models import Q

# Import custom models
from ghostwriter.reporting.models import ReportFindingLink, Severity

# Other Python imports
from collections import defaultdict

register = template.Library()


@register.filter
def get_item(dictionary, key):
    """Accepts a dictionary and key and returns the contents. Used for
    referencing dictionary keys with variables.
    """
    # Use `get` to return `None` if not found
    return dictionary.get(key)


@register.simple_tag
def group_by_severity(queryset):
    """Accepts a queryset and returns a dictionary with the queryset
    grouped by the `Severity` field. Works with the `Finding` and
    `ReportFindingLink` models.
    """
    all_severity = Severity.objects.all().order_by("weight")
    severity_dict = defaultdict(list)
    for severity in all_severity:
        severity_dict[str(severity)] = []
    for finding in queryset:
        severity_dict[str(finding.severity)].append(finding)
    # Return a basic dict because templates can't handle defaultdict
    return dict(severity_dict)
