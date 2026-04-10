"""This contains all of the model Signals used by the oplog application."""

# Standard Libraries
import json
import logging
import os
from asgiref.sync import async_to_sync
from datetime import datetime
from socket import gaierror

# Django Imports
from django.db.models.signals import m2m_changed, post_delete, post_save, pre_save
from django.dispatch import receiver
from django.utils.timezone import make_aware

# 3rd Party Libraries
from channels.layers import get_channel_layer

# Ghostwriter Libraries
from ghostwriter.modules.custom_serializers import OplogEntrySerializer
from ghostwriter.oplog.models import Oplog, OplogEntry, OplogEntryEvidence, OplogEntryRecording

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


@receiver(m2m_changed, sender=OplogEntry.tags.through)
def signal_oplog_entry_tags(sender, instance, **kwargs):
    """
    Send a WebSockets message to update a user's log entry list with the
    new or updated tags applied to an instance of :model:`oplog.OplogEntry`.
    """
    if isinstance(instance, OplogEntry):
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


@receiver(post_save, sender=OplogEntryEvidence)
def oplog_entry_evidence_saved(sender, instance, created, **kwargs):
    """
    Add the "evidence" tag to an :model:`oplog.OplogEntry` when an evidence
    file is linked to it via :model:`oplog.OplogEntryEvidence`.
    """
    if created:
        instance.oplog_entry.tags.add("evidence")


@receiver(post_delete, sender=OplogEntryEvidence)
def oplog_entry_evidence_deleted(sender, instance, **kwargs):
    """
    Remove the "evidence" tag from an :model:`oplog.OplogEntry` when the last
    linked evidence file is removed via :model:`oplog.OplogEntryEvidence`.
    """
    try:
        entry = instance.oplog_entry
        if not entry.evidence_links.exists():
            entry.tags.remove("evidence")
    except OplogEntry.DoesNotExist:  # pragma: no cover
        # Entry has been deleted (cascading delete); nothing to update
        pass


@receiver(post_save, sender=OplogEntryRecording)
def recording_saved(sender, instance, created, **kwargs):
    """
    Add the "recording" tag to an :model:`oplog.OplogEntry` when a terminal recording
    is linked to it, and send a WebSockets message to update clients.
    """
    if created:
        instance.oplog_entry.tags.add("recording")
    try:
        entry = OplogEntry.objects.get(pk=instance.oplog_entry_id)
        channel_layer = get_channel_layer()
        oplog_id = entry.oplog_id.id
        serialized_entry = OplogEntrySerializer(entry).data
        json_message = json.dumps({"action": "create", "data": serialized_entry})
        async_to_sync(channel_layer.group_send)(str(oplog_id), {"type": "send_oplog_entry", "text": json_message})
    except gaierror:  # pragma: no cover
        pass


@receiver(post_delete, sender=OplogEntryRecording)
def delete_recording_file(sender, instance, **kwargs):
    """
    Remove the "recording" tag from an :model:`oplog.OplogEntry`, delete the recording
    file from disk, and broadcast a WebSockets update when an
    :model:`oplog.OplogEntryRecording` is deleted.
    """
    if instance.recording_file:
        try:
            if os.path.isfile(instance.recording_file.path):
                os.remove(instance.recording_file.path)
        except Exception:  # pragma: no cover
            logger.warning("Could not delete recording file: %s", instance.recording_file.name)
    try:
        entry = OplogEntry.objects.get(pk=instance.oplog_entry_id)
        entry.tags.remove("recording")
        channel_layer = get_channel_layer()
        oplog_id = entry.oplog_id.id
        serialized_entry = OplogEntrySerializer(entry).data
        json_message = json.dumps({"action": "create", "data": serialized_entry})
        async_to_sync(channel_layer.group_send)(str(oplog_id), {"type": "send_oplog_entry", "text": json_message})
    except OplogEntry.DoesNotExist:
        # Entry was cascade-deleted; the WebSocket "delete" message was already sent
        pass
    except gaierror:  # pragma: no cover
        pass
