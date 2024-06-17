
import re

from django.db import migrations, models

def migrate_fwd(apps, _schemas_editor):
    ReportConfiguration = apps.get_model("commandcenter", "ReportConfiguration")
    for obj in ReportConfiguration.objects.all():
        obj.report_filename = obj.report_filename.replace("{title}", "{{title}}")
        obj.report_filename = obj.report_filename.replace("{company}", "{{company_name}}")
        obj.report_filename = obj.report_filename.replace("{client}", "{{client.name}}")
        obj.report_filename = obj.report_filename.replace("{date}", "{{now|format_datetime}}")
        obj.report_filename = obj.report_filename.replace("{assessment_type}", "{{project.project_type}}")
        obj.report_filename = re.sub(r"(?<!{)\{([^\{}]+)\}", r'{{now|format_datetime:"\1"}}', obj.report_filename)
        obj.save()

def migrate_back(apps, _schemas_editor):
    ReportConfiguration = apps.get_model("commandcenter", "ReportConfiguration")
    for obj in ReportConfiguration.objects.all():
        obj.report_filename = obj.report_filename.replace("{{title}}", "{title}")
        obj.report_filename = obj.report_filename.replace("{{company_name}}", "{company}")
        obj.report_filename = obj.report_filename.replace("{{client.name}}", "{client}")
        obj.report_filename = obj.report_filename.replace("{{now|format_datetime}}", "{date}")
        obj.report_filename = obj.report_filename.replace("{{project.project_type}}", "{assessment_type}")
        obj.report_filename = re.sub(r'\{\{\s*now\|format_datetime:"([^"]*)"\s*\}\}', r'{\1}', obj.report_filename)
        obj.save()

class Migration(migrations.Migration):

    dependencies = [
        ('commandcenter', '0024_extrafieldspec_description'),
    ]

    operations = [
        migrations.AlterField(
            model_name='reportconfiguration',
            name='report_filename',
            field=models.CharField(default='{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report', help_text='Jinja2 template for report filenames. All template variables are available, plus {{now}} and {{company_name}}.', max_length=255, verbose_name='Default Name for Report Downloads'),
        ),
        migrations.RunPython(migrate_fwd, migrate_back)
    ]