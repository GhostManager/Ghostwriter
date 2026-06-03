# Standard Libraries
import uuid

# Django Imports
from django.db import migrations

# This migration intentionally contains only data updates. The following migration
# adds the unique constraint after PostgreSQL has committed these row changes.


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
        ("api", "0004_apikey_opaque_tokens_and_user_sessions"),
    ]

    operations = [
        migrations.RunPython(
            blank_legacy_api_key_tokens,
            reverse_code=migrations.RunPython.noop,
        ),
        migrations.RunPython(
            populate_api_key_identifiers,
            reverse_code=migrations.RunPython.noop,
        )
    ]
