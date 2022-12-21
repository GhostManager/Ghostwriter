"""This contains all the WebSocket consumers used by the Reporting application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.generic.websocket import AsyncWebsocketConsumer


class ReportConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related to individual :model:`reporting.Report` entries over WebSockets.
    """

    def __init__(self):
        super().__init__()
        self.user = None
        self.report_id = None
        self.report_group_name = None


    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_active:
            self.report_id = self.scope["url_route"]["kwargs"]["report_id"]
            self.report_group_name = "report_%s" % self.report_id
            await self.channel_layer.group_add(self.report_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_active:
            await self.channel_layer.group_discard(self.report_group_name, self.channel_name)
        else:
            pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.report_group_name, {"type": "message", "message": message})

    # Message type of ``message`` for general communication
    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))

    # Message type of ``status_update`` for report generation status
    async def status_update(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))


class ReportFindingConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related to individual :model:`reporting.ReportFindingLink` entries over WebSockets.
    """

    def __init__(self):
        super().__init__()
        self.user = None
        self.finding_id = None
        self.finding_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_active:
            self.finding_id = self.scope["url_route"]["kwargs"]["finding_id"]
            self.finding_group_name = "finding_%s" % self.finding_id
            await self.channel_layer.group_add(self.finding_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_active:
            await self.channel_layer.group_discard(self.finding_group_name, self.channel_name)
        else:
            pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.user_group_name, {"type": "message", "message": message})

    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
