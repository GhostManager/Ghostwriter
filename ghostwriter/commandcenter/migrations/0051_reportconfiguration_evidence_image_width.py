from django.db import migrations, models
import django.core.validators


class Migration(migrations.Migration):
    dependencies = [
        ("commandcenter", "0050_reportconfiguration_evidence_image_alignment"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportconfiguration",
            name="evidence_image_width",
            field=models.FloatField(
                blank=True,
                default=None,
                help_text='Default width for inserted image evidence in Word reports. If left blank, 6.5" is used.',
                null=True,
                validators=[django.core.validators.MinValueValidator(0)],
                verbose_name="Default Evidence Image Width",
            ),
        ),
    ]
