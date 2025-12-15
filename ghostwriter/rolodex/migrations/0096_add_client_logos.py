# Generated manually for adding client logo fields
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0095_project_ai_review"),
    ]

    operations = [
        migrations.AddField(
            model_name="client",
            name="logo",
            field=models.ImageField(
                blank=True,
                help_text="Upload a logo to be used for cover pages",
                null=True,
                upload_to="client_logos/",
                verbose_name="Client Logo",
            ),
        ),
        migrations.AddField(
            model_name="client",
            name="logo_header",
            field=models.ImageField(
                blank=True,
                help_text="Upload a logo to be used for report headers",
                null=True,
                upload_to="client_logos/headers/",
                verbose_name="Client Header Logo",
            ),
        ),
    ]
