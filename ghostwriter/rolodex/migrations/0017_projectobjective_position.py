# Generated by Django 3.0.10 on 2021-02-27 00:56

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0016_auto_20210224_0645"),
    ]

    operations = [
        migrations.AddField(
            model_name="projectobjective",
            name="position",
            field=models.IntegerField(default=1, verbose_name="List Position"),
        ),
    ]
