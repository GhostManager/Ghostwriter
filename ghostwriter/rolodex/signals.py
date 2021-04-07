"""This contains all of the model Signals used by the Rolodex application."""

# Standard Libraries
import logging

# Django Imports
from django.db.models.signals import post_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project, ProjectAssignment
from ghostwriter.shepherd.models import History, ServerHistory

# Using __name__ resolves to ghostwriter.rolodex.signals
logger = logging.getLogger(__name__)


@receiver(post_save, sender=Project)
def update_project(sender, instance, **kwargs):
    """
    Updates dates for :model:`shepherd.History`, :model:`shepherd.ServerHistory`, and
    :model:`rolodex.ProjectAssignments` whenever :model:`rolodex.Project` is updated.
    """
    domain_checkouts = History.objects.filter(project=instance)
    server_checkouts = ServerHistory.objects.filter(project=instance)
    project_assignments = ProjectAssignment.objects.filter(project=instance)
    for domain in domain_checkouts:
        if domain.start_date > instance.start_date or domain.end_date > instance.end_date:
            if domain.start_date > instance.start_date:
                domain.start_date = instance.start_date
            if domain.end_date > instance.end_date:
                domain.end_date = instance.end_date
            domain.save()
    for server in server_checkouts:
        if server.start_date > instance.start_date or server.end_date > instance.end_date:
            if server.start_date > instance.start_date:
                server.start_date = instance.start_date
            if server.end_date > instance.end_date:
                server.end_date = instance.end_date
            server.save()
    for assignment in project_assignments:
        if (
            assignment.start_date > instance.start_date
            or assignment.end_date > instance.end_date
        ):
            if assignment.start_date > instance.start_date:
                assignment.start_date = instance.start_date
            if assignment.end_date > instance.end_date:
                assignment.end_date = instance.end_date
            assignment.save()
