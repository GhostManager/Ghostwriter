"""This contains all the WebSocket routes used by the Home application."""

# Django Imports
from django.urls import re_path

# Ghostwriter Libraries
from ghostwriter.home import consumers

websocket_urlpatterns = [
    re_path(r"ws/users/(?P<username>\w+)/$", consumers.UserConsumer.as_asgi()),
]
