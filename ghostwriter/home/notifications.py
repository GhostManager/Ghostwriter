"""Queries shared by the dashboard and system status page."""

# 3rd Party Libraries
from django_q.models import Task

# Ghostwriter Libraries
from ghostwriter.home.models import DashboardExceptionDismissal


def get_uncleared_failed_tasks():
    """Return failed jobs whose dashboard notifications have not been cleared."""
    dismissed_task_ids = DashboardExceptionDismissal.objects.values_list(
        "task_id", flat=True
    )
    return Task.objects.filter(success=False).exclude(id__in=dismissed_task_ids)
