"""Helpers for generating workbook-driven project questions."""

# Standard Libraries
from typing import Any, Dict, Iterable, List, Mapping, Optional, Set, Tuple

# Django Imports
from django import forms
from django.utils.text import slugify

# Ghostwriter Libraries
from ghostwriter.rolodex.constants import (
    SQL_DATA_FILE_NAME_KEY,
    WIRELESS_DATA_FILE_NAME_KEY,
)
from ghostwriter.rolodex.forms_workbook import MultiValueField, SummaryMultipleChoiceField
from ghostwriter.rolodex.workbook_defaults import (
    WORKBOOK_META_KEY,
    ensure_data_responses_defaults,
    get_uploaded_sections,
)

SECTION_DISPLAY_ORDER = [
    "client",
    "general",
    "report_card",
    "external_internal_grades",
    "osint",
    "dns",
    "external_nexpose",
    "web",
    "firewall",
    "ad",
    "password",
    "internal_nexpose",
    "iot-iomt_nexpose",
    "endpoint",
    "snmp",
    "sql",
    "wireless",
    "cloud_config",
    "system_config",
]

SECTION_ORDER_INDEX = {key: index for index, key in enumerate(SECTION_DISPLAY_ORDER)}

RISK_CHOICES = (
    ("high", "High"),
    ("medium", "Medium"),
    ("low", "Low"),
)

YES_NO_CHOICES = (
    ("yes", "Yes"),
    ("no", "No"),
)

SCOPE_CHOICES = (
    ("external", "External"),
    ("internal", "Internal"),
    ("wireless", "Wireless"),
    ("firewall", "Firewall"),
    ("cloud", "Cloud"),
)

SCOPE_OPTION_ORDER = [choice for choice, _ in SCOPE_CHOICES]

_SCOPE_PRESET_MAP = {
    "silver": {"external", "firewall"},
    "gold": {"external", "internal", "firewall"},
    "platinum": {"external", "internal", "wireless", "firewall"},
    "titanium": {"external", "internal", "wireless", "firewall"},
    "cloudfirst": {"external", "cloud"},
}

_SCOPE_SUMMARY_MAP = {
    "external": "External network and systems",
    "internal": "Internal network and systems",
    "wireless": "Wireless network and systems",
    "firewall": "Firewall configuration(s) & rules",
}

WEAK_PSK_CHOICES = (
    ("too_short", "To short"),
    ("not_enough_entropy", "Not enough entropy"),
    ("dictionary_or_company", "Based on dictionary word or Company name"),
)

WEAK_PSK_SUMMARY_MAP = {
    "too_short": "to short",
    "not_enough_entropy": "not enough entropy",
    "dictionary_or_company": "based on a dictionary word or Company name",
}

WIRELESS_NETWORK_TYPES = (
    ("open", "Open Networks"),
    ("psk", "PSK Networks"),
    ("hidden", "Hidden Networks (typically Medium)"),
    ("rogue", "Rogue Networks"),
)

AD_DOMAIN_METRICS = (
    ("domain_admins", "Domain Admins"),
    ("enterprise_admins", "Enterprise Admins"),
    ("expired_passwords", "Expired Passwords"),
    ("passwords_never_expire", "Passwords Never Expire"),
    ("inactive_accounts", "Inactive Accounts"),
    ("generic_accounts", "Generic Accounts"),
    ("generic_logins", "Generic Logins"),
    ("old_passwords", "Old Passwords"),
    ("disabled_accounts", "Disabled Accounts"),
)


def _as_int(value: Any) -> int:
    try:
        if isinstance(value, bool):  # pragma: no cover - defensive guard
            return int(value)
        return int(float(value))
    except (TypeError, ValueError):
        return 0


def _as_str(value: Any) -> str:
    if value is None:
        return ""
    return str(value)


def _extract_domain(record: Any) -> Optional[str]:
    if isinstance(record, dict):
        for key in ("domain", "name"):
            candidate = record.get(key)
            if candidate:
                return _as_str(candidate)
    elif record:
        return _as_str(record)
    return None


def _slugify_identifier(*parts: Iterable[Any]) -> str:
    identifiers: List[str] = []
    for part in parts:
        if part is None:
            continue
        text = slugify(str(part))
        if text:
            identifiers.append(text)
    return "_".join(identifiers)


WIRELESS_DATA_REQUIREMENT_LABEL = "wireless_data.xlsx"
WIRELESS_DATA_REQUIREMENT_SLUG = _slugify_identifier(
    "required", WIRELESS_DATA_REQUIREMENT_LABEL
)
SQL_DATA_REQUIREMENT_LABEL = "sql_instances_allowing_open_access.xlsx"
SQL_DATA_REQUIREMENT_SLUG = _slugify_identifier(
    "required", SQL_DATA_REQUIREMENT_LABEL
)


def _get_nested(data: Dict[str, Any], path: Iterable[str], default: Any = None) -> Any:
    result: Any = data
    for key in path:
        if not isinstance(result, dict):
            return default
        result = result.get(key)
    return result if result is not None else default


def get_scope_initial(project_type: Optional[str]) -> List[str]:
    """Return default scope selections for the provided ``project_type``."""

    if not project_type:
        return []
    normalized = project_type.replace(" ", "").strip().lower()
    preset = _SCOPE_PRESET_MAP.get(normalized, set())
    if not preset:
        return []
    return [key for key in SCOPE_OPTION_ORDER if key in preset]


def prepare_data_responses_initial(
    responses: Optional[Mapping[str, Any]], project_type: Optional[str]
) -> Dict[str, Any]:
    """Return normalized responses with scope defaults applied for the ``project_type``."""

    normalized = ensure_data_responses_defaults(
        responses if isinstance(responses, Mapping) else {}
    )
    if not project_type:
        return normalized

    default_scope = get_scope_initial(project_type)
    if not default_scope:
        return normalized

    general_values = normalized.setdefault("general", {})
    existing_scope = general_values.get("assessment_scope")
    if not existing_scope:
        general_values["assessment_scope"] = list(default_scope)

    return normalized


def normalize_scope_selection(selection: Iterable[str]) -> List[str]:
    """Return scope choices in canonical order, removing invalid entries."""

    if selection is None:
        return []
    if isinstance(selection, str):
        normalized_set = {selection}
    else:
        normalized_set = {value for value in selection if isinstance(value, str)}
    normalized_set = {value for value in normalized_set if value in SCOPE_OPTION_ORDER}
    return [key for key in SCOPE_OPTION_ORDER if key in normalized_set]


def build_scope_summary(selection: Iterable[str], on_prem: Optional[str]) -> str:
    """Build a human-readable description of the selected assessment scope."""

    ordered_selection = normalize_scope_selection(selection)
    if not ordered_selection:
        return ""

    segments: List[str] = []
    include_on_prem = str(on_prem or "").strip().lower() == "yes"

    for key in ordered_selection:
        if key == "cloud":
            segments.append(
                "Cloud/On-Prem network and systems" if include_on_prem else "Cloud systems"
            )
            segments.append("Cloud management configuration")
            continue
        summary = _SCOPE_SUMMARY_MAP.get(key)
        if summary:
            segments.append(summary)

    if not segments:
        return ""
    if len(segments) == 1:
        return segments[0]
    if len(segments) == 2:
        return " and ".join(segments)
    return ", ".join(segments[:-1]) + " and " + segments[-1]


def _humanize_section_name(raw_key: str) -> str:
    text = (raw_key or "").replace("_", " ").replace("-", " ").strip()
    if not text:
        return "Section"
    return text.title()


def _format_leaf_value(value: Any) -> Any:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "Yes" if value else "No"
    if isinstance(value, (int, float)):
        # Cast numbers to strings so template sanitization handles them uniformly.
        return str(value)
    return str(value)


def _normalise_workbook_value(value: Any) -> Dict[str, Any]:
    """Return a structure suitable for recursive rendering in templates."""

    if isinstance(value, dict):
        items: List[Dict[str, Any]] = []
        for key, item in value.items():
            items.append(
                {
                    "label": _humanize_section_name(str(key)),
                    "raw_key": str(key),
                    "value": _normalise_workbook_value(item),
                }
            )
        return {"type": "dict", "items": items}

    if isinstance(value, list):
        items = []
        for index, item in enumerate(value, 1):
            formatted = _normalise_workbook_value(item)
            label: Optional[str] = None
            if isinstance(item, dict):
                for candidate_key in ("name", "domain", "title", "short_name", "url"):
                    candidate = item.get(candidate_key)
                    if candidate:
                        label = str(candidate)
                        break
            if not label and formatted.get("type") != "value":
                label = f"Item {index}"
            items.append({"label": label, "index": index, "value": formatted})
        return {"type": "list", "items": items}

    return {"type": "value", "display": _format_leaf_value(value)}


def build_workbook_sections(workbook_data: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Return workbook content grouped by top-level keys for easier presentation."""

    if not isinstance(workbook_data, dict):
        return []

    visible_sections = get_uploaded_sections(workbook_data)
    sections: List[Dict[str, Any]] = []
    for position, (key, value) in enumerate(workbook_data.items()):
        if key == WORKBOOK_META_KEY:
            continue
        if visible_sections and key not in visible_sections:
            continue
        slug = _slugify_identifier("workbook", key)
        slug = slug or "workbook-section"
        sections.append(
            {
                "key": key,
                "title": _humanize_section_name(str(key)),
                "slug": slug,
                "script_id": f"workbook-section-data-{slug}",
                "data": value,
                "tree": _normalise_workbook_value(value),
                "_position": position,
            }
        )

    sections.sort(
        key=lambda section: (
            SECTION_ORDER_INDEX.get(section["key"], len(SECTION_DISPLAY_ORDER)),
            section.pop("_position"),
        )
    )

    return sections


def build_data_configuration(
    workbook_data: Optional[Dict[str, Any]],
    project_type: Optional[str] = None,
    data_artifacts: Optional[Dict[str, Any]] = None,
    project_risks: Optional[Dict[str, Any]] = None,
) -> Tuple[List[Dict[str, Any]], List[Dict[str, str]]]:
    """Return dynamic questions and file requirements derived from workbook data."""

    data = workbook_data or {}
    uploaded_sections = get_uploaded_sections(workbook_data)
    artifacts = data_artifacts or {}
    risks = project_risks or {}
    questions: List[Dict[str, Any]] = []
    required_files: List[Dict[str, str]] = []
    required_file_index: Set[Tuple[str, Optional[str]]] = set()

    def has_workbook_section(key: str) -> bool:
        return key in uploaded_sections

    def add_required(label: str, context: Optional[str] = None) -> None:
        key = (label, context)
        if key not in required_file_index:
            required_file_index.add(key)
            slug = _slugify_identifier("required", label, context)
            if not slug:
                slug = f"required-{len(required_file_index)}"
            entry = {"label": label, "slug": slug}
            if context:
                entry["context"] = context
            required_files.append(entry)

    def add_question(
        *,
        key: str,
        label: str,
        field_class: type,
        section: str,
        subheading: Optional[str] = None,
        help_text: Optional[str] = None,
        choices: Optional[Iterable[Tuple[str, str]]] = None,
        widget: Optional[forms.Widget] = None,
        initial: Any = None,
        field_kwargs: Optional[Dict[str, Any]] = None,
        entry_slug: Optional[str] = None,
        entry_field_key: Optional[str] = None,
        storage_section_key: Optional[str] = None,
        storage_key: Optional[str] = None,
    ) -> None:
        base_field_kwargs: Dict[str, Any] = {
            "label": label,
            "required": False,
        }
        if help_text:
            base_field_kwargs["help_text"] = help_text
        if choices is not None:
            base_field_kwargs["choices"] = tuple(choices)
        if widget is not None:
            base_field_kwargs["widget"] = widget
        if initial is not None:
            base_field_kwargs["initial"] = initial
        if field_kwargs:
            base_field_kwargs.update(field_kwargs)
        derived_section_key = SECTION_KEY_MAP.get(section, _slugify_identifier(section).replace("-", "_"))
        question_definition = {
            "key": key,
            "label": label,
            "section": section,
            "section_key": storage_section_key or derived_section_key,
            "subheading": subheading,
            "field_class": field_class,
            "field_kwargs": base_field_kwargs,
        }
        if entry_slug:
            question_definition["entry_slug"] = entry_slug
        if entry_field_key:
            question_definition["entry_field_key"] = entry_field_key
        if storage_key:
            question_definition["storage_key"] = storage_key
        questions.append(question_definition)

    # Project scope confirmation
    scope_initial = get_scope_initial(project_type)
    scope_field_kwargs: Dict[str, Any] = {}
    if scope_initial:
        scope_field_kwargs["initial"] = scope_initial

    add_question(
        key="assessment_scope",
        label="Confirm the assessment scope",
        field_class=forms.MultipleChoiceField,
        section="General",
        choices=SCOPE_CHOICES,
        widget=forms.CheckboxSelectMultiple,
        field_kwargs=scope_field_kwargs or None,
    )

    add_question(
        key="assessment_scope_cloud_on_prem",
        label="Was on-prem testing included?",
        field_class=forms.ChoiceField,
        section="General",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
    )

    add_question(
        key="general_first_ca",
        label="Is this the first CA for this client?",
        field_class=forms.ChoiceField,
        section="General",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
    )

    add_question(
        key="general_scope_changed",
        label="Is the scope of this assessment different than the last one?",
        field_class=forms.ChoiceField,
        section="General",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
    )

    add_question(
        key="general_anonymous_ephi",
        label="Were you able to identify anonymous access to EPHI?",
        field_class=forms.ChoiceField,
        section="General",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
    )

    add_question(
        key="hashes_obtained",
        label="Were password hashes obtained?",
        field_class=forms.ChoiceField,
        section="General",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        storage_section_key="password",
        storage_key="hashes_obtained",
    )

    add_question(
        key="iot_testing_confirm",
        label="Was Internal IoT/IoMT testing performed?",
        field_class=forms.ChoiceField,
        section="IoT/IoMT",
        choices=YES_NO_CHOICES,
        widget=forms.RadioSelect,
        initial="no",
    )

    # Intelligence questions
    if has_workbook_section("osint"):
        osint_data = _get_nested(data, ("osint",), {}) or {}

        if _as_int(_get_nested(osint_data, ("total_squat",), 0)) > 0:
            add_question(
                key="osint_squat_concern",
                label="Of the squatting domains found, which is the most concerning (single domain or comma-separated list)",
                field_class=forms.CharField,
                section="Intelligence",
                widget=forms.TextInput(attrs={"class": "form-control"}),
            )

        osint_risk_choices = (("High", "High"), ("Medium", "Medium"), ("Low", "Low"))

        if _as_int(_get_nested(osint_data, ("total_buckets",), 0)) > 0:
            add_question(
                key="osint_bucket_risk",
                label="What is the risk you would assign to the exposed buckets found?",
                field_class=forms.ChoiceField,
                section="Intelligence",
                choices=osint_risk_choices,
            )

        if _as_int(_get_nested(osint_data, ("total_leaks",), 0)) > 0:
            add_question(
                key="osint_leaked_creds_risk",
                label="What is the risk you would assign to the leaked creds found?",
                field_class=forms.ChoiceField,
                section="Intelligence",
                choices=osint_risk_choices,
            )

    # Required DNS artifacts
    if has_workbook_section("dns"):
        dns_records = _get_nested(data, ("dns", "records"), []) or []
        if isinstance(dns_records, list):
            for record in dns_records:
                domain = _extract_domain(record)
                if domain:
                    add_required("dns_report.csv", domain)

        target_issue = "One or more SOA fields are outside recommended ranges"
        dns_entries = artifacts.get("dns_issues") if isinstance(artifacts, dict) else None
        if isinstance(dns_entries, list):
            seen_domains: Set[str] = set()
            for entry in dns_entries:
                if not isinstance(entry, dict):
                    continue
                domain_name = _as_str(entry.get("domain")) or ""
                issues = entry.get("issues")
                if not isinstance(issues, list):
                    continue
                has_issue = False
                for issue in issues:
                    if isinstance(issue, dict):
                        issue_text = issue.get("issue")
                    else:
                        issue_text = issue
                    if _as_str(issue_text) == target_issue:
                        has_issue = True
                        break
                if not has_issue:
                    continue
                display_domain = domain_name or "Unknown Domain"
                normalized_domain = display_domain.lower()
                if normalized_domain in seen_domains:
                    continue
                seen_domains.add(normalized_domain)
                slug = _slugify_identifier("dns", display_domain)
                if not slug:
                    slug = f"dns_domain_{len(seen_domains)}"
                add_question(
                    key=f"{slug}_soa_fields",
                    label="Which SOA fields are outside the recommended ranges?",
                    field_class=forms.MultipleChoiceField,
                    section="DNS",
                    subheading=display_domain,
                    choices=DNS_SOA_FIELD_CHOICES,
                    widget=forms.CheckboxSelectMultiple,
                    entry_slug=slug,
                    entry_field_key="soa_fields",
                )

    if _as_int(_get_nested(data, ("web", "combined_unique"), 0)) > 0:
        add_required("burp_xml.xml")

    # Vulnerability artifacts
    external_nexpose_total = _as_int(_get_nested(data, ("external_nexpose", "total"), 0))
    internal_nexpose_total = _as_int(_get_nested(data, ("internal_nexpose", "total"), 0))
    iot_nexpose_total = _as_int(_get_nested(data, ("iot_iomt_nexpose", "total"), 0))

    if external_nexpose_total > 0:
        add_required("external_nexpose_xml.xml")

    if internal_nexpose_total > 0:
        add_required("internal_nexpose_xml.xml")

    if iot_nexpose_total > 0:
        add_required("iot_nexpose_xml.xml")

    if has_workbook_section("firewall"):
        firewall_source = _get_nested(data, ("fierwall",), None)
        if not isinstance(firewall_source, dict):
            firewall_source = _get_nested(data, ("firewall",), {})
        if _as_int(_get_nested(firewall_source or {}, ("unique",), 0)) > 0:
            add_required("firewall_xml.xml")

        firewall_devices = _get_nested(firewall_source or {}, ("devices",), []) or []
        if isinstance(firewall_devices, list):
            for index, device in enumerate(firewall_devices, start=1):
                if isinstance(device, dict):
                    device_name = device.get("name") or device.get("device") or device.get("hostname")
                else:
                    device_name = device
                display_name = _as_str(device_name).strip() or f"Device {index}"
                base_slug = _slugify_identifier("firewall", display_name)
                if not base_slug:
                    base_slug = f"firewall_device_{index}"
                slug = f"{base_slug}_type"
                add_question(
                    key=f"{slug}",
                    label="Firewall Type",
                    field_class=forms.CharField,
                    section="Firewall",
                    subheading=display_name,
                    widget=forms.TextInput(attrs={"class": "form-control"}),
                    entry_slug=base_slug,
                    entry_field_key="type",
                )

        add_question(
            key="firewall_periodic_reviews",
            label="Did the client indicate they were performing periodic reviews for firewall rule business justifications?",
            field_class=forms.ChoiceField,
            section="Firewall",
            choices=YES_NO_CHOICES,
            widget=forms.RadioSelect,
        )

    # Active Directory risk questions
    if has_workbook_section("ad"):
        ad_domains = _get_nested(data, ("ad", "domains"), []) or []
        if isinstance(ad_domains, list):
            for record in ad_domains:
                domain = _extract_domain(record)
                if not domain:
                    continue
                slug = _slugify_identifier("ad", domain)
                for metric_key, metric_label in AD_DOMAIN_METRICS:
                    question_key = f"{slug}_{metric_key}"
                    add_question(
                        key=question_key,
                        label=metric_label,
                        field_class=forms.ChoiceField,
                        section="Active Directory",
                        subheading=domain,
                        choices=RISK_CHOICES,
                        widget=forms.RadioSelect,
                        entry_slug=slug,
                        entry_field_key=metric_key,
                    )

    # Password policy risk
    if has_workbook_section("password"):
        password_policies = _get_nested(data, ("password", "policies"), []) or []
        add_question(
            key="password_additional_controls",
            label="Did the client indicate they had additional password controls in place (i.e. blacklisting)?",
            field_class=forms.ChoiceField,
            section="Password Policies",
            choices=YES_NO_CHOICES,
            widget=forms.RadioSelect,
        )

        add_question(
            key="password_enforce_mfa_all_accounts",
            label="Did the client indicate they enforce MFA on all accounts?",
            field_class=forms.ChoiceField,
            section="Password Policies",
            choices=YES_NO_CHOICES,
            widget=forms.RadioSelect,
        )

        if isinstance(password_policies, list):
            for policy in password_policies:
                domain_name = None
                if isinstance(policy, dict):
                    domain_name = policy.get("domain_name") or policy.get("domain")
                domain_name = _as_str(domain_name) or "Unnamed Domain"
                slug = _slugify_identifier("password", domain_name)
                add_question(
                    key=f"{slug}_risk",
                    label=(
                        "What is the risk you assign for the passwords cracked in the "
                        f"'{domain_name}' domain? (High, Medium or Low)"
                    ),
                    field_class=forms.ChoiceField,
                    section="Password Policies",
                    subheading=domain_name,
                    choices=RISK_CHOICES,
                    widget=forms.RadioSelect,
                    entry_slug=slug,
                    entry_field_key="risk",
                )

    # Endpoint risk questions
    if has_workbook_section("endpoint"):
        endpoint_domains = _get_nested(data, ("endpoint", "domains"), []) or []
        if isinstance(endpoint_domains, list):
            for entry in endpoint_domains:
                domain = None
                if isinstance(entry, dict):
                    domain = entry.get("domain") or entry.get("name")
                    if isinstance(domain, dict):
                        domain = domain.get("domain") or domain.get("name")
                domain = _as_str(domain) or "Unnamed Domain"
                slug = _slugify_identifier("endpoint", domain)
                add_question(
                    key=f"{slug}_av_gap",
                    label=(
                        f"What is the risk you associate with the number of systems without active, up-to-date security software "
                        f"found in the '{domain}' domain? (High, Medium, Low)"
                    ),
                    field_class=forms.ChoiceField,
                    section="Endpoint",
                    subheading=domain,
                    choices=RISK_CHOICES,
                    widget=forms.RadioSelect,
                    entry_slug=slug,
                    entry_field_key="av_gap",
                )
                add_question(
                    key=f"{slug}_open_wifi",
                    label=(
                        f"What is the risk you associate with the Open WiFi networks accessed on machines in the '{domain}' domain? "
                        f"(High, Medium, Low)"
                    ),
                    field_class=forms.ChoiceField,
                    section="Endpoint",
                    subheading=domain,
                    choices=RISK_CHOICES,
                    widget=forms.RadioSelect,
                    entry_slug=slug,
                    entry_field_key="open_wifi",
                )

    if has_workbook_section("wireless"):
        # Wireless baseline questions
        for key_suffix, label in WIRELESS_NETWORK_TYPES:
            question_key = f"wireless_{key_suffix}_risk"
            add_question(
                key=question_key,
                label=label,
                field_class=forms.ChoiceField,
                section="Wireless",
                subheading="Wireless Network Risk",
                choices=RISK_CHOICES,
                widget=forms.RadioSelect,
            )

        add_question(
            key="wireless_psk_rotation_concern",
            label="Are you concerned the PSK(s) is not changed periodically (or when people leave the org)? (Yn)",
            field_class=forms.ChoiceField,
            section="Wireless",
            subheading="Wireless Network Risk",
            choices=YES_NO_CHOICES,
            widget=forms.RadioSelect,
        )

        weak_psk_value = _as_str(_get_nested(data, ("wireless", "weak_psks"), "")).lower()
        if weak_psk_value and weak_psk_value != "no":
            add_question(
                key="wireless_psk_weak_reasons",
                label="Why was the wireless PSK(s) weak?",
                field_class=SummaryMultipleChoiceField,
                section="Wireless",
                subheading="PSK Analysis",
                choices=WEAK_PSK_CHOICES,
                widget=forms.CheckboxSelectMultiple,
                field_kwargs={"summary_map": WEAK_PSK_SUMMARY_MAP},
            )
            add_question(
                key="wireless_psk_masterpass",
                label="Was the PSK(s) contained in masterpass? (yN)",
                field_class=forms.ChoiceField,
                section="Wireless",
                subheading="PSK Analysis",
                choices=YES_NO_CHOICES,
                widget=forms.RadioSelect,
                initial="no",
            )
            add_question(
                key="wireless_psk_masterpass_ssids",
                label="Enter the network SSID(s) with PSK's contained in 'masterpass'",
                field_class=MultiValueField,
                section="Wireless",
                subheading="PSK Analysis",
            )

        wep_confirm = _as_str(_get_nested(data, ("wireless", "wep_inuse", "confirm"), "")).lower()
        if wep_confirm == "yes":
            add_question(
                key="wireless_wep_crack_minutes",
                label="How many minutes did it take to crack the WEP key(s)?",
                field_class=forms.CharField,
                section="Wireless",
                subheading="WEP Networks",
                widget=forms.TextInput(attrs={"class": "form-control"}),
            )
            add_question(
                key="wireless_wep_ssids",
                label="Enter the WEP wireless network SSID(s)",
                field_class=MultiValueField,
                section="Wireless",
                subheading="WEP Networks",
            )

        add_question(
            key="wireless_segmentation_tested",
            label="Did you test open/guest wireless network segmentation?",
            field_class=forms.BooleanField,
            section="Wireless",
            subheading="Segmentation",
            help_text="Select if segmentation testing was performed.",
        )
        add_question(
            key="wireless_segmentation_ssids",
            label="Enter the Guest/Open wireless network SSID(s)",
            field_class=MultiValueField,
            section="Wireless",
            subheading="Segmentation",
            help_text="Provide one or more SSIDs discovered during segmentation testing.",
        )

    if has_workbook_section("cloud_config") and _as_int(
        _get_nested(data, ("cloud_config", "fail"), 0)
    ) > 0:
        add_question(
            key="cloud_config_risk",
            label="What is the risk you would assign to the Cloud Management fails? (High, Medium, Low)",
            field_class=forms.ChoiceField,
            section="Cloud Configuration",
            choices=RISK_CHOICES,
            widget=forms.RadioSelect,
        )

    if has_workbook_section("system_config") and _as_int(
        _get_nested(data, ("system_config", "total_fail"), 0)
    ) > 0:
        add_question(
            key="system_config_risk",
            label="What is the risk you would assign to the System Configuration fails? (High, Medium, Low)",
            field_class=forms.ChoiceField,
            section="System Configuration",
            choices=RISK_CHOICES,
            widget=forms.RadioSelect,
        )

    overall_risk_value = _as_str(risks.get("overall_risk")) if isinstance(risks, dict) else ""
    overall_risk_display = overall_risk_value or "Unknown"
    add_question(
        key="overall_risk_major_issues",
        label=(
            "What were the 'major' issues associated with the Overall Risk of "
            f"{overall_risk_display}?"
        ),
        field_class=MultiValueField,
        section="Overall Risk",
    )

    return questions, required_files
SECTION_KEY_MAP = {
    "General": "general",
    "Intelligence": "intelligence",
    "IoT/IoMT": "iot_iomt",
    "Firewall": "firewall",
    "Active Directory": "ad",
    "Password Policies": "password",
    "Endpoint": "endpoint",
    "Wireless": "wireless",
    "DNS": "dns",
    "Overall Risk": "overall_risk",
}

SECTION_ENTRY_FIELD_MAP = {
    "ad": "domain",
    "password": "domain",
    "endpoint": "domain",
    "dns": "domain",
    "firewall": "name",
}

DNS_SOA_FIELD_CHOICES = (
    ("serial", "serial"),
    ("expire", "expire"),
    ("mname", "mname"),
    ("minimum", "minimum"),
    ("refresh", "refresh"),
    ("retry", "retry"),
)

