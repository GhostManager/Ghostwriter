"""Background tasks for system monitoring."""

# Standard Libraries
import logging
from asgiref.sync import async_to_sync

# Django Imports
from django.db import transaction
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.status.models import DashboardHealthSnapshot
from ghostwriter.status.views import HealthCheckCustomView

logger = logging.getLogger(__name__)


def refresh_dashboard_health():
    """Publish a fresh summary without putting diagnostics on dashboard requests."""
    checked_at = timezone.now()
    try:
        summary = async_to_sync(HealthCheckCustomView().collect_health_summary)()
    except Exception:  # pylint: disable=broad-exception-caught
        logger.exception("Unable to complete background system health checks.")
        summary = {"state": "UNKNOWN", "issues": []}
    # Lock only while publishing; a slow older run must not replace a newer result.
    with transaction.atomic():
        snapshots = DashboardHealthSnapshot.objects.select_for_update()
        snapshot, created = snapshots.get_or_create(
            pk=1, defaults={"checked_at": checked_at, "summary": summary}
        )
        if not created and snapshot.checked_at <= checked_at:
            snapshot.checked_at = checked_at
            snapshot.summary = summary
            snapshot.save(update_fields=["checked_at", "summary"])
