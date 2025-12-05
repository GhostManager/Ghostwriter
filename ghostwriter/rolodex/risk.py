"""Helpers for deriving project risk summaries from uploaded workbooks."""

from __future__ import annotations

from typing import Any, Dict, Iterable, Optional, Sequence

from django.apps import apps as django_apps
from django.db.models import Q

from ghostwriter.reporting.models import GradeRiskMapping


_WORKBOOK_RISK_PATHS: Dict[str, Sequence[Sequence[str]]] = {
    "osint": (("external_internal_grades", "external", "osint", "risk"),),
    "dns": (("external_internal_grades", "external", "dns", "risk"),),
    "external_nexpose": (("external_internal_grades", "external", "nexpose", "risk"),),
    "web": (("external_internal_grades", "external", "web", "risk"),),
    "cloud_config": (("external_internal_grades", "internal", "cloud", "risk"),),
    "system_config": (("external_internal_grades", "internal", "configuration", "risk"),),
    "internal_nexpose": (("external_internal_grades", "internal", "nexpose", "risk"),),
    "endpoint": (("external_internal_grades", "internal", "endpoint", "risk"),),
    "snmp": (("external_internal_grades", "internal", "snmp", "risk"),),
    "sql": (("external_internal_grades", "internal", "sql", "risk"),),
    "iam": (("external_internal_grades", "internal", "iam", "risk"),),
    "ad": (("external_internal_grades", "iam", "ad", "risk"),),
    "password": (
        ("external_internal_grades", "iam", "password", "risk"),
        ("external_internal_grades", "internal", "password", "risk"),
    ),
    "wireless": (("external_internal_grades", "wireless", "grade"),),
    "firewall": (("external_internal_grades", "firewall", "grade"),),
    "cloud": (("external_internal_grades", "internal", "cloud", "risk"),),
    "configuration": (("external_internal_grades", "internal", "configuration", "risk"),),
    "iam_management": (("external_internal_grades", "cloud", "iam_management", "risk"),),
    "cloud_management": (("external_internal_grades", "cloud", "cloud_management", "risk"),),
    "system_configuration": (
        ("external_internal_grades", "cloud", "system_configuration", "risk"),
    ),
    "iot_iomt_nexpose": (("external_internal_grades", "internal", "iot_iomt", "risk"),),
}

_GRADE_FIELD_MAP: Dict[str, Sequence[str]] = {
    "overall_risk": ("overall_grade", "overall"),
    "external": ("external_grade", "external"),
    "internal": ("internal_grade", "internal"),
    "wireless": ("wireless_grade", "wireless", "grade"),
    "firewall": ("firewall_grade", "firewall", "grade"),
}


def _get_nested_value(data: Any, path: Iterable[str]) -> Optional[Any]:
    current = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _normalize_risk(value: Any) -> Optional[str]:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    return text


def _collect_grade_sources(workbook_data: Dict[str, Any]) -> Sequence[Dict[str, Any]]:
    candidates: list[Dict[str, Any]] = []
    for key in ("report_card", "grades"):
        candidate = workbook_data.get(key)
        if isinstance(candidate, dict):
            candidates.append(candidate)
            nested = candidate.get("grades")
            if isinstance(nested, dict):
                candidates.append(nested)

    grade_section = workbook_data.get("external_internal_grades")
    if isinstance(grade_section, dict):
        for value in grade_section.values():
            if isinstance(value, dict):
                candidates.append(value)
    return candidates


def _resolve_grade_value(keys: Sequence[str], sources: Sequence[Dict[str, Any]]) -> Optional[Any]:
    for source in sources:
        for key in keys:
            value = source.get(key)
            if value not in (None, ""):
                return value
    return None


def build_project_risk_summary(workbook_data: Any) -> Dict[str, str]:
    """Return a mapping of risk values derived from ``workbook_data``."""

    if not isinstance(workbook_data, dict):
        return {}

    results: Dict[str, str] = {}

    for key, paths in _WORKBOOK_RISK_PATHS.items():
        for path in paths:
            raw_value = _get_nested_value(workbook_data, path)
            normalized = _normalize_risk(raw_value)
            if normalized:
                results[key] = normalized
                break

    grade_sources = _collect_grade_sources(workbook_data)
    grade_map = GradeRiskMapping.get_grade_map()

    for risk_key, grade_keys in _GRADE_FIELD_MAP.items():
        grade_value = _resolve_grade_value(grade_keys, grade_sources)
        if not grade_value:
            continue
        risk_slug = grade_map.get(str(grade_value).strip().upper())
        normalized = _normalize_risk(risk_slug)
        if normalized:
            results[risk_key] = normalized

    return results


def backfill_missing_project_risks(*, using: str = "default", batch_size: int = 200) -> int:
    """Populate stored risk summaries for existing projects missing this data.

    The helper is intended for upgrade paths where :class:`~ghostwriter.rolodex.models.Project`
    instances already contain workbook data but were saved before ``Project.risks`` was
    introduced. Projects that already have risk information recorded are left untouched.

    Parameters
    ----------
    using
        Database alias to operate against.
    batch_size
        Chunk size to use when iterating through projects.

    Returns
    -------
    int
        The number of projects whose risks were backfilled.
    """

    Project = django_apps.get_model("rolodex", "Project")

    queryset = (
        Project.objects.using(using)
        .exclude(workbook_data__isnull=True)
        .exclude(workbook_data={})
        .filter(Q(risks__isnull=True) | Q(risks={}))
    )

    updated = 0
    for project in queryset.iterator(chunk_size=batch_size):
        summary = build_project_risk_summary(getattr(project, "workbook_data", {}))
        if not summary:
            continue
        Project.objects.using(using).filter(pk=project.pk).update(risks=summary)
        updated += 1

    return updated
