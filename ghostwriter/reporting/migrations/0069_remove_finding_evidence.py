from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0068_move_finding_evidence_to_reports"),
    ]

    operations = [
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
