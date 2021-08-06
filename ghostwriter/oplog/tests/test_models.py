# Standard Libraries
import logging
from datetime import datetime

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import OplogEntryFactory, OplogFactory

logging.disable(logging.INFO)


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
        self.assertQuerysetEqual(
            self.Oplog.objects.all(),
            [f"<Oplog: {oplog.name} : {oplog.project}>"],
        )

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
