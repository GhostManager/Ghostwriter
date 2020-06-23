"""This contains all of the WebSocket consumers for the Home application."""

from django.contrib import messages
from channels.generic.websocket import WebsocketConsumer, AsyncWebsocketConsumer
import json


class UserConsumer(AsyncWebsocketConsumer):
    """Basic consumer class written as a test."""
    async def connect(self):
        self.username = self.scope['url_route']['kwargs']['username']
        self.user_group_name = 'notify_%s' % self.username
        # Join user group
        await self.channel_layer.group_add(
            self.user_group_name,
            self.channel_name
        )
        await self.accept()

    async def disconnect(self, close_code):
        # Leave user group
        await self.channel_layer.group_discard(
            self.user_group_name,
            self.channel_name
        )

    # Receive message from WebSocket
    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json['message']

        # Send message to user group
        await self.channel_layer.group_send(
            self.user_group_name,
            {
                'type': 'message',
                'message': message
            }
        )

    # Receive message from user group
    async def message(self, event):
        message = event['message']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message
        }))

    # Receive message from user group
    async def task(self, event):
        message = event['message']
        assignments = event['assignments']
        # Send message to WebSocket
        await self.send(text_data=json.dumps({
            'message': message,
            'assignments': assignments,
        }))
