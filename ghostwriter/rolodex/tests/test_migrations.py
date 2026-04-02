# Standard Libraries
from datetime import date, timedelta

# Django Imports
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ProjectRolePositionMigrationTests(TransactionTestCase):
    """Verify the ProjectRole ordering migration backfills and repairs data."""

    migrate_from = [("rolodex", "0060_alter_clientcontact_options_and_more")]
    migrate_to = [("rolodex", "0061_projectrole_position_ordering")]

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
        ProjectRole = apps.get_model("rolodex", "ProjectRole")
        ProjectAssignment = apps.get_model("rolodex", "ProjectAssignment")

        self.client = Client.objects.create(name="Migration Client")
        self.project_type = ProjectType.objects.create(project_type="Migration Test")
        self.project = Project.objects.create(
            client=self.client,
            project_type=self.project_type,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=1),
        )

        self.first_role = ProjectRole.objects.create(project_role="First Custom Role")
        self.second_role = ProjectRole.objects.create(project_role="Second Custom Role")
        self.assignment = ProjectAssignment.objects.create(
            project=self.project,
            start_date=self.project.start_date,
            end_date=self.project.end_date,
            role=None,
        )

    def test_migration_backfills_positions_and_assigns_missing_roles(self):
        ProjectRole = self.apps.get_model("rolodex", "ProjectRole")
        ProjectAssignment = self.apps.get_model("rolodex", "ProjectAssignment")

        self.assertEqual(
            list(ProjectRole.objects.order_by("position").values_list("project_role", "position")),
            [("First Custom Role", 1), ("Second Custom Role", 2)],
        )

        migrated_assignment = ProjectAssignment.objects.get(pk=self.assignment.pk)
        self.assertEqual(migrated_assignment.role.project_role, "First Custom Role")
