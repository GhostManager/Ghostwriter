# Standard Libraries
from datetime import date, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory

# Django Imports
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase, override_settings


def restore_latest_migrations():
    """Return the shared test database to the current migration state."""
    executor = MigrationExecutor(connection)
    executor.migrate(executor.loader.graph.leaf_nodes())


class FindingEvidenceMigrationTests(TransactionTestCase):
    """Verify finding-owned evidence is moved to report ownership."""

    migrate_from = [("reporting", "0067_alter_reporttemplate_evidence_image_width")]
    migrate_to = [("reporting", "0069_remove_finding_evidence")]

    def setUp(self):
        super().setUp()
        self.media_root_context = TemporaryDirectory()
        self.override = override_settings(MEDIA_ROOT=self.media_root_context.name)
        self.override.enable()

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        self.setUpBeforeMigration(old_apps)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        restore_latest_migrations()
        self.override.disable()
        self.media_root_context.cleanup()
        super().tearDown()

    def create_media_file(self, document_name, content):
        path = Path(self.media_root_context.name) / document_name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return str(path)

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
            description="<p>{{.Collision}}</p><p>{{ .Collision }}</p>",
            impact="<p>{{.ref Collision}}</p><p>{{ .ref Collision }}</p><p>{{.ref   Collision }}</p>",
            mitigation="<p>{{ .caption Collision }}</p>",
            extra_fields={
                "rich_text_direct": "<p>{{.Collision}}</p><p>{{ .Collision }}</p>",
                "rich_text_ref": "<p>{{ .ref Collision }}</p>",
                "rich_text_caption": "<p>{{ .caption Collision }}</p>",
                "nested": {
                    "rich_text": "<p>{{.ref   Collision }}</p>",
                    "plain": "No evidence token here",
                },
                "list": ["{{.Collision}}", 42, None],
            },
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
        self.report_filename_collision = Evidence.objects.create(
            report=self.report,
            friendly_name="Report Filename Collision",
            document=f"evidence/{self.report.pk}/filename-collision.txt",
        )
        self.finding_filename_collision = Evidence.objects.create(
            finding=self.finding,
            friendly_name="Finding Filename Collision",
            document=f"evidence/{self.report.pk}/filename-collision_abc123.txt",
        )

        self.report_filename_collision_document = self.report_filename_collision.document.name
        self.finding_filename_collision_document = self.finding_filename_collision.document.name
        self.report_filename_collision_path = self.create_media_file(
            self.report_filename_collision_document,
            b"existing report evidence",
        )
        self.finding_filename_collision_path = self.create_media_file(
            self.finding_filename_collision_document,
            b"finding evidence",
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
            f"<p>{{{{.{expected_name}}}}}</p><p>{{{{.{expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.impact,
            f"<p>{{{{.ref {expected_name}}}}}</p><p>{{{{.ref {expected_name}}}}}</p>"
            f"<p>{{{{.ref {expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.mitigation,
            f"<p>{{{{.caption {expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.extra_fields["rich_text_direct"],
            f"<p>{{{{.{expected_name}}}}}</p><p>{{{{.{expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.extra_fields["rich_text_ref"],
            f"<p>{{{{.ref {expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.extra_fields["rich_text_caption"],
            f"<p>{{{{.caption {expected_name}}}}}</p>",
        )
        self.assertEqual(
            finding.extra_fields["nested"]["rich_text"],
            f"<p>{{{{.ref {expected_name}}}}}</p>",
        )
        self.assertEqual(finding.extra_fields["nested"]["plain"], "No evidence token here")
        self.assertEqual(finding.extra_fields["list"], [f"{{{{.{expected_name}}}}}", 42, None])

    def test_historical_finding_evidence_in_report_directory_is_preserved(self):
        report_prefix = f"evidence/{self.report.pk}/"

        self.assertTrue(self.finding_filename_collision_document.startswith(report_prefix))
        self.assertTrue(self.report_filename_collision_document.startswith(report_prefix))

    def test_filename_collision_is_already_resolved_by_storage_and_preserved(self):
        Evidence = self.apps.get_model("reporting", "Evidence")

        report_evidence = Evidence.objects.get(pk=self.report_filename_collision.pk)
        migrated_evidence = Evidence.objects.get(pk=self.finding_filename_collision.pk)

        self.assertEqual(report_evidence.document.name, self.report_filename_collision_document)
        self.assertEqual(migrated_evidence.document.name, self.finding_filename_collision_document)
        self.assertNotEqual(report_evidence.document.name, migrated_evidence.document.name)
        self.assertEqual(migrated_evidence.report_id, self.report.pk)

        report_path = Path(self.report_filename_collision_path)
        migrated_path = Path(self.finding_filename_collision_path)
        self.assertTrue(report_path.exists())
        self.assertTrue(migrated_path.exists())
        self.assertEqual(report_path.read_bytes(), b"existing report evidence")
        self.assertEqual(migrated_path.read_bytes(), b"finding evidence")


class EvidenceFriendlyNameConstraintMigrationTests(TransactionTestCase):
    """Verify report evidence friendly names are unique at the database level."""

    migrate_from = [("reporting", "0069_remove_finding_evidence")]
    migrate_to = [("reporting", "0070_evidence_unique_report_friendly_name")]

    def setUp(self):
        super().setUp()

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_from)
        old_apps = self.executor.loader.project_state(self.migrate_from).apps
        self.setUpBeforeMigration(old_apps)

        self.executor = MigrationExecutor(connection)
        self.executor.migrate(self.migrate_to)
        self.apps = self.executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        restore_latest_migrations()
        super().tearDown()

    def setUpBeforeMigration(self, apps):
        Client = apps.get_model("rolodex", "Client")
        Project = apps.get_model("rolodex", "Project")
        ProjectType = apps.get_model("rolodex", "ProjectType")
        Report = apps.get_model("reporting", "Report")
        Evidence = apps.get_model("reporting", "Evidence")

        client = Client.objects.create(name="Unique Constraint Client")
        project_type = ProjectType.objects.create(project_type="Unique Constraint Test")
        project = Project.objects.create(
            client=client,
            project_type=project_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )
        self.report = Report.objects.create(project=project, title="Constraint Report")
        self.other_report = Report.objects.create(project=project, title="Other Constraint Report")
        self.first_duplicate = Evidence.objects.create(
            report=self.report,
            friendly_name="Duplicate",
            document="evidence/duplicate-one.txt",
        )
        self.second_duplicate = Evidence.objects.create(
            report=self.report,
            friendly_name="Duplicate",
            document="evidence/duplicate-two.txt",
        )
        self.other_report_duplicate = Evidence.objects.create(
            report=self.other_report,
            friendly_name="Duplicate",
            document="evidence/other-report-duplicate.txt",
        )

    def test_duplicate_friendly_names_are_deconflicted_before_constraint(self):
        Evidence = self.apps.get_model("reporting", "Evidence")

        first_duplicate = Evidence.objects.get(pk=self.first_duplicate.pk)
        second_duplicate = Evidence.objects.get(pk=self.second_duplicate.pk)
        other_report_duplicate = Evidence.objects.get(pk=self.other_report_duplicate.pk)

        self.assertEqual(first_duplicate.friendly_name, "Duplicate")
        self.assertEqual(
            second_duplicate.friendly_name,
            f"Duplicate (evidence {self.second_duplicate.pk})",
        )
        self.assertEqual(other_report_duplicate.friendly_name, "Duplicate")

    def test_database_rejects_duplicate_friendly_name_for_same_report(self):
        Evidence = self.apps.get_model("reporting", "Evidence")

        with self.assertRaises(IntegrityError):
            with transaction.atomic():
                Evidence.objects.create(
                    report_id=self.report.pk,
                    friendly_name="Duplicate",
                    document="evidence/new-duplicate.txt",
                )

        Evidence.objects.create(
            report_id=self.other_report.pk,
            friendly_name=f"Duplicate (evidence {self.second_duplicate.pk})",
            document="evidence/new-other-report-duplicate.txt",
        )
