# Standard Libraries
import json
import logging
from datetime import date

# Django Imports
from django.conf import settings
from django.test import TestCase
from django.utils import dateformat

# 3rd Party Libraries
from rest_framework.renderers import JSONRenderer

# Ghostwriter Libraries
from ghostwriter.factories import GenerateMockProject
from ghostwriter.modules.custom_serializers import ReportDataSerializer

logging.disable(logging.CRITICAL)


class ReportDataSerializerTests(TestCase):
    """Collection of tests for custom report serializer."""

    @classmethod
    def setUpTestData(cls):
        cls.num_of_contacts = 3
        cls.num_of_assignments = 3
        cls.num_of_findings = 10
        cls.num_of_scopes = 3
        cls.num_of_targets = 10
        cls.num_of_objectives = 3
        cls.num_of_subtasks = 5
        cls.num_of_domains = 6
        cls.num_of_servers = 3
        cls.num_of_deconflictions = 3

        cls.client, cls.project, cls.report = GenerateMockProject(
            cls.num_of_contacts,
            cls.num_of_assignments,
            cls.num_of_findings,
            cls.num_of_scopes,
            cls.num_of_targets,
            cls.num_of_objectives,
            cls.num_of_subtasks,
            cls.num_of_domains,
            cls.num_of_servers,
            cls.num_of_deconflictions,
        )

        cls.serializer = ReportDataSerializer(
            cls.report,
            exclude=[
                "id",
            ],
        )

    def setUp(self):
        pass

    def test_json_rendering(self):
        try:
            report_json = JSONRenderer().render(self.serializer.data)
            report_json = json.loads(report_json)
        except Exception:
            self.fail("Failed to render report data as JSON")

    def test_expected_json_keys_exist(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        # Check expected keys are present
        self.assertTrue("report_date" in report_json)
        self.assertTrue("project" in report_json)
        self.assertTrue("client" in report_json)
        self.assertTrue("team" in report_json)
        self.assertTrue("objectives" in report_json)
        self.assertTrue("targets" in report_json)
        self.assertTrue("scope" in report_json)
        self.assertTrue("deconflictions" in report_json)
        self.assertTrue("infrastructure" in report_json)
        self.assertTrue("findings" in report_json)
        self.assertTrue("docx_template" in report_json)
        self.assertTrue("pptx_template" in report_json)
        self.assertTrue("company" in report_json)
        self.assertTrue("totals" in report_json)

    def test_extra_values(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        self.assertEqual(
            report_json["report_date"],
            dateformat.format(date.today(), settings.DATE_FORMAT),
        )

        totals = report_json["totals"]
        self.assertEqual(totals["findings"], self.num_of_findings)
        self.assertEqual(totals["targets"], self.num_of_targets)
        self.assertEqual(totals["team"], self.num_of_assignments)
        self.assertEqual(totals["objectives"], self.num_of_objectives)

        total_scope_lines = 0
        for scope in report_json["scope"]:
            total_scope_lines += scope["total"]

        self.assertEqual(totals["scope"], total_scope_lines)

        completed_objectives = 0
        for objective in report_json["objectives"]:
            if objective["complete"]:
                completed_objectives += 1

        self.assertEqual(totals["objectives_completed"], completed_objectives)

        for f in report_json["findings"]:
            self.assertTrue("ordering" in f)

    def test_values_are_not_empty(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        for key in report_json:
            self.assertTrue(report_json[key] is not None)
