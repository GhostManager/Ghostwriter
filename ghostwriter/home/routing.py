"""This contains all of the WebSocket routes used by the Home application."""

# Django Imports
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/users/(?P<username>\w+)/$", consumers.UserConsumer.as_asgi()),
    re_path(r"ws/projects/(?P<project_id>\w+)/$", consumers.ProjectConsumer.as_asgi()),
]
