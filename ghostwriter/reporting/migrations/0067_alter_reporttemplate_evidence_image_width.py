from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0066_reporttemplate_evidence_image_alignment"),
    ]

    operations = [
        migrations.AlterField(
            model_name="reporttemplate",
            name="evidence_image_width",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text="Override the global evidence image width for this template, in inches (Word only).",
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Evidence Image Width",
            ),
        ),
    ]
