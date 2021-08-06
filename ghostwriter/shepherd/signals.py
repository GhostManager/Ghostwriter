"""This contains all of the model Signals used by the Reporting application."""

# Standard Libraries
import logging

# Django Imports
from django.db.models.signals import pre_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.shepherd.models import Domain

# Using __name__ resolves to ghostwriter.reporting.signals
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=Domain)
def clean_domain(sender, instance, **kwargs):
    """
    Execute the :model:`shepherd.Domain` ``clean()`` function prior to ``save()``
    to ensure domain names are properly cleaned prior to any save.
    """
    instance.clean()
