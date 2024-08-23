
from django.db import migrations

FIELDS = [
    ("oplog_oplogentry", "command"),
    ("oplog_oplogentry", "comments"),
    ("oplog_oplogentry", "description"),
    ("oplog_oplogentry", "entry_identifier"),
    ("oplog_oplogentry", "output"),
]

SQL_UP = "\n".join(f"ALTER TABLE {table} ALTER COLUMN {column} SET DEFAULT '';" for (table, column) in FIELDS)
SQL_DOWN = "\n".join(f"ALTER TABLE {table} ALTER COLUMN {column} DROP DEFAULT;" for (table, column) in FIELDS)

class Migration(migrations.Migration):

    dependencies = [
        ('oplog', '0018_remove_oplogentry_oplog_fts'),
    ]

    operations = [
        migrations.RunSQL(SQL_UP, reverse_sql=SQL_DOWN),
    ]
