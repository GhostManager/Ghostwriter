"""This contains all of the WebSocket consumers used by the Home application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.generic.websocket import AsyncWebsocketConsumer


class UserConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related individual :model:`users.User` over WebSockets.
    """

    async def connect(self):
        self.user = self.scope["user"]
        if self.user.is_active:
            self.username = self.scope["url_route"]["kwargs"]["username"]
            self.user_group_name = "notify_%s" % self.username
            # Join user group
            await self.channel_layer.group_add(self.user_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        if self.user.is_active:
            # Leave user group
            await self.channel_layer.group_discard(
                self.user_group_name, self.channel_name
            )
        else:
            pass

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to user group
        await self.channel_layer.group_send(
            self.user_group_name, {"type": "message", "message": message}
        )

    # Send a message to the user's channel for notifications
    async def message(self, event):
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    # Update a user with new assignments
    async def task(self, event):
        message = event["message"]
        assignments = event["assignments"]
        # Send message to WebSocket
        await self.send(
            text_data=json.dumps(
                {
                    "message": message,
                    "assignments": assignments,
                }
            )
        )


class ProjectConsumer(AsyncWebsocketConsumer):
    """
    Handle notifications related to individual :model:`rolodex.Project` over WebSockets.
    """

    async def connect(self):
        user = self.scope["user"]
        if user.is_active:
            self.project_id = self.scope["url_route"]["kwargs"]["project_id"]
            self.project_group_name = "notify_%s" % self.project_id
            # Join project group
            await self.channel_layer.group_add(self.project_group_name, self.channel_name)
            await self.accept()

    async def disconnect(self, close_code):
        # Leave project group
        await self.channel_layer.group_discard(self.project_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]

        # Send message to project group
        await self.channel_layer.group_send(
            self.project_group_name, {"type": "message", "message": message}
        )

    # Receive message from user group
    async def message(self, event):
        message = event["message"]
        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))
