"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import datetime
import logging
from datetime import date

# Ghostwriter Libraries
from ghostwriter.modules.notifications_slack import SlackNotification

from .models import Project

# Using __name__ resolves to ghostwriter.rolodex.tasks
logger = logging.getLogger(__name__)


def check_project_freshness():
    """
    Checks all entries in :model:`rolodex.Project` for incomplete projects that are overdue.
    """
    slack = SlackNotification()
    project_queryset = Project.objects.filter(complete=False)
    for project in project_queryset:
        nag_date = project.end_date + datetime.timedelta(1)
        # Check if date is before or is the end date
        if date.today() >= nag_date:
            message = "{} : This project should now be complete but is not marked as such in Ghostwriter. Extend the end date or mark the project and check that all reports have been marked as completed and delivered.".format(
                project
            )
            if project.slack_channel:
                slack.send_msg(message, project.slack_channel)
            else:
                slack.send_msg(message)
