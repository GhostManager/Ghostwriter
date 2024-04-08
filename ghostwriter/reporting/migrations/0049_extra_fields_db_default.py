from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('reporting', '0048_auto_20240307_1831'),
    ]

    operations = [
        migrations.RunSQL(
            "ALTER TABLE reporting_finding ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE reporting_finding ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE reporting_report ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE reporting_report ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE reporting_reportfindinglink ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE reporting_reportfindinglink ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE reporting_observation ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE reporting_observation ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
        migrations.RunSQL(
            "ALTER TABLE reporting_reportobservationlink ALTER COLUMN extra_fields SET DEFAULT '{}'::jsonb;",
            "ALTER TABLE reporting_reportobservationlink ALTER COLUMN extra_fields DROP DEFAULT;"
        ),
    ]
