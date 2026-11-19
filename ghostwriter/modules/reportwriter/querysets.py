"""Querysets for report generation and activity-log serialization."""

from django.db.models import Prefetch

from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Report


def oplog_entries_prefetch(prefix=""):
    """Load entries, their tags, and recording metadata for export."""
    return Prefetch(
        f"{prefix}oplog_set__entries",
        queryset=(
            OplogEntry.objects.select_related("recording")
            .defer("recording__recording_text")
            .prefetch_related("tags")
        ),
    )


def report_generation_queryset(*, include_logs=True):
    """Build the report export queryset, optionally deferring activity logs."""
    queryset = Report.objects.prefetch_related(
        "tags",
        "reportfindinglink_set",
        "reportobservationlink_set",
        "evidence_set",
    ).select_related()
    if include_logs:
        queryset = queryset.prefetch_related(oplog_entries_prefetch("project__"))
    return queryset
