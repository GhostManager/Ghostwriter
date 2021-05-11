"""This contains all of the WebSocket routes used by the Oplog application."""

from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/oplog/<int:pk>/entries", consumers.OplogEntryConsumer.as_asgi()),
]
