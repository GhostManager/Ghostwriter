"""This contains all the WebSocket consumers used by the Reporting application."""

# Standard Libraries
import json

# 3rd Party Libraries
from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

# Ghostwriter Libraries
from ghostwriter.reporting.models import Report, ReportFindingLink


def user_can_access_report(report_id, user):
    """Return whether the user can connect to a report WebSocket group."""
    if not user.is_active:
        return False
    try:
        report = Report.objects.get(pk=report_id)
    except (Report.DoesNotExist, ValueError, TypeError):
        return False
    return report.user_can_view(user)


def user_can_access_report_finding(finding_id, user):
    """Return whether the user can connect to a report-finding WebSocket group."""
    if not user.is_active:
        return False
    try:
        finding = ReportFindingLink.objects.get(pk=finding_id)
    except (ReportFindingLink.DoesNotExist, ValueError, TypeError):
        return False
    return finding.user_can_view(user)


user_can_access_report_async = database_sync_to_async(user_can_access_report)
user_can_access_report_finding_async = database_sync_to_async(user_can_access_report_finding)


class ReportConsumer(AsyncWebsocketConsumer):
    """Handle notifications related to individual :model:`reporting.Report` entries over WebSockets."""

    def __init__(self):
        super().__init__()
        self.user = None
        self.report_id = None
        self.report_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        self.report_id = self.scope["url_route"]["kwargs"]["report_id"]
        if not await user_can_access_report_async(self.report_id, self.user):
            await self.close(code=4403)
            return

        self.report_group_name = "report_%s" % self.report_id
        await self.channel_layer.group_add(self.report_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.user and self.report_group_name and self.user.is_active:
            await self.channel_layer.group_discard(self.report_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.report_group_name, {"type": "message", "message": message})

    # Message type of ``message`` for general communication
    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))

    # Message type of ``status_update`` for report generation status
    async def status_update(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))


class ReportFindingConsumer(AsyncWebsocketConsumer):
    """Handle notifications related to individual :model:`reporting.ReportFindingLink` entries over WebSockets."""

    def __init__(self):
        super().__init__()
        self.user = None
        self.finding_id = None
        self.finding_group_name = None

    async def connect(self):
        self.user = self.scope["user"]
        self.finding_id = self.scope["url_route"]["kwargs"]["finding_id"]
        if not await user_can_access_report_finding_async(self.finding_id, self.user):
            await self.close(code=4403)
            return

        self.finding_group_name = "finding_%s" % self.finding_id
        await self.channel_layer.group_add(self.finding_group_name, self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        if self.user and self.finding_group_name and self.user.is_active:
            await self.channel_layer.group_discard(self.finding_group_name, self.channel_name)

    async def receive(self, text_data):
        text_data_json = json.loads(text_data)
        message = text_data_json["message"]
        await self.channel_layer.group_send(self.finding_group_name, {"type": "message", "message": message})

    async def message(self, event):
        message = event["message"]
        await self.send(text_data=json.dumps({"message": message}))
