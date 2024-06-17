from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('oplog', '0014_merge_20231215_1939'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE oplog_oplogentry ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE oplog_oplogentry ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
    ]
