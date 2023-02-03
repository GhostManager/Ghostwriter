"""This contains all the WebSocket routes used by the Reporting application."""

# Django Imports
from django.urls import re_path

# Ghostwriter Libraries
from ghostwriter.reporting import consumers

websocket_urlpatterns = [
    re_path(r"ws/reports/(?P<report_id>\w+)/$", consumers.ReportConsumer.as_asgi()),
    re_path(r"ws/reports/findings/(?P<finding_id>\w+)/$", consumers.ReportFindingConsumer.as_asgi()),
]
