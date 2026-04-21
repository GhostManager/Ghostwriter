from django.db import migrations, models

import ghostwriter.commandcenter.models


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0061_projectrole_position_ordering"),
    ]

    operations = [
        migrations.AlterField(
            model_name="project",
            name="bloodhound_api_key_id",
            field=models.CharField(
                blank=True,
                default="",
                help_text="The ID portion of a BloodHound API Key",
                max_length=255,
                null=True,
                verbose_name="BloodHound API Key ID",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="bloodhound_api_key_token",
            field=models.CharField(
                blank=True,
                default="",
                help_text="The token portion of a BloodHound API Key",
                max_length=255,
                null=True,
                verbose_name="BloodHound API Key Token",
            ),
        ),
        migrations.AlterField(
            model_name="project",
            name="bloodhound_api_root_url",
            field=models.CharField(
                blank=True,
                default="",
                help_text="The URL of the BloodHound instance",
                max_length=255,
                null=True,
                validators=[ghostwriter.commandcenter.models.validate_endpoint],
                verbose_name="BloodHound API URL",
            ),
        ),
    ]
