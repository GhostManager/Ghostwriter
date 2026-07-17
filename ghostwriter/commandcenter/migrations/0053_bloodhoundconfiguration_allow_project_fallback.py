from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("commandcenter", "0052_alter_bannerconfiguration_banner_link"),
    ]

    operations = [
        migrations.AddField(
            model_name="bloodhoundconfiguration",
            name="allow_project_fallback",
            field=models.BooleanField(
                default=False,
                help_text="Allow projects without their own BloodHound settings to use this shared configuration and its cached results",
                verbose_name="Allow Projects to Use Shared Configuration",
            ),
        ),
    ]
