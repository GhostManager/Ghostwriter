# Standard Libraries
import logging
from datetime import datetime, timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.api.forms import ApiEvidenceForm, ApiKeyForm
from ghostwriter.api.utils import get_reports_list
from ghostwriter.factories import (
    ProjectAssignmentFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    UserFactory,
    EvidenceOnReportFactory,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class ApiKeyFormTests(TestCase):
    """Collection of tests for :form:`api.ApiKeyForm`."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def form_data(
        self,
        name=None,
        expiry_date=None,
        **kwargs,
    ):
        return ApiKeyForm(
            data={
                "name": name,
                "expiry_date": expiry_date,
            },
        )

    def test_valid_data(self):
        form = self.form_data(name="Test Entry", expiry_date=datetime.now() + timedelta(days=1))
        self.assertTrue(form.is_valid())

    def test_empty_name(self):
        form = self.form_data(expiry_date=datetime.now())
        errors = form["name"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_empty_date(self):
        form = self.form_data(name="No Date")
        errors = form["expiry_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_expiry_date_in_past(self):
        form = self.form_data(name="Test Entry", expiry_date=datetime.now())
        errors = form["expiry_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_expiry_date")


class ApiEvidenceFormTests(TestCase):
    """Collection of tests for :form:`api.ApiEvidenceForm`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.other_report = ReportFactory()
        cls.finding = ReportFindingLinkFactory()
        cls.user = UserFactory(password=PASSWORD)
        ProjectAssignmentFactory(operator=cls.user, project=cls.report.project)

    def setUp(self):
        pass

    def form_data(
        self,
        friendly_name=None,
        description=None,
        caption=None,
        tags=None,
        finding=None,
        report=None,
        filename=None,
        file_base64=None,
        user_obj=None,
        report_queryset=None,
        **kwargs,
    ):
        return ApiEvidenceForm(
            data={
                "friendly_name": friendly_name,
                "description": description,
                "caption": caption,
                "tags": tags,
                "finding": finding,
                "report": report,
                "file_base64": file_base64,
                "filename": filename,
            },
            user_obj=user_obj,
            report_queryset=report_queryset,
        )

    def test_valid_data(self):
        form = self.form_data(
            friendly_name="Test Finding & Report",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=None,
            report=self.report,
            filename="test.txt",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        self.assertTrue(form.is_valid())

    def test_finding_and_report(self):
        form = self.form_data(
            friendly_name="Test Finding & Report",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=None,
            report=None,
            filename="test.txt",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        errors = form.errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 2)

        form = self.form_data(
            friendly_name="Test Finding & Report",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=self.finding,
            report=self.report,
            filename="test.txt",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        errors = form.errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)

    def test_invalid_extension(self):
        form = self.form_data(
            friendly_name="Test Finding & Report",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=None,
            report=self.report,
            filename="test.zip",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        errors = form.errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors["filename"][0].code, "invalid")

    def test_invalid_report_and_finding(self):
        form = self.form_data(
            friendly_name="Test Finding & Report",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=None,
            report=self.other_report,
            filename="test.txt",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        errors = form.errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)

    def test_duplicate_friendly_name(self):
        evidence = EvidenceOnReportFactory(report=self.report, friendly_name="Duplicate Test")
        form = self.form_data(
            friendly_name="Duplicate Test",
            description="Test Description",
            caption="Test Caption",
            tags="Test, Tag",
            finding=None,
            report=self.report,
            filename="test.txt",
            file_base64="dGVzdA==",
            user_obj=self.user,
            report_queryset=get_reports_list(self.user),
        )
        errors = form.errors.as_data()
        self.assertFalse(form.is_valid())
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors["friendly_name"][0].code, "duplicate")

    def test_saving_file_content(self):
        pass
