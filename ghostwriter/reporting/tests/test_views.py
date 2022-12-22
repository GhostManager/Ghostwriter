# Standard Libraries
import json
import logging
import os
from datetime import datetime

# Django Imports
from django.conf import settings
from django.contrib.messages import get_messages
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone
from django.utils.dateformat import format as dateformat
from django.utils.encoding import force_str

# 3rd Party Libraries
from rest_framework.renderers import JSONRenderer

# Ghostwriter Libraries
from ghostwriter.factories import (
    CompanyInformationFactory,
    EvidenceFactory,
    FindingFactory,
    FindingNoteFactory,
    FindingTypeFactory,
    GenerateMockProject,
    LocalFindingNoteFactory,
    ProjectFactory,
    ProjectTargetFactory,
    ReportConfigurationFactory,
    ReportDocxTemplateFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportPptxTemplateFactory,
    ReportTemplateFactory,
    SeverityFactory,
    UserFactory,
)
from ghostwriter.modules.custom_serializers import ReportDataSerializer
from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter import (
    add_days,
    compromised,
    filter_severity,
    filter_type,
    format_datetime,
    strip_html,
)
from ghostwriter.reporting.templatetags import report_tags
from ghostwriter.reporting.views import generate_report_name

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class IndexViewTests(TestCase):
    """Collection of tests for :view:`reporting.index`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:index")
        cls.redirect_uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.report = ReportFactory()
        for x in range(3):
            ReportFindingLinkFactory(report=cls.report)

    def setUp(self):
        pass

    def test_tags(self):
        queryset = self.ReportFindingLink.objects.all()

        severity_dict = report_tags.group_by_severity(queryset)
        self.assertEqual(len(severity_dict), 3)

        for group in severity_dict:
            self.assertEqual(report_tags.get_item(severity_dict, group), severity_dict.get(group))


# Tests related to report modification actions


class AssignBlankFindingTests(TestCase):
    """Collection of tests for :view:`reporting.AssignBlankFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)

        # These must exist for the view to function
        cls.high_severity = SeverityFactory(severity="High", weight=1)
        cls.med_severity = SeverityFactory(severity="Medium", weight=2)
        cls.low_severity = SeverityFactory(severity="Low", weight=3)
        cls.info_severity = SeverityFactory(severity="Informational", weight=4)
        cls.finding_type = FindingTypeFactory(finding_type="Network")

        cls.uri = reverse("reporting:assign_blank_finding", kwargs={"pk": cls.report.pk})
        cls.redirect_uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ConvertFindingTests(TestCase):
    """Collection of tests for :view:`reporting.ConvertFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = ReportFindingLinkFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("reporting:convert_finding", kwargs={"pk": cls.finding.pk})
        cls.redirect_uri = reverse("reporting:finding_detail", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_form.html")


class AssignFindingTests(TestCase):
    """Collection of tests for :view:`reporting.AssignFinding`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("reporting:ajax_assign_finding", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_response_with_session_vars(self):
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = self.report.id
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.id, "title": self.report.title},
        )

        response = self.client_auth.post(self.uri)
        message = "{} successfully added to your active report".format(self.finding)
        data = {"result": "success", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_view_response_with_bad_session_vars(self):
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = 999
        self.session["active_report"]["title"] = self.report.title
        self.session.save()

        self.assertEqual(
            self.session["active_report"],
            {"id": 999, "title": self.report.title},
        )

        response = self.client_auth.post(self.uri)
        message = "Please select a report to edit before trying to assign a finding"
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)

    def test_view_response_without_session_vars(self):
        self.session = self.client_auth.session
        self.session["active_report"] = None
        self.session.save()

        self.assertEqual(self.session["active_report"], None)

        response = self.client_auth.post(self.uri)
        message = "Please select a report to edit before trying to assign a finding"
        data = {"result": "error", "message": message}

        self.assertJSONEqual(force_str(response.content), data)


class ReportCloneTests(TestCase):
    """Collection of tests for :view:`reporting.ReportClone`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.Report = ReportFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.Evidence = EvidenceFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(ReportFindingLinkFactory(title=title, report=cls.report))

        cls.uri = reverse("reporting:report_clone", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_nonexistent_report(self):
        uri = reverse("reporting:report_clone", kwargs={"pk": 100})
        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_clone_with_zero_findings(self):
        self.ReportFindingLink.objects.all().delete()
        response = self.client_auth.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

        report_copy = self.Report.objects.latest("id")
        self.assertEqual(report_copy.title, f"{self.report.title} Copy")

        copied_findings = self.ReportFindingLink.objects.filter(report=report_copy)
        self.assertEqual(len(copied_findings), 0)

    def test_clone_with_findings(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("reporting/reports/", response.url)

        report_copy = self.Report.objects.latest("id")
        self.assertEqual(report_copy.title, f"{self.report.title} Copy")

        copied_findings = self.ReportFindingLink.objects.filter(report=report_copy)
        self.assertEqual(len(copied_findings), self.num_of_findings)

    def test_clone_with_evidence_files(self):
        self.Evidence.objects.all().delete()
        report = ReportFactory()
        finding = ReportFindingLinkFactory(title="Evidence Finding 1", report=report)
        evidence = EvidenceFactory(finding=finding)

        uri = reverse("reporting:report_clone", kwargs={"pk": report.pk})
        response = self.client_auth.get(uri)
        self.assertIn("reporting/reports/", response.url)

        evidence_files = self.Evidence.objects.filter(friendly_name=evidence.friendly_name)
        self.assertEqual(len(evidence_files), 2)

        # Check the evidence file was copied to the new report's directory
        report_copy = self.Report.objects.latest("id")
        evidence_copy = evidence_files.latest("id")
        assert os.path.exists(evidence_copy.document.path)
        self.assertIn(f"ghostwriter/media/evidence/{report_copy.pk}", evidence_copy.document.path)

    def test_clone_with_missing_evidence_file(self):
        self.Evidence.objects.all().delete()
        report = ReportFactory()
        finding = ReportFindingLinkFactory(title="Evidence Finding 1", report=report)
        evidence = EvidenceFactory(finding=finding)
        evidence_missing_file = EvidenceFactory(finding=finding)

        # Delete evidence file
        os.remove(evidence_missing_file.document.path)

        uri = reverse("reporting:report_clone", kwargs={"pk": report.pk})
        response = self.client_auth.get(uri)
        self.assertIn("reporting/reports/", response.url)

        # Check that the evidence with the missing file was not copied
        evidence_files = self.Evidence.objects.filter(friendly_name=evidence.friendly_name)
        self.assertEqual(len(evidence_files), 2)
        evidence_files = self.Evidence.objects.filter(friendly_name=evidence_missing_file.friendly_name)
        self.assertEqual(len(evidence_files), 1)
        # Total = 2 from the original report + 1 from the copy
        self.assertEqual(len(self.Evidence.objects.all()), 3)


# Tests related to :model:`reporting.Finding`


class FindingsListViewTests(TestCase):
    """Collection of tests for :view:`reporting.findings_list`."""

    @classmethod
    def setUpTestData(cls):
        cls.Finding = FindingFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(FindingFactory(title=title))

        cls.uri = reverse("reporting:findings")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_list.html")

    def test_lists_all_findings(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.findings))

    def test_search_findings(self):
        response = self.client_auth.get(self.uri + "?finding_search=Finding+2")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)

    def test_filter_findings(self):
        response = self.client_auth.get(self.uri + "?title=Finding+2&submit=Filter")
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == 1)


class FindingDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("reporting:finding_detail", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_detail.html")


class FindingCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.Finding = FindingFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:finding_create")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("reporting:findings"))


class FindingUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:finding_update", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/finding_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:finding_detail", kwargs={"pk": self.finding.pk}),
        )


class FindingDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.FindingDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = FindingFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:finding_delete", kwargs={"pk": cls.finding.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:findings"),
        )
        self.assertEqual(
            response.context["object_type"],
            "finding master record",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.finding.title)


class FindingExportViewTests(TestCase):
    """Collection of tests for :view:`reporting.export_findings_to_csv`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(FindingFactory(title=title))
        cls.uri = reverse("reporting:export_findings_to_csv")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.get("Content-Type"), "text/csv")

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`reporting.Report`


class ReportsListViewTests(TestCase):
    """Collection of tests for :view:`reporting.reports_list`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_reports = 10
        cls.reports = []
        for report_id in range(cls.num_of_reports):
            title = f"Report {report_id}"
            cls.reports.append(ReportFactory(title=title))

        cls.uri = reverse("reporting:reports")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_list.html")

    def test_lists_all_reports(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTrue(len(response.context["filter"].qs) == len(self.reports))


class ReportDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_detail.html")


class ReportCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.Report = ReportFactory._meta.model
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:report_create_no_project")
        cls.project_uri = reverse("reporting:report_create", kwargs={"pk": cls.project.pk})
        cls.success_uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})
        cls.bad_project_uri = reverse("reporting:report_create", kwargs={"pk": 999})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("reporting:reports"))

    def test_view_uri_with_project_exists_at_desired_location(self):
        response = self.client_auth.get(self.project_uri)
        self.assertEqual(response.status_code, 200)

    def test_custom_context_changes_for_project(self):
        response = self.client_auth.get(self.project_uri)
        self.assertIn("project", response.context)
        self.assertEqual(
            response.context["project"],
            self.project,
        )
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.project.pk}),
        )

    def test_form_with_no_active_projects(self):
        self.project.complete = True
        self.project.save()

        response = self.client_auth.get(self.uri)
        self.assertInHTML(
            '<option value="" selected>-- No Active Projects --</option>',
            response.content.decode(),
        )

        self.project.complete = False
        self.project.save()

    def test_get_success_url_with_session_vars(self):
        # Set up session variables to be clear
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = ""
        self.session["active_report"]["title"] = ""
        self.session.save()

        # Send POST to delete and check if session vars are set
        response = self.client_auth.post(
            self.uri,
            {
                "title": "New Report Title",
                "project": self.report.project.pk,
                "docx_template": self.report.docx_template.pk,
                "pptx_template": self.report.pptx_template.pk,
            },
        )

        # Get report created from request and check response
        new_report = self.Report.objects.get(title="New Report Title")
        success_uri = reverse("reporting:report_detail", kwargs={"pk": new_report.pk})
        self.assertRedirects(response, success_uri)
        self.session = self.client_auth.session
        self.assertEqual(
            self.session["active_report"],
            {"id": new_report.pk, "title": f"{new_report.title}"},
        )

    def test_form_with_invalid_project(self):
        response = self.client_auth.get(self.bad_project_uri)
        self.assertIn("exception", response.context)
        self.assertEqual(response.context["exception"], "No Project matches the given query.")
        self.assertEqual(response.status_code, 404)


class ReportUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:report_update", kwargs={"pk": cls.report.pk})
        cls.success_uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:report_detail", kwargs={"pk": self.report.pk}),
        )

    def test_get_success_url_with_session_vars(self):
        # Set up session variables to be clear
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = ""
        self.session["active_report"]["title"] = ""
        self.session.save()

        # Send POST to delete and check if session vars are set
        response = self.client_auth.post(
            self.uri,
            {
                "title": self.report.title,
                "project": self.report.project.pk,
                "docx_template": self.report.docx_template.pk,
                "pptx_template": self.report.pptx_template.pk,
            },
        )
        self.assertRedirects(response, self.success_uri)
        self.session = self.client_auth.session
        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.pk, "title": f"{self.report.title}"},
        )


class ReportDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.Report = ReportFactory._meta.model
        cls.report = ReportFactory()
        cls.delete_report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:report_delete", kwargs={"pk": cls.report.pk})
        cls.delete_uri = reverse("reporting:report_delete", kwargs={"pk": cls.delete_report.pk})
        cls.success_uri = f"{reverse('rolodex:project_detail', kwargs={'pk': cls.delete_report.project.pk})}#reports"

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.report.project.pk}),
        )
        self.assertEqual(
            response.context["object_type"],
            "entire report, evidence and all",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.report.title)

    def test_get_success_url(self):
        # Set session variables to "activate" target report object
        self.session = self.client_auth.session
        self.session["active_report"] = {}
        self.session["active_report"]["id"] = self.delete_report.id
        self.session["active_report"]["title"] = self.delete_report.title
        self.session.save()

        # Send POST to delete and check if session is now cleared
        response = self.client_auth.post(self.delete_uri)
        self.session = self.client_auth.session
        self.assertRedirects(response, self.success_uri)
        self.assertEqual(
            self.session["active_report"],
            {"id": "", "title": ""},
        )


class ReportActivateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportActivate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:ajax_activate_report", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_sets_sessions_variables(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.session = self.client_auth.session
        self.assertEqual(
            self.session["active_report"],
            {"id": self.report.id, "title": self.report.title},
        )

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)


class ReportStatusToggleViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportStatusToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:ajax_toggle_report_status", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_toggles_value(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

        self.report.refresh_from_db()
        self.assertEqual(self.report.complete, True)

        response = self.client_auth.post(self.uri)
        self.report.refresh_from_db()
        self.assertEqual(self.report.complete, False)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)


class ReportDeliveryToggleViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportDeliveryToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(delivered=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:ajax_toggle_report_delivery", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_toggles_value(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 200)

        self.report.refresh_from_db()
        self.assertEqual(self.report.delivered, True)

        response = self.client_auth.post(self.uri)
        self.report.refresh_from_db()
        self.assertEqual(self.report.delivered, False)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`reporting.ReportFindingLink`


class ReportFindingLinkUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportFindingLinkUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory(
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )

        cls.high_severity = SeverityFactory(severity="High", weight=1)
        cls.critical_severity = SeverityFactory(severity="Critical", weight=0)

        cls.user = UserFactory(password=PASSWORD)
        cls.new_user = UserFactory(password=PASSWORD)

        cls.num_of_findings = 10
        cls.findings = []
        for finding_id in range(cls.num_of_findings):
            title = f"Finding {finding_id}"
            cls.findings.append(ReportFindingLinkFactory(title=title, report=cls.report))

        cls.uri = reverse("reporting:local_edit", kwargs={"pk": cls.findings[0].pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/local_edit.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:report_detail", kwargs={"pk": self.report.pk}),
        )


# Tests related to :model:`reporting.Evidence`


class EvidenceDetailViewTests(TestCase):
    """
    Collection of tests for :view:`reporting.EvidenceDetailView` and the related
    :view:`reporting.upload_evidence_modal_success`.
    """

    @classmethod
    def setUpTestData(cls):
        cls.img_evidence = EvidenceFactory(img=True)
        cls.txt_evidence = EvidenceFactory(txt=True)
        cls.unknown_evidence = EvidenceFactory(unknown=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.img_uri = reverse("reporting:evidence_detail", kwargs={"pk": cls.img_evidence.pk})
        cls.txt_uri = reverse("reporting:evidence_detail", kwargs={"pk": cls.txt_evidence.pk})
        cls.unknown_uri = reverse("reporting:evidence_detail", kwargs={"pk": cls.unknown_evidence.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.img_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.img_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.img_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_detail.html")

    def test_custom_context_exists_img(self):
        response = self.client_auth.get(self.img_uri)
        self.assertIn("filetype", response.context)
        self.assertIn("evidence", response.context)
        self.assertIn("file_content", response.context)
        self.assertEqual(
            response.context["filetype"],
            "image",
        )
        self.assertEqual(
            response.context["evidence"],
            self.img_evidence,
        )

    def test_custom_context_exists_txt(self):
        response = self.client_auth.get(self.txt_uri)
        self.assertEqual(
            response.context["filetype"],
            "text",
        )

    def test_custom_context_exists_unknown(self):
        response = self.client_auth.get(self.unknown_uri)
        self.assertEqual(
            response.context["filetype"],
            "unknown",
        )


class EvidenceCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.finding = ReportFindingLinkFactory()
        cls.evidence = EvidenceFactory(finding=cls.finding)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:upload_evidence", kwargs={"pk": cls.finding.pk})
        cls.modal_uri = reverse(
            "reporting:upload_evidence_modal",
            kwargs={"pk": cls.finding.pk, "modal": "modal"},
        )
        cls.success_uri = reverse("reporting:report_detail", args=(cls.finding.report.pk,))
        cls.modal_success_uri = reverse("reporting:upload_evidence_modal_success")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    # Testing regular form view
    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:report_detail", kwargs={"pk": self.finding.report.pk}),
        )

    # Testing modal form view
    def test_view_modal_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.modal_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_modal_requires_login(self):
        response = self.client.get(self.modal_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_modal_uses_correct_template(self):
        response = self.client_auth.get(self.modal_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form_modal.html")

    def test_custom_modal_context_exists(self):
        response = self.client_auth.get(self.modal_uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("used_friendly_names", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:report_detail", kwargs={"pk": self.finding.report.pk}),
        )

    # Testing modal success view
    def test_view_modal_success_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_modal_success_requires_login(self):
        response = self.client.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_modal_success_uses_correct_template(self):
        response = self.client_auth.get(self.modal_success_uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_modal_success.html")


class EvidenceUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.evidence = EvidenceFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:evidence_update", kwargs={"pk": cls.evidence.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/evidence_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:evidence_detail", kwargs={"pk": self.evidence.pk}),
        )


class EvidenceDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.EvidenceDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.evidence = EvidenceFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:evidence_delete", kwargs={"pk": cls.evidence.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:evidence_detail", kwargs={"pk": self.evidence.pk}),
        )
        self.assertEqual(
            response.context["object_type"],
            "evidence file (and associated file on disk)",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.evidence.friendly_name)


# Tests related to :model:`reporting.ReportTemplate`


class ReportTemplateListViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateListView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.num_of_templates = 10
        cls.templates = []
        for template_id in range(cls.num_of_templates):
            cls.templates.append(ReportTemplateFactory())

        cls.uri = reverse("reporting:templates")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_templates_list.html")


class ReportTemplateDownloadTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:template_download", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_returns_desired_download(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.template.filename}"',
        )

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ReportTemplateDetailViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.admin_user = UserFactory(password=PASSWORD, is_staff=True)
        cls.uri = reverse("reporting:template_detail", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_admin = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_admin.login(username=self.admin_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.admin_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_detail.html")

    def test_view_for_protected_template(self):
        response = self.client_auth.get(self.uri)
        self.assertInHTML(
            '<div class="alert alert-danger icon lock-icon" role="alert">This template is protected – only admins and managers may edit it</div>',
            response.content.decode(),
        )

        response = self.client_admin.get(self.uri)
        self.assertInHTML(
            '<div class="alert alert-secondary icon unlock-icon" role="alert">You may edit this protected template</div>',
            response.content.decode(),
        )


class ReportTemplateCreateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:template_create")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("reporting:templates"))

    def test_initial_form_values(self):
        response = self.client_auth.get(self.uri)

        date = datetime.now().strftime("%d %B %Y")
        initial_upload = f'<p><span class="bold">{date}</span></p><p>Initial upload</p>'

        self.assertEqual(response.context["form"].initial["changelog"], initial_upload)


class ReportTemplateUpdateViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        cls.staff_user = UserFactory(password=PASSWORD, is_staff=True)
        cls.uri = reverse("reporting:template_update", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_admin = Client()
        self.client_staff = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.mgr_user.username, password=PASSWORD))
        self.client_admin.login(username=self.admin_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.admin_user.username, password=PASSWORD))
        self.client_staff.login(username=self.staff_user.username, password=PASSWORD)
        self.assertTrue(self.client_staff.login(username=self.staff_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "reporting/report_template_form.html")

    def test_custom_context_exists(self):
        response = self.client_staff.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("reporting:templates"))

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_admin.get(self.uri)
        self.assertEqual(response.status_code, 200)


class ReportTemplateDeleteViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory(protected=True)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        cls.staff_user = UserFactory(password=PASSWORD, is_staff=True)
        cls.uri = reverse("reporting:template_delete", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_admin = Client()
        self.client_staff = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.mgr_user.username, password=PASSWORD))
        self.client_admin.login(username=self.admin_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.admin_user.username, password=PASSWORD))
        self.client_staff.login(username=self.staff_user.username, password=PASSWORD)
        self.assertTrue(self.client_staff.login(username=self.staff_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "confirm_delete.html")

    def test_custom_context_exists(self):
        response = self.client_staff.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("object_type", response.context)
        self.assertIn("object_to_be_deleted", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("reporting:template_detail", kwargs={"pk": self.template.pk}),
        )
        self.assertEqual(
            response.context["object_type"],
            "report template file (and associated file on disk)",
        )
        self.assertEqual(response.context["object_to_be_deleted"], self.template.filename)

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_admin.get(self.uri)
        self.assertEqual(response.status_code, 200)


class ReportTemplateLintViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateLint`."""

    @classmethod
    def setUpTestData(cls):
        cls.docx_template = ReportDocxTemplateFactory()
        cls.pptx_template = ReportPptxTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.docx_uri = reverse("reporting:ajax_lint_report_template", kwargs={"pk": cls.docx_template.pk})
        cls.pptx_uri = reverse("reporting:ajax_lint_report_template", kwargs={"pk": cls.pptx_template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "warnings": [],
            "errors": [],
            "message": "Template linter returned results with no errors or warnings",
        }

        response = self.client_auth.get(self.docx_uri)
        self.assertEqual(response.status_code, 405)

        response = self.client_auth.post(self.docx_uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        response = self.client_auth.post(self.pptx_uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login(self):
        response = self.client.get(self.docx_uri)
        self.assertEqual(response.status_code, 302)


class UpdateTemplateLintResultsViewTests(TestCase):
    """Collection of tests for :view:`reporting.UpdateTemplateLintResults`."""

    @classmethod
    def setUpTestData(cls):
        cls.template = ReportTemplateFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:ajax_update_template_lint_results", kwargs={"pk": cls.template.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_returns_desired_download(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ReportTemplateSwapViewTests(TestCase):
    """Collection of tests for :view:`reporting.ReportTemplateSwap`."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.docx_template = ReportDocxTemplateFactory()
        cls.pptx_template = ReportPptxTemplateFactory()

        cls.docx_template_warning = ReportDocxTemplateFactory()
        cls.docx_template_warning.lint_result = {"result": "warning", "warnings": [], "errors": []}
        cls.docx_template_warning.save()
        cls.pptx_template_warning = ReportPptxTemplateFactory()
        cls.pptx_template_warning.lint_result = {"result": "warning", "warnings": [], "errors": []}
        cls.pptx_template_warning.save()

        cls.docx_template_error = ReportDocxTemplateFactory()
        cls.docx_template_error.lint_result = {"result": "error", "warnings": [], "errors": []}
        cls.docx_template_error.save()
        cls.pptx_template_error = ReportPptxTemplateFactory()
        cls.pptx_template_error.lint_result = {"result": "error", "warnings": [], "errors": []}
        cls.pptx_template_error.save()

        cls.docx_template_failed = ReportDocxTemplateFactory()
        cls.docx_template_failed.lint_result = {"result": "failed", "warnings": [], "errors": []}
        cls.docx_template_failed.save()
        cls.pptx_template_failed = ReportPptxTemplateFactory()
        cls.pptx_template_failed.lint_result = {"result": "failed", "warnings": [], "errors": []}
        cls.pptx_template_failed.save()

        cls.docx_template_unknown = ReportDocxTemplateFactory()
        cls.docx_template_unknown.lint_result = {"result": "unknown", "warnings": [], "errors": []}
        cls.docx_template_unknown.save()
        cls.pptx_template_unknown = ReportPptxTemplateFactory()
        cls.pptx_template_unknown.lint_result = {"result": "unknown", "warnings": [], "errors": []}
        cls.pptx_template_unknown.save()

        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:ajax_swap_report_template", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_valid_templates(self):
        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "docx_lint_result": "success",
            "pptx_lint_result": "success",
        }
        response = self.client_auth.post(
            self.uri, {"docx_template": self.docx_template.pk, "pptx_template": self.pptx_template.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        # Test a negative value indicating no template is selected
        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "pptx_lint_result": "success",
        }
        response = self.client_auth.post(self.uri, {"docx_template": -5, "pptx_template": self.pptx_template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_invalid_templates(self):
        data = {
            "result": "error",
            "message": "Submitted template ID was not an integer",
        }
        response = self.client_auth.post(self.uri, {"docx_template": "C", "pptx_template": self.pptx_template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "error",
            "message": "Submitted template ID does not exist",
        }
        response = self.client_auth.post(self.uri, {"docx_template": 1000, "pptx_template": self.pptx_template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {"result": "error", "message": "Submitted request was incomplete"}
        response = self.client_auth.post(self.uri, {"docx_template": "", "pptx_template": self.pptx_template.pk})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_templates_with_linting_errors(self):
        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "docx_lint_result": "warning",
            "docx_lint_message": "Selected Word template has warnings from linter. Check the template before generating a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_warning.pk}",
            "pptx_lint_result": "warning",
            "pptx_lint_message": "Selected PowerPoint template has warnings from linter. Check the template before generating a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_warning.pk}",
        }
        response = self.client_auth.post(
            self.uri, {"docx_template": self.docx_template_warning.pk, "pptx_template": self.pptx_template_warning.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "docx_lint_result": "error",
            "docx_lint_message": "Selected Word template has linting errors and cannot be used to generate a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_error.pk}",
            "pptx_lint_result": "error",
            "pptx_lint_message": "Selected PowerPoint template has linting errors and cannot be used to generate a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_error.pk}",
        }
        response = self.client_auth.post(
            self.uri, {"docx_template": self.docx_template_error.pk, "pptx_template": self.pptx_template_error.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "docx_lint_result": "failed",
            "docx_lint_message": "Selected Word template failed basic linter checks and can't be used to generate a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_failed.pk}",
            "pptx_lint_result": "failed",
            "pptx_lint_message": "Selected PowerPoint template failed basic linter checks and can't be used to generate a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_failed.pk}",
        }
        response = self.client_auth.post(
            self.uri, {"docx_template": self.docx_template_failed.pk, "pptx_template": self.pptx_template_failed.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "success",
            "message": "Templates successfully updated",
            "docx_lint_result": "unknown",
            "docx_lint_message": "Selected Word template has an unknown linter status. Check and lint the template before generating a report.",
            "docx_url": f"/reporting/templates/{self.docx_template_unknown.pk}",
            "pptx_lint_result": "unknown",
            "pptx_lint_message": "Selected PowerPoint template has an unknown linter status. Check and lint the template before generating a report.",
            "pptx_url": f"/reporting/templates/{self.pptx_template_unknown.pk}",
        }
        response = self.client_auth.post(
            self.uri, {"docx_template": self.docx_template_unknown.pk, "pptx_template": self.pptx_template_unknown.pk}
        )
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)


# Tests related to generating report types


class GenerateReportTests(TestCase):
    """Collection of tests for all :view:`reporting.GenerateReport*`."""

    @classmethod
    def setUpTestData(cls):
        cls.org, cls.project, cls.report = GenerateMockProject()
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("reporting:report_delete", kwargs={"pk": cls.report.pk})
        cls.redirect_uri = reverse("reporting:report_detail", kwargs={"pk": cls.report.pk})
        cls.docx_uri = reverse("reporting:generate_docx", kwargs={"pk": cls.report.pk})
        cls.xlsx_uri = reverse("reporting:generate_xlsx", kwargs={"pk": cls.report.pk})
        cls.pptx_uri = reverse("reporting:generate_pptx", kwargs={"pk": cls.report.pk})
        cls.json_uri = reverse("reporting:generate_json", kwargs={"pk": cls.report.pk})
        cls.all_uri = reverse("reporting:generate_all", kwargs={"pk": cls.report.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_generate_report_name(self):
        company_config = CompanyInformationFactory()
        ReportConfigurationFactory(
            report_filename="{D d m Y} {date} {company} - {client} {assessment_type} Report <>:'/|?.,:;[]"
        )

        current_date = timezone.now()
        date_format = dateformat(current_date, "D d m Y")
        date_str = dateformat(current_date, settings.DATE_FORMAT)

        # Remove any periods or commas that can appear in the `Faker` generated names
        client = self.project.client.name.replace(",", "").replace(".", "")
        company = company_config.company_name.replace(",", "").replace(".", "")

        assessment = self.project.project_type.project_type

        report_name = generate_report_name(self.report)
        self.assertEqual(
            report_name,
            f"{date_format} {date_str} {company} - {client} {assessment} Report",
        )

    def test_view_json_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.json_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_docx_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.docx_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )

    def test_view_xlsx_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.xlsx_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )

    def test_view_pptx_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.pptx_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/application/vnd.openxmlformats-officedocument.presentationml.presentation",
        )

    def test_view_all_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.all_uri)
        self.assertEqual(
            response.get("Content-Type"),
            "application/x-zip-compressed",
        )

    def test_view_json_requires_login(self):
        response = self.client.get(self.json_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_docx_requires_login(self):
        response = self.client.get(self.docx_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_xlsx_requires_login(self):
        response = self.client.get(self.xlsx_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_pptx_requires_login(self):
        response = self.client.get(self.pptx_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_all_requires_login(self):
        response = self.client.get(self.all_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_docx_with_missing_template(self):
        good_template = self.report.docx_template
        bad_template = ReportDocxTemplateFactory()
        self.report.docx_template = bad_template
        self.report.save()

        self.assertTrue(os.path.isfile(bad_template.document.path))
        os.remove(bad_template.document.path)
        self.assertFalse(os.path.isfile(bad_template.document.path))

        response = self.client_auth.get(self.docx_uri)
        messages = list(get_messages(response.wsgi_request))
        self.assertEqual(
            str(messages[0]), "Your selected Word template could not be found on the server – try uploading it again"
        )

        self.report.docx_template = good_template
        self.report.save()


class ReportTemplateFilterTests(TestCase):
    """Collection of tests for custom Jinja2 filters for report templates."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)
        cls.critical_sev = SeverityFactory(severity="Critical", weight=0)
        cls.high_sev = SeverityFactory(severity="High", weight=1)
        cls.med_sev = SeverityFactory(severity="Medium", weight=1)
        cls.network_type = FindingTypeFactory(finding_type="Network")
        cls.web_type = FindingTypeFactory(finding_type="Web")
        cls.mobile_type = FindingTypeFactory(finding_type="Mobile")

        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.critical_sev,
            finding_type=cls.network_type,
        )
        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.high_sev,
            finding_type=cls.web_type,
        )
        ReportFindingLinkFactory.create_batch(
            2,
            report=cls.report,
            severity=cls.med_sev,
            finding_type=cls.mobile_type,
        )

        ProjectTargetFactory.create_batch(5, compromised=True, project=cls.project)
        ProjectTargetFactory.create_batch(5, compromised=False, project=cls.project)

        cls.serializer = ReportDataSerializer(
            cls.report,
            exclude=[
                "id",
            ],
        )
        report_json = JSONRenderer().render(cls.serializer.data)
        cls.report_json = json.loads(report_json)
        cls.findings = cls.report_json["findings"]
        cls.targets = cls.report_json["targets"]

        cls.test_date_string = "d M Y"
        cls.new_date_string = "M d, Y"
        cls.test_date = datetime(2022, 3, 28)

    def setUp(self):
        pass

    def test_format_datetime(self):
        test_date = dateformat(self.test_date, self.test_date_string)
        new_date = format_datetime(test_date, self.new_date_string)
        self.assertEqual(new_date, "Mar 28, 2022")

    def test_format_datetime_with_invalid_string(self):
        test_date = "Not a Date"
        with self.assertRaises(InvalidFilterValue):
            format_datetime(test_date, self.new_date_string)

    def test_add_days(self):
        test_date = dateformat(self.test_date, self.test_date_string)
        future_date = "11 Apr 2022"
        past_date = "21 Mar 2022"

        new_date = add_days(test_date, 10)
        self.assertEqual(new_date, future_date)

        new_date = add_days(test_date, -5)
        self.assertEqual(new_date, past_date)

    def test_add_days_with_invalid_string(self):
        test_date = "Not a Date"
        with self.assertRaises(InvalidFilterValue):
            add_days(test_date, 10)

    def test_compromised(self):
        filtered_list = compromised(self.targets)
        self.assertEqual(len(filtered_list), 5)

    def test_compromised_with_invalid_dict(self):
        targets = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            compromised(targets)

    def test_filter_type(self):
        filtered_list = filter_type(self.findings, ["Network", "Web"])
        self.assertEqual(len(filtered_list), 4)

    def test_filter_type_with_invalid_dict(self):
        findings = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            filter_type(findings, ["Network", "Web"])

    def test_filter_type_with_invalid_allowlist(self):
        with self.assertRaises(InvalidFilterValue):
            filter_type(self.findings, "Network")

    def test_filter_severity(self):
        filtered_list = filter_severity(self.findings, ["Critical", "High"])
        self.assertEqual(len(filtered_list), 4)

    def test_filter_severity_with_invalid_dict(self):
        findings = "Not a Dict"
        with self.assertRaises(InvalidFilterValue):
            filter_severity(findings, ["Critical", "High"])

    def test_filter_severity_with_invalid_allowlist(self):
        with self.assertRaises(InvalidFilterValue):
            filter_severity(self.findings, "Critical")

    def test_strip_html(self):
        test_string = "<p>This is a test<br />with a newline</p>"
        result = strip_html(test_string)
        self.assertEqual(result, "This is a test\nwith a newline")


class LocalFindingNoteUpdateTests(TestCase):
    """Collection of tests for :view:`reporting.LocalFindingNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.LocalFindingNote = LocalFindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = LocalFindingNoteFactory(operator=cls.user)
        cls.uri = reverse("reporting:local_finding_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = LocalFindingNoteFactory()
        cls.other_user_uri = reverse("reporting:local_finding_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class LocalFindingNoteDeleteTests(TestCase):
    """Collection of tests for :view:`reporting.LocalFindingNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.LocalFindingNote = LocalFindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.LocalFindingNote.objects.all().delete()
        note = LocalFindingNoteFactory(operator=self.user)
        uri = reverse("reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.LocalFindingNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.LocalFindingNote.objects.all()), 0)

    def test_view_permissions(self):
        note = LocalFindingNoteFactory()
        uri = reverse("reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = LocalFindingNoteFactory()
        uri = reverse("reporting:ajax_delete_local_finding_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class FindingNoteUpdateTests(TestCase):
    """Collection of tests for :view:`reporting.FindingNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingNote = FindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = FindingNoteFactory(operator=cls.user)
        cls.uri = reverse("reporting:finding_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = FindingNoteFactory()
        cls.other_user_uri = reverse("reporting:finding_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class FindingNoteDeleteTests(TestCase):
    """Collection of tests for :view:`reporting.FindingNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.FindingNote = FindingNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.FindingNote.objects.all().delete()
        note = FindingNoteFactory(operator=self.user)
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.FindingNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.FindingNote.objects.all()), 0)

    def test_view_permissions(self):
        note = FindingNoteFactory()
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = FindingNoteFactory()
        uri = reverse("reporting:ajax_delete_finding_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)
