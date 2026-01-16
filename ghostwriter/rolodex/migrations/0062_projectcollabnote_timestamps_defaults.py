# Add database-level defaults for timestamp columns
# This is needed because GraphQL/Hasura inserts bypass Django ORM

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("rolodex", "0061_migrate_collab_notes"),
    ]

    operations = [
        migrations.RunSQL(
            sql="""
                ALTER TABLE rolodex_projectcollabnote
                ALTER COLUMN created_at SET DEFAULT CURRENT_TIMESTAMP;

                ALTER TABLE rolodex_projectcollabnote
                ALTER COLUMN updated_at SET DEFAULT CURRENT_TIMESTAMP;
            """,
            reverse_sql="""
                ALTER TABLE rolodex_projectcollabnote
                ALTER COLUMN created_at DROP DEFAULT;

                ALTER TABLE rolodex_projectcollabnote
                ALTER COLUMN updated_at DROP DEFAULT;
            """,
        ),
    ]
