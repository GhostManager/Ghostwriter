"""Default schemas and helpers for normalizing workbook content."""

# Standard Libraries
from __future__ import annotations

from copy import deepcopy
from typing import Any, Dict, Mapping, MutableMapping, Optional, Sequence, Set

WORKBOOK_META_KEY = "__meta__"
WORKBOOK_META_SECTIONS_KEY = "uploaded_sections"


def _deepcopy(value: Any) -> Any:
    """Return a deep copy for containers while leaving scalars untouched."""

    if isinstance(value, (dict, list, set, tuple)):
        return deepcopy(value)
    return value


def _merge_structure(source: Optional[Mapping[str, Any]], template: Mapping[str, Any]) -> Dict[str, Any]:
    """Return ``source`` with ``template`` defaults applied recursively."""

    result: Dict[str, Any] = dict(source or {})
    for key, default_value in template.items():
        existing_value = result.get(key)
        if isinstance(default_value, Mapping):
            if not isinstance(existing_value, Mapping):
                existing_value = {}
            result[key] = _merge_structure(existing_value, default_value)
        elif isinstance(default_value, list):
            if isinstance(existing_value, list):
                result[key] = list(existing_value)
            else:
                result[key] = []
        else:
            if key not in result:
                result[key] = _deepcopy(default_value)
    return result


def _has_meaningful_data(value: Any) -> bool:
    """Return ``True`` if ``value`` contains data supplied by the workbook upload."""

    if value in (None, "", [], {}):
        return False
    if isinstance(value, Mapping):
        return any(_has_meaningful_data(item) for item in value.values())
    if isinstance(value, (list, tuple, set)):
        return any(_has_meaningful_data(item) for item in value)
    return True


WORKBOOK_DEFAULTS: Dict[str, Any] = {
    "client": {"name": None, "short_name": None},
    "area_updates": {},
    "report_card": {
        "external": None,
        "internal": None,
        "wireless": None,
        "firewall": None,
        "overall": None,
    },
    "external_internal_grades": {
        "external": {
            "osint": {"score": None, "risk": None},
            "dns": {"score": None, "risk": None},
            "nexpose": {"score": None, "risk": None},
            "web": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
        "internal": {
            "iam": {"score": None, "risk": None},
            "iot_iomt": {"score": None, "risk": None},
            "password": {"score": None, "risk": None},
            "nexpose": {"score": None, "risk": None},
            "endpoint": {"score": None, "risk": None},
            "snmp": {"score": None, "risk": None},
            "sql": {"score": None, "risk": None},
            "cloud": {"score": None, "risk": None},
            "configuration": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
        "iam": {
            "ad": {"score": None, "risk": None},
            "password": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
        "wireless": {
            "walkthru": {"score": None, "risk": None},
            "segmentation": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
        "firewall": {
            "os": {"score": None, "risk": None},
            "configuration": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
        "cloud": {
            "cloud_management": {"score": None, "risk": None},
            "iam_management": {"score": None, "risk": None},
            "system_configuration": {"score": None, "risk": None},
            "total": None,
            "grade": None,
        },
    },
    "general": {
        "external_start": None,
        "external_end": None,
        "internal_start": None,
        "internal_end": None,
        "cloud_start": None,
        "cloud_end": None,
        "wireless": None,
        "firewall": None,
        "internal_subnets": None,
        "cloud_provider": None,
    },
    "osint": {
        "total_domains": None,
        "total_hostnames": None,
        "total_ips": None,
        "total_cloud": None,
        "total_buckets": None,
        "total_squat": None,
        "total_leaks": None,
    },
    "dns": {"records": [], "unique": None},
    "external_nexpose": {
        "total": None,
        "total_high": None,
        "total_med": None,
        "total_low": None,
        "unique": None,
        "unique_high_med": None,
        "host_counts": [],
        "top_hosts": [],
        "top_hosts_high": None,
        "top_hosts_med": None,
        "top_hosts_low": None,
        "top_hosts_total": None,
        "majority_type": None,
        "unique_majority": None,
        "unique_majority_sub": None,
        "unique_majority_sub_info": None,
        "minority_type": None,
        "unique_minority": None,
    },
    "web": {
        "sites": [],
        "combined_unique": None,
        "combined_unique_high": None,
        "combined_unique_med": None,
        "combined_unique_low": None,
    },
    "firewall": {
        "devices": [],
        "unique": None,
        "unique_high": None,
        "unique_med": None,
        "unique_low": None,
        "majority_type": None,
        "majority_count": None,
        "minority_type": None,
        "minority_count": None,
        "complexity_count": None,
    },
    "ad": {"domains": []},
    "password": {"policies": []},
    "internal_nexpose": {
        "total": None,
        "total_high": None,
        "total_med": None,
        "total_low": None,
        "unique": None,
        "unique_high_med": None,
        "host_counts": [],
        "top_hosts": [],
        "top_hosts_high": None,
        "top_hosts_med": None,
        "top_hosts_low": None,
        "top_hosts_total": None,
        "majority_type": None,
        "unique_majority": None,
        "unique_majority_sub": None,
        "unique_majority_sub_info": None,
        "minority_type": None,
        "unique_minority": None,
    },
    "iot_iomt_nexpose": {
        "total": None,
        "total_high": None,
        "total_med": None,
        "total_low": None,
        "unique": None,
        "unique_high_med": None,
        "host_counts": [],
        "top_hosts": [],
        "top_hosts_high": None,
        "top_hosts_med": None,
        "top_hosts_low": None,
        "top_hosts_total": None,
        "majority_type": None,
        "unique_majority": None,
        "unique_majority_sub": None,
        "unique_majority_sub_info": None,
        "minority_type": None,
        "unique_minority": None,
    },
    "endpoint": {"domains": []},
    "snmp": {
        "total_strings": None,
        "total_systems": None,
        "read_write_access": None,
        "subnets": None,
    },
    "sql": {
        "total_open": None,
        "weak_creds": None,
        "unsupported_dbs": {"confirm": None, "count": None},
        "db_types": None,
        "subnets": None,
    },
    "wireless": {
        "open_count": None,
        "psk_count": None,
        "hidden_count": None,
        "rogue_count": None,
        "rogue_signals": None,
        "weak_psks": None,
        "wep_inuse": {"confirm": None, "key_cracked": None},
        "internal_access": None,
        "802_1x_used": None,
    },
    "cloud_config": {"pass": None, "fail": None},
    "iam_cloud_config": {"pass": None, "fail": None},
    "system_config": {
        "total_pass": None,
        "total_fail": None,
        "unique_pass": None,
        "unique_fail": None,
    },
}


DATA_RESPONSES_DEFAULTS: Dict[str, Any] = {
    "general": {
        "assessment_scope": [],
        "assessment_scope_cloud_on_prem": None,
        "general_first_ca": None,
        "general_scope_changed": None,
        "general_anonymous_ephi": None,
        "scope_count": None,
        "scope_string": None,
    },
    "iot_iomt": {"iot_testing_confirm": None},
    "intelligence": {
        "osint_squat_concern": None,
        "osint_bucket_risk": None,
        "osint_leaked_creds_risk": None,
    },
    "dns": {"entries": [], "unique_soa_fields": []},
    "firewall": {
        "firewall_periodic_reviews": None,
        "entries": [],
        "ood_count": 0,
        "ood_name_list": "",
    },
    "ad": {"entries": [], "old_domains_str": None},
    "password": {
        "password_additional_controls": None,
        "password_enforce_mfa_all_accounts": None,
        "hashes_obtained": None,
        "entries": [],
    },
    "endpoint": {
        "entries": [],
        "domains_str": None,
        "ood_count_str": None,
        "wifi_count_str": None,
        "ood_risk_string": None,
        "wifi_risk_string": None,
    },
    "wireless": {
        "open_risk": None,
        "psk_risk": None,
        "hidden_risk": None,
        "rogue_risk": None,
        "psk_rotation_concern": None,
        "psk_weak_reasons": None,
        "psk_masterpass": None,
        "psk_masterpass_ssids": [],
        "segmentation_tested": None,
        "segmentation_ssids": [],
        "wep_crack_minutes": None,
        "wep_ssids": [],
    },
    "cloud_configuration": {"cloud_config_risk": None},
    "system_configuration": {"system_config_risk": None},
    "overall_risk": {"major_issues": []},
}


def normalize_workbook_payload(raw_data: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return ``raw_data`` with default workbook keys populated."""

    normalized = _merge_structure(raw_data if isinstance(raw_data, Mapping) else {}, WORKBOOK_DEFAULTS)
    uploaded_sections = _detect_uploaded_sections(raw_data)
    normalized[WORKBOOK_META_KEY] = {WORKBOOK_META_SECTIONS_KEY: sorted(uploaded_sections)}
    return normalized


def _detect_uploaded_sections(raw_data: Optional[Mapping[str, Any]]) -> Set[str]:
    if not isinstance(raw_data, Mapping):
        return set()
    sections: Set[str] = set()
    for key, value in raw_data.items():
        if key == WORKBOOK_META_KEY:
            continue
        if (
            key in WORKBOOK_DEFAULTS
            and key not in {"area_updates"}
            and _has_meaningful_data(value)
        ):
            sections.add(str(key))
    return sections


def ensure_data_responses_defaults(responses: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    """Return ``responses`` with default data-response structure applied."""

    normalized = _merge_structure(responses if isinstance(responses, Mapping) else {}, DATA_RESPONSES_DEFAULTS)
    return normalized


def get_uploaded_sections(workbook_data: Optional[Mapping[str, Any]]) -> Set[str]:
    """Return the workbook sections supplied by the uploaded workbook."""

    if not isinstance(workbook_data, Mapping):
        return set()
    meta = workbook_data.get(WORKBOOK_META_KEY)
    if isinstance(meta, Mapping):
        stored_sections = meta.get(WORKBOOK_META_SECTIONS_KEY)
        if isinstance(stored_sections, Sequence):
            return {str(item) for item in stored_sections if isinstance(item, str)}
    return _detect_uploaded_sections(workbook_data)


def strip_workbook_meta(data: MutableMapping[str, Any]) -> None:
    """Remove metadata keys used for internal bookkeeping."""

    data.pop(WORKBOOK_META_KEY, None)

