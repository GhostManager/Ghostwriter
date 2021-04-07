"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import datetime
import json
import logging
from datetime import date

# 3rd Party Libraries
import requests

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import SlackConfiguration

from .models import Project

# Using __name__ resolves to ghostwriter.rolodex.tasks
logger = logging.getLogger(__name__)


def send_slack_msg(message, slack_channel=None):
    """
    Send a basic Slack message using the global Slack configuration.

    **Parameters**

    ``message``
        A string to be sent as the Slack message
    ``slack_channel``
        Defaults to using the global setting. Can be set to any Slack channel name
    """
    slack_config = SlackConfiguration.get_solo()

    if slack_config.enable:
        message = slack_config.slack_alert_target + " " + message
        slack_data = {
            "username": slack_config.slack_username,
            "icon_emoji": slack_config.slack_emoji,
            "channel": slack_config.slack_channel,
            "text": message,
        }
        response = requests.post(
            slack_config.webhook_url,
            data=json.dumps(slack_data),
            headers={"Content-Type": "application/json"},
        )
        if response.status_code != 200:
            logger.warning(
                "Request to Slack returned an error %s, the response was: %s",
                response.status_code,
                response.text,
            )
    else:
        logger.warning(
            "Received request to send Slack message, but Slack notifications are disabled in settings"
        )


def check_project_freshness():
    """
    Checks all entries in :model:`rolodex.Project` for incomplete projects that are overdue.
    """
    project_queryset = Project.objects.filter(complete=False)
    for project in project_queryset:
        nag_date = project.end_date + datetime.timedelta(1)
        # Check if date is before or is the end date
        if date.today() >= nag_date:
            message = "{} : This project should now be complete but is not marked as such in Ghostwriter. Extend the end date or mark the project and check that all reports have been marked as completed and delivered.".format(
                project
            )
            if project.slack_channel:
                send_slack_msg(message, project.slack_channel)
            else:
                send_slack_msg(message)
