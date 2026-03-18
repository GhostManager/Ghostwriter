# This migration was created in error during testing and is now a no-op.
# The work it originally attempted (making Report.project non-nullable) is
# correctly handled by 0063_set_report_field_defaults via a safe data migration.
# It is retained as an empty migration to preserve the dependency chain for any
# environment that has already recorded it as applied.

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0063_set_report_field_defaults"),
    ]

    operations = []
