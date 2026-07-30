# Standard Libraries
import json
import logging
from asgiref.sync import async_to_sync
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

# Django Imports
from django.test import TestCase, TransactionTestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    UserFactory,
)
from ghostwriter.oplog.consumers import (
    OplogEntryConsumer,
    copy_oplog_entry,
    create_oplog_entry,
    user_can_access_oplog,
)
from ghostwriter.oplog.models import OplogEntry

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class OplogConsumerAccessTests(TestCase):
    """Tests for oplog WebSocket access decisions."""

    @classmethod
    def setUpTestData(cls):
        cls.oplog = OplogFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.other_user = UserFactory(password=PASSWORD)
        cls.inactive_user = UserFactory(password=PASSWORD, is_active=False)
        ProjectAssignmentFactory(project=cls.oplog.project, operator=cls.user)

    def test_assigned_user_can_access_oplog_socket(self):
        self.assertTrue(user_can_access_oplog(self.oplog.id, self.user))

    def test_unassigned_user_cannot_access_oplog_socket(self):
        self.assertFalse(user_can_access_oplog(self.oplog.id, self.other_user))

    def test_inactive_user_cannot_access_oplog_socket(self):
        self.assertFalse(user_can_access_oplog(self.oplog.id, self.inactive_user))

    def test_missing_oplog_denies_socket_access(self):
        self.assertFalse(user_can_access_oplog(0, self.user))

    @patch(
        "ghostwriter.oplog.consumers.create_oplog_entry",
        new_callable=AsyncMock,
    )
    def test_create_returns_modal_request_scoped_acknowledgement(self, mock_create):
        mock_create.return_value = 42
        consumer = OplogEntryConsumer()
        consumer.scope = {"user": self.user}
        consumer.send = AsyncMock()

        async_to_sync(consumer.receive)(
            text_data=json.dumps(
                {
                    "action": "create",
                    "oplog_id": self.oplog.id,
                    "modal_request_id": "request-123",
                }
            )
        )

        mock_create.assert_awaited_once_with(self.oplog.id, self.user)
        consumer.send.assert_awaited_once()
        response = json.loads(consumer.send.await_args.kwargs["text_data"])
        self.assertEqual(
            response,
            {
                "action": "create_modal_ack",
                "modal_request_id": "request-123",
                "entry_id": 42,
            },
        )

    @patch(
        "ghostwriter.oplog.consumers.create_oplog_entry",
        new_callable=AsyncMock,
    )
    def test_create_failure_returns_empty_acknowledgement(self, mock_create):
        mock_create.return_value = None
        consumer = OplogEntryConsumer()
        consumer.scope = {"user": self.user}
        consumer.send = AsyncMock()

        async_to_sync(consumer.receive)(
            text_data=json.dumps(
                {
                    "action": "create",
                    "oplog_id": self.oplog.id,
                    "modal_request_id": "request-456",
                }
            )
        )

        response = json.loads(consumer.send.await_args.kwargs["text_data"])
        self.assertEqual(response["action"], "create_modal_ack")
        self.assertEqual(response["modal_request_id"], "request-456")
        self.assertIsNone(response["entry_id"])

    @patch(
        "ghostwriter.oplog.consumers.create_oplog_entry",
        new_callable=AsyncMock,
    )
    def test_create_without_modal_request_sends_no_acknowledgement(self, mock_create):
        mock_create.return_value = 42
        consumer = OplogEntryConsumer()
        consumer.scope = {"user": self.user}
        consumer.send = AsyncMock()

        async_to_sync(consumer.receive)(
            text_data=json.dumps(
                {
                    "action": "create",
                    "oplog_id": self.oplog.id,
                }
            )
        )

        mock_create.assert_awaited_once_with(self.oplog.id, self.user)
        consumer.send.assert_not_awaited()


class OplogConsumerCreateTests(TransactionTestCase):
    """Tests for creating entries from the asynchronous consumer."""

    def setUp(self):
        self.oplog = OplogFactory()
        self.user = UserFactory(password=PASSWORD)
        self.other_user = UserFactory(password=PASSWORD)
        ProjectAssignmentFactory(project=self.oplog.project, operator=self.user)

    def test_create_returns_entry_id(self):
        entry_id = async_to_sync(create_oplog_entry)(self.oplog.id, self.user)

        entry = OplogEntry.objects.get(id=entry_id)
        self.assertEqual(entry.oplog_id_id, self.oplog.id)
        self.assertEqual(entry.operator_name, self.user.username)

    def test_create_without_edit_access_returns_none(self):
        entry_id = async_to_sync(create_oplog_entry)(
            self.oplog.id,
            self.other_user,
        )

        self.assertIsNone(entry_id)
        self.assertFalse(
            OplogEntry.objects.filter(
                oplog_id=self.oplog,
                operator_name=self.other_user.username,
            ).exists()
        )

    @patch("ghostwriter.oplog.consumers.timezone.now")
    def test_copy_uses_current_instant(self, mock_now):
        expected_now = datetime(2026, 1, 15, 20, 30, 45, tzinfo=timezone.utc)
        mock_now.return_value = expected_now
        entry = OplogEntryFactory(oplog_id=self.oplog)

        async_to_sync(copy_oplog_entry)(entry.id, self.user)

        copied_entry = OplogEntry.objects.filter(oplog_id=self.oplog).exclude(id=entry.id).get()
        self.assertEqual(copied_entry.start_date, expected_now)
        self.assertEqual(copied_entry.end_date, expected_now)
