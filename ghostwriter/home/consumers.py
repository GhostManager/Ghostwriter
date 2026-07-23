"""This contains all the WebSocket consumers used by the Home application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.generic.websocket import AsyncWebsocketConsumer


def user_can_access_channel(username, user):
    """Return whether a user can connect to the requested notification channel."""
    if not user.is_active:
        return False
    if username == "all":
        return True
    return username == user.get_clean_username()


class UserConsumer(AsyncWebsocketConsumer):
    """Handle notifications related individual :model:`users.User` over WebSockets."""

    def __init__(self):
        super().__init__()
        self.user = None
        self.username = None
        self.user_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        self.username = self.scope["url_route"]["kwargs"]["username"]
        if not user_can_access_channel(self.username, self.user):
            await self.close(code=4403)
            return

        self.user_group_name = "notify_%s" % self.username
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.user and self.user_group_name and self.user.is_active:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.user_group_name, {"type": "message", "message": message})

    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
