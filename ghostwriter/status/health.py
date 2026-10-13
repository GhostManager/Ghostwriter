"""Read shared dashboard health and maintain its background schedule."""

# Standard Libraries
from datetime import timedelta

# Django Imports
from django.db import DEFAULT_DB_ALIAS, transaction
from django.utils import timezone

# 3rd Party Libraries
from django_q.models import Schedule

# Ghostwriter Libraries
from ghostwriter.home.django_q_policy import get_schedule_policy
from ghostwriter.status.models import DashboardHealthSnapshot

DASHBOARD_HEALTH_MAX_AGE = timedelta(minutes=3)
HEALTH_TASK = "ghostwriter.status.tasks.refresh_dashboard_health"
HEALTH_SCHEDULE_NAME = "Dashboard system health"


def get_dashboard_health_summary():
    """Return a recent shared snapshot, or unknown when monitoring is unavailable."""
    snapshot = DashboardHealthSnapshot.objects.filter(pk=1).first()
    if snapshot is not None:
        age = timezone.now() - snapshot.checked_at
        if timedelta(0) <= age <= DASHBOARD_HEALTH_MAX_AGE:
            return snapshot.summary
    return {"state": "UNKNOWN", "issues": []}


def ensure_dashboard_health_schedule(using=DEFAULT_DB_ALIAS):
    """Restore a missing monitor, preserving existing names, intervals, and pauses."""
    if HEALTH_TASK not in get_schedule_policy():
        return None
    schedules = Schedule.objects.using(using)
    schedule = schedules.filter(func=HEALTH_TASK).first()
    if schedule is not None:
        return schedule

    with transaction.atomic(using=using):
        # The singleton serializes creation when there is no schedule row to lock.
        DashboardHealthSnapshot.objects.using(using).select_for_update().get_or_create(
            pk=1,
            defaults={
                "checked_at": timezone.now(),
                "summary": {"state": "UNKNOWN", "issues": []},
            },
        )
        schedule, _created = schedules.get_or_create(
            func=HEALTH_TASK,
            defaults={
                "name": HEALTH_SCHEDULE_NAME,
                "schedule_type": Schedule.MINUTES,
                "minutes": 1,
                "repeats": -1,
            },
        )
        return schedule
