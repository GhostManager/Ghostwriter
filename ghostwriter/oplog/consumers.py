"""This contains all the WebSocket consumers used by the Oplog application."""

# Standard Libraries
import json
import logging
from copy import deepcopy

# 3rd Party Libraries
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer
from rest_framework.utils.serializer_helpers import ReturnList

# Ghostwriter Libraries
from ghostwriter.modules.custom_serializers import OplogEntrySerializer
from ghostwriter.oplog.models import OplogEntry

# Using __name__ resolves to ghostwriter.oplog.consumers
logger = logging.getLogger(__name__)


@database_sync_to_async
def createOplogEntry(oplog_id, user):
    OplogEntry.objects.create(oplog_id_id=oplog_id, operator_name=user.username)


@database_sync_to_async
def deleteOplogEntry(entry_id):
    try:
        OplogEntry.objects.get(pk=entry_id).delete()
    except OplogEntry.DoesNotExist:
        # This is fine, it just means the entry was already deleted
        pass


@database_sync_to_async
def copyOplogEntry(entry_id):
    entry = OplogEntry.objects.get(pk=entry_id)
    if entry:
        copy = deepcopy(entry)
        copy.pk = None
        copy.save()
        copy.tags.add(*entry.tags.all())


class OplogEntryConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def getLogEntries(self, oplog_id: int, offset: int) -> ReturnList:
        entries = OplogEntry.objects.filter(oplog_id=oplog_id).order_by("-start_date")
        if len(entries) == offset:
            serialized_entries = OplogEntrySerializer([], many=True).data
        else:
            if len(entries) < (offset + 100):
                serialized_entries = OplogEntrySerializer(entries[offset:], many=True).data
            else:
                serialized_entries = OplogEntrySerializer(entries[offset : offset + 100], many=True).data

        return serialized_entries

    async def send_oplog_entry(self, event):
        await self.send(text_data=event["text"])

    async def connect(self):
        user = self.scope["user"]
        if user.is_active:
            oplog_id = self.scope["url_route"]["kwargs"]["pk"]
            await self.channel_layer.group_add(str(oplog_id), self.channel_name)
            await self.accept()

            serialized_entries = await self.getLogEntries(oplog_id, 0)
            message = json.dumps({"action": "sync", "data": serialized_entries})

            await self.send(text_data=message)

    async def disconnect(self, close_code):
        logger.info("WebSocket disconnected with close code: %s", close_code)

    async def receive(self, text_data=None, bytes_data=None):
        json_data = json.loads(text_data)
        if json_data["action"] == "delete":
            oplog_entry_id = int(json_data["oplogEntryId"])
            await deleteOplogEntry(oplog_entry_id)

        if json_data["action"] == "copy":
            oplog_entry_id = int(json_data["oplogEntryId"])
            await copyOplogEntry(oplog_entry_id)

        if json_data["action"] == "create":
            await createOplogEntry(json_data["oplog_id"], self.scope["user"])

        if json_data["action"] == "sync":
            oplog_id = json_data["oplog_id"]
            offset = json_data["offset"]
            entries = await self.getLogEntries(oplog_id, offset)
            message = json.dumps({"action": "sync", "data": entries})

            await self.send(text_data=message)
