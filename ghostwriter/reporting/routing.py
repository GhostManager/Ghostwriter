"""This contains all of the WebSocket routes used by the Reporting application."""

# Django Imports
from django.urls import re_path

from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/reports/(?P<report_id>\w+)/$", consumers.ReportConsumer.as_asgi()),
]
