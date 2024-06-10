
import re

from django.db import migrations, models

def migrate_fwd(apps, _schemas_editor):
    ReportConfiguration = apps.get_model("commandcenter", "ReportConfiguration")
    for obj in ReportConfiguration.objects.all():
        obj.report_filename = re.sub(r"format_datetime:\"([^\"]*)\"", "format_datetime(\"\\1\")", obj.report_filename)
        obj.save()

def migrate_back(apps, _schemas_editor):
    ReportConfiguration = apps.get_model("commandcenter", "ReportConfiguration")
    for obj in ReportConfiguration.objects.all():
        obj.report_filename = re.sub(r"format_datetime\(\"([^\"]*)\"\)", "format_datetime:\"\\1\"", obj.report_filename)
        obj.save()

class Migration(migrations.Migration):

    dependencies = [
        ('commandcenter', '0025_report_filename_template_convert'),
    ]

    operations = [
        migrations.RunPython(migrate_fwd, migrate_back)
    ]