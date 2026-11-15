"""
Database invariants for report sizing, including writers that bypass Django forms.
"""

# Standard Libraries
from datetime import date

# Django Imports
from django.db import IntegrityError, connection, transaction
from django.db.migrations.executor import MigrationExecutor
from django.test import TestCase, TransactionTestCase

# Ghostwriter Libraries
from ghostwriter.factories import EvidenceFactory
from ghostwriter.reporting.models import Evidence


class EvidenceReportWidthDatabaseTests(TestCase):
    """
    Enforce valid unit/value pairs for direct database and GraphQL writes.
    """

    @classmethod
    def setUpTestData(cls):
        cls.evidence = EvidenceFactory(document="")

    def test_invalid_pairs_are_rejected_without_model_validation(self):
        invalid = [
            ("", 50),
            ("percent", None),
            ("percent", 0),
            ("percent", 101),
            ("px", None),
            ("px", 0),
            ("inches", 1),
            ("inches", None),
        ]
        for index, (unit, value) in enumerate(invalid):
            with self.subTest(unit=unit, value=value):
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Evidence.objects.create(
                        report=self.evidence.report,
                        friendly_name=f"invalid-{index}",
                        report_width_unit=unit,
                        report_width_value=value,
                    )
                with self.assertRaises(IntegrityError), transaction.atomic():
                    Evidence.objects.filter(pk=self.evidence.pk).update(
                        report_width_unit=unit, report_width_value=value
                    )

    def test_valid_pairs_support_bulk_writes(self):
        valid = [("", None), ("percent", 1), ("percent", 100), ("px", 1), ("px", 5000)]
        objects = [
            Evidence(
                report=self.evidence.report,
                friendly_name=f"valid-{index}",
                report_width_unit=unit,
                report_width_value=value,
            )
            for index, (unit, value) in enumerate(valid)
        ]
        Evidence.objects.bulk_create(objects)
        for evidence, pair in zip(objects, valid):
            evidence.refresh_from_db()
            self.assertEqual(
                (evidence.report_width_unit, evidence.report_width_value), pair
            )

    def test_direct_sql_insert_can_omit_new_size_columns(self):
        with connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO reporting_evidence "
                "(document, friendly_name, caption, description, upload_date, report_id) "
                "VALUES (%s, %s, %s, %s, %s, %s) RETURNING id",
                ["", "legacy-sql-writer", "", "", date.today(), self.evidence.report_id],
            )
            evidence_id = cursor.fetchone()[0]
        evidence = Evidence.objects.get(pk=evidence_id)
        self.assertEqual(
            (evidence.report_width_unit, evidence.report_width_value), ("", None)
        )


class EvidenceReportWidthMigrationTests(TransactionTestCase):
    """
    Normalize invalid legacy sizes before enabling the database constraint.
    """

    def test_migration_preserves_valid_pairs_and_normalizes_invalid_pairs(self):
        report = EvidenceFactory(document="").report
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        previous = [("reporting", "0073_evidence_report_width")]
        try:
            executor.migrate(previous)
            old_evidence = executor.loader.project_state(previous).apps.get_model(
                "reporting", "Evidence"
            )
            cases = [
                ("", None, True),
                ("percent", 50, True),
                ("px", 640, True),
                ("", 50, False),
                ("percent", None, False),
                ("percent", 0, False),
                ("percent", 101, False),
                ("px", None, False),
                ("px", 0, False),
                ("inches", 1, False),
                ("inches", None, False),
            ]
            rows = [
                old_evidence.objects.create(
                    report_id=report.pk,
                    friendly_name=f"migration-{index}",
                    report_width_unit=unit,
                    report_width_value=value,
                )
                for index, (unit, value, _) in enumerate(cases)
            ]
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            for row, (unit, value, valid) in zip(rows, cases):
                with self.subTest(unit=unit, value=value):
                    evidence = Evidence.objects.get(pk=row.pk)
                    expected = (unit, value) if valid else ("", None)
                    self.assertEqual(
                        (evidence.report_width_unit, evidence.report_width_value),
                        expected,
                    )
        finally:
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
