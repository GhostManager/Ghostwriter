"""This contains all of the WebSocket routes used by the Ghostwriter application."""

# Django & Other 3rd Party Libraries
from django.urls import path
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

# Ghostwriter Libraries
from ghostwriter.oplog.consumers import OplogEntryConsumer

application = ProtocolTypeRouter(
    {
        "websocket": AuthMiddlewareStack(
            URLRouter([path("ws/oplog/<int:pk>/entries", OplogEntryConsumer)])
        )
    }
)
