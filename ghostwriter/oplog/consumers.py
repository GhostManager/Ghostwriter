import asyncio
import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async

from .models import Oplog, OplogEntry
from .serializers import OplogEntrySerializer

from django.core.serializers import serialize


@database_sync_to_async
def getAllLogEntries(oplogId):
    return OplogEntry.objects.filter(oplog_id=oplogId).order_by("start_date")


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
def editOplogEntry(oplogEntryId, description, output, comments):
    entry = OplogEntry.objects.get(pk=oplogEntryId)
    if entry:
        entry.description = description
        entry.output = output
        entry.comments = comments
        entry.save()


class OplogEntryConsumer(AsyncWebsocketConsumer):
    async def send_oplog_entry(self, event):
        await self.send(text_data=event["text"])

    async def connect(self):
        oplog_id = self.scope["url_route"]["kwargs"]["pk"]
        await self.channel_layer.group_add(str(oplog_id), self.channel_name)
        await self.accept()

        entries = await getAllLogEntries(oplog_id)
        json_entries = serialize("json", entries)

        await self.channel_layer.group_send(str(oplog_id), {"type": "send_oplog_entry", "text": json_entries})

    async def disconnect(self, close_code):
        print(f"[*] Disconnected: {close_code}")

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
            await editOplogEntry(oplog_entry_id, json_data["description"], json_data["output"], json_data["comments"])

