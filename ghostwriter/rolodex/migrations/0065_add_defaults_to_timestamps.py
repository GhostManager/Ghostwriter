# Generated migration to add database defaults for timestamps

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0064_migrate_note_content_to_fields"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN created_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN created_at DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN updated_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN updated_at DROP DEFAULT;",
        ),
    ]
