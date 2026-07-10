# Django Imports
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ExtraFieldSpecPositionMigrationTests(TransactionTestCase):
    """Verify the ExtraFieldSpec ordering migration backfills positions per model."""

    migrate_from = [("commandcenter", "0045_reportconfiguration_default_cvss_version")]
    migrate_to = [("commandcenter", "0046_alter_extrafieldspec_options_extrafieldspec_position_and_more")]

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
        ExtraFieldModel = apps.get_model("commandcenter", "ExtraFieldModel")
        ExtraFieldSpec = apps.get_model("commandcenter", "ExtraFieldSpec")

        client_model = ExtraFieldModel.objects.create(
            model_internal_name="rolodex.Client",
            model_display_name="Clients",
        )
        report_model = ExtraFieldModel.objects.create(
            model_internal_name="reporting.Report",
            model_display_name="Reports",
        )

        self.client_first = ExtraFieldSpec.objects.create(
            target_model=client_model,
            internal_name="client_first",
            display_name="Client First",
            type="single_line_text",
        )
        self.client_second = ExtraFieldSpec.objects.create(
            target_model=client_model,
            internal_name="client_second",
            display_name="Client Second",
            type="single_line_text",
        )
        self.report_first = ExtraFieldSpec.objects.create(
            target_model=report_model,
            internal_name="report_first",
            display_name="Report First",
            type="single_line_text",
        )

    def test_migration_backfills_positions_from_legacy_order_per_model(self):
        ExtraFieldSpec = self.apps.get_model("commandcenter", "ExtraFieldSpec")

        self.assertEqual(
            list(
                ExtraFieldSpec.objects.filter(target_model="rolodex.Client")
                .order_by("position")
                .values_list("internal_name", "position")
            ),
            [("client_first", 1), ("client_second", 2)],
        )
        self.assertEqual(
            list(
                ExtraFieldSpec.objects.filter(target_model="reporting.Report")
                .order_by("position")
                .values_list("internal_name", "position")
            ),
            [("report_first", 1)],
        )
