# Standard Libraries
import logging
import os

# 3rd Party Libraries
import factory

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ArchiveFactory,
    BlankReportFindingLinkFactory,
    DocTypeFactory,
    EvidenceFactory,
    FindingFactory,
    FindingNoteFactory,
    FindingTypeFactory,
    LocalFindingNoteFactory,
    ReportDocxTemplateFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportPptxTemplateFactory,
    ReportTemplateFactory,
    SeverityFactory,
)

logging.disable(logging.CRITICAL)


class FindingModelTests(TestCase):
    """Collection of tests for :model:`reporting.Finding`."""

    @classmethod
    def setUpTestData(cls):
        cls.Finding = FindingFactory._meta.model

    def test_crud_finding(self):
        # Create
        finding = FindingFactory(title="Awful Finding")

        # Read
        self.assertEqual(finding.title, "Awful Finding")
        self.assertEqual(finding.pk, finding.id)

        # Update
        finding.title = "Not so Bad Finding"
        finding.save()

        # Delete
        finding.delete()
        assert not self.Finding.objects.all().exists()

    def test_get_absolute_url(self):
        finding = FindingFactory()
        try:
            finding.get_absolute_url()
        except:
            self.fail("Finding.get_absolute_url() raised an exception")


class SeverityModelTests(TestCase):
    """Collection of tests for :model:`reporting.Severity`."""

    @classmethod
    def setUpTestData(cls):
        cls.Severity = SeverityFactory._meta.model

    def test_crud_severity(self):
        # Create
        severity = SeverityFactory(severity="High", weight=1, color="FFFFFF")

        # Read
        self.assertEqual(severity.severity, "High")
        self.assertEqual(severity.pk, severity.id)
        self.assertEqual(severity.color, "FFFFFF")
        self.assertEqual(severity.weight, 1)
        self.assertEqual(len(self.Severity.objects.all()), 1)
        self.assertEqual(self.Severity.objects.first(), severity)

        # Update
        severity.severity = "Critical"
        severity.weight = 1
        severity.color = "000000"
        severity.save()
        self.assertEqual(severity.severity, "Critical")
        self.assertEqual(severity.color, "000000")
        self.assertEqual(severity.weight, 1)

        # Delete
        severity.delete()
        assert not self.Severity.objects.all().exists()

    def test_prop_color_rgb(self):
        severity = SeverityFactory(severity="High", weight=2, color="FFFFFF")
        try:
            severity.color_rgb
        except Exception:
            self.fail("Severity model `color_rgb` property failed unexpectedly!")

    def test_prop_color_hex(self):
        severity = SeverityFactory(severity="High", weight=2, color="FFFFFF")
        try:
            severity.color_hex
        except Exception:
            self.fail("Severity model `color_hex` property failed unexpectedly!")

    def test_prop_count(self):
        severity = SeverityFactory(severity="High", weight=2, color="FFFFFF")
        FindingFactory(severity=severity)
        try:
            count = severity.count
            self.assertEqual(1, count)
        except Exception:
            self.fail("Severity model `count` property failed unexpectedly!")

    def test_adjust_severity_weight_signals(self):
        self.Severity.objects.all().delete()
        self.assertTrue(self.Severity.objects.all().count() == 0)

        critical = SeverityFactory(severity="Critical", weight=2, color="FFFFFF")
        high = SeverityFactory(severity="High", weight=2, color="FFF000")
        medium = SeverityFactory(severity="Medium", weight=3, color="000FFF")

        self.assertEqual(critical.severity, "Critical")
        self.assertEqual(critical.color, "FFFFFF")
        self.assertEqual(critical.weight, 1)
        self.assertEqual(high.severity, "High")
        self.assertEqual(high.color, "FFF000")
        self.assertEqual(high.weight, 2)
        self.assertEqual(medium.severity, "Medium")
        self.assertEqual(medium.color, "000FFF")
        self.assertEqual(medium.weight, 3)

        low = SeverityFactory(severity="Low", weight=50, color="000FFF")
        self.assertEqual(low.weight, 4)

        info = SeverityFactory(severity="Info", weight=-1, color="000FFF")
        self.assertEqual(info.weight, 5)

        critical.weight = 2
        critical.save()

        critical.refresh_from_db()
        high.refresh_from_db()

        self.assertEqual(critical.weight, 2)
        self.assertEqual(high.weight, 1)

        critical.delete()
        high.refresh_from_db()
        medium.refresh_from_db()

        self.assertEqual(high.weight, 1)
        self.assertEqual(medium.weight, 2)


class FindingTypeModelTests(TestCase):
    """Collection of tests for :model:`reporting.FindingType`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingType = FindingTypeFactory._meta.model

    def test_crud_finding_type(self):
        # Create
        finding_type = FindingTypeFactory(finding_type="Network")

        # Read
        self.assertEqual(finding_type.finding_type, "Network")
        self.assertEqual(finding_type.pk, finding_type.id)
        self.assertEqual(len(self.FindingType.objects.all()), 1)
        self.assertEqual(self.FindingType.objects.first(), finding_type)

        # Update
        finding_type.finding_type = "Web"
        finding_type.save()
        self.assertEqual(finding_type.finding_type, "Web")

        # Delete
        finding_type.delete()
        assert not self.FindingType.objects.all().exists()

    def test_prop_count(self):
        finding_type = FindingTypeFactory(finding_type="Network")
        FindingFactory(finding_type=finding_type)
        try:
            count = finding_type.count
            self.assertEqual(1, count)
        except Exception:
            self.fail("FindingType model `count` property failed unexpectedly!")


class DocTypeModelTests(TestCase):
    """Collection of tests for :model:`reporting.DocType`."""

    @classmethod
    def setUpTestData(cls):
        cls.DocType = DocTypeFactory._meta.model

    def test_crud_doc_type(self):
        # Create
        doc_type = DocTypeFactory(doc_type="docx")

        # Read
        self.assertEqual(doc_type.doc_type, "docx")
        self.assertEqual(doc_type.pk, doc_type.id)
        self.assertEqual(len(self.DocType.objects.all()), 1)
        self.assertEqual(self.DocType.objects.first(), doc_type)

        # Update
        doc_type.doc_type = "pptx"
        doc_type.save()
        self.assertEqual(doc_type.doc_type, "pptx")

        # Delete
        doc_type.delete()
        assert not self.DocType.objects.all().exists()


class ReportTemplateModelTests(TestCase):
    """Collection of tests for :model:`reporting.ReportTemplate`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportTemplate = ReportTemplateFactory._meta.model

    def test_crud_report_template(self):
        # Create
        report_template = ReportTemplateFactory(name="Test Template")

        # Read
        self.assertEqual(report_template.name, "Test Template")
        self.assertEqual(report_template.pk, report_template.id)
        self.assertEqual(len(self.ReportTemplate.objects.all()), 1)
        self.assertEqual(self.ReportTemplate.objects.first(), report_template)
        assert os.path.exists(report_template.document.path)

        # Update
        report_template.name = "New Template"
        report_template.save()
        self.assertEqual(report_template.name, "New Template")
        assert os.path.exists(report_template.document.path)

        # Delete
        report_template.delete()
        assert not self.ReportTemplate.objects.all().exists()
        assert not os.path.exists(report_template.document.path)

    def test_get_absolute_url(self):
        template = ReportTemplateFactory()
        try:
            template.get_absolute_url()
        except:
            self.fail("ReportTemplate.get_absolute_url() raised an exception")

    def test_prop_filename(self):
        report_template = ReportTemplateFactory()
        try:
            report_template.filename
        except Exception:
            self.fail("ReportTemplate model `filename` property failed unexpectedly!")

    def test_method_get_status(self):
        docx_report_template = ReportDocxTemplateFactory()
        pptx_report_template = ReportPptxTemplateFactory()
        try:
            status = docx_report_template.get_status()
            self.assertEqual("success", status)
        except Exception:
            self.fail("ReportTemplate model `get_status` method failed unexpectedly with DOCX template!")
        try:
            status = pptx_report_template.get_status()
            self.assertEqual("success", status)
        except Exception:
            self.fail("ReportTemplate model `get_status` method failed unexpectedly with PPTX template!")

    def test_clean_template_signal(self):
        template = ReportDocxTemplateFactory()
        new_template = ReportPptxTemplateFactory()
        template.document = new_template.document
        template.doc_type = new_template.doc_type

        template.save()

        self.assertTrue(template._current_template.path not in template.document.path)
        self.assertFalse(os.path.exists(template._current_template.path))
        self.assertTrue(os.path.exists(template.document.path))

    def test_delete_template_signal(self):
        template = ReportTemplateFactory()
        self.assertTrue(os.path.exists(template.document.path))
        template.delete()
        self.assertFalse(os.path.exists(template.document.path))


class ReportModelTests(TestCase):
    """Collection of tests for :model:`reporting.Report`."""

    @classmethod
    def setUpTestData(cls):
        cls.Report = ReportFactory._meta.model

    def test_crud_report(self):
        # Create
        report = ReportFactory(title="New Report")

        # Read
        self.assertEqual(report.title, "New Report")
        self.assertEqual(report.pk, report.id)
        self.assertEqual(len(self.Report.objects.all()), 1)
        self.assertEqual(self.Report.objects.first(), report)

        # Update
        report.title = "Updated Report"
        report.save()
        self.assertEqual(report.title, "Updated Report")

        # Delete
        report.delete()
        assert not self.Report.objects.all().exists()

    def test_get_absolute_url(self):
        report = ReportFactory()
        try:
            report.get_absolute_url()
        except:
            self.fail("Report.get_absolute_url() raised an exception")


class ReportFindingLinkModelTests(TestCase):
    """Collection of tests for :model:`reporting.ReportFindingLink`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.critical_severity = SeverityFactory(severity="Critical", weight=0)
        cls.high_severity = SeverityFactory(severity="High", weight=1)

    def tearDown(self):
        # Need to use atomic because ``TestCase`` and a ``post_delete`` Signal`
        with transaction.atomic():
            self.ReportFindingLink.objects.all().delete()

    def test_crud_report_finding(self):
        # Create
        finding = ReportFindingLinkFactory(title="Attached Finding")

        # Read
        self.assertEqual(finding.title, "Attached Finding")
        self.assertEqual(finding.pk, finding.id)
        self.assertEqual(len(self.ReportFindingLink.objects.all()), 1)
        self.assertEqual(self.ReportFindingLink.objects.first(), finding)

        # Update
        finding.title = "Updated Finding"
        finding.save()
        self.assertEqual(finding.title, "Updated Finding")

        # Delete
        finding.delete()
        assert not self.ReportFindingLink.objects.all().exists()


class EvidenceModelTests(TestCase):
    """Collection of tests for :model:`reporting.Evidence`."""

    @classmethod
    def setUpTestData(cls):
        cls.Evidence = EvidenceFactory._meta.model

    def test_crud_evidence(self):
        # Create
        evidence = EvidenceFactory(friendly_name="Test Evidence")

        # Read
        self.assertEqual(evidence.friendly_name, "Test Evidence")
        self.assertEqual(evidence.pk, evidence.id)
        self.assertEqual(len(self.Evidence.objects.all()), 1)
        self.assertEqual(self.Evidence.objects.first(), evidence)
        assert os.path.exists(evidence.document.path)

        # Update
        evidence.friendly_name = "New Name"
        evidence.save()
        self.assertEqual(evidence.friendly_name, "New Name")
        assert os.path.exists(evidence.document.path)

        # Delete
        evidence.delete()
        assert not self.Evidence.objects.all().exists()
        assert not os.path.exists(evidence.document.path)

    def test_get_absolute_url(self):
        evidence = EvidenceFactory()
        try:
            evidence.get_absolute_url()
        except:
            self.fail("Evidence.get_absolute_url() raised an exception")

    def test_file_extension_validator(self):
        evidence = EvidenceFactory(document=factory.django.FileField(filename="evidence.PnG", data=b"lorem ipsum"))
        self.assertEqual(evidence.filename, "evidence.PnG")

    def test_prop_filename(self):
        evidence = EvidenceFactory()
        try:
            evidence.filename
        except Exception:
            self.fail("Evidence model `filename` property failed unexpectedly!")

    def test_evidence_update_signal(self):
        finding = ReportFindingLinkFactory(
            description="<p>Here is some evidence:</p><p>{{.Evidence}}</p><p>{{.ref Evidence}}</p>"
        )
        evidence = EvidenceFactory(
            finding=finding,
            friendly_name="Evidence",
            document=factory.django.FileField(filename="evidence.txt", data=b"lorem ipsum"),
        )

        self.assertEqual(f"evidence/{finding.report.id}/evidence.txt", evidence.document.name)

        evidence.document = SimpleUploadedFile("new_evidence.txt", b"lorem ipsum")
        evidence.save()
        evidence.refresh_from_db()

        self.assertTrue(hasattr(evidence, "_current_evidence"))
        self.assertTrue(evidence._current_evidence.path not in evidence.document.path)
        self.assertFalse(os.path.exists(evidence._current_evidence.path))
        self.assertTrue(os.path.exists(evidence.document.path))

        evidence.friendly_name = "New Name"
        evidence.save()
        evidence.refresh_from_db()
        finding.refresh_from_db()

        self.assertTrue(hasattr(evidence, "_current_friendly_name"))
        self.assertEqual(evidence._current_friendly_name, "Evidence")
        self.assertEqual(evidence.friendly_name, "New Name")
        self.assertEqual(
            finding.description, "<p>Here is some evidence:</p><p>{{.New Name}}</p><p>{{.ref New Name}}</p>"
        )

        # Regression test for this signal updating a finding with blank fields
        blank = BlankReportFindingLinkFactory()
        evidence = EvidenceFactory(finding=blank, friendly_name="Blank Test")
        evidence.refresh_from_db()

        evidence.friendly_name = "New Name"
        evidence.save()
        evidence.refresh_from_db()


class FindingNoteModelTests(TestCase):
    """Collection of tests for :model:`reporting.FindingNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingNote = FindingNoteFactory._meta.model

    def test_crud_finding_note(self):
        # Create
        note = FindingNoteFactory(note="Test note")

        # Read
        self.assertEqual(note.note, "Test note")
        self.assertEqual(note.pk, note.id)
        self.assertEqual(len(self.FindingNote.objects.all()), 1)
        self.assertEqual(self.FindingNote.objects.first(), note)

        # Update
        note.note = "Updated note"
        note.save()
        self.assertEqual(note.note, "Updated note")

        # Delete
        note.delete()
        assert not self.FindingNote.objects.all().exists()


class LocalFindingNoteModelTests(TestCase):
    """Collection of tests for :model:`reporting.LocalFindingNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.LocalFindingNote = LocalFindingNoteFactory._meta.model

    def test_crud_local_finding_note(self):
        # Create
        note = LocalFindingNoteFactory(note="Test note")

        # Read
        self.assertEqual(note.note, "Test note")
        self.assertEqual(note.pk, note.id)
        self.assertEqual(len(self.LocalFindingNote.objects.all()), 1)
        self.assertEqual(self.LocalFindingNote.objects.first(), note)

        # Update
        note.note = "Updated note"
        note.save()
        self.assertEqual(note.note, "Updated note")

        # Delete
        note.delete()
        assert not self.LocalFindingNote.objects.all().exists()


class ArchiveModelTests(TestCase):
    """Collection of tests for :model:`reporting.Archive`."""

    @classmethod
    def setUpTestData(cls):
        cls.Archive = ArchiveFactory._meta.model

    def test_crud_archive(self):
        # Create
        archive = ArchiveFactory(report_archive="test.zip")

        # Read
        self.assertEqual(archive.report_archive.name, "test.zip")
        self.assertEqual(archive.pk, archive.id)
        self.assertEqual(len(self.Archive.objects.all()), 1)
        self.assertEqual(self.Archive.objects.first(), archive)

        # Update
        archive.report_archive.name = "updated.zip"
        archive.save()
        self.assertEqual(archive.report_archive.name, "updated.zip")

        # Delete
        archive.delete()
        assert not self.Archive.objects.all().exists()

    def test_prop_filename(self):
        archive = ArchiveFactory()
        try:
            archive.filename
        except Exception:
            self.fail("Archive model `filename` property failed unexpectedly!")
