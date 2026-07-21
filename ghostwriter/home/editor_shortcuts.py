"""Server-provided configuration for rich-text editor date shortcuts."""

# Standard Libraries
from datetime import datetime, time, timedelta

# Django Imports
from django.conf import settings
from django.urls import reverse
from django.utils import dateformat, timezone


def get_editor_shortcuts_date_config():
    """Return the formatted current date and its next server-local rollover."""
    current_time = timezone.localtime()
    current_date = current_time.date()
    next_midnight = timezone.make_aware(
        datetime.combine(current_date + timedelta(days=1), time.min),
        timezone.get_current_timezone(),
    )

    return {
        "date": dateformat.format(current_date, settings.DATE_FORMAT),
        "expiresAt": round(next_midnight.timestamp() * 1000),
        "serverTime": round(current_time.timestamp() * 1000),
        "refreshUrl": reverse("home:ajax_editor_shortcuts_date"),
    }
