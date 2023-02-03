"""This contains all the model Signals used by the Reporting application."""

# Standard Libraries
import logging

# Django Imports
from django.db.models.signals import pre_delete, pre_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.shepherd.models import (
    Domain,
    DomainStatus,
    History,
    ServerHistory,
    ServerStatus,
    StaticServer,
)

# Using __name__ resolves to ghostwriter.reporting.signals
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Domain)
def clean_domain(sender, instance, **kwargs):
    """
    Execute the :model:`shepherd.Domain` ``clean()`` function prior to ``save()``
    to ensure domain names are properly cleaned prior to any save.
    """
    instance.clean()


@receiver(pre_delete, sender=History)
def release_domain_on_delete(sender, instance, **kwargs):
    """
    Switch the associated :model:`shepherd.Domain` back to the "Available" status
    when the latest :model:`shepherd.History` is deleted.
    """
    latest_entry = History.objects.filter(domain=instance.domain).latest("end_date")
    if instance == latest_entry:
        available_status = DomainStatus.objects.get(domain_status="Available")
        domain = Domain.objects.get(pk=instance.domain.pk)
        domain.domain_status = available_status
        domain.save()


@receiver(pre_delete, sender=ServerHistory)
def release_server_on_delete(sender, instance, **kwargs):
    """
    Switch the associated :model:`shepherd.StaticServer` back to the "Available" status
    when the latest :model:`shepherd.ServerHistory` is deleted.
    """
    latest_entry = ServerHistory.objects.filter(server=instance.server).latest("end_date")
    if instance == latest_entry:
        available_status = ServerStatus.objects.get(server_status="Available")
        server = StaticServer.objects.get(pk=instance.server.pk)
        server.server_status = available_status
        server.save()
