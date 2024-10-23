# Standard Libraries
import logging
import os

# 3rd Party Libraries
import factory

# Django Imports
from django.db import transaction
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ArchiveFactory,
    ClientFactory,
    DocTypeFactory,
    EvidenceOnFindingFactory,
    FindingFactory,
    FindingNoteFactory,
    FindingTypeFactory,
    LocalFindingNoteFactory,
    ProjectFactory,
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
        doc_type = DocTypeFactory(doc_type="docx", extension="docx", name="docx")

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

    def test_clear_incorrect_template_defaults_unchanged(self):
        docx_template = ReportDocxTemplateFactory()
        pptx_template = ReportPptxTemplateFactory()
        report = ReportFactory(
            title="New report",
            docx_template=docx_template,
            pptx_template=pptx_template,
        )

        # Don't change anything. Clearing should do nothing.

        self.Report.clear_incorrect_template_defaults(docx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.id, report.id)
        self.assertIsNotNone(new_report.docx_template)
        self.assertEqual(new_report.docx_template.id, docx_template.id)
        self.assertIsNotNone(new_report.pptx_template)
        self.assertEqual(new_report.pptx_template.id, pptx_template.id)

        self.Report.clear_incorrect_template_defaults(pptx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.id, report.id)
        self.assertIsNotNone(new_report.docx_template)
        self.assertEqual(new_report.docx_template.id, docx_template.id)
        self.assertIsNotNone(new_report.pptx_template)
        self.assertEqual(new_report.pptx_template.id, pptx_template.id)

    def test_clear_incorrect_template_defaults_docx_to_pptx(self):
        docx_template = ReportDocxTemplateFactory()
        report = ReportFactory(
            title="New report",
            docx_template=docx_template,
        )

        docx_template.doc_type = DocTypeFactory(doc_type="pptx", extension="pptx", name="pptx")
        docx_template.save()

        self.Report.clear_incorrect_template_defaults(docx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.id, report.id)
        self.assertIsNone(new_report.docx_template)

    def test_clear_incorrect_template_defaults_pptx_to_docx(self):
        pptx_template = ReportPptxTemplateFactory()
        report = ReportFactory(
            title="New report",
            pptx_template=pptx_template,
        )

        pptx_template.doc_type = DocTypeFactory(doc_type="docx", extension="docx", name="docx")
        pptx_template.save()

        self.Report.clear_incorrect_template_defaults(pptx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.id, report.id)
        self.assertIsNone(new_report.pptx_template)

    def test_clear_incorrect_template_defaults_client_change_clear(self):
        client = ClientFactory()
        pptx_template = ReportDocxTemplateFactory()
        report = ReportFactory(
            title="New report",
            pptx_template=pptx_template,
        )

        pptx_template.client = client
        pptx_template.save()

        self.Report.clear_incorrect_template_defaults(pptx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.id, report.id)
        self.assertIsNone(new_report.pptx_template)

    def test_clear_incorrect_template_defaults_client_change_set_same(self):
        client = ClientFactory()
        project = ProjectFactory(client=client)
        pptx_template = ReportPptxTemplateFactory()
        report = ReportFactory(
            title="New report",
            pptx_template=pptx_template,
            project=project,
        )

        self.assertEqual(report.project.client, client)

        pptx_template.client = client
        pptx_template.save()

        self.Report.clear_incorrect_template_defaults(pptx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.project.client, client)
        self.assertIsNotNone(new_report.pptx_template)
        self.assertEqual(new_report.pptx_template.id, pptx_template.id)

    def test_clear_incorrect_template_defaults_client_change_set_different(self):
        client = ClientFactory()
        project = ProjectFactory(client=client)
        pptx_template = ReportPptxTemplateFactory()
        report = ReportFactory(
            title="New report",
            pptx_template=pptx_template,
            project=project,
        )

        self.assertEqual(report.project.client, client)

        pptx_template.client = ClientFactory()
        pptx_template.save()

        self.Report.clear_incorrect_template_defaults(pptx_template)
        new_report = self.Report.objects.first()
        self.assertEqual(new_report.project.client, client)
        self.assertIsNone(new_report.pptx_template)


class ReportFindingLinkModelTests(TestCase):
    """Collection of tests for :model:`reporting.ReportFindingLink`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.critical_severity = SeverityFactory(severity="Critical", weight=0, color="966FD6")
        cls.high_severity = SeverityFactory(severity="High", weight=1, color="FF7E79")
        cls.medium_severity = SeverityFactory(severity="Medium", weight=2, color="F4B083")

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

    def test_cvss_scores_property(self):
        # CVSS v3.1 – 8.0 High, 7.6 High, 5.4 Medium
        three_vector = (
            "CVSS:3.1/AV:N/AC:H/PR:H/UI:N/S:C/C:H/I:H/A:H/E:P/RL:U/RC:C/CR:L/IR:L/AR:L/MAV:P/MAC:L/MPR:L/MUI:N/MS:C"
        )
        # CVSS v4.1 – 9.1 Critical
        four_vector = "CVSS:4.0/AV:N/AC:L/AT:N/PR:L/UI:N/VC:H/VI:H/VA:H/SC:L/SI:H/SA:L/E:A/CR:H/IR:H/AR:L/MAV:N/MAC:H/MAT:N/MPR:N/MUI:N/MVI:L/MVA:H/MSC:H/MSI:H/MSA:N/R:I/V:C/RE:M/U:Red"

        critical_finding = ReportFindingLinkFactory(severity=self.critical_severity, cvss_vector=four_vector)
        medium_finding = ReportFindingLinkFactory(severity=self.medium_severity, cvss_vector=three_vector)
        unknown_finding = ReportFindingLinkFactory(severity=self.high_severity, cvss_vector="Not a Vector")

        critical_data = ("4.0", 9.1, "Critical", "966FD6")
        medium_data = ("3.1", (8.0, 7.6, 5.4), ("High", "High", "Medium"), ["FF7E79", "FF7E79", "F4B083"])
        unknown_data = ("Unknown", "", "", "")

        self.assertEqual(critical_finding.cvss_data, critical_data)
        self.assertEqual(medium_finding.cvss_data, medium_data)
        self.assertEqual(unknown_finding.cvss_data, unknown_data)


class EvidenceModelTests(TestCase):
    """Collection of tests for :model:`reporting.Evidence`."""

    @classmethod
    def setUpTestData(cls):
        cls.Evidence = EvidenceOnFindingFactory._meta.model

    def test_crud_evidence(self):
        # Create
        evidence = EvidenceOnFindingFactory(friendly_name="Test Evidence")

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

    def test_get_absolute_url(self):
        evidence = EvidenceOnFindingFactory()
        try:
            evidence.get_absolute_url()
        except:
            self.fail("Evidence.get_absolute_url() raised an exception")
        evidence.delete()

    def test_file_extension_validator(self):
        evidence = EvidenceOnFindingFactory(
            document=factory.django.FileField(filename="ext_test.PnG", data=b"lorem ipsum")
        )
        self.assertEqual(evidence.filename, "ext_test.PnG")
        evidence.delete()

    def test_prop_filename(self):
        evidence = EvidenceOnFindingFactory()
        try:
            evidence.filename
        except Exception:
            self.fail("Evidence model `filename` property failed unexpectedly!")

    def test_long_filename(self):
        name = (
            "In-mi-nisi-dignissim-nec-eleifend-sed-porta-eu-lacus-Sed-nunc-nisl-tristique-at-enim-bibendum-rutrum-sodales-ligula-Aliquam-quis-pharetra-sem-Morbi-nec-vestibulum-nunc-Nullam-urna-tortor-venenatis-et-nisi-ac-"
            + "fringilla-sodales-sed.txt"
        )
        evidence = EvidenceOnFindingFactory(document=factory.django.FileField(filename=name, data=b"lorem ipsum"))
        self.assertEqual(evidence.filename, name)
        try:
            evidence.get_absolute_url()
        except:
            self.fail("Evidence.get_absolute_url() raised an exception")
        evidence.delete()


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
