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
from ghostwriter.factories import (
    ClientFactory,
    ObjectivePriorityFactory,
    ObjectiveStatusFactory,
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ProjectRoleFactory,
    ProjectScopeFactory,
    ProjectTargetFactory,
    ReportDocxTemplateFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportPptxTemplateFactory,
    SeverityFactory,
    UserFactory,
)
from ghostwriter.modules.custom_serializers import ReportDataSerializer

logging.disable(logging.CRITICAL)


class ReportDataSerializerTests(TestCase):
    """Collection of tests for custom report serializer."""

    @classmethod
    def setUpTestData(cls):
        cls.num_of_assignments = 3
        cls.num_of_findings = 10
        cls.num_of_scopes = 3
        cls.num_of_targets = 10
        cls.num_of_objectives = 3

        cls.client = ClientFactory()
        cls.project = ProjectFactory(client=cls.client)
        cls.report = ReportFactory(
            project=cls.project,
            docx_template=ReportDocxTemplateFactory(),
            pptx_template=ReportPptxTemplateFactory(),
        )
        assignments = ProjectAssignmentFactory.create_batch(
            cls.num_of_assignments,
            project=cls.project,
        )
        severities = [
            SeverityFactory(severity="Critical", weight=0),
            SeverityFactory(severity="High", weight=1),
            SeverityFactory(severity="Medium", weight=2),
            SeverityFactory(severity="Low", weight=3),
        ]
        for index in range(cls.num_of_findings):
            ReportFindingLinkFactory(
                report=cls.report,
                severity=severities[index % len(severities)],
                assigned_to=assignments[index % len(assignments)].operator,
            )

        scope_states = (
            (False, False),
            (False, True),
            (True, False),
        )
        for index, (disallowed, requires_caution) in enumerate(scope_states):
            ProjectScopeFactory(
                project=cls.project,
                scope=f"192.0.2.{index + 1}",
                disallowed=disallowed,
                requires_caution=requires_caution,
            )

        for index in range(cls.num_of_targets):
            ProjectTargetFactory(
                project=cls.project,
                compromised=index % 2 == 0,
            )

        priorities = [
            ObjectivePriorityFactory(priority="Primary", weight=0),
            ObjectivePriorityFactory(priority="Secondary", weight=1),
            ObjectivePriorityFactory(priority="Tertiary", weight=2),
        ]
        statuses = [
            ObjectiveStatusFactory(objective_status="Done"),
            ObjectiveStatusFactory(objective_status="Missed"),
            ObjectiveStatusFactory(objective_status="In Progress"),
        ]
        for index in range(cls.num_of_objectives):
            ProjectObjectiveFactory(
                project=cls.project,
                priority=priorities[index],
                status=statuses[index],
                complete=index % 2 == 0,
            )

        # Create an object with a null value for later testing
        oplog = OplogFactory.create(project=cls.project)
        OplogEntryFactory.create(tool=None, oplog_id=oplog)

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
            _ = json.loads(report_json)
        except Exception:
            self.fail("Failed to render report data as JSON")

    def test_expected_json_keys_exist(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        # Check expected keys are present
        self.assertIn("report_date", report_json)
        self.assertIn("project", report_json)
        self.assertIn("client", report_json)
        self.assertIn("team", report_json)
        self.assertIn("objectives", report_json)
        self.assertIn("targets", report_json)
        self.assertIn("scope", report_json)
        self.assertIn("deconflictions", report_json)
        self.assertIn("infrastructure", report_json)
        self.assertIn("findings", report_json)
        self.assertIn("docx_template", report_json)
        self.assertIn("pptx_template", report_json)
        self.assertIn("company", report_json)
        self.assertIn("totals", report_json)

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
            self.assertIn("ordering", f)

    def test_report_fixture_has_deliberate_variants(self):
        finding_severities = set(
            self.report.reportfindinglink_set.values_list("severity_id", flat=True)
        )
        finding_assignees = set(
            self.report.reportfindinglink_set.values_list("assigned_to_id", flat=True)
        )
        objective_states = set(
            self.project.projectobjective_set.values_list("complete", flat=True)
        )
        objective_statuses = set(
            self.project.projectobjective_set.values_list("status_id", flat=True)
        )
        target_states = set(
            self.project.projecttarget_set.values_list("compromised", flat=True)
        )
        scope_states = set(
            self.project.projectscope_set.values_list(
                "disallowed",
                "requires_caution",
            )
        )

        self.assertEqual(len(finding_severities), 4)
        self.assertEqual(len(finding_assignees), self.num_of_assignments)
        self.assertEqual(objective_states, {False, True})
        self.assertEqual(len(objective_statuses), self.num_of_objectives)
        self.assertEqual(target_states, {False, True})
        self.assertEqual(
            scope_states,
            {
                (False, False),
                (False, True),
                (True, False),
            },
        )

    def test_values_are_not_empty(self):
        report_json = JSONRenderer().render(self.serializer.data)
        report_json = json.loads(report_json)

        for key in report_json:
            self.assertIsNotNone(report_json[key])

        for log in report_json["logs"]:
            for entry in log["entries"]:
                self.assertIsNotNone(entry["tool"])

    def test_team_entries_are_ordered_by_role_position_then_operator_name(self):
        project = ProjectFactory()
        report = ReportFactory(project=project)
        lead_role = ProjectRoleFactory(project_role="Lead", position=1)
        operator_role = ProjectRoleFactory(project_role="Operator", position=2)

        ProjectAssignmentFactory(
            project=project,
            role=operator_role,
            operator=UserFactory(name="Zed Zebra"),
        )
        ProjectAssignmentFactory(
            project=project,
            role=lead_role,
            operator=UserFactory(name="Beth Baker"),
        )
        ProjectAssignmentFactory(
            project=project,
            role=lead_role,
            operator=UserFactory(name="Amy Adams"),
        )

        serializer = ReportDataSerializer(report, exclude=["id"])
        report_json = json.loads(JSONRenderer().render(serializer.data))

        self.assertEqual(
            [entry["name"] for entry in report_json["team"]],
            ["Amy Adams", "Beth Baker", "Zed Zebra"],
        )

    def test_unknown_excluded_field_is_ignored(self):
        serializer = ReportDataSerializer(self.report, exclude=["does_not_exist"])
        report_json = json.loads(JSONRenderer().render(serializer.data))

        self.assertIn("project", report_json)
