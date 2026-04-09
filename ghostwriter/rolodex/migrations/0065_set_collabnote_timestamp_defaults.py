"""Set database-level defaults for collab note timestamp columns.

Django 4.2's ``default=timezone.now`` only applies at the ORM level.
Hasura and the collab server insert rows directly, bypassing the ORM,
so database-level defaults are required.
"""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("rolodex", "0064_alter_projectcollabnote_id_and_more"),
    ]

    operations = [
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnote ALTER COLUMN created_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnote ALTER COLUMN created_at DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnote ALTER COLUMN updated_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnote ALTER COLUMN updated_at DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN created_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN created_at DROP DEFAULT;",
        ),
        migrations.RunSQL(
            sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN updated_at SET DEFAULT NOW();",
            reverse_sql="ALTER TABLE rolodex_projectcollabnotefield ALTER COLUMN updated_at DROP DEFAULT;",
        ),
    ]
