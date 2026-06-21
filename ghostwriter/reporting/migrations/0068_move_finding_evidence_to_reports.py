import re

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


LEGACY_EVIDENCE_REFERENCE_RE = re.compile(r"\{\{\s*\.([^\{\}]*?)\s*\}\}")


def update_legacy_evidence_reference(match, old_name, new_name):
    contents = match.group(1).strip()
    if contents == old_name:
        return "{{." + new_name + "}}"
    if re.fullmatch(r"ref\s+" + re.escape(old_name), contents):
        return "{{.ref " + new_name + "}}"
    if re.fullmatch(r"caption\s+" + re.escape(old_name), contents):
        return "{{.caption " + new_name + "}}"
    return match.group(0)


def update_legacy_evidence_references_text(text, old_name, new_name):
    return LEGACY_EVIDENCE_REFERENCE_RE.sub(
        lambda match: update_legacy_evidence_reference(match, old_name, new_name),
        text,
    )


def update_extra_field_references(value, old_name, new_name):
    if isinstance(value, str):
        return update_legacy_evidence_references_text(value, old_name, new_name)
    if isinstance(value, list):
        return [update_extra_field_references(item, old_name, new_name) for item in value]
    if isinstance(value, dict):
        return {
            key: update_extra_field_references(item, old_name, new_name)
            for key, item in value.items()
        }
    return value


def update_source_finding_references(finding, old_name, new_name):
    update_fields = []

    for field_name in REFERENCE_FIELDS:
        current = getattr(finding, field_name)
        if not current:
            continue

        updated = update_legacy_evidence_references_text(current, old_name, new_name)
        if updated != current:
            setattr(finding, field_name, updated)
            update_fields.append(field_name)

    extra_fields = getattr(finding, "extra_fields", None)
    if extra_fields:
        updated_extra_fields = update_extra_field_references(extra_fields, old_name, new_name)
        if updated_extra_fields != extra_fields:
            finding.extra_fields = updated_extra_fields
            update_fields.append("extra_fields")

    if update_fields:
        finding.save(update_fields=update_fields)


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
    finding_ids = finding_evidences.values_list("finding_id", flat=True).distinct()
    findings_by_id = ReportFindingLink.objects.only(
        "id",
        "report_id",
        "extra_fields",
        *REFERENCE_FIELDS,
    ).in_bulk(finding_ids)

    for evidence in finding_evidences.iterator():
        finding = findings_by_id.get(evidence.finding_id)
        if finding is None:
            raise ValueError(
                f"Cannot migrate evidence {evidence.id}: finding {evidence.finding_id} does not exist."
            )

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
