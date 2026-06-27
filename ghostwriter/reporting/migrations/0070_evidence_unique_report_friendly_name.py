from django.db import migrations, models


CONSTRAINT_NAME = "reporting_evidence_unique_report_friendly_name"


def get_unique_friendly_name(original_name, used_names, evidence_id):
    suffix = f" (evidence {evidence_id})"
    max_base_length = 255 - len(suffix)
    base_name = original_name[:max_base_length]
    new_name = f"{base_name}{suffix}"
    counter = 2

    while new_name in used_names:
        suffix = f" (evidence {evidence_id}-{counter})"
        max_base_length = 255 - len(suffix)
        base_name = original_name[:max_base_length]
        new_name = f"{base_name}{suffix}"
        counter += 1

    return new_name


def deconflict_report_evidence_friendly_names(apps, schema_editor):
    Evidence = apps.get_model("reporting", "Evidence")

    with schema_editor.connection.cursor() as cursor:
        cursor.execute("ALTER TABLE reporting_evidence DISABLE TRIGGER USER;")
    try:
        used_names_by_report = {}
        evidences = Evidence.objects.order_by("report_id", "id").only("id", "report_id", "friendly_name")
        for evidence in evidences.iterator():
            used_names = used_names_by_report.setdefault(evidence.report_id, set())
            friendly_name = evidence.friendly_name

            if friendly_name in used_names:
                friendly_name = get_unique_friendly_name(friendly_name, used_names, evidence.id)
                evidence.friendly_name = friendly_name
                evidence.save(update_fields=["friendly_name"])

            used_names.add(friendly_name)
    finally:
        with schema_editor.connection.cursor() as cursor:
            cursor.execute("ALTER TABLE reporting_evidence ENABLE TRIGGER USER;")


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0069_remove_finding_evidence"),
    ]

    operations = [
        migrations.RunPython(deconflict_report_evidence_friendly_names, migrations.RunPython.noop),
        migrations.SeparateDatabaseAndState(
            database_operations=[
                migrations.RunSQL(
                    sql=(
                        f"ALTER TABLE reporting_evidence "
                        f"ADD CONSTRAINT {CONSTRAINT_NAME} UNIQUE (report_id, friendly_name);"
                    ),
                    reverse_sql=f"ALTER TABLE reporting_evidence DROP CONSTRAINT {CONSTRAINT_NAME};",
                ),
            ],
            state_operations=[
                migrations.AddConstraint(
                    model_name="evidence",
                    constraint=models.UniqueConstraint(
                        fields=("report", "friendly_name"),
                        name=CONSTRAINT_NAME,
                    ),
                ),
            ],
        ),
    ]
