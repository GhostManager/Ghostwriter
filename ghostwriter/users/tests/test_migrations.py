# Django Imports
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class UserReportEmailMigrationTests(TransactionTestCase):
    """Preserve user data when either migration history joins the UI refresh."""

    baseline = [("users", "0013_remove_user_require_2fa_user_require_mfa")]
    report_email = ("users", "0017_user_report_email")
    ui_refresh = ("users", "0016_merge_ui_refresh_master")
    merged = [("users", "0018_merge_report_email_ui_refresh")]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.baseline)

    def tearDown(self):
        executor = MigrationExecutor(connection)
        executor.migrate(executor.loader.graph.leaf_nodes())
        super().tearDown()

    def migrate(self, targets):
        executor = MigrationExecutor(connection)
        executor.loader.check_consistent_history(connection)
        executor.migrate(targets)
        return executor.loader.project_state(targets).apps

    def test_master_upgrade_preserves_report_email_and_adds_preferences(self):
        old_apps = self.migrate([self.report_email])
        old_user = old_apps.get_model("users", "User").objects.create(
            username="master-operator",
            email="account@example.com",
            report_email="reports@example.com",
        )

        executor = MigrationExecutor(connection)
        self.assertNotIn(self.ui_refresh, executor.loader.applied_migrations)
        self.assertNotIn(
            self.report_email,
            [
                (migration.app_label, migration.name)
                for migration, _ in executor.migration_plan(self.merged)
            ],
        )

        apps = self.migrate(self.merged)
        user = apps.get_model("users", "User").objects.get(pk=old_user.pk)
        self.assertEqual(user.report_email, "reports@example.com")
        self.assertEqual(user.email, "account@example.com")
        self.assertEqual(user.sidebar_preferences, {})
        self.assertEqual(user.workspace_preferences, {})

    def test_ui_refresh_upgrade_preserves_report_email_and_preferences(self):
        old_apps = self.migrate([self.ui_refresh, self.report_email])
        old_user = old_apps.get_model("users", "User").objects.create(
            username="ui-operator",
            email="account@example.com",
            report_email="reports@example.com",
            sidebar_preferences={"version": 1, "pinned": ["reports"]},
            workspace_preferences={"version": 1, "report_ids": [42]},
        )

        executor = MigrationExecutor(connection)
        self.assertEqual(
            [
                ((migration.app_label, migration.name), backwards)
                for migration, backwards in executor.migration_plan(self.merged)
            ],
            [(self.merged[0], False)],
        )

        apps = self.migrate(self.merged)
        user = apps.get_model("users", "User").objects.get(pk=old_user.pk)
        self.assertEqual(user.report_email, "reports@example.com")
        self.assertEqual(user.email, "account@example.com")
        self.assertEqual(user.sidebar_preferences, old_user.sidebar_preferences)
        self.assertEqual(user.workspace_preferences, old_user.workspace_preferences)
