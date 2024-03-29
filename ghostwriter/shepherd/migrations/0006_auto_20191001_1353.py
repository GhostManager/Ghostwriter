# Generated by Django 2.2.3 on 2019-10-01 13:53

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("shepherd", "0005_auto_20191001_1352"),
    ]

    operations = [
        migrations.AlterField(
            model_name="history",
            name="activity_type",
            field=models.ForeignKey(
                help_text="Select the intended use of this domain",
                on_delete=django.db.models.deletion.PROTECT,
                to="shepherd.ActivityType",
            ),
        ),
    ]
