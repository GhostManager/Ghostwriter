"""This contains all the ``import_export`` model resources used by the Oplog application."""

# Standard Libraries
from datetime import datetime

# Django Imports
from django.conf import settings
from django.utils import timezone
from django.utils.dateparse import parse_datetime

# 3rd Party Libraries
from import_export import resources, widgets
from import_export.fields import Field
from taggit.models import Tag

# Ghostwriter Libraries
from ghostwriter.modules.shared import TagFieldImport, TagWidget, taggit_before_import_row
from ghostwriter.oplog.models import OplogEntry


def check_timestamps(datetime_val: str):
    """Check the timestamps in the imported data. If they are not timezone-aware, make them so."""
    tz = timezone.get_current_timezone()
    datetime_val = parse_datetime(datetime_val)
    if datetime_val.tzinfo is None or datetime_val.tzinfo.utcoffset(datetime_val) is None:
        datetime_val = timezone.make_aware(datetime_val, tz)
    return datetime_val


class TzDateTimeWidget(widgets.DateTimeWidget):
    """Custom widget to handle timezone-aware datetimes in export data."""

    def clean(self, value, row=None, *args, **kwargs):
        if not value:  # pragma: no cover
            return None
        if isinstance(value, datetime):  # pragma: no cover
            return value
        for _ in self.formats:
            try:
                if settings.USE_TZ:
                    dt = parse_datetime(value)
                    return dt
            except (ValueError, TypeError):  # pragma: no cover
                continue
        raise ValueError("Enter a valid date/time.")  # pragma: no cover


class OplogEntryResource(resources.ModelResource):
    """
    Import and export for :model:`oplog.OplogEntry`.
    """

    entry_identifier = None

    start_date = Field(attribute="start_date", column_name="start_date", widget=TzDateTimeWidget())
    end_date = Field(attribute="end_date", column_name="end_date", widget=TzDateTimeWidget())
    tags = TagFieldImport(attribute="tags", column_name="tags", widget=TagWidget(Tag, separator=","), default="")

    def before_import_row(self, row, **kwargs):
        # Track the `entry_identifier` for use in `get_import_id_fields()`
        self.entry_identifier = row.get("entry_identifier")
        taggit_before_import_row(row)
        row["start_date"] = check_timestamps(row["start_date"])
        row["end_date"] = check_timestamps(row["end_date"])

    def get_import_id_fields(self):
        # The `entry_identifier` is not unique in the table
        # We do want it unique in a log, so we'll use it as the import identifier, if it's present
        if not self.entry_identifier:
            return ["id"]

        return ("oplog_id", "entry_identifier")

    class Meta:
        model = OplogEntry
        skip_unchanged = False
        export_order = (
            "entry_identifier",
            "start_date",
            "end_date",
            "source_ip",
            "dest_ip",
            "tool",
            "user_context",
            "command",
            "description",
            "output",
            "comments",
            "operator_name",
            "tags",
            "extra_fields",
            "oplog_id",
        )
