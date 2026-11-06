"""Regression tests for activity log monitoring."""

# Standard Libraries
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import OplogEntryFactory, OplogFactory, ProjectFactory
from ghostwriter.modules.oplog_monitors import review_active_logs
from ghostwriter.oplog.models import OplogEntry


class ActiveLogReviewTests(TestCase):
    """Review dated activity even when logs contain entries without dates."""

    def setUp(self):
        # A Tuesday ensures the existing weekend exclusion does not skip review.
        self.now = datetime(2026, 11, 3, 12, tzinfo=timezone.utc)
        clock = patch("ghostwriter.modules.oplog_monitors.datetime").start()
        self.addCleanup(patch.stopall)
        clock.utcnow.return_value = self.now
        clock.now.return_value = self.now
        self.slack = patch("ghostwriter.modules.oplog_monitors.SlackNotification").start().return_value
        self.slack.enabled = True
        self.slack.send_msg.return_value = None
        project = ProjectFactory(
            start_date=self.now.date() - timedelta(days=1),
            end_date=self.now.date() + timedelta(days=1),
        )
        self.log = OplogFactory(project=project)

    def add_undated_entry(self, log=None):
        """Persist a nullable date without the Django pre-save date defaults."""
        entry = OplogEntryFactory(oplog_id=log or self.log)
        OplogEntry.objects.filter(pk=entry.pk).update(start_date=None)

    def test_empty_log_is_inactive(self):
        results = review_active_logs()

        self.assertEqual(results["errors"], [])
        self.assertEqual(results["logs"][0]["status"], "inactive")
        self.slack.craft_inactive_log_msg.assert_called_once_with(self.log, 24, None)
        self.slack.send_msg.assert_called_once()

    def test_undated_log_is_inactive_and_other_logs_are_reviewed(self):
        self.add_undated_entry()
        other_log = OplogFactory(project=self.log.project)
        OplogEntryFactory(oplog_id=other_log, start_date=self.now - timedelta(hours=1))

        results = review_active_logs()

        self.assertEqual(results["errors"], [])
        statuses = {log["id"]: log["status"] for log in results["logs"]}
        self.assertEqual(statuses, {str(self.log.pk): "inactive", str(other_log.pk): "passing"})
        self.slack.craft_inactive_log_msg.assert_called_once_with(self.log, 24, None)
        self.slack.send_msg.assert_called_once()
        self.assertTrue(OplogEntry.objects.filter(oplog_id=self.log, start_date__isnull=True).exists())

    def test_recent_dated_entry_with_undated_entry_is_passing(self):
        OplogEntryFactory(oplog_id=self.log, start_date=self.now - timedelta(hours=48))
        OplogEntryFactory(oplog_id=self.log, start_date=self.now - timedelta(hours=1))
        self.add_undated_entry()

        results = review_active_logs()

        self.assertEqual(results["logs"][0]["status"], "passing")
        self.slack.send_msg.assert_not_called()

    def test_stale_dated_entry_with_undated_entry_is_inactive(self):
        last_activity = self.now - timedelta(hours=48)
        OplogEntryFactory(oplog_id=self.log, start_date=last_activity)
        self.add_undated_entry()

        results = review_active_logs()

        self.assertEqual(results["logs"][0]["status"], "inactive")
        self.slack.craft_inactive_log_msg.assert_called_once_with(self.log, 24, last_activity)
        self.slack.send_msg.assert_called_once()
