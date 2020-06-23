"""This contains all of the WebSocket routes for the Home application."""

from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r'ws/users/(?P<username>\w+)/$', consumers.UserConsumer),
]
