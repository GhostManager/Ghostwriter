# Standard Libraries
import logging

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    EvidenceOnReportFactory,
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ReportFactory,
    UserFactory,
)
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.oplog.forms import OplogEntryForm, OplogEvidenceForm, OplogForm

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class OplogFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        pass

    def form_data(
        self,
        user=None,
        name=None,
        project_id=None,
        **kwargs,
    ):
        return OplogForm(
            user=user,
            data={
                "name": name,
                "project": project_id,
            },
        )

    def test_valid_data(self):
        project = ProjectFactory()
        oplog = OplogFactory.build(project=project)
        form = self.form_data(user=self.user, **oplog.__dict__)
        self.assertFalse(form.is_valid())
        self.assertTrue(form.errors.as_data()["project"][0].code == "invalid_choice")

        ProjectAssignmentFactory(operator=self.user, project=project)
        form = self.form_data(user=self.user, **oplog.__dict__)
        self.assertTrue(form.is_valid())


class OplogEntryFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogEntryForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.oplog = OplogFactory()

    def setUp(self):
        pass

    def form_data(
        self,
        oplog_id=None,
        start_date=None,
        end_date=None,
        source_ip=None,
        dest_ip=None,
        tool=None,
        user_context=None,
        command=None,
        description=None,
        output=None,
        comments=None,
        operator_name=None,
        oplog_kwarg=None,
        instance=None,
        **kwargs,
    ):
        return OplogEntryForm(
            data={
                "oplog_id": oplog_id,
                "start_date": start_date,
                "end_date": end_date,
                "source_ip": source_ip,
                "dest_ip": dest_ip,
                "tool": tool,
                "user_context": user_context,
                "command": command,
                "description": description,
                "output": output,
                "comments": comments,
                "operator_name": operator_name,
            },
            oplog=oplog_kwarg,
            instance=instance,
        )

    def test_valid_data(self):
        entry = OplogEntryFactory.build()
        form = self.form_data(**to_dict(entry), oplog_kwarg=self.oplog)
        self.assertTrue(form.is_valid())

    def test_valid_update_data(self):
        entry = OplogEntryFactory.create()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())

    def test_invalid_data(self):
        entry = OplogEntryFactory.create()
        start_date = entry.start_date
        entry.start_date = None
        entry.end_date = None
        entry.save()
        entry.refresh_from_db()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())

        entry.start_date = start_date
        entry.save()
        entry.refresh_from_db()
        form = self.form_data(**to_dict(entry), instance=entry)
        self.assertTrue(form.is_valid())


class OplogEvidenceFormTests(TestCase):
    """Collection of tests for :form:`oplog.OplogEvidenceForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)

    def test_report_queryset_filtered_to_project(self):
        other_project = ProjectFactory()
        other_report = ReportFactory(project=other_project)
        form = OplogEvidenceForm(project=self.project)
        qs = form.fields["report"].queryset
        self.assertIn(self.report, qs)
        self.assertNotIn(other_report, qs)

    def test_report_auto_selected_first_when_no_active(self):
        form = OplogEvidenceForm(project=self.project)
        self.assertEqual(form.fields["report"].initial, self.report)

    def test_report_auto_selected_first_when_multiple_no_active(self):
        second_report = ReportFactory(project=self.project)
        form = OplogEvidenceForm(project=self.project)
        first_in_list = form.fields["report"].queryset.first()
        self.assertEqual(form.fields["report"].initial, first_in_list)

    def test_active_report_selected_when_valid_for_project(self):
        form = OplogEvidenceForm(project=self.project, active_report_id=self.report.pk)
        self.assertEqual(form.fields["report"].initial, self.report)

    def test_active_report_ignored_when_not_in_project(self):
        other_report = ReportFactory()  # different project
        form = OplogEvidenceForm(project=self.project, active_report_id=other_report.pk)
        # Falls back to first report in the project
        first_in_list = form.fields["report"].queryset.first()
        self.assertEqual(form.fields["report"].initial, first_in_list)

    def test_active_report_invalid_id_falls_back_to_first(self):
        form = OplogEvidenceForm(project=self.project, active_report_id=999999)
        first_in_list = form.fields["report"].queryset.first()
        self.assertEqual(form.fields["report"].initial, first_in_list)

    def test_report_required(self):
        form = OplogEvidenceForm(project=self.project, data={
            "friendly_name": "Test Evidence",
        })
        self.assertFalse(form.is_valid())
        self.assertIn("report", form.errors)

    def test_clean_rejects_duplicate_friendly_name(self):
        """Submitting evidence with a friendly name already used in the same report triggers a ValidationError."""
        EvidenceOnReportFactory(friendly_name="Duplicate Evidence", report=self.report)
        file = SimpleUploadedFile("evidence.png", b"img data", content_type="image/png")
        form = OplogEvidenceForm(
            project=self.project,
            data={"friendly_name": "Duplicate Evidence", "report": self.report.pk, "caption": "Test"},
            files={"document": file},
        )
        self.assertFalse(form.is_valid())
        self.assertIn("__all__", form.errors)
        self.assertIn("friendly name already exists", form.errors["__all__"][0])

    def test_clean_allows_same_friendly_name_different_report(self):
        """Same friendly name on a different report is allowed."""
        other_report = ReportFactory(project=self.project)
        EvidenceOnReportFactory(friendly_name="Shared Name", report=self.report)
        file = SimpleUploadedFile("evidence.png", b"img data", content_type="image/png")
        form = OplogEvidenceForm(
            project=self.project,
            data={"friendly_name": "Shared Name", "report": other_report.pk, "caption": "Test"},
            files={"document": file},
        )
        self.assertTrue(form.is_valid())

    def test_clean_allows_update_existing_instance(self):
        """Updating an existing evidence instance does not falsely trigger the duplicate check."""
        evidence = EvidenceOnReportFactory(friendly_name="Existing Evidence", report=self.report)
        file = SimpleUploadedFile("evidence.png", b"img data", content_type="image/png")
        form = OplogEvidenceForm(
            project=self.project,
            data={"friendly_name": "Existing Evidence", "report": self.report.pk, "caption": "Updated"},
            files={"document": file},
            instance=evidence,
        )
        self.assertTrue(form.is_valid())
