# Standard Libraries
import logging
from datetime import datetime

# 3rd Party Libraries
import pytz

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import OplogEntryFactory, OplogFactory

logging.disable(logging.CRITICAL)


class OplogModelTests(TestCase):
    """Collection of tests for :model:`oplog.Oplog`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model

    def test_crud_finding(self):
        # Create
        oplog = OplogFactory(name="Oplog 1")

        # Read
        self.assertEqual(oplog.name, "Oplog 1")
        self.assertEqual(oplog.pk, oplog.id)

        # Update
        oplog.name = "Updated Oplog"
        oplog.save()
        self.assertEqual(oplog.name, "Updated Oplog")

        # Delete
        oplog.delete()
        assert not self.Oplog.objects.all().exists()


class OplogEntryModelTests(TestCase):
    """Collection of tests for :model:`oplog.OplogEntry`."""

    @classmethod
    def setUpTestData(cls):
        cls.OplogEntry = OplogEntryFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = OplogEntryFactory(tool="Rubeus.exe")

        # Read
        self.assertEqual(entry.tool, "Rubeus.exe")
        self.assertEqual(entry.pk, entry.id)

        # Update
        entry.tool = "Seatbelt.exe"
        entry.save()
        self.assertEqual(entry.tool, "Seatbelt.exe")

        # Delete
        entry.delete()
        assert not self.OplogEntry.objects.all().exists()

    def test_pre_save_signal(self):
        entry = OplogEntryFactory(start_date=None, end_date=None)
        entry.tool = "Rubeus.exe"
        entry.save()
        self.assertIsInstance(entry.start_date, datetime)
        self.assertIsInstance(entry.end_date, datetime)

    def test_invalid_dates(self):
        valid_start_date = datetime.now(pytz.UTC)
        valid_end_date = datetime.now(pytz.UTC)
        invalid_start_date = "2021-09-14 14:09"
        invalid_end_date = "Totally a Date"

        # Create new entry with valid dates
        entry = OplogEntryFactory(start_date=valid_start_date, end_date=valid_end_date)

        # Try invalid start date
        entry.start_date = invalid_start_date
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.start_date, valid_start_date)

        # Try invalid end date
        entry.end_date = invalid_end_date
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.end_date, valid_end_date)

    def test_tagging(self):
        tags = ["tag1", "tag2", "tag3"]
        entry = OplogEntryFactory(tags=tags)

        self.assertEqual(list(entry.tags.names()), tags)

        tags.append("tag4")
        entry.tags.add("tag4")
        entry.refresh_from_db()

        self.assertEqual(list(entry.tags.names()), tags)
