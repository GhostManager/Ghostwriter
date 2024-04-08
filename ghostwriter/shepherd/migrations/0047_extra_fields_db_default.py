from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('shepherd', '0046_staticserver_extra_fields'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE shepherd_domain ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE shepherd_domain ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE shepherd_staticserver ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE shepherd_staticserver ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
    ]
