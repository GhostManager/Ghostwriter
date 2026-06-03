# Django Imports
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0003_service_token_project_access_views"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.AddField(
            model_name="apikey",
            name="identifier",
            field=models.UUIDField(editable=False, null=True),
        ),
        migrations.AddField(
            model_name="apikey",
            name="secret_hash",
            field=models.CharField(
                blank=True, editable=False, max_length=255, null=True
            ),
        ),
        migrations.AddField(
            model_name="apikey",
            name="token_prefix",
            field=models.CharField(
                blank=True,
                db_index=True,
                editable=False,
                max_length=24,
                null=True,
                unique=True,
            ),
        ),
        migrations.AlterField(
            model_name="apikey",
            name="token",
            field=models.TextField(blank=True, default="", editable=False),
        ),
    ]
