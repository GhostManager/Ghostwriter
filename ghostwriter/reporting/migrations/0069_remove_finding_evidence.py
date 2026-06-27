from importlib import import_module

from django.db import migrations, models
import django.db.models.deletion


previous_api_migration = import_module("ghostwriter.api.migrations.0007_service_token_user_access_view")


DROP_SERVICE_TOKEN_USER_ACCESS_VIEW = """
DROP VIEW IF EXISTS api_service_token_user_access;
"""


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0007_service_token_user_access_view"),
        ("reporting", "0068_move_finding_evidence_to_reports"),
    ]

    operations = [
        migrations.RunSQL(
            sql=DROP_SERVICE_TOKEN_USER_ACCESS_VIEW,
            reverse_sql=previous_api_migration.CREATE_SERVICE_TOKEN_USER_ACCESS_VIEW,
        ),
        migrations.RemoveConstraint(
            model_name="evidence",
            name="reporting_evidence_finding_or_report",
        ),
        migrations.AlterModelOptions(
            name="evidence",
            options={
                "ordering": ["report", "document"],
                "verbose_name": "Evidence",
                "verbose_name_plural": "Evidence",
            },
        ),
        migrations.AlterField(
            model_name="evidence",
            name="report",
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to="reporting.report"),
        ),
        migrations.RemoveField(
            model_name="evidence",
            name="finding",
        ),
    ]
