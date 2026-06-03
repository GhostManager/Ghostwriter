# Standard Libraries
import uuid

# Django Imports
import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


def populate_api_key_identifiers(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    for api_key in APIKey.objects.filter(identifier__isnull=True):
        api_key.identifier = uuid.uuid4()
        api_key.save(update_fields=["identifier"])


def blank_legacy_api_key_tokens(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    APIKey.objects.exclude(token="").update(token="")


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
        migrations.RunPython(
            blank_legacy_api_key_tokens,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_api_key_identifiers,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.AlterField(
            model_name="apikey",
            name="identifier",
            field=models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
        ),
        migrations.CreateModel(
            name="UserSession",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "identifier",
                    models.UUIDField(
                        default=uuid.uuid4, editable=False, unique=True
                    ),
                ),
                ("created", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("expires_at", models.DateTimeField(db_index=True)),
                (
                    "revoked_at",
                    models.DateTimeField(blank=True, db_index=True, null=True),
                ),
                (
                    "revoked_by",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="revoked_graphql_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="graphql_sessions",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ("-created",),
            },
        ),
    ]
