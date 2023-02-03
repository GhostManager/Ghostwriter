"""This contains all of the model Signals used by the oplog application."""

# Standard Libraries
import json
import logging
from datetime import datetime
from socket import gaierror

from asgiref.sync import async_to_sync
# 3rd Party Libraries
from channels.layers import get_channel_layer
# Django Imports
from django.db.models.signals import post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.timezone import make_aware

# Ghostwriter Libraries
from ghostwriter.modules.custom_serializers import OplogEntrySerializer
from ghostwriter.oplog.models import Oplog, OplogEntry

# Using __name__ resolves to ghostwriter.rolodex.signals
logger = logging.getLogger(__name__)


@receiver(pre_save, sender=OplogEntry)
def oplog_pre_save(sender, instance, **kwargs):
    """
    Set any missing ``start_date`` and ``end_date`` values for an entry for
    :model:`oplog.OplogEntry`.
    """
    if not instance.start_date:
        instance.start_date = make_aware(datetime.utcnow())
    if not instance.end_date:
        instance.end_date = make_aware(datetime.utcnow())

    instance.clean()


@receiver(post_save, sender=OplogEntry)
def signal_oplog_entry(sender, instance, **kwargs):
    """
    Send a WebSockets message to update a user's log entry list with the
    new or updated instance of :model:`oplog.OplogEntry`.
    """
    try:
        channel_layer = get_channel_layer()
        oplog_id = instance.oplog_id.id
        serialized_entry = OplogEntrySerializer(instance).data
        json_message = json.dumps({"action": "create", "data": serialized_entry})

        async_to_sync(channel_layer.group_send)(str(oplog_id), {"type": "send_oplog_entry", "text": json_message})
    except gaierror:  # pragma: no cover
        # WebSocket are unavailable (unit testing)
        pass


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
        async_to_sync(channel_layer.group_send)(str(oplog_id), {"type": "send_oplog_entry", "text": json_message})
    except Oplog.DoesNotExist:  # pragma: no cover
        # Oplog has been deleted and this is a cascading delete
        pass
    except gaierror:  # pragma: no cover
        # WebSocket are unavailable (unit testing)
        pass
