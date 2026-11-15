"""
Protect report image sizes for Django and direct GraphQL/SQL writers.
"""

# Django Imports
from django.db import migrations, models


def normalize_report_widths(apps, schema_editor):
    """
    Reset invalid existing size pairs to the backward-compatible full width.
    """
    evidence = apps.get_model("reporting", "Evidence")
    valid_width = (
        models.Q(report_width_unit="", report_width_value__isnull=True)
        | models.Q(
            report_width_unit="percent",
            report_width_value__isnull=False,
            report_width_value__gte=1,
            report_width_value__lte=100,
        )
        | models.Q(
            report_width_unit="px",
            report_width_value__isnull=False,
            report_width_value__gte=1,
        )
    )
    evidence.objects.using(schema_editor.connection.alias).exclude(valid_width).update(
        report_width_unit="", report_width_value=None
    )


class Migration(migrations.Migration):
    dependencies = [("reporting", "0073_evidence_report_width")]

    operations = [
        migrations.RunPython(normalize_report_widths, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="evidence",
            name="report_width_unit",
            field=models.CharField(
                blank=True,
                choices=[("percent", "Percent of evidence width"), ("px", "Pixels")],
                db_default="",
                default="",
                help_text="Shrink an image in the report by a percentage of the evidence width or to a width in pixels",
                max_length=10,
                verbose_name="Report Size Unit",
            ),
        ),
        migrations.AddConstraint(
            model_name="evidence",
            constraint=models.CheckConstraint(
                condition=(
                    models.Q(report_width_unit="", report_width_value__isnull=True)
                    | models.Q(
                        report_width_unit="percent",
                        report_width_value__isnull=False,
                        report_width_value__gte=1,
                        report_width_value__lte=100,
                    )
                    | models.Q(
                        report_width_unit="px",
                        report_width_value__isnull=False,
                        report_width_value__gte=1,
                    )
                ),
                name="reporting_evidence_valid_report_width",
            ),
        ),
    ]
