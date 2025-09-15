"""
Jinja filters that ghostwriter exposes
"""

from datetime import datetime, timedelta
import html
import logging
import re

from bs4 import BeautifulSoup
from dateutil.parser import parse as parse_datetime
from dateutil.parser._parser import ParserError
from django.conf import settings
from django.utils.dateformat import format as dateformat
import jinja2
from markupsafe import Markup

from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError

logger = logging.getLogger(__name__)

# Custom Jinja2 filters for DOCX templates
def filter_severity(findings, allowlist):
    """
    Filter a list of findings to return only those with a severity in the allowlist.

    **Parameters**

    ``findings``
        List of dictionary objects (JSON) for findings
    ``allowlist``
        List of strings matching severity categories to allow through filter
    """
    filtered_values = []
    if isinstance(allowlist, list):
        allowlist = [severity.lower() for severity in allowlist]
    else:
        raise InvalidFilterValue(
            f'Allowlist passed into `filter_severity()` filter is not a list ("{allowlist}"); must be like `["Critical", "High"]`'
        )
    try:
        for finding in findings:
            if finding["severity"].lower() in allowlist:
                filtered_values.append(finding)
    except (KeyError, TypeError):
        logger.exception("Error parsing ``findings`` as a list of dictionaries: %s", findings)
        raise InvalidFilterValue(
            "Invalid list of findings passed into `filter_severity()` filter; must be the `{{ findings }}` object"
        )
    return filtered_values


def filter_type(findings, allowlist):
    """
    Filter a list of findings to return only those with a type in the allowlist.

    **Parameters**

    ``findings``
        List of dictionary objects (JSON) for findings
    ``allowlist``
        List of strings matching severity categories to allow through filter
    """
    filtered_values = []
    if isinstance(allowlist, list):
        allowlist = [t.lower() for t in allowlist]
    else:
        raise InvalidFilterValue(
            f'Allowlist passed into `filter_type()` filter is not a list ("{allowlist}"); must be like `["Network", "Web"]`'
        )
    try:
        for finding in findings:
            if finding["finding_type"].lower() in allowlist:
                filtered_values.append(finding)
    except (KeyError, TypeError):
        logger.exception("Error parsing ``findings`` as a list of dictionaries: %s", findings)
        raise InvalidFilterValue(
            "Invalid list of findings passed into `filter_type()` filter; must be the `{{ findings }}` object"
        )
    return filtered_values


def strip_html(s):
    """
    Strip HTML tags from the provided HTML while preserving newlines created by
    ``<br />`` and ``<p>`` tags and spaces.

    **Parameters**

    ``s``
        String of HTML text to strip down
    """
    soup = BeautifulSoup(s, "lxml")
    output = ""
    for tag in soup.descendants:
        if isinstance(tag, str):
            output += tag
        elif tag.name in ("br", "p"):
            output += "\n"
    return output.strip()


def compromised(targets):
    """
    Filter a list of targets to return only those marked as compromised.

    **Parameters**

    ``targets``
        List of dictionary objects (JSON) for targets
    """
    filtered_targets = []
    try:
        for target in targets:
            if target["compromised"]:
                filtered_targets.append(target)
    except (KeyError, TypeError) as e:
        logger.exception("Error parsing ``targets`` as a list of dictionaries: %s", targets)
        raise InvalidFilterValue(
            "Invalid list of targets passed into `compromised()` filter; must be the `{{ targets }}` object"
        ) from e
    return filtered_targets


def add_days(date, days):
    """
    Add a number of business days to a date.

    **Parameters**

    ``date``
        Date string to add business days to
    ``days``
        Number of business days to add to the date
    """
    new_date = None
    try:
        days = int(days)
    except ValueError as e:
        logger.exception("Error parsing ``days`` as an integer: %s", days)
        raise InvalidFilterValue(f'Invalid integer ("{days}") passed into the `add_days()` filter') from e

    try:
        date_obj = date if isinstance(date, datetime) else parse_datetime(date)
        # Loop until all days added
        if days > 0:
            while days > 0:
                # Add one day to the date
                date_obj += timedelta(days=1)
                # Check if the day is a business day
                weekday = date_obj.weekday()
                if weekday >= 5:
                    # Return to the top (Sunday is 6)
                    continue
                # Decrement the number of days to add
                days -= 1
        else:
            # Same as above but in reverse for negative days
            while days < 0:
                date_obj -= timedelta(days=1)
                weekday = date_obj.weekday()
                if weekday >= 5:
                    continue
                days += 1
        new_date = dateformat(date_obj, settings.DATE_FORMAT)
    except ParserError as e:
        logger.exception("Error parsing ``date`` as a date: %s", date)
        raise InvalidFilterValue(f'Invalid date string ("{date}") passed into the `add_days()` filter') from e
    return new_date


def format_datetime(date, new_format=None):
    """
    Change the format of a given date string.

    **Parameters**

    ``date``
        Date string to modify
    ``format_str``
        The format of the provided date. If omitted, use the global setting.
    """
    try:
        date_obj = date if isinstance(date, datetime) else parse_datetime(date)
        formatted_date = dateformat(date_obj, new_format if new_format is not None else settings.DATE_FORMAT)
    except ParserError as e:
        logger.exception("Error parsing ``date`` as a date: %s", date)
        raise InvalidFilterValue(f'Invalid date string ("{date}") passed into the `format_datetime()` filter') from e
    return formatted_date


def get_item(lst, index):
    """
    Get the item at the specified index in a list.

    **Parameters**

    ``list``
        List to get item from
    ``index``
        Index of item to get
    """
    try:
        return lst[index]
    except TypeError as e:
        logger.exception("Error getting list index %s from this list: %s", index, lst)
        raise InvalidFilterValue("Invalid list or string passed into the `get_item()` filter") from e
    except IndexError as e:
        logger.exception("Error getting index %s from this list: %s", index, lst)
        raise InvalidFilterValue("Invalid or unavailable index passed into the `get_item()` filter") from e


def regex_search(text, regex):
    """
    Perform a regex search on the provided text and return the first match.

    **Parameters**

    ``regex``
        Regular expression to search with
    ``text``
        Text to search
    """
    match = re.search(regex, text)
    if match:
        return match.group(0)
    return None


def filter_tags(objects, allowlist):
    """
    Filter a list of objects to return only those with a tag in the allowlist.

    **Parameters**

    ``objects``
        List of dictionary objects (JSON) for findings
    ``allowlist``
        List of strings matching severity categories to allow through filter
    """
    filtered_values = []
    if not isinstance(allowlist, list):
        raise InvalidFilterValue(
            f'Allowlist passed into `filter_tags()` filter is not a list ("{allowlist}"); must be like `["xss", "T1651"]`'
        )
    try:
        for obj in objects:
            common_tags = set(obj["tags"]) & set(allowlist)
            if common_tags:
                filtered_values.append(obj)
    except (KeyError, TypeError) as e:
        logger.exception("Error parsing object as a list of dictionaries: %s", object)
        raise InvalidFilterValue(
            "Invalid list of objects passed into `filter_tags()` filter; must be an object with a `tags` key"
        ) from e
    return filtered_values


def caption(caption_name):
    return Markup('<span data-gw-caption="' + html.escape(caption_name) + '"></span>')


def ref(ref_name):
    return Markup('<span data-gw-ref="' + html.escape(ref_name) + '"></span>')


@jinja2.pass_context
def mk_evidence(context: jinja2.runtime.Context, evidence_name: str) -> Markup:
    """
    `{{mk_evidence(name)}}` function in jinja.
    """
    evidences = context.get("_evidences")
    if evidences is None:
        raise ReportExportTemplateError("No evidences are available in this context")
    evidence_id = evidences.get(evidence_name)
    if evidence_id is None:
        raise ReportExportTemplateError(f"No such evidence with name '{evidence_name}'")
    return raw_mk_evidence(evidence_id)


def raw_mk_evidence(evidence_id) -> Markup:
    return Markup('<span data-gw-evidence="' + html.escape(str(evidence_id)) + '"></span>')


def replace_blanks(list_of_dicts, placeholder=""):
    """
    Replace blank strings in a dictionary with a placeholder string.

    **Parameters**

    ``dict``
        Dictionary to replace blanks in
    """

    try:
        for d in list_of_dicts:
            for key, value in d.items():
                if value is None:
                    d[key] = placeholder
    except (AttributeError, TypeError) as e:
        logger.exception("Error parsing ``list_of_dicts`` as a list of dictionaries: %s", list_of_dicts)
        raise InvalidFilterValue(
            "Invalid list of dictionaries passed into `replace_blanks()` filter; must be a list of dictionaries"
        ) from e
    return list_of_dicts
