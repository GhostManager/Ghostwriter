from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("commandcenter", "0049_alter_reportconfiguration_outline_tags"),
    ]

    operations = [
        migrations.AddField(
            model_name="reportconfiguration",
            name="evidence_image_alignment",
            field=models.CharField(
                choices=[
                    ("LEFT", "Left"),
                    ("CENTER", "Center"),
                    ("RIGHT", "Right"),
                ],
                default="CENTER",
                help_text="Default alignment for inserted image evidence in Word reports.",
                max_length=16,
                verbose_name="Default Image Evidence Alignment",
            ),
        ),
    ]
