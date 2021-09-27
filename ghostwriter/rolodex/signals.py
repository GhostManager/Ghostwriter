"""This contains all of the model Signals used by the Rolodex application."""

# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project
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


@receiver(post_save, sender=Project)
def update_project(sender, instance, **kwargs):
    """
    Updates dates for :model:`shepherd.History`, :model:`shepherd.ServerHistory`, and
    :model:`rolodex.ProjectAssignments` whenever :model:`rolodex.Project` is updated.
    """
    if kwargs["created"]:
        logger.info(
            "Newly saved project was just created so skipping `post_save` Signal used for updates"
        )
    else:
        domain_checkouts = History.objects.filter(project=instance)
        server_checkouts = ServerHistory.objects.filter(project=instance)

        if (
            instance.initial_start_date != instance.start_date
            or instance.initial_end_date != instance.end_date
        ):
            logger.info(
                "Project dates have changed so adjusting domain and server checkouts"
            )

            today = date.today()

            start_date_delta = (instance.initial_start_date - instance.start_date).days
            end_date_delta = (instance.initial_end_date - instance.end_date).days

            logger.info("Start date changed by %s days", start_date_delta)
            logger.info("End date changed by %s days", end_date_delta)

            for entry in domain_checkouts:
                # Don't adjust checkouts that are in the past
                if entry.end_date > today:
                    if start_date_delta != 0:
                        entry.start_date = entry.start_date - timedelta(
                            days=start_date_delta
                        )

                    if end_date_delta != 0:
                        entry.end_date = entry.end_date - timedelta(days=end_date_delta)
                    entry.save()

            for entry in server_checkouts:
                # Don't adjust checkouts that are in the past
                if entry.end_date > today:
                    if start_date_delta != 0:
                        entry.start_date = entry.start_date - timedelta(
                            days=start_date_delta
                        )

                    if end_date_delta != 0:
                        entry.end_date = entry.end_date - timedelta(days=end_date_delta)
                    entry.save()
