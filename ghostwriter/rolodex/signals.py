from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver
from django.contrib import messages

from ghostwriter.rolodex.models import Project
from ghostwriter.rolodex.models import ProjectAssignment
from ghostwriter.shepherd.models import History, ServerHistory


@receiver(post_save, sender=Project)
def update_project(sender, instance, **kwargs):
    """Update domain checkouts, server checkouts, and operator assignments
    whenever a `Project` model entry is updated.
    """
    domain_checkouts = History.objects.filter(project=instance)
    server_checkouts = ServerHistory.objects.filter(project=instance)
    project_assignments = ProjectAssignment.objects.filter(project=instance)
    for domain in domain_checkouts:
        if domain.end_date > instance.end_date:
            domain.end_date = instance.end_date
            domain.save()
    for server in server_checkouts:
        if server.end_date > instance.end_date:
            server.end_date = instance.end_date
            server.save()
    for assignment in project_assignments:
        if assignment.end_date > instance.end_date:
            assignment.end_date = instance.end_date
            assignment.save()
