# Standard Libraries
from datetime import date, timedelta

# Django Imports
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class FindingEvidenceMigrationTests(TransactionTestCase):
    """Verify finding-owned evidence is moved to report ownership."""

    migrate_from = [("reporting", "0067_alter_reporttemplate_evidence_image_width")]
    migrate_to = [("reporting", "0069_remove_finding_evidence")]

    def setUp(self):
        super().setUp()
        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        self.setUpBeforeMigration(old_apps)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def setUpBeforeMigration(self, apps):
        Client = apps.get_model("rolodex", "Client")
        Project = apps.get_model("rolodex", "Project")
        ProjectType = apps.get_model("rolodex", "ProjectType")
        Report = apps.get_model("reporting", "Report")
        ReportFindingLink = apps.get_model("reporting", "ReportFindingLink")
        Severity = apps.get_model("reporting", "Severity")
        FindingType = apps.get_model("reporting", "FindingType")
        Evidence = apps.get_model("reporting", "Evidence")

        client = Client.objects.create(name="Migration Client")
        project_type = ProjectType.objects.create(project_type="Migration Test")
        project = Project.objects.create(
            client=client,
            project_type=project_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        self.report = Report.objects.create(project=project, title="Migration Report")
        severity = Severity.objects.create(severity="Critical", weight=1)
        finding_type = FindingType.objects.create(finding_type="Network")
        self.finding = ReportFindingLink.objects.create(
            report=self.report,
            severity=severity,
            finding_type=finding_type,
            description="<p>{{.Collision}}</p><p>{{.ref Collision}}</p>",
        )

        self.report_evidence = Evidence.objects.create(
            report=self.report,
            friendly_name="Collision",
            document="evidence/existing.txt",
        )
        self.migrated_collision = Evidence.objects.create(
            finding=self.finding,
            friendly_name="Collision",
            document="evidence/collision.txt",
        )
        self.migrated_unique = Evidence.objects.create(
            finding=self.finding,
            friendly_name="Unique",
            document="evidence/unique.txt",
        )

    def test_finding_evidence_moves_to_report_and_removes_finding_field(self):
        Evidence = self.apps.get_model("reporting", "Evidence")

        field_names = {field.name for field in Evidence._meta.get_fields()}
        self.assertNotIn("finding", field_names)

        migrated_unique = Evidence.objects.get(pk=self.migrated_unique.pk)
        self.assertEqual(migrated_unique.report_id, self.report.pk)
        self.assertEqual(migrated_unique.friendly_name, "Unique")

    def test_duplicate_friendly_name_is_renamed_and_references_updated(self):
        Evidence = self.apps.get_model("reporting", "Evidence")
        ReportFindingLink = self.apps.get_model("reporting", "ReportFindingLink")

        migrated_collision = Evidence.objects.get(pk=self.migrated_collision.pk)
        expected_name = f"Collision (evidence {self.migrated_collision.pk})"
        self.assertEqual(migrated_collision.report_id, self.report.pk)
        self.assertEqual(migrated_collision.friendly_name, expected_name)

        finding = ReportFindingLink.objects.get(pk=self.finding.pk)
        self.assertEqual(
            finding.description,
            f"<p>{{{{.{expected_name}}}}}</p><p>{{{{.ref {expected_name}}}}}</p>",
        )
