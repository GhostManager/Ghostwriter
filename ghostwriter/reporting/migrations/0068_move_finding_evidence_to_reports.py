from django.db import migrations


REFERENCE_FIELDS = [
    "affected_entities",
    "description",
    "impact",
    "mitigation",
    "replication_steps",
    "host_detection_techniques",
    "network_detection_techniques",
    "references",
]


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


def update_source_finding_references(finding, old_name, new_name):
    old_token = f"{{{{.{old_name}}}}}"
    old_ref_token = f"{{{{.ref {old_name}}}}}"
    new_token = f"{{{{.{new_name}}}}}"
    new_ref_token = f"{{{{.ref {new_name}}}}}"
    changed = False

    for field_name in REFERENCE_FIELDS:
        current = getattr(finding, field_name)
        if not current:
            continue

        updated = current.replace(old_token, new_token).replace(old_ref_token, new_ref_token)
        if updated != current:
            setattr(finding, field_name, updated)
            changed = True

    if changed:
        finding.save(update_fields=REFERENCE_FIELDS)


def move_finding_evidence_to_reports(apps, schema_editor):
    Evidence = apps.get_model("reporting", "Evidence")
    ReportFindingLink = apps.get_model("reporting", "ReportFindingLink")

    used_names_by_report = {}
    report_evidences = (
        Evidence.objects.exclude(report_id=None)
        .order_by("report_id", "id")
        .values_list("report_id", "friendly_name")
    )
    for report_id, friendly_name in report_evidences:
        used_names_by_report.setdefault(report_id, set()).add(friendly_name)

    finding_evidences = Evidence.objects.exclude(finding_id=None).order_by("id")
    for evidence in finding_evidences:
        finding = ReportFindingLink.objects.only(
            "id",
            "report_id",
            *REFERENCE_FIELDS,
        ).get(id=evidence.finding_id)

        if finding.report_id is None:
            raise ValueError(
                f"Cannot migrate evidence {evidence.id}: finding {finding.id} has no report."
            )

        used_names = used_names_by_report.setdefault(finding.report_id, set())
        new_name = evidence.friendly_name
        update_fields = ["finding", "report"]

        if new_name in used_names:
            new_name = get_unique_friendly_name(evidence.friendly_name, used_names, evidence.id)
            update_source_finding_references(finding, evidence.friendly_name, new_name)
            evidence.friendly_name = new_name
            update_fields.append("friendly_name")

        used_names.add(new_name)
        evidence.finding_id = None
        evidence.report_id = finding.report_id
        evidence.save(update_fields=update_fields)


class Migration(migrations.Migration):
    dependencies = [
        ("reporting", "0067_alter_reporttemplate_evidence_image_width"),
    ]

    operations = [
        migrations.RunPython(move_finding_evidence_to_reports, migrations.RunPython.noop),
    ]
