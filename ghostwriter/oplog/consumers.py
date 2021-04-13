"""This contains all of the WebSocket consumers used by the Oplog application."""

# Standard Libraries
import json
import logging

# Django Imports
from django.core.serializers import serialize

# 3rd Party Libraries
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

from .models import OplogEntry

# Using __name__ resolves to ghostwriter.oplog.consumers
logger = logging.getLogger(__name__)


@database_sync_to_async
def createOplogEntry(oplog_id):
    newEntry = OplogEntry.objects.create(oplog_id_id=oplog_id)
    newEntry.output = ""
    newEntry.save()


@database_sync_to_async
def deleteOplogEntry(oplogEntryId):
    OplogEntry.objects.get(pk=oplogEntryId).delete()


@database_sync_to_async
def copyOplogEntry(oplogEntryId):
    entry = OplogEntry.objects.get(pk=oplogEntryId)
    if entry:
        entry.pk = None
        entry.save()


@database_sync_to_async
def editOplogEntry(oplogEntryId, modifiedRow):
    entry = OplogEntry.objects.get(pk=oplogEntryId)

    for key, value in modifiedRow.items():
        setattr(entry, key, value)

    entry.save()


class OplogEntryConsumer(AsyncWebsocketConsumer):
    @database_sync_to_async
    def getLogEntries(self, oplogId, offset):
        entries = OplogEntry.objects.filter(oplog_id=oplogId).order_by("-start_date")
        if len(entries) == offset:
            serialized_entries = json.loads(serialize("json", []))
        else:
            if len(entries) < (offset + 100):
                serialized_entries = json.loads(serialize("json", entries[offset:]))
            else:
                serialized_entries = json.loads(
                    serialize("json", entries[offset : offset + 100])
                )
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

        if json_data["action"] == "edit":
            oplog_entry_id = int(json_data["oplogEntryId"])
            await editOplogEntry(oplog_entry_id, json_data["modifiedRow"])

        if json_data["action"] == "create":
            await createOplogEntry(json_data["oplog_id"])

        if json_data["action"] == "sync":
            oplog_id = json_data["oplog_id"]
            offset = json_data["offset"]
            entries = await self.getLogEntries(oplog_id, offset)
            message = json.dumps({"action": "sync", "data": entries})

            await self.send(text_data=message)
