from django.db import migrations


def protect_global_report_templates(apps, schema_editor):
    ReportTemplate = apps.get_model("reporting", "ReportTemplate")
    ReportTemplate.objects.filter(client_id__isnull=True).update(protected=True)


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0070_evidence_unique_report_friendly_name"),
    ]

    operations = [
        migrations.RunPython(
            protect_global_report_templates,
            migrations.RunPython.noop,
        ),
    ]
