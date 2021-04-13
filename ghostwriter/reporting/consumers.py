"""This contains all of the WebSocket consumers used by the Reporting application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.generic.websocket import AsyncWebsocketConsumer


class ReportConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related to individual :model:`rolodex.Project` over WebSockets.
    """

    async def connect(self):
        user = self.scope["user"]
        if user.is_active:
            self.report_id = self.scope["url_route"]["kwargs"]["report_id"]
            self.report_group_name = "report_%s" % self.report_id
            # Join report group
            await self.channel_layer.group_add(self.report_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        # Leave report group
        await self.channel_layer.group_discard(self.report_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to project group
        await self.channel_layer.group_send(
            self.report_group_name, {"type": "message", "message": message}
        )

    # Message type of ``message`` for general communication
    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))

    # Message type of ``status_update`` for report generation status
    async def status_update(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
