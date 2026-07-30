"""Server-provided configuration for rich-text editor date shortcuts."""

# Standard Libraries
from datetime import datetime, time, timedelta, timezone as datetime_timezone

# Django Imports
from django.conf import settings
from django.urls import reverse
from django.utils import dateformat, timezone


def _current_utc_time():
    """Return the current time normalized to UTC."""
    return timezone.now().astimezone(datetime_timezone.utc)


def get_editor_shortcuts_date_config():
    """Return the formatted current UTC date and its next UTC rollover."""
    current_time = _current_utc_time()
    current_date = current_time.date()
    next_midnight = datetime.combine(
        current_date + timedelta(days=1),
        time.min,
        tzinfo=datetime_timezone.utc,
    )

    return {
        "date": dateformat.format(current_date, settings.DATE_FORMAT),
        "expiresAt": round(next_midnight.timestamp() * 1000),
        "serverTime": round(current_time.timestamp() * 1000),
        "refreshUrl": reverse("home:ajax_editor_shortcuts_date"),
    }
