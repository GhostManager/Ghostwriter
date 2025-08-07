# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    EvidenceOnFindingFactory,
    EvidenceOnReportFactory,
    FindingFactory,
    FindingNoteFactory,
    LocalFindingNoteFactory,
    ObservationFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportObservationLinkFactory,
    ReportTemplateFactory,
    SeverityFactory,
    UserFactory,
)
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.reporting.forms import (
    EvidenceForm,
    FindingNoteForm,
    LocalFindingNoteForm,
    ReportForm,
    ReportObservationLinkUpdateForm,
    ReportTemplateForm,
    SelectReportTemplateForm,
    SeverityForm,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class ReportFormTests(TestCase):
    """Collection of tests for :form:`reporting.ReportForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.report_dict = cls.report.__dict__
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        title=None,
        complete=None,
        archived=None,
        project_id=None,
        docx_template_id=None,
        pptx_template_id=None,
        created_by_id=None,
        delivered=None,
        **kwargs,
    ):
        return ReportForm(
            user=user,
            data={
                "title": title,
                "complete": complete,
                "archived": archived,
                "project": project_id,
                "docx_template": docx_template_id,
                "pptx_template": pptx_template_id,
                "created_by": created_by_id,
                "delivered": delivered,
            },
        )

    def test_valid_data(self):
        report = self.report_dict.copy()
        form = self.form_data(user=self.user, **report)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors.as_data()["project"][0].code == "invalid_choice")

        ProjectAssignmentFactory(operator=self.user, project=self.project)
        form = self.form_data(user=self.user, **report)
        self.assertTrue(form.is_valid())

    def test_invalid_docx_template(self):
        report = self.report_dict.copy()
        report["docx_template_id"] = report["pptx_template_id"]

        form = self.form_data(user=self.user, **report)
        errors = form["docx_template"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_choice")

    def test_invalid_pptx_template(self):
        report = self.report_dict.copy()
        report["pptx_template_id"] = report["docx_template_id"]

        form = self.form_data(user=self.user, **report)
        errors = form["pptx_template"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_choice")


class ReportObservationLinkUpdateFormTests(TestCase):
    """Collection of tests for :form:`reporting.ReportObservationLinkForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.observation = ReportObservationLinkFactory()
        cls.blank_observation = ReportObservationLinkFactory(added_as_blank=True)

    def test_valid_data(self):
        data = self.observation.__dict__.copy()
        data["instance"] = self.observation
        form = ReportObservationLinkUpdateForm(data=data)
        self.assertTrue(form.is_valid())

    def test_blank_assigned_to(self):
        self.observation.assigned_to = None

        data = self.observation.__dict__.copy()
        data["instance"] = self.observation
        form = ReportObservationLinkUpdateForm(data)
        self.assertTrue(form.is_valid())

    def test_added_as_blank_field(self):
        data = self.observation.__dict__.copy()
        data["instance"] = self.blank_observation
        form = ReportObservationLinkUpdateForm(data=data)
        self.assertTrue(form.is_valid())
        form.save()
        self.assertTrue(self.blank_observation.added_as_blank)


class BaseEvidenceFormTests:
    """Collection of tests for :form:`reporting.EvidenceForm`."""

    @classmethod
    def factory(cls):
        raise NotImplementedError()

    @classmethod
    def querySet(cls):
        raise NotImplementedError()

    @classmethod
    def setUpTestData(cls):
        cls.Factory = cls.factory()
        cls.Evidence = cls.Factory._meta.model
        cls.evidence = cls.Factory()
        cls.evidence_dict = cls.evidence.__dict__
        cls.evidence_queryset = cls.querySet(cls.evidence)

        cls.other_finding = ReportFindingLinkFactory()
        cls.other_finding.report = cls.evidence.associated_report
        cls.other_finding.save()

        cls.other_finding_evidence = EvidenceOnFindingFactory()
        cls.other_finding_evidence.friendly_name = "EvidenceOnFinding"
        cls.other_finding_evidence.finding = cls.other_finding
        cls.other_finding_evidence.save()

        cls.other_report_finding = EvidenceOnReportFactory()
        cls.other_report_finding.friendly_name = "EvidenceOnReport"
        cls.other_report_finding.report = cls.evidence.associated_report
        cls.other_report_finding.save()

    def setUp(self):
        pass

    def form_data(
        self,
        document=None,
        friendly_name=None,
        caption=None,
        description=None,
        evidence_queryset=None,
        modal=False,
        **kwargs,
    ):
        if not evidence_queryset:
            evidence_queryset = self.evidence_queryset

        return EvidenceForm(
            data={
                "friendly_name": friendly_name,
                "caption": caption,
                "description": description,
            },
            files={
                "document": document,
            },
            evidence_queryset=evidence_queryset,
            is_modal=modal,
        )

    def test_valid_data(self):
        evidence = self.evidence_dict.copy()
        evidence["friendly_name"] = "Valid Data"

        form = self.form_data(**evidence)
        self.assertTrue(form.is_valid())

    def test_blank_evidence(self):
        evidence = self.evidence_dict.copy()
        evidence["document"] = None
        evidence["friendly_name"] = "Blank Evidence"

        form = self.form_data(**evidence)
        errors = form["document"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_duplicate_friendly_name(self):
        new_evidence = self.evidence_dict.copy()
        new_evidence["friendly_name"] = self.evidence.friendly_name

        form = self.form_data(**new_evidence)
        errors = form["friendly_name"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_duplicate_friendly_name_on_diff_finding(self):
        new_evidence = self.evidence_dict.copy()
        new_evidence["friendly_name"] = "EvidenceOnFinding"

        form = self.form_data(**new_evidence)
        errors = form["friendly_name"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_duplicate_friendly_name_on_report(self):
        new_evidence = self.evidence_dict.copy()
        new_evidence["friendly_name"] = "EvidenceOnReport"

        form = self.form_data(**new_evidence)
        errors = form["friendly_name"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_modal_argument(self):
        modal_evidence = self.evidence_dict.copy()
        modal_evidence["friendly_name"] = "Modal Evidence"

        form = self.form_data(**modal_evidence, is_modal=True)
        self.assertTrue(form.is_valid())

    def test_null_evidence_queryset_argument(self):
        evidence = self.evidence_dict.copy()
        evidence["friendly_name"] = "Blank Queryset"

        form = self.form_data(**evidence, evidence_queryset=None)
        self.assertTrue(form.is_valid())


class EvidenceFormForFindingTests(BaseEvidenceFormTests, TestCase):
    @classmethod
    def factory(cls):
        return EvidenceOnFindingFactory

    @classmethod
    def querySet(cls, evidence):
        return evidence.finding.report.all_evidences()


class EvidenceFormForReportTests(BaseEvidenceFormTests, TestCase):
    @classmethod
    def factory(cls):
        return EvidenceOnReportFactory

    @classmethod
    def querySet(cls, evidence):
        return evidence.report.all_evidences()


class FindingNoteFormTests(TestCase):
    """Collection of tests for :form:`reporting.FindingNoteForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.note = FindingNoteFactory()
        cls.note_dict = cls.note.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        note=None,
        **kwargs,
    ):
        return FindingNoteForm(
            data={
                "note": note,
            },
        )

    def test_valid_data(self):
        note = self.note_dict.copy()

        form = self.form_data(**note)
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        note = self.note_dict.copy()
        note["note"] = ""

        form = self.form_data(**note)
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")


class LocalFindingNoteFormTests(TestCase):
    """Collection of tests for :form:`reporting.LocalFindingNoteForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.note = LocalFindingNoteFactory()
        cls.note_dict = cls.note.__dict__

    def setUp(self):
        pass

    def form_data(
        self,
        note=None,
        **kwargs,
    ):
        return LocalFindingNoteForm(
            data={
                "note": note,
            },
        )

    def test_valid_data(self):
        note = self.note_dict.copy()

        form = self.form_data(**note)
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        note = self.note_dict.copy()
        note["note"] = ""

        form = self.form_data(**note)
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")


class ReportTemplateFormTests(TestCase):
    """Collection of tests for :form:`reporting.ReportTemplateForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.template_dict = cls.template.__dict__
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        pass

    def form_data(
        self,
        document=None,
        name=None,
        description=None,
        protected=False,
        lint_result=None,
        changelog=None,
        client_id=None,
        doc_type=None,
        p_type=None,
        evidence_image_width=None,
        user=None,
        **kwargs,
    ):
        return ReportTemplateForm(
            data={
                "name": name,
                "description": description,
                "protected": protected,
                "lint_result": lint_result,
                "changelog": changelog,
                "client": client_id,
                "doc_type": doc_type,
                "p_type": p_type,
                "evidence_image_width": evidence_image_width,
            },
            user=user,
            files={
                "document": document,
            },
        )

    def test_valid_data(self):
        template = self.template_dict.copy()

        form = self.form_data(**template, user=self.user)
        self.assertTrue(form.is_valid())

    def test_blank_template(self):
        template = self.template_dict.copy()
        template["document"] = None

        form = self.form_data(**template, user=self.user)
        errors = form["document"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")


class SelectReportTemplateFormTests(TestCase):
    """Collection of tests for :form:`reporting.SelectReportTemplateForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.docx_template = cls.report.docx_template
        cls.pptx_template = cls.report.pptx_template

    def setUp(self):
        pass

    def form_data(
        self,
        instance,
        docx_template=None,
        pptx_template=None,
        **kwargs,
    ):
        return SelectReportTemplateForm(
            instance=instance,
            data={
                "docx_template": docx_template,
                "pptx_template": pptx_template,
            },
        )

    def test_valid_data(self):
        form = self.form_data(
            instance=self.report,
            docx_template=self.docx_template,
            pptx_template=self.pptx_template,
        )
        self.assertTrue(form.is_valid())

    def test_blank_docx_template(self):
        form = self.form_data(instance=self.report, docx_template=None, pptx_template=self.pptx_template)
        errors = form["docx_template"].errors.as_data()
        self.assertEqual(len(errors), 0)

    def test_blank_pptx_template(self):
        form = self.form_data(instance=self.report, docx_template=self.docx_template, pptx_template=None)
        errors = form["pptx_template"].errors.as_data()
        self.assertEqual(len(errors), 0)

    def test_mismatch_docx_template(self):
        form = self.form_data(
            instance=self.report,
            docx_template=self.pptx_template,
            pptx_template=self.pptx_template,
        )
        errors = form["docx_template"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_choice")

    def test_mismatch_pptx_template(self):
        form = self.form_data(
            instance=self.report,
            docx_template=self.docx_template,
            pptx_template=self.docx_template,
        )
        errors = form["pptx_template"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_choice")


class SeverityFormTests(TestCase):
    """Collection of tests for :form:`reporting.SeverityForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.severity = SeverityFactory(severity="Critical", weight=1, color="966FD6")

    def setUp(self):
        pass

    def form_data(
        self,
        severity=None,
        weight=None,
        color=None,
        **kwargs,
    ):
        return SeverityForm(
            data={
                "severity": severity,
                "weight": weight,
                "color": color,
            },
        )

    def test_valid_data(self):
        severity = to_dict(self.severity).copy()
        severity["severity"] = "High"
        form = self.form_data(**severity)
        self.assertTrue(form.is_valid())

    def test_invalid_color(self):
        severity = to_dict(self.severity).copy()
        severity["severity"] = "Medium"
        severity["color"] = "#F4B083"
        form = self.form_data(**severity)
        errors = form["color"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "max_length")

        severity["color"] = "#F4B08"
        form = self.form_data(**severity)
        errors = form["color"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")
        self.assertEqual(
            errors[0].message,
            "Do not include the # symbol in the color field.",
        )

        severity["color"] = "F4B08G"
        form = self.form_data(**severity)
        errors = form["color"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")
        self.assertEqual(
            errors[0].message,
            "Please enter a valid hex color, three pairs of characters using A-F and 0-9 (e.g., 7A7A7A).",
        )

        severity["color"] = "FFFFF"
        form = self.form_data(**severity)
        errors = form["color"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")
        self.assertEqual(errors[0].message, "Your hex color code should be six characters in length.")
