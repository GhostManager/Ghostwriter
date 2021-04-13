"""This contains all of the database models used by the Oplog application."""

# Standard Libraries
import json
import logging
from datetime import datetime

# Django Imports
from django.core.serializers import serialize
from django.db import models
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver

# 3rd Party Libraries
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

# Using __name__ resolves to ghostwriter.oplog.models
logger = logging.getLogger(__name__)


class Oplog(models.Model):
    """
    Stores an individual operation log.
    """

    name = models.CharField(max_length=50)
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project that will own this oplog",
    )

    class Meta:
        unique_together = ["name", "project"]

    def __str__(self):
        return f"{self.name} : {self.project}"


# Create your models here.
class OplogEntry(models.Model):
    """
    Stores an individual log entry, related to :model:`oplog.Oplog`.
    """

    oplog_id = models.ForeignKey(
        "Oplog",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select which log to which this entry will be inserted.",
        related_name="entries",
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    source_ip = models.TextField(
        "Source IP / Hostname",
        blank=True,
        help_text="Provide the source hostname / IP from which the command originated.",
    )

    dest_ip = models.TextField(
        "Destination IP/Hostname",
        blank=True,
        help_text="Provide the destination hostname / ip on which the command was ran.",
    )

    tool = models.TextField(
        "Tool name", blank=True, help_text="The tool used to execute the action"
    )

    user_context = models.TextField(
        "User Context",
        blank=True,
        help_text="The user context that executed the command",
    )

    command = models.TextField(
        "Command",
        blank=True,
        help_text="The command that was executed",
    )

    description = models.TextField(
        "Description",
        blank=True,
        help_text="A description of why the command was executed and expected results.",
    )

    output = models.TextField(
        "Output",
        null=True,
        blank=True,
        help_text="The output of the executed command",
    )

    comments = models.TextField(
        "Comments",
        blank=True,
        help_text="Any additional comments or useful information.",
    )

    operator_name = models.CharField(
        "Operator",
        blank=True,
        help_text="The operator that performed the action.",
        max_length=50,
    )


@receiver(pre_save, sender=OplogEntry)
def oplog_pre_save(sender, instance, **kwargs):
    """
    Set any missing ``start_date`` and ``end_date`` values for an entry for
    :model:`oplog.OplogEntry`.
    """
    if not instance.start_date:
        instance.start_date = datetime.utcnow()
    if not instance.end_date:
        instance.end_date = datetime.utcnow()


@receiver(post_save, sender=OplogEntry)
def signal_oplog_entry(sender, instance, **kwargs):
    """
    Send a WebSockets message to update a user's log entry list with the
    new or updated instance of :model:`oplog.OplogEntry`.
    """
    channel_layer = get_channel_layer()
    oplog_id = instance.oplog_id.id
    serialized_entry = serialize(
        "json",
        [
            instance,
        ],
    )
    entry = json.loads(serialized_entry)
    json_message = json.dumps({"action": "create", "data": entry})

    async_to_sync(channel_layer.group_send)(
        str(oplog_id), {"type": "send_oplog_entry", "text": json_message}
    )


@receiver(post_delete, sender=OplogEntry)
def delete_oplog_entry(sender, instance, **kwargs):
    """
    Send a WebSockets message to update a user's log entry list and remove
    the deleted instance of :model:`oplog.OplogEntry`.
    """
    channel_layer = get_channel_layer()
    try:
        oplog_id = instance.oplog_id.id
        entry_id = instance.id
        json_message = json.dumps({"action": "delete", "data": entry_id})
        async_to_sync(channel_layer.group_send)(
            str(oplog_id), {"type": "send_oplog_entry", "text": json_message}
        )
    except Oplog.DoesNotExist:
        # Oplog has been deleted and this is a cascading delete
        pass
