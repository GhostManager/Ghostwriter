from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('rolodex', '0048_merge_20240117_1537'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE rolodex_client ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE rolodex_client ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE rolodex_project ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE rolodex_project ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
    ]
