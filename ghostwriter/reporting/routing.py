"""This contains all of the WebSocket routes used by the Reporting application."""

# Django & Other 3rd Party Libraries
from django.urls import re_path

# Ghostwriter Libraries
from . import consumers

websocket_urlpatterns = [
    re_path(r"ws/reports/(?P<report_id>\w+)/$", consumers.ReportConsumer),
]
