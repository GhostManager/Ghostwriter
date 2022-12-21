"""This contains all the WebSocket consumers used by the Home application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.generic.websocket import AsyncWebsocketConsumer


class UserConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related individual :model:`users.User` over WebSockets.
    """

    def __init__(self):
        super().__init__()
        self.user = None
        self.username = None
        self.user_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_active:
            self.username = self.scope["url_route"]["kwargs"]["username"]
            self.user_group_name = "notify_%s" % self.username
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_active:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
        else:
            pass

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.user_group_name, {"type": "message", "message": message})

    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))


class ProjectConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related to individual :model:`rolodex.Project` over WebSockets.
    """

    def __init__(self):
        super().__init__()
        self.project_id = None
        self.project_group_name = None

    async def connect(self):
        user = self.scope["user"]
        if user.is_active:
            self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
            self.project_group_name = "notify_%s" % self.project_id
            await self.channel_layer.group_add(self.project_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard(self.project_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.project_group_name, {"type": "message", "message": message})

    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
