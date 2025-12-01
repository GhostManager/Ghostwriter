"""Helpers for capturing workbook data via inline entry forms."""

from __future__ import annotations

from collections import OrderedDict
from copy import deepcopy
from decimal import Decimal
import math
from typing import Any, Dict, Mapping, MutableMapping, Optional

from ghostwriter.reporting.models import RiskScoreRangeMapping
from ghostwriter.rolodex.models import normalize_project_scoping
from ghostwriter.rolodex.workbook_defaults import normalize_workbook_payload


_SCORE_PRECISION = Decimal("0.1")
_SCORE_MIN = Decimal("0.0")
_SCORE_MAX = Decimal("6.0")

GENERAL_FIELDS = {
    "external_start",
    "external_end",
    "internal_start",
    "internal_end",
    "cloud_start",
    "cloud_end",
    "wireless",
    "firewall",
    "internal_subnets",
    "cloud_provider",
}

OSINT_FIELDS = {
    "total_domains",
    "total_hostnames",
    "total_ips",
    "total_cloud",
    "total_buckets",
    "total_squat",
    "total_leaks",
}

FIREWALL_SUMMARY_FIELDS = {
    "unique",
    "unique_high",
    "unique_med",
    "unique_low",
    "majority_type",
    "majority_count",
    "minority_type",
    "minority_count",
    "complexity_count",
}

AREA_FIELDS = {"osint": OSINT_FIELDS, "firewall": FIREWALL_SUMMARY_FIELDS}

AD_DOMAIN_COUNT_FIELDS = {
    "domain_admins",
    "ent_admins",
    "exp_passwords",
    "passwords_never_exp",
    "inactive_accounts",
    "generic_accounts",
    "old_passwords",
    "generic_logins",
    "enabled_accounts",
    "total_accounts",
}

AD_OLD_PASSWORD_COUNT_FIELDS = {
    "compliant",
    "30_days",
    "90_days",
    "180_days",
    "1_year",
    "2_year",
    "3_year",
    "never",
}

AD_INACTIVE_ACCOUNT_COUNT_FIELDS = {
    "active",
    "30_days",
    "90_days",
    "180_days",
    "1_year",
    "2_year",
    "3_year",
    "never",
}


def _as_decimal(value: Any) -> Optional[Decimal]:
    if value in (None, ""):
        return None
    try:
        decimal_value = Decimal(str(value)).quantize(_SCORE_PRECISION)
    except Exception:
        return None
    if decimal_value < _SCORE_MIN:
        return _SCORE_MIN
    if decimal_value > _SCORE_MAX:
        return _SCORE_MAX
    return decimal_value


def _score_to_risk(score: Optional[Decimal], score_map: Mapping[str, Any]) -> Optional[str]:
    if score is None:
        return None
    for risk, bounds in score_map.items():
        lower, upper = bounds
        if lower is None or upper is None:
            continue
        if lower <= score <= upper:
            return risk
    return None


def _as_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, (int, Decimal)):
        return int(value)
    if isinstance(value, float):
        if math.isnan(value):
            return None
        return int(value)
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return None
        try:
            return int(float(text))
        except ValueError:
            return None
    return None


def _normalize_general_payload(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    if not isinstance(payload, Mapping):
        return normalized
    for field in GENERAL_FIELDS:
        value = payload.get(field)
        if value in (None, ""):
            normalized[field] = None
        else:
            normalized[field] = str(value)
    return normalized


def _normalize_area_payload(area: str, payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}

    def _normalize_yes_no(value: Any) -> Optional[str]:
        if isinstance(value, bool):
            return "Yes" if value else "No"
        text = str(value).strip().lower()
        if not text:
            return None
        return "Yes" if text in {"yes", "y", "true", "1"} else "No"

    if area == "web":
        if isinstance(payload, Mapping):
            sites: list[dict[str, Any]] = []
            raw_sites = payload.get("sites")
            if isinstance(raw_sites, list):
                for site_payload in raw_sites:
                    if not isinstance(site_payload, Mapping):
                        continue
                    site_entry: dict[str, Any] = {}
                    url_value = str(site_payload.get("url") or "").strip()
                    if url_value:
                        site_entry["url"] = url_value
                    for field in ("unique_high", "unique_med", "unique_low"):
                        if field in site_payload:
                            site_entry[field] = _as_int(site_payload.get(field))
                    if site_entry:
                        sites.append(site_entry)
            normalized["sites"] = sites
            for field in (
                "combined_unique",
                "combined_unique_high",
                "combined_unique_med",
                "combined_unique_low",
            ):
                if field in payload:
                    normalized[field] = _as_int(payload.get(field))
        return normalized
    if area == "firewall" and isinstance(payload, Mapping):
        normalized_devices: list[dict[str, Any]] = []
        raw_devices = payload.get("devices")
        if isinstance(raw_devices, list):
            for device_payload in raw_devices:
                if not isinstance(device_payload, Mapping):
                    continue
                device_entry: dict[str, Any] = {}
                name_value = (
                    device_payload.get("device")
                    or device_payload.get("name")
                    or device_payload.get("hostname")
                    or ""
                )
                name_text = str(name_value).strip()
                if name_text:
                    device_entry["device"] = name_text
                for field in ("total_high", "total_med", "total_low"):
                    if field in device_payload:
                        device_entry[field] = _as_int(device_payload.get(field))
                if "ood" in device_payload:
                    ood_value = device_payload.get("ood")
                    if isinstance(ood_value, bool):
                        device_entry["ood"] = "yes" if ood_value else "no"
                    else:
                        ood_text = str(ood_value).strip().lower()
                        if ood_text in {"yes", "true", "1", "y"}:
                            device_entry["ood"] = "yes"
                        elif ood_text in {"no", "false", "0", "n", ""}:
                            device_entry["ood"] = "no"
                if device_entry:
                    normalized_devices.append(device_entry)
        if normalized_devices:
            normalized["devices"] = normalized_devices
        for field in FIREWALL_SUMMARY_FIELDS:
            if field in payload:
                if field.endswith("_type"):
                    normalized[field] = (
                        str(payload.get(field)).strip()
                        if payload.get(field) not in (None, "")
                        else None
                    )
                else:
                    normalized[field] = _as_int(payload.get(field))
        return normalized
    if area == "ad" and isinstance(payload, Mapping):
        raw_domains = payload.get("domains")
        normalized_domains: list[dict[str, Any]] = []
        if isinstance(raw_domains, list):
            for domain_payload in raw_domains:
                if not isinstance(domain_payload, Mapping):
                    continue
                domain_entry: dict[str, Any] = {}
                domain_value = (
                    domain_payload.get("domain")
                    or domain_payload.get("name")
                    or ""
                )
                domain_text = str(domain_value).strip()
                if domain_text:
                    domain_entry["domain"] = domain_text
                if "functionality_level" in domain_payload:
                    level_value = str(domain_payload.get("functionality_level") or "").strip()
                    domain_entry["functionality_level"] = level_value or None
                for field in AD_DOMAIN_COUNT_FIELDS:
                    if field in domain_payload:
                        domain_entry[field] = _as_int(domain_payload.get(field))

                raw_old_counts = domain_payload.get("old_password_counts")
                if isinstance(raw_old_counts, Mapping):
                    old_counts: dict[str, Any] = {}
                    for field in AD_OLD_PASSWORD_COUNT_FIELDS:
                        if field in raw_old_counts:
                            old_counts[field] = _as_int(raw_old_counts.get(field))
                    domain_entry["old_password_counts"] = old_counts

                raw_inactive_counts = domain_payload.get("inactive_account_counts")
                if isinstance(raw_inactive_counts, Mapping):
                    inactive_counts: dict[str, Any] = {}
                    for field in AD_INACTIVE_ACCOUNT_COUNT_FIELDS:
                        if field in raw_inactive_counts:
                            inactive_counts[field] = _as_int(
                                raw_inactive_counts.get(field)
                            )
                    domain_entry["inactive_account_counts"] = inactive_counts

                if domain_entry:
                    normalized_domains.append(domain_entry)
            normalized["domains"] = normalized_domains
        return normalized
    if area == "password" and isinstance(payload, Mapping):
        raw_policies = payload.get("policies")
        removed_domains_raw = payload.get("removed_ad_domains")

        removed_domains: list[str] = []
        if isinstance(removed_domains_raw, list):
            for entry in removed_domains_raw:
                name = (entry or "").strip()
                if name:
                    removed_domains.append(name)

        def _normalize_bool_string(value: Any) -> Optional[str]:
            if isinstance(value, bool):
                return "TRUE" if value else "FALSE"
            text = str(value).strip().upper()
            if text in {"TRUE", "FALSE"}:
                return text
            return None

        def _normalize_password_pattern(pattern_payload: Mapping[str, Any]) -> dict[str, Any]:
            normalized_pattern: dict[str, Any] = {}
            confirm_value = _normalize_yes_no(pattern_payload.get("confirm"))
            if confirm_value:
                normalized_pattern["confirm"] = confirm_value
            passwords_value = pattern_payload.get("passwords")
            if confirm_value == "Yes" and isinstance(passwords_value, list):
                passwords: list[dict[str, Any]] = []
                for entry in passwords_value:
                    if not isinstance(entry, Mapping):
                        continue
                    password_value = (entry.get("password") or "").strip()
                    count_value = _as_int(entry.get("count")) if "count" in entry else None
                    if password_value or count_value is not None:
                        passwords.append({"password": password_value, "count": count_value})
                normalized_pattern["passwords"] = passwords
            return normalized_pattern

        def _normalize_fgpp_entries(entries: Any) -> list[dict[str, Any]]:
            normalized_fgpp: list[dict[str, Any]] = []
            if not isinstance(entries, list):
                return normalized_fgpp
            for entry in entries:
                if not isinstance(entry, Mapping):
                    continue
                fgpp_entry: dict[str, Any] = {}
                name_value = (entry.get("fgpp_name") or "").strip()
                if name_value:
                    fgpp_entry["fgpp_name"] = name_value
                for field in (
                    "max_age",
                    "min_age",
                    "min_length",
                    "history",
                    "lockout_threshold",
                    "lockout_reset",
                    "lockout_duration",
                ):
                    if field in entry:
                        fgpp_entry[field] = _as_int(entry.get(field))
                if "complexity_enabled" in entry:
                    fgpp_entry["complexity_enabled"] = _normalize_bool_string(
                        entry.get("complexity_enabled")
                    )
                if fgpp_entry:
                    normalized_fgpp.append(fgpp_entry)
            return normalized_fgpp

        def _policy_has_values(policy_entry: Mapping[str, Any], fgpp_entries: list[dict[str, Any]]) -> bool:
            if fgpp_entries:
                return True

            if not isinstance(policy_entry, Mapping):
                return False

            for field in (
                "max_age",
                "min_age",
                "min_length",
                "history",
                "lockout_threshold",
                "lockout_reset",
                "lockout_duration",
                "complexity_enabled",
                "mfa_required",
                "passwords_cracked",
                "admin_cracked",
                "lanman_stored",
                "enabled_accounts",
                "password_pattern",
            ):
                if field not in policy_entry:
                    continue

                if field == "admin_cracked":
                    admin_entry = policy_entry.get("admin_cracked")
                    if isinstance(admin_entry, Mapping) and admin_entry:
                        return True
                    continue

                if field == "password_pattern":
                    pattern_entry = policy_entry.get("password_pattern")
                    if isinstance(pattern_entry, Mapping) and pattern_entry:
                        return True
                    continue

                if policy_entry.get(field) not in (None, "", []):
                    return True

            return False

        normalized_policies: list[dict[str, Any]] = []
        if isinstance(raw_policies, list):
            for policy in raw_policies:
                if not isinstance(policy, Mapping):
                    continue
                normalized_policy: dict[str, Any] = {}
                domain_value = (policy.get("domain_name") or "").strip()
                if domain_value:
                    normalized_policy["domain_name"] = domain_value

                for field in (
                    "max_age",
                    "min_age",
                    "min_length",
                    "history",
                    "lockout_threshold",
                    "lockout_reset",
                    "lockout_duration",
                    "passwords_cracked",
                    "strong_passwords",
                    "enabled_accounts",
                ):
                    if field in policy:
                        normalized_policy[field] = _as_int(policy.get(field))

                if "complexity_enabled" in policy:
                    normalized_policy["complexity_enabled"] = _normalize_bool_string(
                        policy.get("complexity_enabled")
                    )
                if "mfa_required" in policy:
                    normalized_policy["mfa_required"] = _normalize_bool_string(
                        policy.get("mfa_required")
                    )

                if "lanman_stored" in policy:
                    normalized_policy["lanman_stored"] = _normalize_yes_no(
                        policy.get("lanman_stored")
                    )

                admin_payload = policy.get("admin_cracked")
                if isinstance(admin_payload, Mapping):
                    admin_confirm = _normalize_yes_no(admin_payload.get("confirm"))
                    admin_entry: dict[str, Any] = {}
                    if admin_confirm:
                        admin_entry["confirm"] = admin_confirm
                        admin_entry["count"] = (
                            _as_int(admin_payload.get("count"))
                            if admin_confirm == "Yes"
                            else 0
                        )
                    if admin_entry:
                        normalized_policy["admin_cracked"] = admin_entry

                pattern_payload = policy.get("password_pattern")
                if isinstance(pattern_payload, Mapping):
                    pattern_entry = _normalize_password_pattern(pattern_payload)
                    if pattern_entry:
                        normalized_policy["password_pattern"] = pattern_entry

                fgpp_entries = _normalize_fgpp_entries(policy.get("fgpp"))
                if _policy_has_values(normalized_policy, fgpp_entries):
                    normalized_policy["fgpp"] = fgpp_entries
                    normalized_policies.append(normalized_policy)

        if removed_domains:
            normalized["removed_ad_domains"] = removed_domains

        if normalized_policies:
            normalized["policies"] = normalized_policies
        return normalized
    if area == "endpoint" and isinstance(payload, Mapping):
        raw_domains = payload.get("domains")
        normalized_domains: list[dict[str, Any]] = []
        raw_domains_provided = isinstance(raw_domains, list)
        if raw_domains_provided:
            for domain_payload in raw_domains:
                if not isinstance(domain_payload, Mapping):
                    continue
                domain_entry: dict[str, Any] = {}
                domain_value = domain_payload.get("domain") or domain_payload.get("name")
                domain_text = str(domain_value).strip() if domain_value not in (None, "") else ""
                if domain_text:
                    domain_entry["domain"] = domain_text
                for field in ("csv_file_name", "log_file_name"):
                    if field in domain_payload:
                        text = (
                            str(domain_payload.get(field)).strip()
                            if domain_payload.get(field) not in (None, "")
                            else ""
                        )
                        if text:
                            domain_entry[field] = text
                for field in (
                    "total_computers",
                    "audited_computers",
                    "systems_ood",
                    "open_wifi",
                ):
                    if field in domain_payload:
                        domain_entry[field] = _as_int(domain_payload.get(field))

                if "usb_control_indication" in domain_payload:
                    usb_value = _normalize_yes_no(domain_payload.get("usb_control_indication"))
                    if usb_value:
                        domain_entry["usb_control_indication"] = usb_value

                has_metrics = any(
                    domain_entry.get(key) not in (None, "")
                    for key in (
                        "total_computers",
                        "audited_computers",
                        "systems_ood",
                        "open_wifi",
                        "usb_control_indication",
                    )
                )

                if domain_entry and (domain_entry.get("domain") or has_metrics) and has_metrics:
                    normalized_domains.append(domain_entry)

        removed_domains_raw = payload.get("removed_ad_domains")
        removed_domains: list[str] = []
        removed_domains_provided = isinstance(removed_domains_raw, list)
        if removed_domains_provided:
            for entry in removed_domains_raw:
                name = (entry or "").strip()
                if name:
                    removed_domains.append(name)

        if raw_domains_provided:
            normalized["domains"] = normalized_domains
        if removed_domains_provided:
            normalized["removed_ad_domains"] = removed_domains
        return normalized
    allowed_fields = AREA_FIELDS.get(area, set())
    if not allowed_fields or not isinstance(payload, Mapping):
        return normalized
    for field in allowed_fields:
        if field in payload:
            normalized[field] = _as_int(payload.get(field))
    return normalized


def _normalize_dns_payload(payload: Optional[Mapping[str, Any]]) -> Dict[str, Any]:
    normalized: Dict[str, Any] = {}
    if not isinstance(payload, Mapping):
        return normalized

    def _normalize_zone_transfer(value: Any) -> Optional[str]:
        if value in (None, ""):
            return None
        if isinstance(value, bool):
            return "yes" if value else "no"
        text = str(value).strip().lower()
        if not text:
            return None
        return "yes" if text in {"yes", "y", "true", "1"} else "no"

    records_value = payload.get("records")
    if isinstance(records_value, list):
        normalized_records: list[dict[str, Any]] = []
        for record in records_value:
            if not isinstance(record, Mapping):
                continue
            domain_value = record.get("domain")
            domain = str(domain_value).strip() if domain_value not in (None, "") else None
            normalized_record: dict[str, Any] = {
                "domain": domain,
                "total": _as_int(record.get("total")),
                "zone_transfer": _normalize_zone_transfer(record.get("zone_transfer")),
            }
            normalized_records.append(normalized_record)
        normalized["records"] = normalized_records

    if "unique" in payload:
        normalized["unique"] = _as_int(payload.get("unique"))

    return normalized


def _calculate_category_total(
    *, scores: Mapping[str, Optional[Decimal]], weights: Mapping[str, Decimal]
) -> Optional[Decimal]:
    if not scores:
        return None
    if not weights:
        provided = [score for score in scores.values() if score is not None]
        if not provided:
            return None
        return sum(provided) / Decimal(len(provided))

    total = Decimal("0")
    for option, weight in weights.items():
        score = scores.get(option) or Decimal("0")
        total += score * weight
    return total.quantize(_SCORE_PRECISION)


def _normalize_score_map(score_map: Mapping[str, Mapping[str, Any]]) -> OrderedDict[str, tuple[Decimal, Decimal]]:
    normalized: "OrderedDict[str, tuple[Decimal, Decimal]]" = OrderedDict()
    for risk, bounds in score_map.items():
        try:
            lower, upper = bounds
        except Exception:
            continue
        try:
            normalized[risk] = (Decimal(lower), Decimal(upper))
        except Exception:
            continue
    return normalized


def _compute_overall_grade(
    *,
    category_scores: Mapping[str, Optional[Decimal]],
    risk_score_map: Mapping[str, Any],
    scoping: Mapping[str, Mapping[str, Any]],
) -> Optional[str]:
    totals: list[Decimal] = []
    for category, score in category_scores.items():
        if score is None:
            continue
        scope_state = scoping.get(category, {})
        if not scope_state.get("selected"):
            continue
        adjusted = score
        if category == "wireless":
            adjusted = score * Decimal("0.9")
        totals.append(adjusted)
    if not totals:
        return None
    average = (sum(totals) / Decimal(len(totals))).quantize(_SCORE_PRECISION)
    return _score_to_risk(average, risk_score_map)


def build_workbook_entry_payload(
    *,
    project,
    general: Optional[Mapping[str, Any]] = None,
    scores: Optional[Mapping[str, Any]] = None,
    grades: Optional[Mapping[str, Any]] = None,
    areas: Optional[Mapping[str, Any]] = None,
    dns: Optional[Mapping[str, Any]] = None,
) -> Dict[str, Any]:
    """Return updated workbook data for inline workbook entry."""

    normalized_workbook = normalize_workbook_payload(getattr(project, "workbook_data", {}))
    scoping_state = normalize_project_scoping(getattr(project, "scoping", {}))
    risk_score_map = _normalize_score_map(RiskScoreRangeMapping.get_risk_score_map())

    if general:
        normalized_general = _normalize_general_payload(general)
        normalized_workbook.setdefault("general", {}).update(normalized_general)

    if dns:
        normalized_dns = _normalize_dns_payload(dns)
        if normalized_dns:
            existing_dns = normalized_workbook.get("dns")
            if not isinstance(existing_dns, dict):
                existing_dns = {}
            existing_dns.update(normalized_dns)
            normalized_workbook["dns"] = existing_dns

    if isinstance(areas, Mapping):
        for area_key, area_payload in areas.items():
            normalized_area = _normalize_area_payload(area_key, area_payload)
            if not normalized_area:
                continue

            if area_key == "password":
                existing_password = (
                    normalized_workbook.get("password")
                    if isinstance(normalized_workbook.get("password"), dict)
                    else {}
                )
                updated_password = dict(existing_password)

                removed_domains = normalized_area.get("removed_ad_domains")
                removed_set: set[str] = set()
                merged_removed: list[str] = []
                if isinstance(removed_domains, list):
                    for entry in removed_domains:
                        name = (entry or "").strip()
                        if not name:
                            continue
                        lowered = name.lower()
                        if lowered not in removed_set:
                            removed_set.add(lowered)
                            merged_removed.append(name)

                existing_removed = (
                    existing_password.get("removed_ad_domains")
                    if isinstance(existing_password.get("removed_ad_domains"), list)
                    else []
                )
                seen_removed = set(removed_set)
                for entry in existing_removed:
                    name = (entry or "").strip()
                    if not name:
                        continue
                    lowered = name.lower()
                    if lowered in seen_removed:
                        continue
                    seen_removed.add(lowered)
                    merged_removed.insert(0, name)

                base_policies = (
                    normalized_area["policies"]
                    if "policies" in normalized_area
                    else existing_password.get("policies")
                )
                if not isinstance(base_policies, list):
                    base_policies = []

                blocked_domains = seen_removed
                filtered_policies: list[dict[str, Any]] = []
                for policy in base_policies:
                    if not isinstance(policy, Mapping):
                        continue
                    domain_value = (policy.get("domain_name") or "").strip()
                    if domain_value and domain_value.lower() in blocked_domains:
                        continue
                    filtered_policies.append(policy)

                updated_password["policies"] = filtered_policies

                if merged_removed:
                    updated_password["removed_ad_domains"] = merged_removed
                elif "removed_ad_domains" in updated_password:
                    updated_password.pop("removed_ad_domains", None)

                normalized_workbook["password"] = updated_password
                continue

            if area_key == "endpoint":
                normalized_workbook["endpoint"] = dict(normalized_area)
                continue

            normalized_workbook.setdefault(area_key, {}).update(normalized_area)

    ad_domains: set[str] = set()
    ad_state = (
        normalized_workbook.get("ad")
        if isinstance(normalized_workbook.get("ad"), Mapping)
        else {}
    )
    if isinstance(ad_state, Mapping):
        domain_entries = (
            ad_state.get("domains") if isinstance(ad_state.get("domains"), list) else []
        )
        if isinstance(domain_entries, list):
            for entry in domain_entries:
                if not isinstance(entry, Mapping):
                    continue
                domain_name = (entry.get("domain") or entry.get("name") or "").strip()
                if domain_name:
                    ad_domains.add(domain_name.lower())

    password_state = (
        normalized_workbook.get("password")
        if isinstance(normalized_workbook.get("password"), Mapping)
        else None
    )
    if isinstance(password_state, Mapping):
        removed_domains = password_state.get("removed_ad_domains")
        if isinstance(removed_domains, list):
            filtered_removed: list[str] = []
            seen_removed: set[str] = set()
            for entry in removed_domains:
                name = (entry or "").strip()
                lowered = name.lower()
                if not name or lowered in seen_removed:
                    continue
                seen_removed.add(lowered)
                if lowered in ad_domains:
                    filtered_removed.append(name)
            if filtered_removed:
                password_state["removed_ad_domains"] = filtered_removed
            elif "removed_ad_domains" in password_state:
                password_state.pop("removed_ad_domains", None)

    endpoint_state = (
        normalized_workbook.get("endpoint")
        if isinstance(normalized_workbook.get("endpoint"), Mapping)
        else None
    )
    if isinstance(endpoint_state, Mapping):
        removed_domains = endpoint_state.get("removed_ad_domains")
        if isinstance(removed_domains, list):
            filtered_removed = []
            seen_removed: set[str] = set()
            for entry in removed_domains:
                name = (entry or "").strip()
                lowered = name.lower()
                if not name or lowered in seen_removed:
                    continue
                seen_removed.add(lowered)
                if lowered in ad_domains:
                    filtered_removed.append(name)
            if filtered_removed:
                endpoint_state["removed_ad_domains"] = filtered_removed
            elif "removed_ad_domains" in endpoint_state:
                endpoint_state.pop("removed_ad_domains", None)

    score_updates: MutableMapping[str, MutableMapping[str, Any]] = {}
    category_scores: Dict[str, Optional[Decimal]] = {}
    if isinstance(scores, Mapping):
        score_updates = deepcopy(normalized_workbook.get("external_internal_grades", {}))
        scoping_weights = getattr(project, "scoping_weights", {}) or {}
        for category, option_payload in scores.items():
            if not isinstance(option_payload, Mapping):
                continue
            category_entry = score_updates.setdefault(category, {})
            option_scores: Dict[str, Optional[Decimal]] = {}
            for option_key, value in option_payload.items():
                score_value = _as_decimal(value)
                option_scores[option_key] = score_value
                if isinstance(category_entry.get(option_key), Mapping):
                    category_entry[option_key]["score"] = None if score_value is None else float(score_value)
                    category_entry[option_key]["risk"] = _score_to_risk(score_value, risk_score_map)
                else:
                    category_entry[option_key] = {
                        "score": None if score_value is None else float(score_value),
                        "risk": _score_to_risk(score_value, risk_score_map),
                    }
            weights = scoping_weights.get(category, {}) or {}
            total = _calculate_category_total(scores=option_scores, weights=weights)
            category_scores[category] = total
            category_entry["total"] = None if total is None else float(total)
            category_entry["grade"] = _score_to_risk(total, risk_score_map)
        normalized_workbook["external_internal_grades"] = score_updates

    grade_updates: Dict[str, Any] = {}
    if isinstance(grades, Mapping):
        for key, value in grades.items():
            if value in (None, ""):
                continue
            grade_updates[key] = str(value)

    if category_scores and not grade_updates:
        grade_updates = {category: details.get("grade") for category, details in score_updates.items()}

    if category_scores:
        overall_grade = _compute_overall_grade(
            category_scores=category_scores,
            risk_score_map=risk_score_map,
            scoping=scoping_state,
        )
        if overall_grade:
            grade_updates.setdefault("overall", overall_grade)

    if grade_updates:
        normalized_workbook.setdefault("report_card", {}).update(grade_updates)

    return normalized_workbook
