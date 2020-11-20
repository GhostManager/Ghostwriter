"""This contains all of the WebSocket routes used by the Home application."""

# Django & Other 3rd Party Libraries
from django.urls import re_path

# Ghostwriter Libraries
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/users/(?P<username>\w+)/$", consumers.UserConsumer),
    re_path(r"ws/projects/(?P<project_id>\w+)/$", consumers.ProjectConsumer),
]
