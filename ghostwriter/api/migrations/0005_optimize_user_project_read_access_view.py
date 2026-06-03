# Standard Libraries
import uuid

# Django Imports
from django.db import migrations

# This migration intentionally contains only data updates. The following migration
# adds the unique constraint after PostgreSQL has committed these row changes.

API_KEY_IDENTIFIER_BATCH_SIZE = 1000


def populate_api_key_identifiers(apps, schema_editor):
    APIKey = apps.get_model("api", "APIKey")
    api_keys = []
    queryset = APIKey.objects.filter(identifier__isnull=True).only(
        "id", "identifier"
    )
    for api_key in queryset.iterator(chunk_size=API_KEY_IDENTIFIER_BATCH_SIZE):
        api_key.identifier = uuid.uuid4()
        api_keys.append(api_key)
        if len(api_keys) >= API_KEY_IDENTIFIER_BATCH_SIZE:
            APIKey.objects.bulk_update(
                api_keys,
                ["identifier"],
                batch_size=API_KEY_IDENTIFIER_BATCH_SIZE,
            )
            api_keys.clear()

    if api_keys:
        APIKey.objects.bulk_update(
            api_keys,
            ["identifier"],
            batch_size=API_KEY_IDENTIFIER_BATCH_SIZE,
        )


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
        ),
    ]
