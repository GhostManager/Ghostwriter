from django.db import migrations


class Migration(migrations.Migration):
    operations = [
        migrations.RunSQL(
            sql="DROP TABLE IF EXISTS health_check_db_testmodel;",
            reverse_sql=migrations.RunSQL.noop,
        ),
    ]
