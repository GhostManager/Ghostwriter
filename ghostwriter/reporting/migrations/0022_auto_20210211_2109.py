# Generated by Django 3.0.10 on 2021-02-11 21:09

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0021_auto_20201119_2343"),
    ]

    operations = [
        migrations.AlterField(
            model_name="report",
            name="last_update",
            field=models.DateField(
                auto_now=True, help_text="Date the report was last touched", verbose_name="Last Update"
            ),
        ),
    ]
