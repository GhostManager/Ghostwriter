"""This contains all functions for monitoring operational logging activities."""

# Standard Libraries
import logging
from datetime import datetime, timedelta, timezone

# Django Imports
from django.conf import settings
from django.db.models import Q
from django.utils import dateformat

# Ghostwriter Libraries
from ghostwriter.modules.notifications_slack import SlackNotification
from ghostwriter.oplog.models import Oplog, OplogEntry

# Using __name__ resolves to ghostwriter.modules.cloud_monitors
logger = logging.getLogger(__name__)


def review_active_logs(hours: int = 24) -> dict:
    """
    Review :model:`oplog.OpLog` objects associated with :model:`rolodex.Project` entries
    still marked as active. If the log has not been updated in the past X hours
    (excluding weekends), send a notification to the configured Slack channel.

    **Parameters**

    ``hours``
        The number of hours to check for log activity (Default: 24)
    """
    logger.info("Checking for active logs that have not been updated in the past %s hours", hours)

    results = {"errors": [], "logs": []}

    # Setup dates with a consistent UTC timezone for comparisons
    today = datetime.utcnow().date()
    yesterday = today - timedelta(days=1)
    hours_ago = datetime.now(timezone.utc) - timedelta(hours=hours)

    # Check if yesterday was a weekend day (5 and 6 are Saturday and Sunday)
    if yesterday.weekday() < 5:
        slack = SlackNotification()
        active_logs = Oplog.objects.select_related("project").filter(
            Q(project__complete=False)
            & Q(project__end_date__gte=today)
            & Q(project__start_date__lte=today)
            & Q(mute_notifications=False)
        )
        logger.warning(active_logs)
        for log in active_logs:
            # Check if the latest log entry is older than the ``hours`` parameter
            inactive = False
            status = "passing"
            last_activity = None
            latest_log_entry = None

            # Try to get the latest log entry
            try:
                latest_log_entry = OplogEntry.objects.filter(oplog_id=log).latest("start_date")
            except OplogEntry.DoesNotExist:
                pass

            # If there is log entry, check if it is older than the ``hours`` parameter
            if latest_log_entry:
                last_activity = latest_log_entry.start_date.replace(tzinfo=timezone.utc)
                if last_activity < hours_ago:
                    inactive = True

            # If there are no logs or latest log is stale, handle notifications
            if not latest_log_entry or inactive:
                status = "inactive"

                logger.warning(
                    "Found a log for %s that has not been updated in the past %s hours",
                    log.project,
                    hours,
                )

                # If Slack is enabled, send a message to the configured project or global channel
                if slack.enabled:
                    channel = None
                    if log.project.slack_channel:
                        channel = log.project.slack_channel

                    logger.info("Sending Slack notification about inactive log to %s", channel)
                    blocks = slack.craft_inactive_log_msg(log, hours, last_activity)
                    err = slack.send_msg(
                        message=f"This activity log has had no activity in the past {hours} hours",
                        channel=channel,
                        blocks=blocks,
                    )
                    if err:
                        logger.warning("Attempt to send a Slack notification returned an error: %s", err)
                        results["errors"].append(err)
            else:
                if latest_log_entry:
                    last_activity = dateformat.format(latest_log_entry.start_date, settings.DATE_FORMAT)

            # Record results
            results["logs"].append(
                {
                    "id": f"{log.id}",
                    "name": f"{log.name}",
                    "project": f"{log.project}",
                    "latest_entry": f"{last_activity}",
                    "status": f"{status}",
                }
            )
    else:
        logger.info("Yesterday was a weekend day, skipping log review")

    logger.info("Finished checking for inactive logs")
    return results
