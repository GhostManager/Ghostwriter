
from django.db import migrations

FIELDS = [
    ('shepherd_domain', 'burned_explanation'),
    ('shepherd_domain', 'note'),
    ('shepherd_domain', 'registrar'),
    ('shepherd_domain', 'vt_permalink'),
    ('shepherd_domainnote', 'note'),
    ('shepherd_domainserverconnection', 'endpoint'),
    ('shepherd_domainserverconnection', 'subdomain'),
    ('shepherd_history', 'note'),
    ('shepherd_serverhistory', 'note'),
    ('shepherd_servernote', 'note'),
    ('shepherd_staticserver', 'name'),
    ('shepherd_staticserver', 'note'),
    ('shepherd_transientserver', 'name'),
    ('shepherd_transientserver', 'note'),
]

SQL_UP = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" SET DEFAULT '';" for (table, column) in FIELDS)
SQL_DOWN = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" DROP DEFAULT;" for (table, column) in FIELDS)

class Migration(migrations.Migration):

    dependencies = [
        ('shepherd', '0048_auto_20240516_1722'),
    ]

    operations = [
        migrations.RunSQL(SQL_UP, reverse_sql=SQL_DOWN),
    ]
