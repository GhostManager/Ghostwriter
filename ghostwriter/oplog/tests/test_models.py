# Standard Libraries
import logging
from datetime import datetime, timezone

# Django Imports
from django.db import IntegrityError
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    EvidenceOnReportFactory,
    OplogEntryEvidenceFactory,
    OplogEntryFactory,
    OplogFactory,
)
from ghostwriter.oplog.models import OplogEntryEvidence

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
        valid_start_date = datetime.now(timezone.utc)
        valid_end_date = datetime.now(timezone.utc)
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


class OplogEntryEvidenceModelTests(TestCase):
    """Collection of tests for :model:`oplog.OplogEntryEvidence`."""

    @classmethod
    def setUpTestData(cls):
        cls.OplogEntryEvidence = OplogEntryEvidenceFactory._meta.model

    def test_crud(self):
        # Create
        link = OplogEntryEvidenceFactory()
        self.assertIsNotNone(link.pk)

        # Read
        self.assertIsNotNone(link.oplog_entry)
        self.assertIsNotNone(link.evidence)

        # Delete
        link.delete()
        assert not self.OplogEntryEvidence.objects.all().exists()

    def test_unique_together(self):
        link = OplogEntryEvidenceFactory()
        with self.assertRaises(IntegrityError):
            OplogEntryEvidenceFactory(
                oplog_entry=link.oplog_entry,
                evidence=link.evidence,
            )

    def test_cascade_delete_entry(self):
        link = OplogEntryEvidenceFactory()
        entry = link.oplog_entry
        entry.delete()
        assert not self.OplogEntryEvidence.objects.filter(pk=link.pk).exists()

    def test_cascade_delete_evidence(self):
        link = OplogEntryEvidenceFactory()
        evidence = link.evidence
        evidence.delete()
        assert not self.OplogEntryEvidence.objects.filter(pk=link.pk).exists()

    def test_str(self):
        link = OplogEntryEvidenceFactory()
        self.assertIn(str(link.oplog_entry), str(link))

    def test_evidence_tag_added_on_link_create(self):
        """Creating an OplogEntryEvidence link adds 'evidence' tag to the OplogEntry."""
        link = OplogEntryEvidenceFactory()
        self.assertIn("evidence", list(link.oplog_entry.tags.names()))

    def test_evidence_tag_removed_when_last_link_deleted(self):
        """Deleting the last evidence link removes the 'evidence' tag from the OplogEntry."""
        link = OplogEntryEvidenceFactory()
        entry = link.oplog_entry
        link.delete()
        self.assertNotIn("evidence", list(entry.tags.names()))

    def test_evidence_tag_retained_when_other_links_remain(self):
        """Deleting one evidence link keeps the 'evidence' tag when other links remain."""
        link1 = OplogEntryEvidenceFactory()
        entry = link1.oplog_entry
        evidence2 = EvidenceOnReportFactory()
        link2 = OplogEntryEvidence.objects.create(oplog_entry=entry, evidence=evidence2)
        # Now delete only one link; the tag should remain because link2 still exists
        link1.delete()
        self.assertIn("evidence", list(entry.tags.names()))

    def test_evidence_tag_removed_on_cascade_evidence_delete(self):
        """Deleting an Evidence record cascade-removes the tag when it was the last link."""
        link = OplogEntryEvidenceFactory()
        entry = link.oplog_entry
        link.evidence.delete()
        self.assertNotIn("evidence", list(entry.tags.names()))
