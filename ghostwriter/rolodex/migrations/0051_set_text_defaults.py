
from django.db import migrations

FIELDS = [
    ('rolodex_client', 'address'),
    ('rolodex_client', 'codename'),
    ('rolodex_client', 'note'),
    ('rolodex_client', 'short_name'),
    ('rolodex_clientcontact', 'email'),
    ('rolodex_clientcontact', 'job_title'),
    ('rolodex_clientcontact', 'note'),
    ('rolodex_clientcontact', 'phone'),
    ('rolodex_clientinvite', 'comment'),
    ('rolodex_clientnote', 'note'),
    ('rolodex_deconfliction', 'alert_source'),
    ('rolodex_deconfliction', 'description'),
    ('rolodex_project', 'codename'),
    ('rolodex_project', 'note'),
    ('rolodex_project', 'slack_channel'),
    ('rolodex_projectassignment', 'note'),
    ('rolodex_projectcontact', 'email'),
    ('rolodex_projectcontact', 'job_title'),
    ('rolodex_projectcontact', 'note'),
    ('rolodex_projectcontact', 'phone'),
    ('rolodex_projectinvite', 'comment'),
    ('rolodex_projectnote', 'note'),
    ('rolodex_projectobjective', 'description'),
    ('rolodex_projectobjective', 'objective'),
    ('rolodex_projectscope', 'description'),
    ('rolodex_projectscope', 'name'),
    ('rolodex_projectscope', 'scope'),
    ('rolodex_projectsubtask', 'task'),
    ('rolodex_projecttarget', 'hostname'),
    ('rolodex_projecttarget', 'ip_address'),
    ('rolodex_projecttarget', 'note'),
    ('rolodex_whitecard', 'description'),
    ('rolodex_whitecard', 'title'),
]

SQL_UP = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" SET DEFAULT '';" for (table, column) in FIELDS)
SQL_DOWN = "\n".join(f"ALTER TABLE \"{table}\" ALTER COLUMN \"{column}\" DROP DEFAULT;" for (table, column) in FIELDS)

class Migration(migrations.Migration):

    dependencies = [
        ('rolodex', '0050_auto_20240516_1722'),
    ]

    operations = [
        migrations.RunSQL(SQL_UP, reverse_sql=SQL_DOWN),
    ]
