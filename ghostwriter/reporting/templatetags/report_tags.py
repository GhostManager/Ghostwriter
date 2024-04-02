"""Custom template tags for the reporting app."""

# Standard Libraries
import logging
import os
from collections import defaultdict

# Django Imports
from django import template

# Ghostwriter Libraries
from ghostwriter.reporting.models import Evidence, Severity

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


@register.filter
def get_file_type(file):
    """
    Determine the file type of a given evidence file.

    **Parameters**

    ``file``
        Instance of :model:`reporting.Evidence`
    """
    filetype = "unknown"
    if isinstance(file, Evidence):
        if os.path.isfile(file.document.path):
            if (
                file.document.name.lower().endswith(".txt")
                or file.document.name.lower().endswith(".log")
                or file.document.name.lower().endswith(".md")
            ):
                filetype = "text"
                file_content = []
                temp = file.document.read().splitlines()
                for line in temp:
                    try:
                        file_content.append(line.decode("utf-8", errors="replace"))
                    except UnicodeError:
                        file_content.append(line)
            elif (
                file.document.name.lower().endswith(".jpg")
                or file.document.name.lower().endswith(".png")
                or file.document.name.lower().endswith(".jpeg")
            ):
                filetype = "image"
        else:
            filetype = "missing"

    return filetype


@register.filter
def get_file_content(file):
    """
    Return the content of a text file (*.txt, *.log, or *.md).

    **Parameters**

    ``file``
        Instance of :model:`reporting.Evidence`
    """
    file_content = []
    if isinstance(file, Evidence):
        if os.path.isfile(file.document.path):
            if (
                file.document.name.lower().endswith(".txt")
                or file.document.name.lower().endswith(".log")
                or file.document.name.lower().endswith(".md")
            ):
                with open(file.document.path, "r", encoding="utf-8") as f:
                    file_content = f.read()
                    file_content.strip()
        else:
            file_content = "FILE NOT FOUND"

    return file_content


@register.filter
def get_file_basename(file):
    """
    Return the basename of a file.

    **Parameters**

    ``file``
        Instance of :model:`reporting.Evidence`
    """
    basename = "unknown"
    if isinstance(file, Evidence):
        basename = os.path.basename(file.document.name)

    return basename
