from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("commandcenter", "0045_merge_20251217_1544"),
    ]

    operations = [
        migrations.RenameField(
            model_name="openaiconfiguration",
            old_name="assistant_id",
            new_name="prompt_id",
        ),
    ]
