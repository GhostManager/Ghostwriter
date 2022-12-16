"""This contains all the model Signals used by the Rolodex application."""

# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.modules.notifications_slack import SlackNotification
from ghostwriter.rolodex.models import Project, ProjectObjective, ProjectSubTask
from ghostwriter.shepherd.models import History, ServerHistory

# Using __name__ resolves to ghostwriter.rolodex.signals
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Project)
def memorize_project(sender, instance, **kwargs):
    """
    Memorize the start and end dates of a :model:`shepherd.Project` entry
    prior to saving changes.
    """
    if instance.pk:
        initial_project = Project.objects.get(pk=instance.pk)
        instance.initial_start_date = initial_project.start_date
        instance.initial_end_date = initial_project.end_date
        instance.initial_slack_channel = initial_project.slack_channel


@receiver(post_save, sender=Project)
def update_project(sender, instance, **kwargs):
    """
    Post-save signal to perform various actions when :model:`shepherd.Project`
    entries are created or updated.

    Send Slack messages to test a :model:`rolodex.Project` entry's ``slack_channel``
    configuration on creation and whenever that value changes.

    Updates the dates for :model:`shepherd.History`, :model:`shepherd.ServerHistory`, and
    :model:`rolodex.ProjectAssignments` whenever the :model:`rolodex.Project` is updated.
    """
    slack = SlackNotification()

    if kwargs["created"]:
        logger.info("Newly saved project was just created so skipping `post_save` Signal used for updates")
        # If Slack is configured for this project, send a confirmation message
        if instance.slack_channel and slack.enabled:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Notifications Configured Successfully",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"Ghostwriter will send important notifications here for *{instance}*",
                    },
                },
            ]
            err = slack.send_msg(
                "Slack Notifications Configured Successfully",
                channel=instance.slack_channel,
                blocks=blocks,
            )
            if err:
                logger.warning(
                    "Attempt to send a Slack notification returned an error: %s",
                    err,
                )
    else:
        # If the ``slack_channel`` changed and a channel is still set, send a notification
        if instance.initial_slack_channel != instance.slack_channel and instance.slack_channel and slack.enabled:
            blocks = [
                {
                    "type": "header",
                    "text": {
                        "type": "plain_text",
                        "text": "Notifications Updated Successfully",
                    },
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"You're seeing this message because the channel for notifications related to *{instance}* changed. Ghostwriter will now send notifications here.",
                    },
                },
            ]
            err = slack.send_msg(
                "Notifications Updated Successfully",
                channel=instance.slack_channel,
                blocks=blocks,
            )
            if err:
                logger.warning(
                    "Attempt to send a Slack notification returned an error: %s",
                    err,
                )
        # If project dates changed, update all checkouts
        if instance.initial_start_date != instance.start_date or instance.initial_end_date != instance.end_date:
            logger.info("Project dates have changed so adjusting domain and server checkouts")

            domain_checkouts = History.objects.filter(project=instance)
            server_checkouts = ServerHistory.objects.filter(project=instance)

            today = date.today()

            start_date_delta = (instance.initial_start_date - instance.start_date).days
            end_date_delta = (instance.initial_end_date - instance.end_date).days

            logger.info("Start date changed by %s days", start_date_delta)
            logger.info("End date changed by %s days", end_date_delta)

            if slack.enabled and instance.slack_channel:
                blocks = [
                    {
                        "type": "header",
                        "text": {
                            "type": "plain_text",
                            "text": "Updated Project Dates",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"The dates for *{instance}* have been updated to {instance.start_date} – {instance.end_date}.",
                        },
                    },
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": f"Ghostwriter will now adjust any infrastructure checkouts by {abs(start_date_delta)} days for \
the start date and {abs(end_date_delta)} days for the end date.",
                        },
                    },
                ]
                err = slack.send_msg(
                    "Updated Project Dates",
                    channel=instance.slack_channel,
                    blocks=blocks,
                )
                if err:
                    logger.warning(
                        "Attempt to send a Slack notification returned an error: %s",
                        err,
                    )
            for entry in domain_checkouts:
                # Don't adjust checkouts that are in the past
                if entry.end_date > today:
                    if start_date_delta != 0:
                        entry.start_date = entry.start_date - timedelta(days=start_date_delta)

                    if end_date_delta != 0:
                        entry.end_date = entry.end_date - timedelta(days=end_date_delta)
                    entry.save()

            for entry in server_checkouts:
                if entry.end_date > today:
                    if start_date_delta != 0:
                        entry.start_date = entry.start_date - timedelta(days=start_date_delta)

                    if end_date_delta != 0:
                        entry.end_date = entry.end_date - timedelta(days=end_date_delta)
                    entry.save()


@receiver(pre_save, sender=ProjectObjective)
def memorize_project_objective(sender, instance, **kwargs):
    """
    Memorize the deadline of a :model:`rolodex.ProjectObjective` entry
    prior to saving changes.
    """
    if instance.pk:
        initial_objective = ProjectObjective.objects.get(pk=instance.pk)
        instance.initial_deadline = initial_objective.deadline


@receiver(post_save, sender=ProjectObjective)
def update_project_objective(sender, instance, **kwargs):
    """
    Updates dates for :model:`rolodex.ProjectSubTask` whenever
    :model:`rolodex.ProjectObjective` is updated.
    """

    subtasks = ProjectSubTask.objects.filter(parent=instance)
    for task in subtasks:
        if task.deadline > instance.deadline or task.deadline == instance.initial_deadline:
            task.deadline = instance.deadline
            task.save()
