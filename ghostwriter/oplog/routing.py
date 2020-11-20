"""This contains all of the WebSocket routes used by the Oplog application."""

# Django & Other 3rd Party Libraries
from django.urls import path

from . import consumers

websocket_urlpatterns = [
    path("ws/oplog/<int:pk>/entries", consumers.OplogEntryConsumer),
]
