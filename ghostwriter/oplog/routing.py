"""This contains all the WebSocket routes used by the Oplog application."""

# Django Imports
from django.urls import path

# Ghostwriter Libraries
from ghostwriter.oplog import consumers

websocket_urlpatterns = [
    path("ws/oplog/<int:pk>/entries", consumers.OplogEntryConsumer.as_asgi()),
]
