"""This contains all the ``import_export`` model resources used by the Oplog application."""

# Standard Libraries
from datetime import datetime as dt

# 3rd Party Libraries
from import_export import resources

# Ghostwriter Libraries
from ghostwriter.oplog.models import OplogEntry


class OplogEntryResource(resources.ModelResource):
    def before_import_row(self, row, **kwargs):
        if "start_date" in row.keys():
            try:
                timestamp = int(float(row["start_date"]))
                dt_object = dt.fromtimestamp(timestamp / 1000)
                row["start_date"] = str(dt_object)
            except ValueError:  # pragma: no cover
                pass
        if "end_date" in row.keys():
            try:
                timestamp = int(float(row["end_date"]))
                dt_object = dt.fromtimestamp(timestamp / 1000)
                row["end_date"] = str(dt_object)
            except ValueError:  # pragma: no cover
                pass

    class Meta:
        model = OplogEntry
        skip_unchanged = True
        exclude = ("id",)
        import_id_fields = (
            "oplog_id",
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
        )
