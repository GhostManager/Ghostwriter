# Standard Libraries
import csv
import logging
import os
from datetime import datetime

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import (
    OplogEntryFactory,
    OplogFactory,
    ProjectFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    UserFactory,
)
from ghostwriter.reporting.templatetags import report_tags

logging.disable(logging.INFO)

PASSWORD = "SuperNaturalReporting!"


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
            self.assertEqual(
                report_tags.get_item(severity_dict, group), severity_dict.get(group)
            )

        lint_json = report_tags.load_json(self.report.docx_template.lint_result)
        data = {"result": "success", "warnings": [], "errors": []}
        self.assertEqual(lint_json, data)


# Tests related to report modification actions


class OplogListTests(TestCase):
    """Collection of tests for :view:`oplog.index`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("oplog:index")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_list.html")

    def test_custom_context_exists(self):
        OplogFactory.create_batch(5)
        response = self.client_auth.get(self.uri)
        self.assertIn("op_logs", response.context)
        self.assertEqual(response.context["op_logs"][0], self.Oplog.objects.all()[0])


class OplogListEntriesTests(TestCase):
    """Collection of tests for :view:`oplog.OplogListEntries`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.OplogEntry = OplogEntryFactory._meta.model

        cls.oplog = OplogFactory()
        OplogEntryFactory.create_batch(5, oplog_id=cls.oplog)

        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("oplog:oplog_entries", kwargs={"pk": cls.oplog.id})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/entries_list.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)

        entries = self.OplogEntry.objects.filter(oplog_id=self.oplog.pk).order_by(
            "-start_date"
        )
        self.assertIn("entries", response.context)
        self.assertIn("pk", response.context)
        self.assertIn("name", response.context)
        self.assertIn("project", response.context)
        self.assertEqual(response.context["entries"][0], entries[0])
        self.assertEqual(response.context["pk"], self.oplog.pk)
        self.assertEqual(response.context["name"], self.oplog.name)
        self.assertEqual(response.context["project"], self.oplog.project)


class OplogEntriesImportTests(TestCase):
    """Collection of tests for :view:`oplog.OplogEntriesImport`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.OplogEntry = OplogEntryFactory._meta.model

        cls.oplog = OplogFactory()
        cls.num_of_entries = 5
        for x in range(cls.num_of_entries):
            OplogEntryFactory(oplog_id=cls.oplog)

        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("oplog:oplog_import")
        cls.redirect_uri = reverse("oplog:oplog_entries", kwargs={"pk": cls.oplog.pk})
        cls.failure_redirect_uri = reverse("oplog:oplog_import")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_import.html")

    def test_post_data(self):
        filename = "oplog_import_test.csv"
        fieldnames = [
            "oplog_id",
            "start_date",
            "end_date",
            "source_ip",
            "dest_ip",
            "tool",
            "user_context",
            "command",
            "description",
            "output",
            "comments",
            "operator_name",
        ]
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(
                csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONE
            )
            writer.writeheader()
            for entry in self.OplogEntry.objects.all():
                row = {}
                for field in fieldnames:
                    if field == "oplog_id":
                        row[field] = int(entry.oplog_id.id)
                    elif field == "start_date":
                        row[field] = datetime.timestamp(entry.start_date)
                    elif field == "end_date":
                        row[field] = datetime.timestamp(entry.end_date)
                    else:
                        row[field] = getattr(entry, field)
                writer.writerow(row)

        with open(filename, "r") as csvfile:
            response = self.client_auth.post(self.uri, {"csv_file": csvfile})
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.redirect_uri)
            self.assertEqual(self.OplogEntry.objects.count(), self.num_of_entries * 2)
        os.remove(filename)


class OplogCreateViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("oplog:oplog_create_no_project")
        cls.project_uri = reverse("oplog:oplog_create", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uri_with_project_exists_at_desired_location(self):
        response = self.client_auth.get(self.project_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_form.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("project", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("oplog:index"))
        self.assertEqual(response.context["project"], "")

    def test_custom_context_exists_with_project(self):
        response = self.client_auth.get(self.project_uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.project.pk}),
        )
        self.assertEqual(response.context["project"], self.project)

    def test_custom_context_changes_for_project(self):
        response = self.client_auth.get(self.project_uri)
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
