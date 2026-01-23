"""Utilities for parsing uploaded project data files."""

from __future__ import annotations

# Standard Libraries
import base64
import csv
import io
import logging
import os
import re
import unicodedata
from base64 import b64decode
from collections import Counter, OrderedDict
from collections import abc
from typing import Any, Callable, Dict, Iterable, List, Mapping, Optional, Set, Tuple

try:  # pragma: no cover - optional hardening dependency
    from defusedxml import ElementTree as DefusedElementTree
except ImportError:  # pragma: no cover - fallback when defusedxml is unavailable
    DefusedElementTree = None

if DefusedElementTree is None:  # pragma: no cover - handled when defusedxml missing
    from xml.etree import ElementTree as ElementTree
else:  # pragma: no cover - exercised indirectly via parser tests
    ElementTree = DefusedElementTree

from django.apps import apps
from django.core.files.base import File
from django.db.utils import OperationalError, ProgrammingError

from xlsxwriter.workbook import Workbook

if False:  # pragma: no cover - typing only
    from ghostwriter.rolodex.models import Project, ProjectDataFile  # noqa: F401

from ghostwriter.commandcenter.models import OpenAIConfiguration
from ghostwriter.modules.openai_client import submit_prompt_to_assistant
from ghostwriter.rolodex.ip_artifacts import IP_ARTIFACT_DEFINITIONS, parse_ip_text
from ghostwriter.rolodex.constants import BURP_XML_FILE_NAME_KEY, FIREWALL_XML_FILE_NAME_KEY
from ghostwriter.rolodex.workbook import AD_DOMAIN_METRICS
from ghostwriter.rolodex.ad_thresholds import AD_THRESHOLD_DEFAULTS

logger = logging.getLogger(__name__)


EXCEL_CELL_CHARACTER_LIMIT = 32766

DEFAULT_DNS_RECOMMENDATION_MAP: Dict[str, str] = {
    "One or more SOA fields are outside recommended ranges": "update SOA fields to follow best practice",
    "Less than 2 nameservers exist": "assign a minimum of 2 nameservers for the domain",
    "More than 8 nameservers exist": "limit the number of nameservers to less than 8",
    "Some nameservers have duplicate addresses": "ensure all nameserver addresses are unique",
    "Some nameservers did not respond": "ensure all nameservers respond to queries",
    "Some nameservers respond recursive queries": "configure nameservers to not respond to recursive queries",
    "Some nameservers do not respond to TCP queries": "ensure all nameservers respond to TCP queries",
    "Some nameservers return version numbers": "configure nameservers to not return version numbers",
    "Some nameservers provide a differing list of nameservers": "ensure all nameservers provide the same list of nameservers",
    "Some nameserver addresses are private": "ensure all nameserver addresses are public",
    "Some nameservers do not provide a SOA record for the zone": "ensure all nameservers provide a SOA record for the zone",
    "Some nameserver SOAs have differing serial numbers": "ensure all nameserver SOA serial numbers match",
    "No MX records exist within the zone": "implement an MX record and corrisponding mail server",
    "Only one MX record exists within the zone": "consider implementing a secondary MX record and corresponding mail server",
    "MX record resolves to a single IP address": "consider implementing a secondary MX record and corresponding mail server",
    "Some addresses referenced by MX records do not have matching reverse DNS entries": "create PTR records for MX IP addresses",
    "Some mailserver IP addresses are private": "ensure all listed mailserver IP addresses are public",
    "Some connections to Mailservers port 25 failed": "ensure all mailservers allow access",
    "Some mailservers appear to be open relays": "configure mailservers to not allow open relaying",
    "This domain does not have DNSSEC records": "consider implementing DNSSEC",
    "The DNSKEY does not appear to be valid for the domain": "ensure a valid DNSKEY record exists",
    "The domain does not have an SPF record": "consider implementing a SPF record",
    "The SPF value does not allow mail delivery from all mailservers in the domain": "update the SPF record to include all authorized mail servers",
    "The SPF record contains the overly permissive modifier '+all'": "remove the '+all' modifier",
}

DEFAULT_DNS_CAP_MAP: Dict[str, str] = {
    "One or more SOA fields are outside recommended ranges": "Get-SOA $domname",
    "Less than 2 nameservers exist": "Assign a minimum of 2 nameservers for the domain",
    "More than 8 nameservers exist": "Limit the number of nameservers to less than 8",
    "Some nameservers have duplicate addresses": "Ensure all nameserver addresses are unique",
    "Some nameservers did not respond": "Ensure all nameservers respond to queries",
    "Some nameservers respond recursive queries": "Configure nameservers to not respond to recursive queries",
    "Some nameservers do not respond to TCP queries": "Ensure all nameservers respond to TCP queries",
    "Some nameservers return version numbers": "Configure nameservers to not return version numbers",
    "Some nameservers provide a differing list of nameservers": "Ensure all nameservers provide the same list of nameservers",
    "Some nameserver addresses are private": "Ensure all nameserver addresses are public",
    "Some nameservers do not provide a SOA record for the zone": "Ensure all nameservers provide a SOA record for the zone",
    "Some nameserver SOAs have differing serial numbers": "Ensure all nameserver SOA serial numbers match",
    "No MX records exist within the zone": "Implement an MX record and corrisponding mail server",
    "Only one MX record exists within the zone": "Consider implementing a secondary MX record and corresponding mail server",
    "MX record resolves to a single IP address": "Consider implementing a secondary mail server and corresponding MX record",
    "Hostnames referenced by MX records resolve to the same IP address": "Consider implementing a secondary mail server and corresponding MX record",
    "Some addresses referenced by MX records do not have matching reverse DNS entries": "Create PTR records for MX IP addresses",
    "Some mailserver IP addresses are private": "Ensure all listed mailserver IP addresses are public",
    "Some connections to Mailservers port 25 failed": "Ensure all mailservers allow access",
    "Some mailservers appear to be open relays": "Configure mailservers to not allow open relaying",
    "This domain does not have DNSSEC records": "Consider implementing DNSSEC",
    "The DNSKEY does not appear to be valid for the domain": "Ensure a valid DNSKEY record exists",
    "The domain does not have an SPF record": "Consider implementing a SPF record",
    "The SPF value does not allow mail delivery from all mailservers in the domain": "Update the SPF record to include all authorized mail servers",
    "The SPF record contains the overly permissive modifier '+all'": "Remove the '+all' modifier",
}

DEFAULT_PASSWORD_CAP_MAP: Dict[str, str] = {
    "max_age": (
        "Change 'Maximum Age' from {{ max_age }} to == 0 to align with NIST recommendations "
        "to not force users to arbitrarily change passwords based solely on age"
    ),
    "min_age": "Change 'Minimum Age' from {{ min_age }} to >= 1 and < 7",
    "min_length": "Change 'Minimum Length' from {{ min_length }} to >= 8",
    "history": "Change 'History' from {{ history }} to >= 10",
    "lockout_threshold": "Change 'Lockout Threshold' from {{ lockout_threshold }} to > 0 and <= 6",
    "lockout_duration": "Change 'Lockout Duration' from {{ lockout_duration }} to >= 30 or admin unlock",
    "lockout_reset": "Change 'Lockout Reset' from {{ lockout_reset }} to >= 30",
    "complexity_enabled": (
        "Change 'Complexity Required' from TRUE to FALSE and implement additional password selection controls "
        "such as blacklists"
    ),
}

_CAP_PLACEHOLDER_PATTERN = re.compile(r"\{\{\s*([A-Za-z0-9_]+)\s*\}\}")

WEB_ISSUE_PROMPT_TEMPLATE = (
    "For '{{ .issue }}' an attacker could [short description of exploitation], "
    "which could then allow them to [short description of impact of successful exploitation]."
)

DEFAULT_GENERAL_CAP_MAP: Dict[str, Tuple[str, int]] = {
    "Weak passwords in use": (
        "Force all accounts whose password was cracked to change their password. "
        "Provide training on secure password creation",
        7,
    ),
    "LANMAN password hashing enabled": (
        "Configure the domain to disable LANMAN password hashing. Force accounts with stored "
        "LANMAN password hashes to change their password",
        5,
    ),
    "Fine-grained Password Policies not defined": (
        "Define and assign Fine-grained Password Policies for security groups based on the risk "
        "associated with an account compromise.\n(Secure Password policy & procedures)",
        4,
    ),
    "Additional password controls not implemented": (
        "Implement additional password controls as recommended by NIST for blacklisting and/or "
        "repetitive/sequential characters, which are not available natively in Active Directory\n"
        "(Secure Password policy & procedures)",
        4,
    ),
    "MFA not enforced for all accounts": (
        "Enforce MFA for all accounts as recommended by NIST",
        4,
    ),
    "Systems without active up-to-date security software": (
        "Review the systems identified without active, current security software and remediate as appropriate",
        5,
    ),
    "Systems connecting to Open WiFi networks": (
        "Review the systems that have connected to Open WiFi networks to ensure appropriate protections are in place",
        5,
    ),
    "Domain Functionality Level less than 2008": (
        "Upgrade the domain functionality level to 2008 or greater.",
        5,
    ),
    "Number of Disabled Accounts": (
        "Delete accounts that are no longer needed. Additionally, develop a policy and procedure to delete accounts "
        "that have remained disabled for 90 or more days.\r(Account Management policy & procedures)",
        5,
    ),
    "Number of Systems with Logged in Generic Accounts": (
        "Review systems with 'generic account' login activity to ensure it is authorized and/or intended",
        5,
    ),
    "Number of 'Generic Accounts'": (
        "Unique user accounts should always be used to access data and systems; deviations from this must be documented "
        "including a valid business justification. Additionally, extra security controls should be enforced on any "
        "shared or generic accounts as appropriate.\r(Account Management policy & procedures)",
        5,
    ),
    "Potentially Inactive Accounts": (
        "Review the potentially inactive accounts and disable or delete those no longer needed. Additionally, it should be "
        "recorded why valid account users have not logged into the domain in a timely fashion.\r(Account Management policy "
        "& procedures)",
        5,
    ),
    "Accounts with Passwords that Never Expire": (
        "Company policy should force users to change their passwords minimally every 90 days. All groups should follow this "
        "policy (except service accounts which should typically force or remind administrators to change these account "
        "passwords every six to twelve months). If service account password expiration dates are handled differently from "
        "user accounts, company policy must dictate that in writing.\r(Account Management policy & procedures)",
        5,
    ),
    "Accounts with Expired Passwords": (
        "Review accounts with expired passwords and disable or delete those no longer needed.\r(Account Management policy "
        "& procedures)",
        5,
    ),
    "Number of Enterprise Admins": (
        "Members of the Enterprise Admins group should be restricted to no more than 3 accounts.\r(Account Management "
        "policy & procedures)",
        5,
    ),
    "Number of Domain Admins": (
        "Members of the Domain Admins group should be restricted to the least number of accounts possible.\r(Account "
        "Management policy & procedures)",
        5,
    ),
    "Databases allowing open access": (
        "Review the data contained in databases allowing open access to determine the sensitivity level and thus additional "
        "security controls.",
        5,
    ),
    "Default SNMP community strings & default credentials in use": (
        "Configure all systems to use unique credentials, including SNMP community strings",
        5,
    ),
    "OSINT identified assets": (
        "Review the assets identified to ensure they are known and managed appropriately",
        1,
    ),
    "Exposed buckets identified": (
        "Review the identified buckets to ensure they are not exposing sensitive information",
        1,
    ),
    "Exposed Credentials identified": (
        "Review the exposed credentials identified and take appropriate action",
        1,
    ),
    "Potential domain squatters identified": (
        "Review the domains identified as potentially being used for domain typo-squatting and take appropriate action",
        1,
    ),
    "PSK’s in use on wireless networks": (
        "Ensure all Pre-Shared Keys (PSK) in use for wireless networks are changed periodically or whenever someone with "
        "knowledge of the keys leaves the company",
        3,
    ),
    "Weak PSK's in use": (
        "Change the PSK's to be of sufficient length & entropy; ensure PSK's are not "
        "based on Company information or dictionary words",
        4,
    ),
    "Potentially Rogue Access Points": (
        "Investigate the potentially rogue access points identified to ensure they are not connected to the internal network",
        5,
    ),
    "WEP in use on wireless networks": (
        "Disable WEP and utilize WPA2 at a minimum",
        9,
    ),
    "Open wireless network connected to the Internal network": (
        "Properly segment the open wireless network from the Internal network",
        9,
    ),
    "802.1x authentication not implemented for wireless networks": (
        "Review if 802.1x authentication is possible with the existing Access Points in use. If so, transition SSID’s to utilize "
        "802.1x authentication instead of the PSK’s. If not, investigate replacing the devices",
        3,
    ),
    "Business justification for firewall rules": (
        "Review all firewall rules to ensure there is a valid business justification; document the business justification and "
        "network access requirements",
        5,
    ),
}

DEFAULT_PASSWORD_COMPLIANCE_MATRIX: Dict[str, Dict[str, Any]] = {
    "max_age": {
        "data_type": "numeric",
        "rule": {
            "operator": "any",
            "rules": [
                {"operator": "ne", "value": 0},
                {"operator": "lt", "value": 365},
            ],
        },
    },
    "min_age": {
        "data_type": "numeric",
        "rule": {
            "operator": "any",
            "rules": [
                {"operator": "lt", "value": 1},
                {"operator": "gt", "value": 7},
            ],
        },
    },
    "min_length": {
        "data_type": "numeric",
        "rule": {"operator": "lt", "value": 8},
    },
    "history": {
        "data_type": "numeric",
        "rule": {"operator": "lt", "value": 10},
    },
    "lockout_threshold": {
        "data_type": "numeric",
        "rule": {
            "operator": "any",
            "rules": [
                {"operator": "eq", "value": 0},
                {"operator": "gt", "value": 6},
            ],
        },
    },
    "lockout_duration": {
        "data_type": "numeric",
        "rule": {
            "operator": "all",
            "rules": [
                {"operator": "gte", "value": 1},
                {"operator": "lte", "value": 29},
            ],
        },
    },
    "lockout_reset": {
        "data_type": "numeric",
        "rule": {"operator": "lt", "value": 30},
    },
    "complexity_enabled": {
        "data_type": "string",
        "rule": {
            "operator": "any",
            "rules": [
                {"operator": "eq", "value": "TRUE"},
                {"operator": "eq", "value": "YES"},
            ],
        },
    },
}

DEFAULT_DNS_SOA_CAP_MAP: Dict[str, str] = {
    "serial": "Update to match the 'YYYYMMDDnn' scheme",
    "expire": "Update to a value between 1209600 to 2419200",
    "mname": "Update to a value that is an authoritative name server",
    "minimum": "Update to a value greater than 300",
    "refresh": "Update to a value between 1200 and 43200 seconds",
    "retry": "Update to a value less than or equal to half the REFRESH",
}

DEFAULT_DNS_FINDING_MAP: Dict[str, str] = {
    "One or more SOA fields are outside recommended ranges": "configuring DNS records according to best practice",
    "Less than 2 nameservers exist": "the number/availability of nameservers",
    "More than 8 nameservers exist": "the number/availability of nameservers",
    "Some nameservers have duplicate addresses": "the number/availability of nameservers",
    "Some nameservers did not respond": "the number/availability of nameservers",
    "Some nameservers respond recursive queries": "the number/availability of nameservers",
    "Some nameservers do not respond to TCP queries": "the number/availability of nameservers",
    "Some nameservers return version numbers": "information leakage by nameservers",
    "Some nameservers provide a differing list of nameservers": "the number/availability of nameservers",
    "Some nameserver addresses are private": "the number/availability of nameservers",
    "Some nameservers do not provide a SOA record for the zone": "configuring DNS records according to best practice",
    "Some nameserver SOAs have differing serial numbers": "configuring DNS records according to best practice",
    "No MX records exist within the zone": "email delivery for the domain",
    "Only one MX record exists within the zone": "email delivery for the domain",
    "MX record resolves to a single IP address": "email delivery for the domain",
    "Some addresses referenced by MX records do not have matching reverse DNS entries": "email delivery for the domain",
    "Some mailserver IP addresses are private": "email delivery for the domain",
    "Some connections to Mailservers port 25 failed": "email delivery for the domain",
    "Some mailservers appear to be open relays": "email delivery for the domain",
    "This domain does not have DNSSEC records": "protection of DNS records",
    "The DNSKEY does not appear to be valid for the domain": "protection of DNS records",
    "The domain does not have an SPF record": "email delivery for the domain",
    "The SPF value does not allow mail delivery from all mailservers in the domain": "email delivery for the domain",
    "The SPF record contains the overly permissive modifier '+all'": "email delivery for the domain",
}

DNS_IMPACT_MAP: Dict[str, str] = {
    "One or more SOA fields are outside recommended ranges": "Incorrect SOA settings can disrupt DNS propagation, caching, and zone transfers, leading to stale or inconsistent domain data.",
    "Less than 2 nameservers exist": "Having fewer than two nameservers creates a single point of failure, increasing risk of domain outage if the sole server becomes unreachable.",
    "More than 8 nameservers exist": "Excessive nameservers increase administrative complexity and the likelihood of inconsistent configurations or stale records.",
    "Some nameservers have duplicate addresses": "Duplicate nameserver IPs reduce redundancy and can lead to query failures during DNS resolution.",
    "Some nameservers did not respond": "Non-responsive nameservers degrade DNS availability and can cause intermittent domain resolution failures.",
    "Some nameservers respond recursive queries": "Allowing recursion on authoritative servers exposes them to cache poisoning and amplification attacks.",
    "Some nameservers do not respond to TCP queries": "Failure to handle TCP queries can break large DNS responses (e.g., DNSSEC), reducing reliability and availability.",
    "Some nameservers return version numbers": "Exposing version information allows attackers to identify and exploit known vulnerabilities in the DNS software.",
    "Some nameservers provide a differing list of nameservers": "Inconsistent NS records cause DNS resolution instability and may enable spoofing or cache corruption.",
    "Some nameserver addresses are private": "Private IP addresses make external resolution impossible and indicate misconfigured or non-routable infrastructure.",
    "Some nameservers do not provide a SOA record for the zone": "Missing SOA records prevent proper zone management and replication, causing inconsistencies between servers.",
    "Some nameserver SOAs have differing serial numbers": "Mismatched SOA serials suggest replication issues that can result in outdated or inconsistent zone data.",
    "No MX records exist within the zone": "Without MX records, the domain cannot receive email, potentially disrupting communication or business operations.",
    "Only one MX record exists within the zone": "A single MX record creates a single point of failure for mail delivery, reducing availability and redundancy.",
    "MX record resolves to a single IP address": "A single IP for mail delivery increases the likelihood of downtime or delivery failure if that host becomes unavailable.",
    "Some addresses referenced by MX records do not have matching reverse DNS entries": "Missing PTR records can cause mail rejection by spam filters and lower sender reputation.",
    "Some mailserver IP addresses are private": "Private IPs on mailservers prevent delivery from external networks and indicate improper public DNS configuration.",
    "Some connections to Mailservers port 25 failed": "Unreachable mailservers degrade or halt inbound email delivery, impacting availability and communication.",
    "Some mailservers appear to be open relays": "Open relays allow unauthorized third parties to send spam, risking blacklisting and abuse of the domain.",
    "This domain does not have DNSSEC records": "Without DNSSEC, DNS responses can be forged, enabling cache poisoning and redirection attacks.",
    "The DNSKEY does not appear to be valid for the domain": "Invalid DNSSEC keys undermine trust and cause validation failures for secure resolvers.",
    "The domain does not have an SPF record": "Lack of SPF allows attackers to spoof emails from the domain, enabling phishing or spam campaigns.",
    "The SPF value does not allow mail delivery from all mailservers in the domain": "An incomplete SPF record causes legitimate emails to be rejected or marked as spam.",
    "The SPF record contains the overly permissive modifier '+all'": "The '+all' modifier allows any host to send mail for the domain, enabling spoofing and abuse.",
}


def _load_mapping(
    model_name: str,
    value_field: str,
    default_map: Dict[str, str],
    *,
    key_field: str = "issue_text",
) -> Dict[str, str]:
    """Return mappings from the database, falling back to defaults."""

    try:
        model = apps.get_model("rolodex", model_name)
    except LookupError:
        return default_map

    try:
        values = model.objects.all().values_list(key_field, value_field)
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return default_map

    mapping = {issue: text for issue, text in values if issue}
    return mapping or default_map


def _default_general_cap_map() -> Dict[str, Dict[str, Any]]:
    """Return a sanitized copy of the default general CAP mapping."""

    return {
        issue: {"recommendation": recommendation, "score": score}
        for issue, (recommendation, score) in DEFAULT_GENERAL_CAP_MAP.items()
    }


def load_general_cap_map() -> Dict[str, Dict[str, Any]]:
    """Return general CAP mappings from the database or fall back to defaults."""

    try:
        model = apps.get_model("rolodex", "GeneralCapMapping")
    except LookupError:
        return _default_general_cap_map()

    try:
        entries = model.objects.all().values(
            "issue_text", "recommendation_text", "score"
        )
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return _default_general_cap_map()

    mapping: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        issue = entry.get("issue_text")
        if not issue:
            continue
        mapping[issue] = {
            "recommendation": entry.get("recommendation_text", ""),
            "score": entry.get("score"),
        }

    return mapping or _default_general_cap_map()


def load_dns_soa_cap_map() -> Dict[str, str]:
    """Return SOA field CAP mappings from the database or fall back to defaults."""

    return _load_mapping(
        "DNSSOACapMapping",
        "cap_text",
        DEFAULT_DNS_SOA_CAP_MAP,
        key_field="soa_field",
    )


def load_password_cap_map() -> Dict[str, str]:
    """Return password policy CAP mappings from the database or fall back to defaults."""

    return _load_mapping(
        "PasswordCapMapping",
        "cap_text",
        DEFAULT_PASSWORD_CAP_MAP,
        key_field="setting",
    )


def _default_ad_threshold_map() -> Dict[str, Dict[str, Any]]:
    """Return a copy of the default AD threshold mapping."""

    return {key: dict(meta) for key, meta in AD_THRESHOLD_DEFAULTS.items()}


def load_ad_threshold_map() -> Dict[str, Dict[str, Any]]:
    """Return AD CAP threshold mappings from the database or fall back to defaults."""

    try:
        model = apps.get_model("rolodex", "ADThresholdMapping")
    except LookupError:
        return _default_ad_threshold_map()

    try:
        entries = model.objects.all().values(
            "key", "label", "issue_text", "threshold_type", "value"
        )
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return _default_ad_threshold_map()

    mapping: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        key = entry.get("key")
        if not key:
            continue
        defaults = AD_THRESHOLD_DEFAULTS.get(key, {})
        merged = dict(defaults)
        merged.update(
            {
                "label": entry.get("label") or defaults.get("label") or key,
                "issue": entry.get("issue_text") or defaults.get("issue"),
                "threshold_type": entry.get("threshold_type")
                or defaults.get("threshold_type"),
                "value": entry.get("value")
                if entry.get("value") is not None
                else defaults.get("value"),
            }
        )
        mapping[key] = merged

    return mapping or _default_ad_threshold_map()


def _normalize_matrix_key(value: Any) -> Optional[str]:
    """Return a normalized lookup key for matrix entries."""

    if value in (None, ""):
        return None
    normalized = " ".join(str(value).strip().lower().split())
    return normalized or None


def load_vulnerability_matrix() -> Dict[str, Dict[str, str]]:
    """Return vulnerability matrix entries from the database."""

    try:
        model = apps.get_model("rolodex", "VulnerabilityMatrixEntry")
    except LookupError:  # pragma: no cover - defensive guard
        return {}

    try:
        entries = model.objects.all().values(
            "vulnerability",
            "action_required",
            "remediation_impact",
            "vulnerability_threat",
            "category",
        )
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return {}

    matrix: Dict[str, Dict[str, str]] = {}
    for entry in entries:
        key = _normalize_matrix_key(entry.get("vulnerability"))
        if not key:
            continue
        matrix[key] = {
            "action_required": entry.get("action_required") or "",
            "remediation_impact": entry.get("remediation_impact") or "",
            "vulnerability_threat": entry.get("vulnerability_threat") or "",
            "category": entry.get("category") or "",
        }

    return matrix


def load_web_issue_matrix() -> Dict[str, Dict[str, str]]:
    """Return web issue matrix entries from the database."""

    try:
        model = apps.get_model("rolodex", "WebIssueMatrixEntry")
    except LookupError:  # pragma: no cover - defensive guard
        return {}

    try:
        entries = model.objects.all().values("title", "impact", "fix")
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return {}

    matrix: Dict[str, Dict[str, str]] = {}
    for entry in entries:
        key = _normalize_matrix_key(entry.get("title"))
        if not key:
            continue
        matrix[key] = {
            "impact": entry.get("impact") or "",
            "fix": entry.get("fix") or "",
        }

    return matrix


def _normalize_issue_name(value: str) -> str:
    """Normalize Burp issue names for grouping and matrix lookups."""

    if "Vulnerable Software detected" in value:
        return "Vulnerable Software detected"
    if "PostgreSQL injection" in value:
        return "SQL injection"
    if "SQL Server injection" in value:
        return "SQL injection"
    return value


def _get_matrix_entry(
    lookup_title: str, web_issues_matrix: Optional[Mapping[str, Dict[str, str]]]
) -> Optional[Dict[str, str]]:
    """Return a web issue matrix entry matching ``lookup_title`` when available."""

    if not web_issues_matrix:
        return None

    normalized = _normalize_matrix_key(lookup_title)
    if not normalized:
        return None

    if isinstance(web_issues_matrix, dict):
        entry = web_issues_matrix.get(normalized)
        if entry:
            return entry

    for _, entry in getattr(web_issues_matrix, "items", lambda: [])():
        if not isinstance(entry, dict):
            continue
        issue_key = _normalize_matrix_key(entry.get("issue"))
        if issue_key and issue_key == normalized:
            return entry

    return None


def _compute_lookup_title(issue_name: str) -> str:
    """Derive the lookup title for matrix resolution."""

    if " includes a vulnerable version of the library " in issue_name:
        return "includes a vulnerable version of the library"
    if "Vulnerable version of the library " in issue_name:
        return "includes a vulnerable version of the library"
    if "Detected Deserialization" in issue_name:
        return "Detected Deserialization"
    if " Vulnerable Software detected" in issue_name or "Vulnerable version of " in issue_name:
        return "Vulnerable Software detected"
    if "Cross-Site Request Forgery (CSRF)" in issue_name:
        return "Cross-site request forgery"
    return issue_name


def _clean_burp_text(text: str) -> str:
    """Clean Burp XML strings into normalized plain text."""

    replacements = {
        "<p>": "",
        "</p>": "\n",
        "<br>": "\n",
        "</br>": "\n",
        "<br/>": "\n",
        "<b>": "'",
        "</b>": "'",
        "<i>": "'",
        "</i>": "'",
        "<pre>": "",
        "</pre>": "\n",
        "&lt;": "<",
        "&gt;": ">",
        "&amp;": "&",
        "&quote;": "'",
        "&quot;": "'",
        "<ul>": "\n",
        "</ul>": "",
        "<li>": "",
        "</li>": "\n",
        "<table>": "",
        "</table>": "",
        "<tr>": "",
        "</tr>": "\n",
        "<td>": "",
        "</td>": "",
        "<h4>": "",
        "</h4>": ":\n",
        "Burp Suite": "ecfirst",
        "Burp ": "ecfirst ",
    }

    cleaned = text.replace("\n", " ")
    for target, replacement in replacements.items():
        cleaned = cleaned.replace(target, replacement)

    cleaned = re.sub(r"<a href=\".*?\">", "", cleaned)
    cleaned = cleaned.replace("</a>", "")
    cleaned = cleaned.replace(
        "<div style=\"font-size:8px\">This issue was reported by ActiveScan++</div>",
        "",
    )
    cleaned = cleaned.replace(
        "Refer to Backslash Powered Scanning for further details and guidance interpreting results.",
        "",
    )

    while "  " in cleaned:
        cleaned = cleaned.replace("  ", " ")

    return cleaned.strip()


def _compute_burp_score(severity: str, confidence: str) -> float:
    """Calculate Burp numeric score based on severity and confidence."""

    base_map = {"High": 9.0, "Medium": 6.0, "Low": 3.0, "Information": 1.0}
    modifier_map = {"Certain": 1.0, "Firm": 0.0, "Tentative": -1.0}

    base = base_map.get(severity, 0.0)
    modifier = modifier_map.get(confidence, 0.0)
    if severity == "Information":
        modifier = 0.0
    return float(base + modifier)


def _parse_burp_background(issue: ElementTree.Element, issue_name: str) -> str:
    """Return background text for an issue."""

    background_elem = issue.find("issueBackground")
    if background_elem is not None and background_elem.text:
        return _clean_burp_text(background_elem.text)

    if issue_name == "Vulnerable Software detected":
        return (
            "Software that is out of date may contain known unpatched vulnerabilities "
            "that attacker can exploit to compromise the application, system and/or users."
        )

    issue_detail_elem = issue.find("issueDetail")
    if issue_detail_elem is not None and issue_detail_elem.text:
        return _clean_burp_text(issue_detail_elem.text)

    return ""


def _parse_burp_remediation(issue: ElementTree.Element) -> str:
    """Return remediation text or a placeholder when absent."""

    remediation_elem = issue.find("remediationBackground")
    if remediation_elem is not None and remediation_elem.text:
        return _clean_burp_text(remediation_elem.text)

    remediation_detail_elem = issue.find("remediationDetail")
    if remediation_detail_elem is not None and remediation_detail_elem.text:
        return _clean_burp_text(remediation_detail_elem.text)

    return "<<CUSTOM_REMED>>"


def _parse_burp_fix(
    issue_name: str,
    web_issues_matrix: Optional[Mapping[str, Dict[str, str]]],
    *,
    missing_issues: Optional[Set[str]] = None,
    matrix_entry: Optional[Mapping[str, str]] = None,
) -> str:
    """Return fix text from the web issues matrix when present."""

    lookup_title = _compute_lookup_title(issue_name)
    entry = matrix_entry or _get_matrix_entry(lookup_title, web_issues_matrix)
    if entry:
        return entry.get("fix", "")
    if missing_issues is not None:
        missing_issues.add(issue_name)
    return ""


def _parse_burp_impact(
    issue_name: str,
    web_issues_matrix: Optional[Mapping[str, Dict[str, str]]],
    *,
    missing_issues: Optional[Set[str]] = None,
    matrix_entry: Optional[Mapping[str, str]] = None,
) -> str:
    """Return impact text from the web issues matrix when present."""

    lookup_title = _compute_lookup_title(issue_name)
    entry = matrix_entry or _get_matrix_entry(lookup_title, web_issues_matrix)
    if entry:
        return entry.get("impact", "")
    if missing_issues is not None:
        missing_issues.add(issue_name)
    return ""


def _decode_burp_response(issue: ElementTree.Element) -> Optional[str]:
    """Return the decoded response body from the first requestresponse block."""

    for rr in issue.findall("requestresponse"):
        response_elem = rr.find("response")
        if response_elem is None or response_elem.text is None:
            continue

        text = response_elem.text
        if response_elem.get("base64", "false").lower() == "true":
            try:
                decoded = b64decode(text)
                return decoded.decode("utf-8", errors="replace")
            except Exception:  # pragma: no cover - defensive fallback
                return None
        return text

    return None


def _parse_burp_details(issue: ElementTree.Element, issue_name: str) -> str:
    """Return evidence/details text for an issue."""

    issue_detail_elem = issue.find("issueDetail")
    issue_background_elem = issue.find("issueBackground")
    issue_type = (issue.findtext("type") or "").strip()
    path_text = (issue.findtext("path") or "").strip()

    if issue_detail_elem is not None and issue_detail_elem.text:
        if (issue_background_elem is not None and issue_background_elem.text) or (
            issue_name == "Vulnerable Software detected"
        ):
            return _clean_burp_text(issue_detail_elem.text)

    response_text = _decode_burp_response(issue)

    if (
        issue_type == "134217728"
        and issue_name == "Detailed Error Messages Revealed"
        and "ScriptResource.axd" not in path_text
        and "WebResource.axd" not in path_text
        and response_text
    ):
        t1 = response_text.find("</html>")
        if t1 >= 0:
            t2 = t1 + 7
        else:
            t2 = 0
        if t2 == len(response_text):
            opening_index = response_text.find("<html ")
            if opening_index >= 0:
                t2 = opening_index + 6
        snippet = response_text[t2:]
        if len(snippet) >= 32000:
            snippet = f"{snippet[:30000]} ... [SNIP] ..."
        if t1 >= 0:
            return f"... {snippet}"
        return snippet

    if (
        issue_type == "5245344"
        and issue_name == "Frameable response (potential Clickjacking)"
        and "ScriptResource.axd" not in path_text
        and "WebResource.axd" not in path_text
        and response_text
    ):
        header_end = response_text.find("\r\n\r\n")
        headers = response_text[:header_end] if header_end >= 0 else response_text
        return f"{headers}\n... [SNIP] ..."

    return "See response(s)"


def parse_burp_xml_report(
    file_obj: File, web_issues_matrix: Optional[Mapping[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Parse a Burp XML export into normalized finding entries."""

    raw_content = file_obj.read()
    if hasattr(file_obj, "seek"):
        file_obj.seek(0)

    if isinstance(raw_content, bytes):
        xml_content = raw_content.decode("utf-8", errors="replace")
    else:
        xml_content = str(raw_content)

    try:
        root = ElementTree.fromstring(xml_content)
    except ElementTree.ParseError:
        return []

    grouped: Dict[str, Dict[str, Dict[str, Dict[str, Any]]]] = {}
    missing_matrix_issues: Set[str] = set()

    for issue in root.findall("issue"):
        severity = (issue.findtext("severity") or "").strip() or "Low"
        confidence = (issue.findtext("confidence") or "").strip()
        risk_label = "Low" if severity == "Information" else severity
        score = _compute_burp_score(severity, confidence)

        issue_name_raw = (issue.findtext("name") or "").strip()
        issue_name = _normalize_issue_name(issue_name_raw)
        host_name = (issue.findtext("host") or "").strip()
        path = (issue.findtext("location") or issue.findtext("path") or "").strip()
        details = _parse_burp_details(issue, issue_name)

        path_detail_key = f"{path}::{details}"
        risk_key = f"{risk_label}::{score:.1f}"

        lookup_title = _compute_lookup_title(issue_name)
        matrix_entry = _get_matrix_entry(lookup_title, web_issues_matrix)
        if matrix_entry is None:
            missing_matrix_issues.add(issue_name)

        risk_entry = grouped.setdefault(risk_key, {})
        issue_entry = risk_entry.setdefault(issue_name, {})
        host_entry = issue_entry.setdefault(
            host_name,
            {
                "background": _parse_burp_background(issue, issue_name),
                "remediation": _parse_burp_remediation(issue),
                "impact": _parse_burp_impact(
                    issue_name,
                    web_issues_matrix,
                    missing_issues=missing_matrix_issues,
                    matrix_entry=matrix_entry,
                ),
                "fix": _parse_burp_fix(
                    issue_name,
                    web_issues_matrix,
                    missing_issues=missing_matrix_issues,
                    matrix_entry=matrix_entry,
                ),
                "paths": {},
            },
        )

        if path_detail_key in host_entry["paths"]:
            continue

        host_entry["paths"][path_detail_key] = {"path": path, "details": details}

        if not host_entry.get("background"):
            host_entry["background"] = _parse_burp_background(issue, issue_name)
        if not host_entry.get("remediation"):
            host_entry["remediation"] = _parse_burp_remediation(issue)
        if not host_entry.get("impact"):
            host_entry["impact"] = _parse_burp_impact(
                issue_name,
                web_issues_matrix,
                missing_issues=missing_matrix_issues,
                matrix_entry=matrix_entry,
            )
        if not host_entry.get("fix"):
            host_entry["fix"] = _parse_burp_fix(
                issue_name,
                web_issues_matrix,
                missing_issues=missing_matrix_issues,
                matrix_entry=matrix_entry,
            )

    findings: List[Dict[str, Any]] = []

    for risk_key in sorted(grouped.keys()):
        risk_label, score_text = risk_key.split("::", 1)
        try:
            score = float(score_text)
        except (TypeError, ValueError):
            score = float(_coerce_int(score_text) or 0)

        for issue_name, host_map in grouped[risk_key].items():
            for host_name, host_data in host_map.items():
                remediation_text = host_data.get("remediation", "")
                fix_text = host_data.get("fix", "")
                detailed_remediation = (
                    remediation_text if remediation_text != "<<CUSTOM_REMED>>" else fix_text
                )

                for path_detail in host_data.get("paths", {}).values():
                    findings.append(
                        {
                            "Risk": risk_label,
                            "Issue": issue_name,
                            "Impact": host_data.get("impact", ""),
                            "Background": host_data.get("background", ""),
                            "Fix": fix_text,
                            "Host": host_name,
                            "Path": path_detail.get("path", ""),
                            "Evidence": path_detail.get("details", ""),
                            "Detailed Remediation": detailed_remediation,
                            "Score": score,
                        }
                    )

    missing_entries = [
        {"issue": issue_name, "impact": "", "fix": ""}
        for issue_name in sorted(missing_matrix_issues, key=str.lower)
        if issue_name
    ]

    return {"findings": findings, "missing_matrix_entries": missing_entries}


def _default_password_compliance_matrix() -> Dict[str, Dict[str, Any]]:
    """Return a sanitized copy of the default password compliance matrix."""

    return {
        setting: {
            "data_type": str(definition.get("data_type", "numeric")).lower()
            if isinstance(definition, dict)
            else "numeric",
            "rule": definition.get("rule", {}) if isinstance(definition, dict) else {},
        }
        for setting, definition in DEFAULT_PASSWORD_COMPLIANCE_MATRIX.items()
    }


def load_password_compliance_matrix() -> Dict[str, Dict[str, Any]]:
    """Return password compliance rules from the database or fall back to defaults."""

    try:
        model = apps.get_model("reporting", "PasswordComplianceMapping")
    except LookupError:
        return _default_password_compliance_matrix()

    try:
        entries = model.objects.all().values("setting", "data_type", "rule")
    except (OperationalError, ProgrammingError):  # pragma: no cover - defensive guard
        return _default_password_compliance_matrix()

    matrix: Dict[str, Dict[str, Any]] = {}
    for entry in entries:
        setting = entry.get("setting")
        if not setting:
            continue
        data_type = str(entry.get("data_type", "numeric") or "numeric").lower()
        if data_type not in {"numeric", "string"}:
            data_type = "numeric"
        rule = entry.get("rule") if isinstance(entry.get("rule"), (dict, list)) else {}
        matrix[setting] = {"data_type": data_type, "rule": rule}

    return matrix or _default_password_compliance_matrix()


AD_RISK_CONTRIBUTION_PHRASES: Dict[str, str] = {
    "domain_admins": "the number of Domain Admin accounts",
    "enterprise_admins": "the number of Enterprise Admin accounts",
    "expired_passwords": "the number of accounts with expired passwords",
    "passwords_never_expire": "the number of accounts set with passwords that never expire",
    "inactive_accounts": "the number of potentially inactive accounts",
    "generic_accounts": "the number of potentially generic accounts",
    "generic_logins": "the number of generic accounts logged into systems",
    "old_passwords": "the number of accounts with 'old' passwords",
    "disabled_accounts": "the number of disabled accounts",
}


def _get_nested_value(data: Any, path: Iterable[str]) -> Any:
    """Safely fetch a nested value from ``data`` using ``path`` of keys."""

    current: Any = data
    for key in path:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def build_ad_risk_contrib(
    workbook_data: Optional[Dict[str, Any]],
    entries: Optional[Iterable[Dict[str, Any]]],
) -> List[str]:
    """Return risk contribution phrases derived from AD response entries."""

    source_data: Dict[str, Any] = workbook_data if isinstance(workbook_data, dict) else {}

    risk_value = _get_nested_value(
        source_data,
        ("external_internal_grades", "internal", "iam", "risk"),
    )
    risk_text = str(risk_value).strip().lower() if risk_value is not None else ""
    if risk_text not in ("medium", "high"):
        return []

    allowed_values = {"high", "medium"} if risk_text == "medium" else {"high"}

    if isinstance(entries, dict):
        candidate = entries.get("entries")
        if isinstance(candidate, (list, tuple)):
            potential_entries: Iterable[Dict[str, Any]] = candidate
        else:
            potential_entries = []
    elif isinstance(entries, (list, tuple)):
        potential_entries = entries
    elif isinstance(entries, abc.Iterable) and not isinstance(entries, (str, bytes)):
        potential_entries = entries
    else:
        potential_entries = []

    matched_metrics = set()
    for entry in potential_entries:
        if not isinstance(entry, dict):
            continue
        for metric_key in AD_RISK_CONTRIBUTION_PHRASES:
            value = entry.get(metric_key)
            if value is None:
                continue
            text = str(value).strip().lower()
            if text in allowed_values:
                matched_metrics.add(metric_key)

    if not matched_metrics:
        return []

    ordered_metrics = [
        metric_key
        for metric_key, _ in AD_DOMAIN_METRICS
        if metric_key in matched_metrics
    ]

    return [AD_RISK_CONTRIBUTION_PHRASES[key] for key in ordered_metrics]


def _decode_file(file_obj: File) -> Iterable[Dict[str, str]]:
    """Return a DictReader for the provided file object."""

    raw_bytes: bytes

    if hasattr(file_obj, "open"):
        try:
            file_obj.open("rb")
        except FileNotFoundError:
            logger.warning("Uploaded data file is missing from storage", exc_info=True)
            raw_bytes = b""
        else:
            try:
                raw_bytes = file_obj.read() or b""
            finally:
                file_obj.close()
    elif hasattr(file_obj, "read"):
        data = file_obj.read()
        if isinstance(data, str):
            raw_bytes = data.encode("utf-8")
        else:
            raw_bytes = data or b""
    else:
        raw_bytes = b""

    for encoding in ("utf-8-sig", "utf-8", "latin-1"):
        try:
            text = raw_bytes.decode(encoding)
            break
        except UnicodeDecodeError:
            continue
    else:
        text = raw_bytes.decode("utf-8", errors="ignore")

    stream = io.StringIO(text)
    return csv.DictReader(stream)


def _read_binary_file(file_obj: File) -> bytes:
    """Return the raw bytes stored in ``file_obj``."""

    try:
        file_obj.open("rb")
    except FileNotFoundError:
        logger.warning("Uploaded data file is missing from storage", exc_info=True)
        return b""
    try:
        return file_obj.read() or b""
    finally:
        file_obj.close()


def _collapse_whitespace(value: Any) -> str:
    """Return ``value`` with consecutive whitespace collapsed."""

    if value in (None, ""):
        return ""
    text = str(value)
    return re.sub(r"\s+", " ", text).strip()


def _normalize_multiline_text(value: Any) -> str:
    """Return ``value`` with paragraph-friendly spacing."""

    if value in (None, ""):
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    paragraphs: List[str] = []
    current_lines: List[str] = []

    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            if current_lines:
                paragraphs.append(" ".join(current_lines))
                current_lines = []
            continue
        current_lines.append(_collapse_whitespace(stripped))

    if current_lines:
        paragraphs.append(" ".join(current_lines))

    return "\n\n".join(paragraphs)


def _normalize_evidence_text(value: Any) -> str:
    """Return ``value`` formatted for multi-line evidence blocks."""

    if value in (None, ""):
        return ""

    text = str(value).replace("\r\n", "\n").replace("\r", "\n").replace("\t", " ")
    lines: List[str] = []
    for raw_line in text.split("\n"):
        stripped = raw_line.strip()
        if not stripped:
            if lines and lines[-1] != "":
                lines.append("")
            continue
        lines.append(_collapse_whitespace(stripped))

    while lines and lines[-1] == "":
        lines.pop()

    return "\n".join(lines)


def _clean_ascii_text(value: Any) -> str:
    """Return ``value`` normalized to ASCII with collapsed whitespace."""

    if value in (None, ""):
        return ""
    normalized = unicodedata.normalize("NFKD", str(value))
    ascii_text = normalized.encode("ascii", "ignore").decode("ascii")
    return _collapse_whitespace(ascii_text)


def _element_text(element: Optional["ElementTree.Element"]) -> str:
    """Return the string content extracted from ``element``."""

    if element is None:
        return ""
    text = "".join(element.itertext())
    return text.strip()


def _generate_key_variants(key: str) -> List[str]:
    """Return possible attribute/child names for ``key``."""

    variants: Set[str] = set()
    parts = re.split(r"[-_]", key)
    if parts:
        camel = parts[0] + "".join(part.title() for part in parts[1:])
        pascal = "".join(part.title() for part in parts)
        variants.update({camel, pascal})
    variants.update(
        {
            key,
            key.replace("-", ""),
            key.replace("-", "_"),
            key.replace("_", ""),
            key.lower(),
            key.upper(),
            key.title(),
        }
    )
    return [variant for variant in variants if variant]


def _normalize_xml_tag(tag: Optional[str]) -> str:
    """Return a lowercase representation of ``tag`` without namespaces."""

    if not tag:
        return ""
    text = str(tag)
    if "}" in text:
        text = text.rsplit("}", 1)[-1]
    return text.strip().lower()


def _get_element_field(element: Optional["ElementTree.Element"], key: str) -> str:
    """Return ``key`` from ``element`` attributes or child elements."""

    if element is None:
        return ""
    for candidate in _generate_key_variants(key):
        value = element.attrib.get(candidate)
        if value not in (None, ""):
            return str(value).strip()
    for candidate in _generate_key_variants(key):
        child = element.find(candidate)
        if child is not None:
            text = _element_text(child)
            if text:
                return text
    normalized_key = _normalize_xml_tag(key)
    if not normalized_key:
        return ""
    for child in element:
        if _normalize_xml_tag(getattr(child, "tag", "")) == normalized_key:
            text = _element_text(child)
            if text:
                return text
    return ""


def _find_child_element(
    element: Optional["ElementTree.Element"], key: str
) -> Optional["ElementTree.Element"]:
    """Return the first child element that matches ``key`` variants."""

    if element is None:
        return None
    for candidate in _generate_key_variants(key):
        found = element.find(candidate)
        if found is not None:
            return found
    normalized_key = _normalize_xml_tag(key)
    if not normalized_key:
        return None
    for child in element:
        if _normalize_xml_tag(getattr(child, "tag", "")) == normalized_key:
            return child
    return None


def _find_child_elements(
    element: Optional["ElementTree.Element"], key: str
) -> List["ElementTree.Element"]:
    """Return all child elements that match ``key`` variants."""

    if element is None:
        return []
    children: List["ElementTree.Element"] = []
    seen_ids: Set[int] = set()
    for candidate in _generate_key_variants(key):
        if not candidate:
            continue
        for child in element.findall(candidate):
            identifier = id(child)
            if identifier in seen_ids:
                continue
            seen_ids.add(identifier)
            children.append(child)
    normalized_key = _normalize_xml_tag(key)
    if not normalized_key:
        return children
    for child in element:
        identifier = id(child)
        if identifier in seen_ids:
            continue
        if _normalize_xml_tag(getattr(child, "tag", "")) == normalized_key:
            seen_ids.add(identifier)
            children.append(child)
    return children


def _truncate_excel_text(value: str, limit: int = EXCEL_CELL_CHARACTER_LIMIT) -> str:
    """Ensure ``value`` fits within an Excel cell by truncating when needed."""

    text = value or ""
    if len(text) <= limit:
        return text
    ellipsis = "…"
    return text[: max(0, limit - len(ellipsis))] + ellipsis


def _safe_float(value: Any) -> float:
    """Best effort conversion of ``value`` to ``float``."""

    if value in (None, ""):
        return 0.0
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):  # pragma: no cover - defensive
        return 0.0


_VULN_DOWNGRADE_SUBSTRINGS: Tuple[str, ...] = (
    "only if",
    "context-dependent",
    "might allow",
    "when configured as a cgi script",
    "extension in php",
    "where an affected version",
    "the potential for",
    "disputed",
    "are not affected",
    "man-in-the-middle attackers to",
    "which might",
    "in certain configurations",
    "may be vulnerable",
    "could lead to",
    "was configured pointing to",
    "if an intermediary proxy is in use",
    "when using a block cipher algorithm in cipher block chaining (cbc) mode",
    "traffic amplification attacks",
    "conduct drdos attacks",
    "a drdos attack",
    "anonymous root logins should only be allowed from system console",
    "domain name server (dns) amplification attack",
    "while this is not a definite vulnerability on its own",
    "when used in",
    "allows local users to",
    "allows user-assisted remote attackers",
    "on android",
    "with physical access",
    "physically proximate attackers",
    "potentially exploitable",
    "requires local system access",
)

_VULN_DOWNGRADE_PATTERNS = [
    re.compile(pattern, re.IGNORECASE)
    for pattern in (
        r"function in the .* extension",
        r"when\s+.+?\s+is\s+used",
        r"when\s+.+?\s+are\s+used",
        r"when\s+.+?\s+is\s+enabled",
        r"when\s+.+?\s+setting\s+is\s+disabled",
        r"when\s+.+?\s+are\s+enabled",
        r"when\s+the\s+.+?\s+is\s+in\s+place",
        r"when\s+.+?\s+is\s+being\s+used",
        r"with\s+.+?\s+enabled",
    )
]

_VULN_DOWNGRADE_PHRASES = (
    "a carefully crafted, invalid isakmp cert request packet will cause the isakmpd daemon to attempt an out-of-bounds read, crashing the service.",
    "a carefully crafted, invalid isakmp delete packet with a very large number of spi's will cause the isakmpd daemon to attempt an out-of-bounds read, crashing the service.",
)


def _should_adjust_vuln_code(description: str) -> bool:
    """Return ``True`` when ``description`` indicates a potential finding."""

    if not description:
        return False
    desc_lower = description.lower()
    if any(token in desc_lower for token in _VULN_DOWNGRADE_SUBSTRINGS):
        return True

    if "potentially" in desc_lower and "timestamp response" not in desc_lower:
        return True

    if "on os x" in desc_lower and not any(
        exclusion in desc_lower for exclusion in ("adobe flash", "adobe air")
    ):
        return True
    if "on linux" in desc_lower and not any(
        exclusion in desc_lower for exclusion in ("adobe flash", "adobe air")
    ):
        return True
    if "on windows" in desc_lower and not any(
        exclusion in desc_lower for exclusion in ("adobe flash", "adobe air")
    ):
        return True

    if "when running on" in desc_lower or "when running with" in desc_lower:
        return True

    if "when using a block cipher algorithm in cipher block chaining (cbc) mode" in desc_lower:
        return True

    if any(phrase in desc_lower for phrase in _VULN_DOWNGRADE_PHRASES):
        return True

    for pattern in _VULN_DOWNGRADE_PATTERNS:
        if pattern.search(description):
            return True

    return False


def _adjust_vulnerability_code(code: str, description: str) -> str:
    """Adjust Nexpose test codes based on descriptive context."""

    normalized = (code or "").upper()
    if normalized in {"VV", "VE"} and _should_adjust_vuln_code(description):
        normalized = "VP"
    if normalized == "VV":
        return "VE"
    return normalized


def _map_test_status(raw_status: Any) -> str:
    """Normalize Nexpose test status strings."""

    text = _collapse_whitespace(raw_status)
    if not text:
        return ""
    mapped = NEXPOSE_TEST_STATUS_MAP.get(text.lower())
    if mapped:
        return mapped
    return text.upper()


def _collect_node_hostnames(node: "ElementTree.Element") -> List[str]:
    """Return a list of unique hostnames recorded for ``node``."""

    hostnames: List[str] = []
    for name_element in node.findall("./names/name"):
        hostname = _collapse_whitespace(_element_text(name_element))
        if hostname and hostname not in hostnames:
            hostnames.append(hostname)
    return hostnames


def _extract_os_description(node: "ElementTree.Element") -> str:
    """Select the best matching OS description for ``node``."""

    os_entries = node.findall("./fingerprints/os")
    if not os_entries:
        os_entries = node.findall("./fingerprints/fingerprint")
    fallback = ""
    for os_element in os_entries:
        certainty = _safe_float(_get_element_field(os_element, "certainty"))
        vendor = _get_element_field(os_element, "vendor")
        product = _get_element_field(os_element, "product")
        family = _get_element_field(os_element, "family")
        device_class = _get_element_field(os_element, "device-class") or _get_element_field(
            os_element, "deviceClass"
        )
        if not fallback:
            fallback = product or vendor or family or device_class or ""
        if certainty == 1.0 and product:
            return product
        if certainty >= 0.67:
            if vendor and vendor.lower() == "microsoft":
                return product or "Microsoft Windows UNKNOWN"
            if vendor:
                return vendor
            if family:
                return family
            if device_class:
                return device_class
    return fallback


def _extract_test_evidence(test_element: "ElementTree.Element") -> str:
    """Return the best-effort evidence string for ``test_element``."""

    for key in ("evidence", "details", "description", "proof"):
        evidence = _get_element_field(test_element, key)
        if evidence:
            return _normalize_evidence_text(evidence)
    return _normalize_evidence_text(_element_text(test_element))


def _extract_vulnerability_id(test_element: "ElementTree.Element") -> str:
    """Return the vulnerability identifier linked to ``test_element``."""

    for key in ("id", "vulnerability-id", "vulnerabilityId", "vuln-id"):
        value = _get_element_field(test_element, key)
        if value:
            return value
    return ""


def _build_vulnerability_lookup(report_root: "ElementTree.Element") -> Dict[str, Dict[str, str]]:
    """Return a mapping of vulnerability IDs to descriptive fields."""

    lookup: Dict[str, Dict[str, str]] = {}
    definitions = _find_child_element(report_root, "vulnerabilityDefinitions")
    if definitions is None:
        return lookup
    for vulnerability in _find_child_elements(definitions, "vulnerability"):
        vuln_id = (
            _collapse_whitespace(_get_element_field(vulnerability, "id"))
            or _collapse_whitespace(_element_text(vulnerability.find("id")))
        )
        if not vuln_id:
            continue
        title = _clean_ascii_text(
            _element_text(vulnerability.find("title"))
            or _get_element_field(vulnerability, "title")
            or vuln_id
        )
        severity_text = _collapse_whitespace(
            _element_text(vulnerability.find("severity"))
            or _get_element_field(vulnerability, "severity")
        )
        severity_value = _coerce_int(severity_text)
        description = _normalize_multiline_text(
            _element_text(vulnerability.find("description"))
            or _get_element_field(vulnerability, "description")
        )
        solution = _truncate_excel_text(
            _normalize_multiline_text(
                _element_text(vulnerability.find("solution"))
                or _get_element_field(vulnerability, "solution")
            )
        )
        references = _find_child_element(vulnerability, "references")
        cve_ids: List[str] = []
        reference_nodes = _find_child_elements(references, "reference")
        for reference in reference_nodes:
            source = _collapse_whitespace(_get_element_field(reference, "source"))
            if source.upper() != "CVE":
                continue
            value = _collapse_whitespace(
                _get_element_field(reference, "value") or _element_text(reference)
            )
            if value:
                cve_ids.append(value)

        cves_parent = _find_child_element(vulnerability, "cves")
        cve_nodes = _find_child_elements(cves_parent, "cve")
        for cve_node in cve_nodes:
            identifier = _collapse_whitespace(
                _get_element_field(cve_node, "id")
                or _get_element_field(cve_node, "value")
                or _element_text(cve_node)
            )
            if identifier:
                cve_ids.append(identifier)

        normalized_cves: List[str] = []
        seen_cves: Set[str] = set()
        for cve in cve_ids:
            cleaned = cve.strip()
            if not cleaned:
                continue
            key = cleaned.upper()
            if key in seen_cves:
                continue
            seen_cves.add(key)
            normalized_cves.append(cleaned)

        entry = {
            "title": title or vuln_id,
            "severity": severity_value if severity_value is not None else severity_text,
            "description": description,
            "cves": ", ".join(normalized_cves),
            "solution": solution,
        }
        lookup[vuln_id] = entry
        normalized_id = vuln_id.lower()
        if normalized_id and normalized_id not in lookup:
            lookup[normalized_id] = entry
    return lookup


def _build_cve_links(cve_field: str) -> str:
    """Return newline-delimited NIST references for the provided CVE string."""

    text = str(cve_field or "").strip()
    if not text:
        return "No NIST reference available"
    links = []
    for token in re.split(r"[,;]", text):
        candidate = token.strip()
        if not candidate:
            continue
        links.append(f"http://web.nvd.nist.gov/view/vuln/detail?vulnId={candidate}")
    return "\n".join(links) if links else "No NIST reference available"


def _adjust_matrix_impact(threat: str, status_code: str) -> str:
    """Return ``threat`` with ``<EC>`` placeholders tailored to ``status_code``."""

    if not threat:
        return ""
    replacement = "can"
    if (status_code or "").upper() == "VP":
        replacement = "may"
    return threat.replace("<EC>", replacement)


def _apply_matrix_metadata_to_finding(
    entry: Dict[str, Any],
    vulnerability_matrix: Optional[Dict[str, Dict[str, str]]],
    cve_links: str,
) -> bool:
    """Populate matrix-backed fields for a finding entry and return success state."""

    entry.setdefault("Impact", "")
    entry.setdefault("Solution", "")
    entry.setdefault("Category", "")
    entry["References"] = cve_links
    if not vulnerability_matrix:
        return False

    key = _normalize_matrix_key(entry.get("Vulnerability Title"))
    if not key:
        return False
    metadata = vulnerability_matrix.get(key)
    if not metadata:
        return False

    threat_text = metadata.get("vulnerability_threat") or ""
    entry["Impact"] = _adjust_matrix_impact(
        threat_text,
        entry.get("Vulnerability Test Result Code", ""),
    )
    entry["Solution"] = metadata.get("action_required") or ""
    entry["Category"] = metadata.get("category") or ""
    return True


def _build_nexpose_finding_entry(
    *,
    ip_address: str,
    hostnames: str,
    os_description: str,
    port: str,
    protocol: str,
    test_element: "ElementTree.Element",
    vulnerability_lookup: Dict[str, Dict[str, str]],
    vulnerability_matrix: Optional[Dict[str, Dict[str, str]]] = None,
) -> Tuple[Optional[Dict[str, str]], Optional[Dict[str, str]]]:
    """Return a populated finding entry for ``test_element`` if possible."""

    vulnerability_id = _extract_vulnerability_id(test_element)
    if not vulnerability_id:
        return None, None
    definition = vulnerability_lookup.get(vulnerability_id) or vulnerability_lookup.get(
        vulnerability_id.lower(), {}
    )
    title = _clean_ascii_text(definition.get("title") or vulnerability_id)
    severity = definition.get("severity")
    severity_value = _coerce_int(severity)
    description = definition.get("description") or ""
    cve_ids = definition.get("cves") or ""
    remediation = definition.get("solution") or ""
    evidence = _extract_test_evidence(test_element)
    status = _adjust_vulnerability_code(
        _map_test_status(_get_element_field(test_element, "status")),
        description,
    )
    cve_links = _build_cve_links(cve_ids)

    entry: Dict[str, Any] = {
        "Asset IP Address": ip_address,
        "Hostname(s)": hostnames,
        "Asset Operating System": os_description,
        "Service Port": port,
        "Protocol": protocol,
        "Vulnerability Test Result Code": status,
        "Vulnerability ID": vulnerability_id,
        "Vulnerability CVE IDs": cve_ids,
        "Vulnerability Severity Level": severity_value if severity_value is not None else severity,
        "Vulnerability Title": title,
        "Details": description,
        "Evidence": evidence,
        "Detailed Remediation": remediation,
    }
    entry.setdefault("Impact", "")
    entry.setdefault("Solution", "")
    entry.setdefault("Category", "")
    entry["References"] = cve_links
    has_matrix_metadata = _apply_matrix_metadata_to_finding(
        entry, vulnerability_matrix, cve_links
    )
    missing_row: Optional[Dict[str, str]] = None
    if not has_matrix_metadata:
        missing_row = {
            "Vulnerability": entry.get("Vulnerability Title", ""),
            "Action Required": "",
            "Remediation Impact": "",
            "Vulnerability Threat": "",
            "Category": "",
            "CVE": cve_links,
        }

    return entry, missing_row



def _normalize_nexpose_identifier(value: Any) -> str:
    """Normalize Nexpose identifiers into a comparable form."""

    if value is None:
        return ""
    return re.sub(r"[^a-z0-9]+", "_", str(value).strip().lower()).strip("_")


def _detect_nexpose_xml_artifact_key(values: Iterable[Any]) -> Optional[str]:
    """Infer the artifact key for any Nexpose XML specific ``values``."""

    normalized = " ".join(
        str(value).strip().lower() for value in values if value and str(value).strip()
    )
    if not normalized or "nexpose_xml" not in normalized:
        return None
    for keyword, artifact_key in NEXPOSE_XML_ARTIFACT_MAP.items():
        if keyword in normalized:
            return artifact_key
    return None


def _resolve_nexpose_xml_artifact_key(data_file: "ProjectDataFile") -> Optional[str]:
    """Infer the artifact key that should store a Nexpose XML upload."""

    candidates = [
        (data_file.requirement_label or ""),
        (data_file.requirement_slug or ""),
        (data_file.requirement_context or ""),
        (data_file.description or ""),
    ]
    for candidate in candidates:
        normalized = _normalize_nexpose_identifier(candidate)
        if not normalized:
            continue
        artifact_key = NEXPOSE_XML_REQUIREMENT_MAP.get(normalized)
        if artifact_key:
            return artifact_key
    return _detect_nexpose_xml_artifact_key(candidates)


def resolve_nexpose_requirement_artifact_key(
    requirement: Mapping[str, Any]
) -> Optional[str]:
    """Infer the artifact key that corresponds to a workbook requirement."""

    if not isinstance(requirement, abc.Mapping):
        return None
    candidates = [
        requirement.get("label", ""),
        requirement.get("slug", ""),
        requirement.get("context", ""),
        requirement.get("requirement_context", ""),
    ]
    return _detect_nexpose_xml_artifact_key(candidates)


def _parse_ip_list(file_obj: File) -> List[str]:
    """Parse a newline-delimited text file into a list of IP entries."""

    try:
        file_obj.open("rb")
    except FileNotFoundError:
        logger.warning("Uploaded data file is missing from storage", exc_info=True)
        raw_bytes = b""
    else:
        try:
            raw_bytes = file_obj.read() or b""
        finally:
            file_obj.close()

    try:
        text = raw_bytes.decode("utf-8")
    except UnicodeDecodeError:
        text = raw_bytes.decode("utf-8", errors="ignore")

    return parse_ip_text(text)


FIREWALL_REPORT_FIELD_SPECS: Tuple[Tuple[str, str], ...] = (
    ("risk", "Risk"),
    ("issue", "Issue"),
    ("devices", "Devices"),
    ("solution", "Solution"),
    ("impact", "Impact"),
    ("details", "Details"),
    ("reference", "Reference"),
    ("accepted", "Accepted"),
    ("type", "Type"),
)


def _get_case_insensitive(row: Dict[str, Any], key: str) -> Any:
    """Return the value for ``key`` in ``row`` using case-insensitive matching."""

    if key in row:
        return row[key]
    lowered = key.lower()
    for candidate_key, value in row.items():
        if candidate_key.lower() == lowered:
            return value
    return ""


def _parse_firewall_score(raw_value: Any) -> Optional[float]:
    """Convert the provided value into a floating point score if possible."""

    text = str(raw_value).strip() if raw_value is not None else ""
    if not text:
        return None
    normalized = text.replace(",", "")
    try:
        return float(normalized)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None


def _parse_severity_level(raw_value: Any) -> Optional[float]:
    """Normalize a Nexpose severity level value to a floating point score."""

    text = str(raw_value).strip() if raw_value is not None else ""
    if not text:
        return None
    try:
        return float(text)
    except (TypeError, ValueError):
        upper_text = text.upper()
        if upper_text == "HIGH":
            return 9.0
        if upper_text == "MEDIUM":
            return 6.0
        if upper_text == "LOW":
            return 2.0
    return None


def _categorize_severity(score: Optional[float]) -> Optional[str]:
    """Return the severity bucket for the provided Nexpose score."""

    if score is None:
        return None
    if score >= 8:
        return "High"
    if score >= 4:
        return "Medium"
    if score >= 0:
        return "Low"
    return None


def _coerce_int(value: Any) -> Optional[int]:
    """Best-effort conversion of ``value`` to ``int`` or ``None`` if conversion fails."""

    if value is None:
        return None

    if isinstance(value, int):
        return value

    text = str(value).strip()
    if not text:
        return None

    normalized = text.replace(",", "")
    try:
        return int(normalized)
    except (TypeError, ValueError):
        try:
            return int(float(normalized))
        except (TypeError, ValueError):
            return None


NEXPOSE_SEVERITY_SCORE_MAP = {
    "critical": 5,
    "high": 4,
    "medium": 3,
    "moderate": 3,
    "low": 2,
    "informational": 1,
    "info": 1,
}


def coerce_cap_score(value: Any) -> Optional[int]:
    """Normalize score/severity values into an integer scale."""

    score = _coerce_int(value)
    if score is not None:
        return score
    if isinstance(value, str):
        normalized = value.strip().lower()
        if normalized:
            return NEXPOSE_SEVERITY_SCORE_MAP.get(normalized)
    return None


def _normalize_cap_text(value: Any) -> str:
    """Return a normalized string for CAP-style CSV fields."""

    if value in (None, ""):
        return ""
    return str(value).strip()


def parse_burp_cap_report(file_obj: File) -> List[Dict[str, Any]]:
    """Parse a ``burp_cap.csv`` upload into structured CAP entries."""

    entries: List[Dict[str, Any]] = []
    for row in _decode_file(file_obj):
        entry: Dict[str, Any] = {}

        issue = _normalize_cap_text(_get_case_insensitive(row, "Issue"))
        hosts = _normalize_cap_text(_get_case_insensitive(row, "Host(s)"))
        if not hosts:
            hosts = _normalize_cap_text(_get_case_insensitive(row, "Hosts"))
        action = _normalize_cap_text(_get_case_insensitive(row, "Action"))
        ecfirst = _normalize_cap_text(_get_case_insensitive(row, "ecfirst"))
        severity = _normalize_cap_text(_get_case_insensitive(row, "Sev"))
        if not severity:
            severity = _normalize_cap_text(_get_case_insensitive(row, "Severity"))
        score_value = _coerce_int(_get_case_insensitive(row, "Score"))
        score_text = _normalize_cap_text(_get_case_insensitive(row, "Score"))

        if issue:
            entry["issue"] = issue
        if hosts:
            entry["hosts"] = hosts
        if action:
            entry["action"] = action
        if ecfirst:
            entry["ecfirst"] = ecfirst
        if severity:
            entry["severity"] = severity
        if score_value is not None:
            entry["score"] = score_value
        elif score_text:
            entry["score"] = score_text

        if entry:
            entries.append(entry)

    return entries


def parse_nexpose_cap_report(file_obj: File) -> List[Dict[str, Any]]:
    """Parse a ``nexpose_cap.csv`` upload into structured CAP entries."""

    entries: List[Dict[str, Any]] = []
    for row in _decode_file(file_obj):
        systems = _normalize_cap_text(_get_case_insensitive(row, "Systems"))
        action = _normalize_cap_text(_get_case_insensitive(row, "Action"))
        score = coerce_cap_score(_get_case_insensitive(row, "Sev"))
        if score is None:
            score = coerce_cap_score(_get_case_insensitive(row, "Score"))
        if score is None:
            score = coerce_cap_score(_get_case_insensitive(row, "Severity"))
        issue = _normalize_cap_text(_get_case_insensitive(row, "Issue"))
        ecfirst = _normalize_cap_text(_get_case_insensitive(row, "ecfirst"))

        entry: Dict[str, Any] = {}
        if systems:
            entry["systems"] = systems
        if action:
            entry["action"] = action
        if score is not None:
            entry["score"] = score
        if issue:
            entry["issue"] = issue
        if ecfirst:
            entry["ecfirst"] = ecfirst

        if entry:
            entries.append(entry)

    return entries


def _normalize_policy_string(value: Any) -> str:
    """Return a normalized string representation for password policy values."""

    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().upper()
    return str(value).strip().upper()


def _evaluate_compliance_rule(rule: Any, value: Any, data_type: str) -> bool:
    """Evaluate a compliance rule against ``value`` using the provided ``data_type``."""

    if isinstance(rule, list):
        return any(_evaluate_compliance_rule(entry, value, data_type) for entry in rule)

    if not isinstance(rule, dict):
        return False

    operator = str(rule.get("operator", "")).lower()

    if operator in {"any", "or"}:
        sub_rules = rule.get("rules") or rule.get("conditions") or []
        return any(
            _evaluate_compliance_rule(sub_rule, value, data_type)
            for sub_rule in sub_rules
            if isinstance(sub_rule, (dict, list))
        )

    if operator in {"all", "and"}:
        sub_rules = rule.get("rules") or rule.get("conditions") or []
        relevant = [
            sub_rule
            for sub_rule in sub_rules
            if isinstance(sub_rule, (dict, list))
        ]
        if not relevant:
            return False
        return all(
            _evaluate_compliance_rule(sub_rule, value, data_type)
            for sub_rule in relevant
        )

    if value is None:
        return False

    if data_type == "numeric":
        try:
            numeric_value = float(value)
            comparator = float(rule.get("value"))
        except (TypeError, ValueError):
            return False

        if operator in {"lt", "<"}:
            return numeric_value < comparator
        if operator in {"lte", "<="}:
            return numeric_value <= comparator
        if operator in {"gt", ">"}:
            return numeric_value > comparator
        if operator in {"gte", ">="}:
            return numeric_value >= comparator
        if operator in {"eq", "=="}:
            return numeric_value == comparator
        if operator in {"ne", "!=", "<>"}:
            return numeric_value != comparator
        return False

    normalized_value = _normalize_policy_string(value)
    comparator_text = _normalize_policy_string(rule.get("value"))

    if operator in {"eq", "=="}:
        return normalized_value == comparator_text
    if operator in {"ne", "!=", "<>"}:
        return normalized_value != comparator_text

    return False


def _calculate_percentage(numerator: Optional[int], denominator: Optional[int]) -> Optional[float]:
    """Return ``numerator`` / ``denominator`` as a percentage rounded to one decimal place."""

    if numerator is None or denominator in (None, 0):
        return None

    return round((numerator / denominator) * 100, 1)


def parse_firewall_report(file_obj: File) -> List[Dict[str, Any]]:
    """Parse a firewall_csv.csv export into normalized issue entries."""

    findings: List[Dict[str, Any]] = []
    for row in _decode_file(file_obj):
        normalized_entry: Dict[str, Any] = {}
        has_content = False

        for field_key, header in FIREWALL_REPORT_FIELD_SPECS:
            value = _get_case_insensitive(row, header)
            text_value = str(value).strip() if value is not None else ""
            normalized_entry[field_key] = text_value
            if text_value:
                has_content = True

        score_value = _parse_firewall_score(_get_case_insensitive(row, "Score"))
        normalized_entry["score"] = score_value
        if score_value is not None:
            has_content = True

        if has_content:
            findings.append(normalized_entry)

    return findings


def _get_nipper_impact(block: str) -> str:
    """Return an impact string derived from a CVSSv2 vector ``block``."""

    segments = (block or "").split("/")
    if len(segments) < 6:
        return ""

    conf_code = segments[3].split(":")[-1].strip().upper()
    integ_code = segments[4].split(":")[-1].strip().upper()
    avail_segment = segments[5].split()
    avail_code = avail_segment[0].split(":")[-1].strip().upper() if avail_segment else ""
    score = avail_segment[1] if len(avail_segment) > 1 else ""

    conf_phrase = {
        "N": "has no impact on the confidentiality of the system(s)",
        "P": "allows considerable disclosure of information",
        "C": "allows for total information disclosure, providing access to any / all data",
    }.get(conf_code, "has no impact on the confidentiality of the system(s)")

    integ_phrase = {
        "N": "has no impact on the integrity of the system(s)",
        "P": "allows for the modification of some data or system files",
        "C": "allows an attacker to modify any files or information on the target system(s)",
    }.get(integ_code, "has no impact on the integrity of the system(s)")

    avail_phrase = {
        "N": "has no impact on the availability of the system(s)",
        "P": "can result in reduced performance or loss of some functionality",
        "C": "can result in total loss of availability of the attacked resource(s)",
    }.get(avail_code, "has no impact on the availability of the system(s)")

    impact_score = score if score else ""
    impact_template = (
        "This vulnerability {conf_phrase}, {integ_phrase}, and {avail_phrase}"
    )
    if impact_score:
        impact_template = (
            f"{impact_template} with a base CVSSv2 score of {{score}}"
        )
    return impact_template.format(
        conf_phrase=conf_phrase, integ_phrase=integ_phrase, avail_phrase=avail_phrase, score=impact_score
    )


def _normalize_firewall_risk(value: str) -> Optional[str]:
    """Map textual firewall risk levels to ``high``/``med``/``low`` buckets."""

    if not value:
        return None

    normalized = value.strip().lower()
    if not normalized:
        return None

    if normalized.startswith("crit") or normalized.startswith("high"):
        return "high"
    if normalized.startswith("med") or normalized.startswith("moder"):
        return "med"
    if normalized.startswith("low"):
        return "low"
    return None


_SENTENCE_BOUNDARY_RE = re.compile(r"(?<=[.!?])\s+")


def _first_sentence(value: str) -> str:
    """Return the first sentence from the provided ``value`` string."""

    text = (value or "").strip()
    if not text:
        return ""

    normalized = " ".join(text.split())
    parts = _SENTENCE_BOUNDARY_RE.split(normalized, maxsplit=1)
    return parts[0].strip()


def _safe_float(value: Any) -> Any:
    """Attempt to convert ``value`` to a float, returning the original on failure."""

    if isinstance(value, (int, float)):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            return value
        try:
            return float(text)
        except ValueError:
            return value
    return value


def _summarize_firewall_vulnerabilities(
    findings: Iterable[Dict[str, Any]]
) -> Dict[str, Dict[str, Any]]:
    """Aggregate firewall findings into severity summaries."""

    severity_counters: Dict[str, Counter[Tuple[str, str]]] = {
        "high": Counter(),
        "med": Counter(),
        "low": Counter(),
    }

    for entry in findings:
        if not isinstance(entry, dict):
            continue

        risk_raw = entry.get("risk")
        if risk_raw is None:
            risk_raw = entry.get("Risk")

        risk_value = _normalize_firewall_risk(str(risk_raw or ""))
        if not risk_value:
            continue

        issue_text = (entry.get("issue") or entry.get("Issue") or "").strip()
        impact_text = _first_sentence(entry.get("impact") or entry.get("Impact") or "")

        if not issue_text and not impact_text:
            continue

        severity_counters[risk_value][(issue_text, impact_text)] += 1

    summaries: Dict[str, Dict[str, Any]] = {}
    for severity, counter in severity_counters.items():
        sorted_items = sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                item[0][0].lower(),
                item[0][1].lower(),
            ),
        )
        top_items = [
            {"issue": issue, "impact": impact, "count": count}
            for (issue, impact), count in sorted_items[:5]
        ]
        summaries[severity] = {
            "total_unique": len(counter),
            "items": top_items,
        }

    return summaries


def _coerce_firewall_score(raw_value: Any) -> float:
    """Normalize firewall scores to a float for risk bucketing."""

    if isinstance(raw_value, (int, float)):
        try:
            return float(raw_value)
        except (TypeError, ValueError):  # pragma: no cover - defensive
            return 0.0
    if isinstance(raw_value, str):
        text = raw_value.strip().replace(",", "")
        if not text:
            return 0.0
        try:
            return float(text)
        except ValueError:
            return 0.0
    return 0.0


def _risk_bucket_from_score(score: float) -> str:
    """Translate a numeric score into High/Medium/Low buckets."""

    if score >= 7.0:
        return "High"
    if score >= 4.0:
        return "Medium"
    return "Low"


def _extract_firewall_devices(devices_value: Any) -> List[str]:
    """Split newline-delimited device strings into a normalized list."""

    if devices_value in (None, ""):
        return []
    if isinstance(devices_value, str):
        devices = [segment.strip() for segment in devices_value.split("\n") if segment.strip()]
        return devices
    if isinstance(devices_value, (list, tuple)):
        devices: List[str] = []
        for entry in devices_value:
            if entry in (None, ""):
                continue
            devices.append(str(entry).strip())
        return [device for device in devices if device]
    return [str(devices_value).strip()]


def _build_firewall_metrics_payload(
    firewall_findings: List[Dict[str, Any]]
) -> Dict[str, Any]:
    """Construct summary metrics, device breakdowns, and workbook bytes."""

    findings = firewall_findings or []
    summary_high = summary_med = summary_low = 0
    rule_count = config_count = complexity_count = vuln_count = 0
    device_tracker: Dict[str, Dict[str, Any]] = {}
    top_impacts_counter: Counter[str] = Counter()
    all_issues: List[Dict[str, Any]] = []
    high_issues: List[Dict[str, Any]] = []
    med_issues: List[Dict[str, Any]] = []
    low_issues: List[Dict[str, Any]] = []
    rule_issues: List[Dict[str, Any]] = []
    config_issues: List[Dict[str, Any]] = []
    complexity_issues: List[Dict[str, Any]] = []
    vuln_issues: List[Dict[str, Any]] = []

    for entry in findings:
        if not isinstance(entry, dict):
            continue

        score_value = _coerce_firewall_score(entry.get("Score"))
        bucket = _risk_bucket_from_score(score_value)
        if bucket == "High":
            summary_high += 1
        elif bucket == "Medium":
            summary_med += 1
        else:
            summary_low += 1

        type_value = (entry.get("Type") or "").strip()
        normalized_type = type_value.lower()
        if normalized_type in {"rule", "rules"}:
            rule_count += 1
            rule_issues.append(entry)
        elif normalized_type in {"config", "configuration"}:
            config_count += 1
            config_issues.append(entry)
        elif normalized_type == "complexity":
            complexity_count += 1
            complexity_issues.append(entry)
        elif normalized_type in {"vuln", "vulnerability"}:
            vuln_count += 1
            vuln_issues.append(entry)

        all_issues.append(entry)

        if bucket == "High":
            high_issues.append(entry)
        elif bucket == "Medium":
            med_issues.append(entry)
        else:
            low_issues.append(entry)

        impact_value = (entry.get("Impact") or "").strip()
        if impact_value:
            top_impacts_counter[impact_value] += 1

        devices = _extract_firewall_devices(entry.get("Devices"))
        for device in devices:
            device_key = device or "Unknown Device"
            device_entry = device_tracker.setdefault(
                device_key,
                {"device": device_key, "total_high": 0, "total_med": 0, "total_low": 0, "ood": "no"},
            )
            if bucket == "High":
                device_entry["total_high"] += 1
            elif bucket == "Medium":
                device_entry["total_med"] += 1
            else:
                device_entry["total_low"] += 1

            if device_entry["ood"] != "yes" and normalized_type in {"vuln", "vulnerability"}:
                device_entry["ood"] = "yes"

    unique_count = len(all_issues)
    majority_type: str
    minority_type: str
    majority_count = max(rule_count, config_count)
    minority_count = min(rule_count, config_count)
    if rule_count > config_count:
        majority_type = "Rules"
        minority_type = "Config"
    elif rule_count < config_count:
        majority_type = "Config"
        minority_type = "Rules"
    else:
        majority_type = "Even"
        minority_type = "Even"

    summary = {
        "unique": unique_count,
        "unique_high": summary_high,
        "unique_med": summary_med,
        "unique_low": summary_low,
        # Legacy aliases used by templates and downstream consumers
        "total": unique_count,
        "total_high": summary_high,
        "total_med": summary_med,
        "total_low": summary_low,
        "rule_count": rule_count,
        "config_count": config_count,
        "complexity_count": complexity_count,
        "vuln_count": vuln_count,
        "majority_type": majority_type,
        "minority_type": minority_type,
        "majority_count": majority_count,
        "minority_count": minority_count,
    }

    device_metrics = sorted(device_tracker.values(), key=lambda item: item["device"].lower())
    top_impacts = [
        {"impact": impact, "count": count}
        for impact, count in top_impacts_counter.most_common(10)
    ]

    metrics_payload: Dict[str, Any] = {
        "summary": summary,
        "devices": device_metrics,
        "top_impacts": top_impacts,
        "all_issues": all_issues,
        "high_issues": high_issues,
        "med_issues": med_issues,
        "low_issues": low_issues,
        "rule_issues": rule_issues,
        "config_issues": config_issues,
        "complexity_issues": complexity_issues,
        "vuln_issues": vuln_issues,
        "xlsx_filename": "firewall_data.xlsx",
    }

    workbook_bytes = _render_firewall_metrics_workbook(metrics_payload)
    if workbook_bytes:
        metrics_payload["xlsx_base64"] = base64.b64encode(workbook_bytes).decode("ascii")

    return metrics_payload


def _normalize_nipper_text(value: str) -> str:
    """Return normalized text with Nipper-specific replacements applied."""

    text = (value or "").strip()
    if not text:
        return ""

    replacements = {
        "shown in Table and": "shown below and",
    }
    for needle, replacement in replacements.items():
        text = text.replace(needle, replacement)

    trailing_replacements = ["in Table .", "in Table "]
    for trailing in trailing_replacements:
        if text.endswith(trailing):
            text = text[: -len(trailing)].rstrip() + " below:"
            break

    if re.search(r"in Table\s+\d+\s+below\.?$", text):
        text = re.sub(r"in Table\s+\d+\s+below\.?$", "below:", text).rstrip()

    return _collapse_whitespace(text)


def _parse_nipper_table(
    table_element: "ElementTree.Element",
    headings: List[str],
    row_parser: Callable[[Dict[str, str]], str],
) -> List[str]:
    """Convert a Nipper table into formatted rows using ``row_parser``."""

    rows: List[str] = []
    normalized_headings = [heading.strip() for heading in headings]

    def _iter_rows():
        inline_rows = _find_child_elements(table_element, "row")
        if inline_rows:
            return inline_rows
        body = _find_child_element(table_element, "tablebody")
        if body is not None:
            nested_rows = _find_child_elements(body, "tablerow")
            if nested_rows:
                return nested_rows
        return []

    for row in _iter_rows():
        cell_values: List[str] = []
        nested_cells = _find_child_elements(row, "cell")
        if not nested_cells:
            nested_cells = _find_child_elements(row, "tablecell")
        for cell in nested_cells:
            items = _find_child_elements(cell, "item") or list(cell)
            if items:
                item_values = []
                for item in items:
                    item_text = _collapse_whitespace(_element_text(item))
                    if item_text:
                        item_values.append(item_text)
                if item_values:
                    cell_values.append("; ".join(item_values))
                else:
                    cell_values.append(_element_text(cell))
            else:
                cell_values.append(_element_text(cell))
        if not cell_values and list(row):
            cell_values = [_element_text(child) for child in row]
        heading_map = {
            heading: cell_values[index] if index < len(cell_values) else ""
            for index, heading in enumerate(normalized_headings)
        }
        parsed_row = row_parser(heading_map)
        if parsed_row:
            rows.append(parsed_row)
    return rows


def _nipper_rules_row(row: Dict[str, str]) -> str:
    rule = (row.get("Rule") or row.get("rule") or "").strip()
    action = (row.get("Action") or row.get("action") or "").strip()
    src = (row.get("Source") or row.get("source") or "").strip()
    srcp = (row.get("Src Port") or row.get("src port") or "").strip()
    dst = (row.get("Destination") or row.get("destination") or "").strip()
    dstp = (row.get("Dst Port") or row.get("dst port") or "").strip()
    proto = (row.get("Protocol") or row.get("protocol") or "").strip()
    service = (row.get("Service") or row.get("service") or "").strip()

    if proto.lower() == "any":
        proto = "Any Protocol"
    if not proto:
        proto = service
    if "any" in service.lower():
        service = "Any Service"

    if srcp and dstp:
        return f"Rule '{rule}'-:- {action} '{proto or service}' from '{src}:{srcp}' to '{dst}:{dstp}'"
    return f"Rule '{rule}'-:- {action} '{proto or service}' from '{src}' to '{dst}'"


def _nipper_security_table_row(row: Dict[str, str]) -> str:
    parts = []
    for heading, value in row.items():
        if heading:
            parts.append(f"{heading}:[{value}]")
    return " ".join(parts).strip()


def _nipper_complex_table_row(row: Dict[str, str]) -> str:
    name = (row.get("Name") or row.get("name") or "").strip()
    address = (row.get("Address") or row.get("address") or "").strip()
    protocol = (row.get("Protocol") or row.get("protocol") or "").strip()
    dst = (row.get("Destination Port") or row.get("destination port") or "").strip()

    if not protocol:
        return f"{name} :: {address}".strip()
    return f"{name} :: [{protocol}]{dst}".strip()


def _get_nipper_finding(
    block: Optional["ElementTree.Element"],
    ref: str,
    *,
    is_complexity: bool = False,
) -> str:
    """Build a combined description string from a Nipper evidence block."""

    if block is None:
        return ""

    parts: List[str] = []
    remaining_rows = 225 if is_complexity else 222
    truncation = "...Due to the large number of findings the evidence has been truncated..."

    for child in block:
        tag = _normalize_xml_tag(getattr(child, "tag", ""))
        if tag in {"text", "para", "p"}:
            text_value = _normalize_nipper_text(_element_text(child))
            if text_value:
                parts.append(text_value)
            continue

        if tag == "list":
            rows: List[str] = []
            for item in _find_child_elements(child, "item") + _find_child_elements(
                child, "listitem"
            ):
                text_value = _normalize_nipper_text(_element_text(item))
                if text_value:
                    rows.append(text_value)
            for row in rows:
                if remaining_rows <= 0:
                    break
                parts.append(row)
                remaining_rows -= 1
            if remaining_rows <= 0:
                parts.append(truncation)
                break
            continue

        if tag == "table":
            heading_elements = _find_child_elements(child, "heading")
            if not heading_elements:
                heading_elements = _find_child_elements(_find_child_element(child, "headings"), "heading")
            headings = [_element_text(element) for element in heading_elements]
            if not headings and list(child):
                headings = [
                    _normalize_nipper_text(_normalize_xml_tag(getattr(table_child, "tag", "")))
                    for table_child in list(child)[0]
                ]

            table_title = _normalize_nipper_text(_get_element_field(child, "title"))
            if table_title:
                parts.append(table_title)

            headings_lower = [heading.lower() for heading in headings]

            if ref.startswith("FILTER."):
                parser = _nipper_rules_row
            elif is_complexity and (
                "filter rules" in (_get_element_field(block, "title") or "").lower()
                or "filter rules" in (table_title or "").lower()
                or "rule" in headings_lower
            ):
                parser = _nipper_rules_row
            elif is_complexity:
                parser = _nipper_complex_table_row
            else:
                parser = _nipper_security_table_row

            rows = _parse_nipper_table(child, headings, parser)
            for row in rows:
                if remaining_rows <= 0:
                    break
                parts.append(row)
                remaining_rows -= 1
            if remaining_rows <= 0:
                parts.append(truncation)
                break
            continue

        nested_text = _normalize_nipper_text(_element_text(child))
        if nested_text:
            parts.append(nested_text)

    return "\n".join(part for part in parts if part)


def _iter_nipper_sections(root: "ElementTree.Element", ref: str) -> List["ElementTree.Element"]:
    """Return sections (or parts) matching ``ref`` from the provided XML tree."""

    matches: List["ElementTree.Element"] = []
    normalized_ref = (ref or "").strip().lower()
    for node in root.iter():
        tag = _normalize_xml_tag(getattr(node, "tag", ""))
        if tag not in {"section", "part"}:
            continue
        node_ref = node.attrib.get("ref") or node.attrib.get("name") or ""
        if node_ref.strip().lower() == normalized_ref:
            matches.append(node)
    return matches


def get_extra(section: Optional["ElementTree.Element"], key: str) -> str:
    """Return text from a report-root ``extra-info`` block."""

    extra_info = _find_child_element(section, "extra-info")
    return _get_element_field(extra_info, key)


def get_devices(section: Optional["ElementTree.Element"]) -> str:
    """Return newline-delimited device names for the provided section."""

    devices_node = _find_child_element(section, "devices")
    device_names = [
        device.attrib.get("name") or _get_element_field(device, "name")
        for device in _find_child_elements(devices_node, "device")
        if device is not None
    ]
    return "\n".join(dict.fromkeys([name for name in device_names if name]))


def get_subsection_text(section: Optional["ElementTree.Element"], title_name: str) -> str:
    """Return concatenated ``content`` text for matching subsection titles."""

    if section is None:
        return ""
    text_parts: List[str] = []
    subsections = _find_child_element(section, "subsections")
    for candidate in _find_child_elements(subsections, "section"):
        title = (_get_element_field(candidate, "title") or "").strip()
        if title != title_name:
            continue
        contents = _find_child_element(candidate, "contents")
        for content in _find_child_elements(contents, "content"):
            content_text = _element_text(content)
            if content_text:
                text_parts.append(content_text)
    return "\n".join(text_parts)


def normalize_risk(text: Optional[str]) -> str:
    """Normalize report risk strings to match legacy mapping."""

    value = (text or "").strip()
    if not value:
        return ""
    lower_value = value.lower()
    if lower_value == "critical":
        return "High"
    if lower_value == "informational":
        return "Low"
    return value


def iter_report_findings(root: "ElementTree.Element") -> Iterable["ElementTree.Element"]:
    """Yield candidate finding sections from a report-root Nipper export."""

    sections_node = _find_child_element(root, "sections")
    for section in _find_child_elements(sections_node, "section"):
        subsections = _find_child_element(section, "subsections")
        for candidate in _find_child_elements(subsections, "section"):
            title = (_get_element_field(candidate, "title") or "").strip()
            devices = get_devices(candidate)
            audit_text = get_extra(candidate, "AUDIT")
            finding_text = get_subsection_text(candidate, "Finding")
            recommendation_text = get_subsection_text(candidate, "Recommendation")
            lower_title = title.lower() if title else ""
            if (
                (
                    not title
                    or any(keyword in lower_title for keyword in ("introduction", "conclusions", "recommendations"))
                )
                and not audit_text
                and not devices
                and not finding_text
                and not recommendation_text
            ):
                continue
            yield candidate


def _extract_report_cvss_score(section: "ElementTree.Element") -> Any:
    """Return CVSS score for report-root section if present."""

    cvss_node = _find_child_element(section, "cvssv3.1")
    base_node = _find_child_element(cvss_node, "base")
    score_node = _find_child_element(base_node, "score")
    if score_node is None:
        return ""
    return _safe_float(_element_text(score_node))


def parse_nipper_firewall_report_report_root(
    root: "ElementTree.Element", project_type: Optional[str], raw_bytes: Optional[bytes] = None
) -> List[Dict[str, Any]]:
    """Parse report-root Nipper firewall exports into normalized findings."""

    tier_map = {
        "silver": 1,
        "gold": 2,
        "cloudfirst": 2,
        "platinum": 3,
        "titanium": 3,
    }
    normalized_tier = (project_type or "").strip().lower()
    tier = tier_map.get(normalized_tier, 3)

    logger.info(
        "Parsing Nipper firewall report (report-root; tier=%s); bytes_read=%s",
        normalized_tier or "auto",
        len(raw_bytes or b""),
    )

    findings: List[Dict[str, Any]] = []
    applicable_refs = ["VULNAUDIT"]
    if tier >= 2:
        applicable_refs.append("SECURITYAUDIT")
    if tier >= 3:
        applicable_refs.append("COMPLEXITY")

    candidate_sections = list(iter_report_findings(root))

    vulnaudit_count = 0
    security_count = 0
    complexity_count = 0

    for section in candidate_sections:
        audit_text = (get_extra(section, "AUDIT") or "").lower()
        if not any(keyword in audit_text for keyword in ("nvd", "vuln", "vulnerability", "nist")):
            continue

        nipper_block = _find_child_element(section, "nipper")
        risk = normalize_risk(_get_element_field(nipper_block, "summary"))
        if not risk:
            risk = normalize_risk(_get_element_field(nipper_block, "impact"))

        details = get_subsection_text(section, "Finding") or get_extra(section, "CON")
        impact = get_subsection_text(section, "Impact") or details
        score = _extract_report_cvss_score(section)

        issue = _get_element_field(section, "title")
        devices = get_devices(section)
        reference = _build_cve_links(issue)

        findings.append(
            {
                "Risk": risk,
                "Issue": issue,
                "Devices": devices,
                "Solution": "Apply a patch, upgrade the OS or apply vendor mitigations",
                "Impact": impact,
                "Details": details,
                "Reference": reference,
                "Score": score,
                "Accepted": "No",
                "Type": "Vuln",
            }
        )
        vulnaudit_count += 1

    if "SECURITYAUDIT" in applicable_refs:
        for section in candidate_sections:
            audit_text = (get_extra(section, "AUDIT") or "").lower()
            if not any(keyword in audit_text for keyword in ("best practice", "security", "configuration", "audit")):
                continue

            nipper_block = _find_child_element(section, "nipper")
            risk = normalize_risk(_get_element_field(nipper_block, "summary"))
            if not risk:
                risk = normalize_risk(_get_element_field(nipper_block, "impact"))

            issue = _get_element_field(section, "title")
            devices = get_devices(section)
            impact = (
                get_subsection_text(section, "Impact")
                or get_extra(section, "CON")
                or get_subsection_text(section, "Finding")
            )
            details = get_subsection_text(section, "Finding") or get_extra(section, "CON")
            solution = get_subsection_text(section, "Recommendation") or get_extra(section, "REC")
            score = _extract_report_cvss_score(section)
            classification = (get_extra(section, "CLASSIFICATION") or "").upper()
            section_type = "Rule" if classification.startswith("FILTER") or "FILTER" in classification else "Config"

            findings.append(
                {
                    "Risk": risk,
                    "Issue": issue,
                    "Devices": devices,
                    "Solution": solution,
                    "Impact": impact,
                    "Details": details,
                    "Reference": "N/A",
                    "Score": score,
                    "Accepted": "No",
                    "Type": section_type,
                }
            )
            security_count += 1

    if "COMPLEXITY" in applicable_refs:
        default_impact = (
            "While not a technical vulnerability, adherence to best practice calls for these items to be addressed"
        )
        default_solution = "Review these items and address them appropriately"

        for section in candidate_sections:
            audit_text = (get_extra(section, "AUDIT") or "").lower()
            classification_text = (get_extra(section, "CLASSIFICATION") or "").lower()
            related_text = (get_extra(section, "RELATED") or "").lower()
            if (
                "complexity" not in audit_text
                and "complexity" not in classification_text
                and "complexity" not in related_text
            ):
                continue

            issue = _get_element_field(section, "title")
            devices = get_devices(section)

            details_parts: List[str] = []
            finding_text = get_subsection_text(section, "Finding")
            if finding_text:
                details_parts.append(finding_text)
            else:
                subsections = _find_child_element(section, "subsections")
                for subsection in _find_child_elements(subsections, "section"):
                    contents = _find_child_element(subsection, "contents")
                    for content in _find_child_elements(contents, "content"):
                        content_text = _element_text(content)
                        if content_text:
                            details_parts.append(content_text)

            findings.append(
                {
                    "Risk": "Low",
                    "Issue": issue,
                    "Devices": devices,
                    "Solution": default_solution,
                    "Impact": default_impact,
                    "Details": "\n".join([part for part in details_parts if part]),
                    "Reference": "N/A",
                    "Score": 1,
                    "Accepted": "No",
                    "Type": "Complexity",
                }
            )
            complexity_count += 1

    logger.info(
        (
            "Finished Nipper firewall parsing (report-root): tier=%s bytes_read=%s "
            "vulnaudit_findings=%d security_findings=%d complexity_findings=%d findings=%d"
        ),
        normalized_tier or "auto",
        len(raw_bytes or b""),
        vulnaudit_count,
        security_count,
        complexity_count,
        len(findings),
    )

    return findings


def parse_nipper_firewall_report(
    file_obj: File, project_type: Optional[str] = None
) -> List[Dict[str, Any]]:
    """Parse a Nipper XML export into normalized firewall findings."""

    try:
        if hasattr(file_obj, "open"):
            try:
                file_obj.open("rb")
            except Exception:
                pass
        if hasattr(file_obj, "seek"):
            try:
                file_obj.seek(0)
            except Exception:
                pass
        raw_bytes = file_obj.read()
    except Exception:  # pragma: no cover - unexpected I/O failure
        logger.info("Failed to read Nipper firewall report", exc_info=True)
        return []

    try:
        root = ElementTree.fromstring(raw_bytes)
    except ElementTree.ParseError:
        logger.info("Unable to parse Nipper firewall XML", exc_info=True)
        return []

    root_tag = getattr(root, "tag", "")
    normalized_root_tag = _normalize_xml_tag(root_tag)
    document_node = _find_child_element(root, "document")
    if not (root_tag == "document" or normalized_root_tag == "document" or document_node is not None):
        if root_tag == "report" or normalized_root_tag == "report":
            return parse_nipper_firewall_report_report_root(root, project_type, raw_bytes=raw_bytes)

    document = document_node or root
    info_block = _find_child_element(document, "information")
    devices_node = _find_child_element(info_block, "devices")
    device_names = [
        _get_element_field(device, "name")
        for device in _find_child_elements(devices_node, "device")
        if _get_element_field(device, "name")
    ]
    device_name_set = set(device_names)

    tier_map = {
        "silver": 1,
        "gold": 2,
        "cloudfirst": 2,
        "platinum": 3,
        "titanium": 3,
    }
    normalized_tier = (project_type or "").strip().lower()
    tier = tier_map.get(normalized_tier, 3)

    logger.info(
        "Parsing Nipper firewall report (tier=%s); bytes_read=%s", normalized_tier or "auto", len(raw_bytes)
    )

    findings: List[Dict[str, Any]] = []
    applicable_refs = ["VULNAUDIT"]
    if tier >= 2:
        applicable_refs.append("SECURITYAUDIT")
    if tier >= 3:
        applicable_refs.append("COMPLEXITY")

    vulnaudit_sections = _iter_nipper_sections(root, "VULNAUDIT")
    for parent in vulnaudit_sections:
        skip_refs = {
            "VULNAUDIT.INTRO",
            "VULNAUDIT.CONCLUSIONS",
            "VULNAUDIT.RECOMMENDATIONS",
        }
        for section in _find_child_elements(parent, "section"):
            section_ref = (section.attrib.get("ref") or "").upper()
            if section_ref in skip_refs:
                continue

            issue = _get_element_field(section, "title")
            risk = ""
            impact = ""
            score: Any = ""
            device_entries: List[str] = []
            devices = ""
            reference = ""
            details = ""

            for child in section:
                child_tag = _normalize_xml_tag(getattr(child, "tag", ""))
                child_title = (_get_element_field(child, "title") or "").strip()
                if child_tag == "infobox":
                    risk_text = _get_element_field(child, "title")
                    if ": " in risk_text:
                        risk_text = risk_text.split(": ")[-1]
                    normalized_risk = risk_text.strip()
                    if normalized_risk.lower() == "critical":
                        normalized_risk = "High"
                    if normalized_risk.lower() == "informational":
                        normalized_risk = "Low"
                    risk = normalized_risk

                    metric_nodes = _find_child_elements(child, "item") + _find_child_elements(
                        child, "infodata"
                    )
                    for item in metric_nodes:
                        label = (item.attrib.get("label") or "").strip()
                        value = _element_text(item)
                        if label == "CVSSv2 Score":
                            score = _safe_float(value)
                        elif label == "CVSSv2 Base":
                            impact = _get_nipper_impact(value)
                elif child_title.lower() == "summary":
                    details = _element_text(child)
                    impact = details
                    summary_text = (details or "").lower()
                    for device_name in device_names:
                        if device_name and device_name.lower() in summary_text:
                            device_entries.append(device_name)
                elif child_title.lower() == "affected devices":
                    for item in child.iter():
                        tag = _normalize_xml_tag(getattr(item, "tag", ""))
                        if tag not in {"listitem", "item"}:
                            continue
                        item_text = _element_text(item)
                        if not item_text:
                            continue
                        matched = [
                            name for name in device_names if name and name.lower() in item_text.lower()
                        ]
                        if matched:
                            device_entries.extend(matched)
                        else:
                            device_entries.append(item_text)
                    devices = "\n".join(dict.fromkeys(device_entries))
                elif child_title.lower() == "affected device":
                    device_text = _element_text(child)
                    matched_devices = [name for name in device_names if name and name in device_text]
                    devices = "\n".join(matched_devices)
                elif child_title.lower() in {"vendor security advisory", "vendor security advisories"}:
                    advisories: List[str] = []
                    for item in _find_child_elements(child, "item"):
                        link = item.attrib.get("weblink") or _element_text(item)
                        if link:
                            advisories.append(link)
                    reference = "\n".join(advisories)

            reference = _build_cve_links(issue)
            devices = "\n".join(dict.fromkeys(device_entries)) or devices

            findings.append(
                {
                    "Risk": risk,
                    "Issue": issue,
                    "Devices": devices,
                    "Solution": "Apply a patch, upgrade the OS or apply vendor mitigations",
                    "Impact": impact,
                    "Details": details,
                    "Reference": reference,
                    "Score": score,
                    "Accepted": "No",
                    "Type": "Vuln",
                }
            )

    security_sections: List[ElementTree.Element] = []
    if "SECURITYAUDIT" in applicable_refs:
        security_sections = _iter_nipper_sections(root, "SECURITYAUDIT")
        for parent in security_sections:
            skip_refs = {
                "SECURITY.INTRODUCTION",
                "SECURITY.CONCLUSIONS",
                "SECURITY.RECOMMENDATIONS",
                "SECURITY.MITIGATIONS",
                "SECURITY.CLASSIFICATIONS",
                "SECURITY.FINDINGS.SUMMARY",
            }

            for section in _find_child_elements(parent, "section"):
                section_ref = (section.attrib.get("ref") or "").upper()
                if section_ref in skip_refs:
                    continue

                issue = _get_element_field(section, "title")
                reference = "N/A"
                risk = ""
                impact = ""
                devices = ""
                solution = ""
                details = ""
                score: Any = ""
                section_type = "Rule" if section_ref.startswith("FILTER") else "Config"

                for subsection in section:
                    sub_tag = _normalize_xml_tag(getattr(subsection, "tag", ""))
                    sub_ref = (subsection.attrib.get("ref") or "").upper()
                    if sub_tag == "issuedetails":
                        issue_devices: List[str] = []
                        for device in _find_child_elements(_find_child_element(subsection, "devices"), "device"):
                            name = _get_element_field(device, "name")
                            if name:
                                issue_devices.append(name)
                        devices = "\n".join(issue_devices)

                        ratings = _find_child_element(subsection, "ratings")
                        for rating in ratings or []:
                            rating_tag = _normalize_xml_tag(getattr(rating, "tag", ""))
                            if rating_tag == "rating":
                                rating_value = (_element_text(rating) or "").strip()
                                if rating_value.lower() == "informational":
                                    rating_value = "Low"
                                if rating_value.lower() == "critical":
                                    rating_value = "High"
                                risk = rating_value
                            elif rating_tag == "cvssv2-temporal":
                                rating_score = rating.attrib.get("score") or ""
                                if rating_score == "0":
                                    rating_score = "1"
                                score = _safe_float(rating_score)

                    elif sub_ref == "IMPACT":
                        if issue == "SSH Protocol Version 1 Supported":
                            impact = (
                                "Although flaws have been identified with SSH protocol version 2, "
                                "fundamental flaws exist in protocol version 1"
                            )
                        else:
                            impact = _get_nipper_finding(subsection, section_ref)
                    elif sub_ref == "RECOMMENDATION":
                        for child in subsection:
                            solution = _element_text(child)
                            if solution:
                                break
                    elif sub_ref == "FINDING":
                        details = _get_nipper_finding(subsection, section_ref)

                findings.append(
                    {
                        "Risk": risk,
                        "Issue": issue,
                        "Devices": devices,
                        "Solution": solution,
                        "Impact": impact,
                        "Details": details,
                        "Reference": reference,
                        "Score": score,
                        "Accepted": "No",
                        "Type": section_type,
                    }
                )

    complexity_sections: List[ElementTree.Element] = []
    if "COMPLEXITY" in applicable_refs:
        complexity_sections = _iter_nipper_sections(root, "COMPLEXITY")
        for parent in complexity_sections:
            skip_titles = {"introduction", "no filter rules found", "no issues found"}
            default_impact = (
                "While not a technical vulnerability, adherence to best practice calls for these items to be addressed"
            )
            default_solution = "Review these items and address them appropriately"

            for section in _find_child_elements(parent, "section"):
                title = (_get_element_field(section, "title") or "").strip()
                if title.lower() in skip_titles:
                    continue

                devices: List[str] = []
                details_parts: List[str] = []
                risk = "Low"
                score = 1
                reference = "N/A"
                section_type = "Complexity"

                for subsection in section:
                    if _normalize_xml_tag(getattr(subsection, "tag", "")) != "section":
                        continue
                    sub_ref = (subsection.attrib.get("ref") or "").upper()
                    subtitle = (_get_element_field(subsection, "title") or "").strip()
                    if subtitle:
                        first_word = subtitle.split()[0]
                        if first_word and (
                            sub_ref.endswith(".10")
                            or not device_name_set
                            or first_word in device_name_set
                        ):
                            devices.append(first_word)

                    table_title = (subtitle or "").lower()
                    is_filter_rules = "filter rules" in table_title
                    if is_filter_rules:
                        details_parts.append(
                            _get_nipper_finding(subsection, "FILTER.", is_complexity=True)
                        )
                    else:
                        details_parts.append(
                            _get_nipper_finding(subsection, "COMPLEXITY", is_complexity=True)
                        )

                findings.append(
                    {
                        "Risk": risk,
                        "Issue": title,
                        "Devices": "\n".join([device for device in devices if device]),
                        "Solution": default_solution,
                        "Impact": default_impact,
                        "Details": "\n".join([part for part in details_parts if part]),
                        "Reference": reference,
                        "Score": score,
                        "Accepted": "No",
                        "Type": section_type,
                    }
                )

    logger.info(
        "Finished Nipper firewall parsing: vulnaudit_sections=%d security_sections=%d complexity_sections=%d findings=%d",
        len(vulnaudit_sections),
        len(security_sections),
        len(complexity_sections),
        len(findings),
    )

    return findings


def parse_dns_report(file_obj: File) -> List[Dict[str, str]]:
    """Parse a dns_report.csv file, returning issue metadata for failed checks."""

    finding_map = _load_mapping(
        "DNSFindingMapping",
        "finding_text",
        DEFAULT_DNS_FINDING_MAP,
    )
    recommendation_map = _load_mapping(
        "DNSRecommendationMapping",
        "recommendation_text",
        DEFAULT_DNS_RECOMMENDATION_MAP,
    )
    cap_map = _load_mapping(
        "DNSCapMapping",
        "cap_text",
        DEFAULT_DNS_CAP_MAP,
    )

    issues: List[Dict[str, str]] = []
    target_issue = "One or more SOA fields are outside recommended ranges"

    for row in _decode_file(file_obj):
        status = (row.get("Status") or row.get("status") or "").strip().upper()
        if status != "FAIL":
            continue
        info = (row.get("Info") or row.get("info") or "").strip()
        if not info:
            continue

        info_lines = [line.strip() for line in info.splitlines()]
        while info_lines and not info_lines[0]:
            info_lines.pop(0)

        if not info_lines:
            continue

        issue_text = info_lines[0]
        if not issue_text:
            continue

        soa_fields: List[str] = []
        if issue_text == target_issue:
            for line in info_lines[1:]:
                if not line:
                    continue
                field_name = line.split(" |", 1)[0].strip()
                if field_name and field_name not in soa_fields:
                    soa_fields.append(field_name)

        finding = finding_map.get(issue_text, "")
        recommendation = recommendation_map.get(issue_text, "")
        cap = cap_map.get(issue_text, "")
        impact = DNS_IMPACT_MAP.get(issue_text, "")

        issue_entry: Dict[str, str] = {
            "issue": issue_text,
            "finding": finding,
            "recommendation": recommendation,
            "cap": cap,
            "impact": impact,
        }

        if soa_fields:
            issue_entry["soa_fields"] = soa_fields

        issues.append(issue_entry)
    return issues


class _SeverityItemsAccessor:
    """Provide dual behaviour for severity ``items`` access."""

    __slots__ = ("_data",)

    def __init__(self, data: "_SeverityGroup") -> None:
        self._data = data

    def __call__(self, *args, **kwargs):  # pragma: no cover - compatibility shim
        return dict.items(self._data, *args, **kwargs)

    def __iter__(self):
        return iter(dict.get(self._data, "items", []))

    def __len__(self):  # pragma: no cover - defensive guard
        return len(dict.get(self._data, "items", []))

    def __bool__(self):
        return bool(dict.get(self._data, "items", []))

    def __repr__(self):  # pragma: no cover - used for debugging
        return repr(dict.get(self._data, "items", []))


class _SeverityGroup(dict):
    """Dictionary subclass exposing list-like ``items`` attribute access."""

    __slots__ = ()

    def __getattribute__(self, name):
        if name == "items":
            return _SeverityItemsAccessor(self)
        return dict.__getattribute__(self, name)


def _coerce_severity_group(value: Any) -> _SeverityGroup:
    """Normalize a severity mapping into a ``_SeverityGroup`` instance."""

    if isinstance(value, _SeverityGroup):
        return value
    total_unique = 0
    items: List[Dict[str, Any]] = []
    if isinstance(value, dict):
        raw_total = value.get("total_unique", 0)
        try:
            total_unique = int(raw_total)
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            total_unique = 0
        raw_items = value.get("items", [])
        if isinstance(raw_items, list):
            items = list(raw_items)
        elif raw_items:  # pragma: no cover - defensive guard
            items = list(raw_items)
    return _SeverityGroup(total_unique=total_unique, items=items)


def _empty_severity_group() -> _SeverityGroup:
    """Return a severity group with zero findings."""

    return _SeverityGroup(total_unique=0, items=[])


def _default_nexpose_artifact(label: str) -> Dict[str, Any]:
    """Return a default Nexpose artifact payload for the provided label."""

    return {
        "label": label,
        "high": _empty_severity_group(),
        "med": _empty_severity_group(),
        "low": _empty_severity_group(),
    }


def normalize_nexpose_artifact_payload(payload: Any) -> Dict[str, Any]:
    """Return a copy of ``payload`` with severity buckets wrapped for templates."""

    if not isinstance(payload, dict):
        return payload
    normalized: Dict[str, Any] = dict(payload)
    for severity_key in ("high", "med", "low"):
        if severity_key in normalized:
            normalized[severity_key] = _coerce_severity_group(normalized[severity_key])
    return normalized


def _normalize_web_site_payload(payload: Any, site_name: Optional[str] = None) -> Any:
    """Normalize a single web issue site payload for template access."""

    if not isinstance(payload, dict):
        return payload

    normalized: Dict[str, Any] = dict(payload)
    if site_name and not normalized.get("site"):
        normalized["site"] = site_name

    for severity_key in ("high", "med", "low"):
        normalized[severity_key] = _coerce_severity_group(normalized.get(severity_key, {}))

    return normalized


def _coerce_web_issue_summary(
    value: Any, *, web_issue_matrix: Optional[Dict[str, Dict[str, str]]] = None
) -> Dict[str, Any]:
    """Return a normalized mapping of aggregate web issue severities."""

    low_sample_string = ""
    med_sample_string = ""
    ai_response: Optional[str] = None
    severity_groups = {
        key: _coerce_severity_group({}) for key in ("high", "med", "low")
    }

    if isinstance(value, dict):
        low_sample_string = str(value.get("low_sample_string") or "")
        med_sample_string = str(value.get("med_sample_string") or "")
        if value.get("ai_response"):
            ai_response = str(value.get("ai_response"))
        has_explicit_summary = False

        for severity_key in ("high", "med", "low"):
            if severity_key in value:
                severity_groups[severity_key] = _coerce_severity_group(
                    value.get(severity_key, {})
                )
                has_explicit_summary = True

        if has_explicit_summary:
            return {
                "low_sample_string": low_sample_string,
                "med_sample_string": med_sample_string,
                "ai_response": ai_response,
                **severity_groups,
            }

        raw_sites = value.get("sites")
        if isinstance(raw_sites, list):
            site_entries = [
                _normalize_web_site_payload(site_payload)
                for site_payload in raw_sites
                if isinstance(site_payload, dict)
            ]
        else:
            site_entries = [
                _normalize_web_site_payload(site_payload, site)
                for site, site_payload in sorted(
                    value.items(), key=lambda item: (item[0] or "").lower()
                )
                if site
                not in {"low_sample_string", "med_sample_string", "high", "med", "low"}
                and isinstance(site_payload, dict)
            ]
    elif isinstance(value, list):
        site_entries = [
            _normalize_web_site_payload(site_payload)
            for site_payload in value
            if isinstance(site_payload, dict)
        ]
    else:
        site_entries = []

    if site_entries:
        aggregated: Dict[str, Counter[Tuple[str, str]]] = {
            "high": Counter(),
            "med": Counter(),
            "low": Counter(),
        }
        fallback_totals = {"high": 0, "med": 0, "low": 0}
        for site_payload in site_entries:
            for severity_key in ("high", "med", "low"):
                group = _coerce_severity_group(site_payload.get(severity_key, {}))
                total_unique = group.get("total_unique")
                try:
                    total_value = int(total_unique)
                except (TypeError, ValueError):  # pragma: no cover - defensive guard
                    total_value = 0
                fallback_totals[severity_key] = max(
                    fallback_totals[severity_key], max(total_value, 0)
                )
                for item in group.get("items", []):
                    issue = str(item.get("issue", "") or "").strip()
                    impact = str(item.get("impact", "") or "").strip()
                    count = item.get("count", 1)
                    try:
                        count_value = int(count)
                    except (TypeError, ValueError):  # pragma: no cover - defensive guard
                        count_value = 1
                    aggregated[severity_key][(issue, impact)] += max(count_value, 0)
        severity_groups = {
            severity_key: _summarize_severity_counter(
                counter, web_issue_matrix=web_issue_matrix
            )
            for severity_key, counter in aggregated.items()
        }
        for severity_key, fallback_total in fallback_totals.items():
            group = severity_groups.get(severity_key)
            if group.get("total_unique", 0) or not fallback_total:
                continue
            group["total_unique"] = fallback_total

    return {
        "low_sample_string": low_sample_string,
        "med_sample_string": med_sample_string,
        "ai_response": ai_response,
        **severity_groups,
    }


def _normalize_nexpose_metrics_payload(metrics: Any) -> Dict[str, Any]:
    """Return a Nexpose metrics payload with expected keys populated."""

    if not isinstance(metrics, Mapping):
        metrics = {}

    normalized: Dict[str, Any] = dict(metrics)

    summary_defaults = {
        "total": 0,
        "total_high": 0,
        "total_med": 0,
        "total_low": 0,
        "unique": 0,
        "unique_high": 0,
        "unique_med": 0,
        "unique_low": 0,
        "unique_high_med": 0,
        "total_ood": 0,
        "total_isc": 0,
        "total_iwc": 0,
        "majority_count": 0,
        "minority_count": 0,
    }

    summary = normalized.get("summary")
    summary_data = dict(summary) if isinstance(summary, Mapping) else {}
    for key, default in summary_defaults.items():
        summary_data.setdefault(key, default)
    normalized["summary"] = summary_data

    normalized["host_counts"] = (
        list(normalized.get("host_counts"))
        if isinstance(normalized.get("host_counts"), list)
        else []
    )
    normalized["top_hosts"] = (
        list(normalized.get("top_hosts"))
        if isinstance(normalized.get("top_hosts"), list)
        else []
    )

    for key in ("top_hosts_high", "top_hosts_med", "top_hosts_low", "top_hosts_total"):
        normalized[key] = _coerce_int(normalized.get(key)) or 0

    for key in (
        "top_impacts",
        "tab_index_entries",
        "unique_issues",
        "majority_unique",
        "majority_subset",
        "all_issues",
        "high_issues",
        "med_issues",
        "low_issues",
    ):
        normalized[key] = (
            list(normalized.get(key)) if isinstance(normalized.get(key), list) else []
        )

    for key in ("majority_type", "minority_type"):
        raw_value = normalized.get(key)
        normalized[key] = raw_value.strip() if isinstance(raw_value, str) else None

    normalized["xlsx_filename"] = (
        normalized.get("xlsx_filename")
        if isinstance(normalized.get("xlsx_filename"), str)
        else None
    )
    normalized["xlsx_base64"] = (
        normalized.get("xlsx_base64") if isinstance(normalized.get("xlsx_base64"), str) else None
    )

    return normalized


def normalize_nexpose_artifacts_map(artifacts: Any) -> Any:
    """Normalize Nexpose and web issue artifact entries for template access."""

    if not isinstance(artifacts, dict):
        return artifacts
    normalized: Dict[str, Any] = dict(artifacts)

    for legacy_key, new_key in LEGACY_NEXPOSE_ARTIFACT_ALIASES.items():
        if legacy_key not in normalized:
            continue
        if new_key not in normalized:
            normalized[new_key] = normalized[legacy_key]
        normalized.pop(legacy_key, None)

    for key, value in list(normalized.items()):
        if isinstance(key, str) and key.endswith("_nexpose_vulnerabilities"):
            normalized[key] = normalize_nexpose_artifact_payload(value)
        elif key == "web_issues":
            normalized[key] = _coerce_web_issue_summary(value)

    for metrics_key in NEXPOSE_METRICS_LABELS:
        normalized[metrics_key] = _normalize_nexpose_metrics_payload(
            normalized.get(metrics_key)
        )
    return normalized


def summarize_nexpose_matrix_gaps(artifacts: Any) -> Dict[str, List[Dict[str, str]]]:
    """Return artifact-scoped missing Nexpose matrix entries."""

    if not isinstance(artifacts, dict):
        return {}
    gap_data = artifacts.get("nexpose_matrix_gaps")
    if not isinstance(gap_data, dict):
        return {}
    missing_by_artifact = gap_data.get("missing_by_artifact")
    if not isinstance(missing_by_artifact, dict):
        return {}
    summary: Dict[str, List[Dict[str, str]]] = {}
    for artifact_key, payload in missing_by_artifact.items():
        entries = payload.get("entries") if isinstance(payload, dict) else payload
        if isinstance(entries, list) and entries:
            summary[artifact_key] = entries
    return summary


def has_open_nexpose_matrix_gaps(artifacts: Any) -> bool:
    """Return ``True`` if any Nexpose XML findings are missing matrix entries."""

    summary = summarize_nexpose_matrix_gaps(artifacts)
    return any(summary.values())


def summarize_web_issue_matrix_gaps(artifacts: Any) -> List[Dict[str, str]]:
    """Return missing web issue matrix entries when present."""

    if not isinstance(artifacts, dict):
        return []
    gap_data = artifacts.get("web_issue_matrix_gaps")
    if not isinstance(gap_data, dict):
        return []
    entries = gap_data.get("entries")
    if isinstance(entries, list):
        normalized_entries: List[Dict[str, str]] = []
        for entry in entries:
            if not isinstance(entry, dict):
                continue
            issue_value = (entry.get("issue") or "").strip()
            if not issue_value:
                continue
            normalized_entries.append(
                {"issue": issue_value, "impact": entry.get("impact", ""), "fix": entry.get("fix", "")}
            )
        return normalized_entries
    return []


def has_open_web_issue_matrix_gaps(artifacts: Any) -> bool:
    """Return ``True`` when Burp XML findings reference missing matrix issues."""

    summary = summarize_web_issue_matrix_gaps(artifacts)
    return bool(summary)


def _build_web_issue_ai_response(
    summary: Dict[str, Any], *, require_web_data: bool
) -> Optional[str]:
    """Generate an OpenAI summary for high or medium web issues when enabled."""

    if not require_web_data:
        return None

    try:
        config = OpenAIConfiguration.get_solo()
    except (OpenAIConfiguration.DoesNotExist, ProgrammingError, OperationalError):
        return None

    if not config.enable:
        return None

    severity_order = ("high", "med")
    target_items: List[Dict[str, Any]] = []
    for severity_key in severity_order:
        group = summary.get(severity_key)
        if not isinstance(group, dict):
            continue
        total_unique = group.get("total_unique")
        try:
            total_value = int(total_unique)
        except (TypeError, ValueError):
            total_value = 0
        if total_value > 0:
            target_items = group.get("items", [])
            break

    if not target_items:
        return None

    responses: List[str] = []
    for item in target_items:
        if not isinstance(item, dict):
            continue
        issue = (item.get("issue") or item.get("title") or "").strip()
        if not issue:
            continue
        prompt = WEB_ISSUE_PROMPT_TEMPLATE.replace("{{ .issue }}", issue)
        try:
            result = submit_prompt_to_assistant(prompt, config=config)
        except Exception as exc:  # pragma: no cover - defensive guard
            logger.warning("OpenAI prompt submission failed: %s", exc)
            result = None
        if result:
            responses.append(result.strip())

    if responses:
        return " ".join(response for response in responses if response).strip()
    return None


def parse_nexpose_vulnerability_report(
    file_obj: File,
    *,
    vulnerability_matrix: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, Dict[str, Any]]:
    """Parse a Nexpose CSV export into grouped vulnerability summaries."""

    grouped: Dict[str, Counter] = {
        "High": Counter(),
        "Medium": Counter(),
        "Low": Counter(),
    }

    for row in _decode_file(file_obj):
        severity_value = _parse_severity_level(
            _get_case_insensitive(row, "Vulnerability Severity Level")
        )
        severity_bucket = _categorize_severity(severity_value)
        if not severity_bucket:
            continue

        title = str(_get_case_insensitive(row, "Vulnerability Title") or "").strip()
        impact = str(_get_case_insensitive(row, "Impact") or "").strip()
        if not title and not impact:
            continue

        grouped[severity_bucket][(title, impact)] += 1

    summaries: Dict[str, Dict[str, Any]] = {}
    severity_map = {
        "High": "high",
        "Medium": "med",
        "Low": "low",
    }

    for severity in ("High", "Medium", "Low"):
        counter = grouped.get(severity, Counter())
        ordered = sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                (item[0][0] or "").lower(),
                (item[0][1] or "").lower(),
            ),
        )
        items: List[Dict[str, Any]] = []
        for (title, impact), count in ordered[:5]:
            entry = {"title": title, "impact": impact, "count": count}
            _apply_vulnerability_matrix_fields(entry, vulnerability_matrix)
            items.append(entry)

        summaries[severity_map[severity]] = _SeverityGroup(
            total_unique=len(counter),
            items=items,
        )

    return summaries


def _build_nexpose_vulnerability_summary_from_findings(
    findings: Any,
    *,
    vulnerability_matrix: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, _SeverityGroup]:
    """Summarize Nexpose findings into vulnerability groupings."""

    grouped: Dict[str, Counter] = {
        "High": Counter(),
        "Medium": Counter(),
        "Low": Counter(),
    }

    if isinstance(findings, list):
        for entry in findings:
            if not isinstance(entry, dict):
                continue
            severity_value = _parse_severity_level(
                entry.get("Vulnerability Severity Level")
            )
            severity_bucket = _categorize_severity(severity_value)
            if not severity_bucket:
                continue

            title = str(entry.get("Vulnerability Title") or "").strip()
            impact = str(entry.get("Impact") or "").strip()
            if not title and not impact:
                continue
            grouped[severity_bucket][(title, impact)] += 1

    severity_map = {
        "High": "high",
        "Medium": "med",
        "Low": "low",
    }

    summaries: Dict[str, _SeverityGroup] = {}
    for severity in ("High", "Medium", "Low"):
        counter = grouped.get(severity, Counter())
        ordered = sorted(
            counter.items(),
            key=lambda item: (
                -item[1],
                (item[0][0] or "").lower(),
                (item[0][1] or "").lower(),
            ),
        )
        items: List[Dict[str, Any]] = []
        for (title, impact), count in ordered[:5]:
            entry = {"title": title, "impact": impact, "count": count}
            _apply_vulnerability_matrix_fields(entry, vulnerability_matrix)
            items.append(entry)

        summaries[severity_map[severity]] = _SeverityGroup(
            total_unique=len(counter),
            items=items,
        )

    return summaries


def parse_nexpose_xml_report(
    file_obj: File,
    *,
    vulnerability_matrix: Optional[Dict[str, Dict[str, str]]] = None,
) -> Dict[str, List[Dict[str, str]]]:
    """Parse a ``nexpose_xml.xml`` upload into structured findings and software entries."""

    findings: List[Dict[str, str]] = []
    software_entries: List[Dict[str, str]] = []
    missing_matrix_rows: Dict[str, Dict[str, str]] = {}

    raw_bytes = _read_binary_file(file_obj)
    if not raw_bytes.strip():
        return {"findings": findings, "software": software_entries}

    try:
        report_root = ElementTree.fromstring(raw_bytes)
    except ElementTree.ParseError:  # pragma: no cover - invalid XML is ignored
        logger.warning("Unable to parse Nexpose XML upload", exc_info=True)
        return {"findings": findings, "software": software_entries}

    vulnerability_lookup = _build_vulnerability_lookup(report_root)
    nodes_parent = report_root.find("nodes")
    if nodes_parent is None:
        return {"findings": findings, "software": software_entries}

    for node in nodes_parent.findall("node"):
        ip_address = _collapse_whitespace(_get_element_field(node, "address"))
        hostnames = _collect_node_hostnames(node)
        hostname_text = "; ".join(hostnames)
        os_description = _extract_os_description(node)

        for test_element in node.findall("./tests/test"):
            entry, missing_row = _build_nexpose_finding_entry(
                ip_address=ip_address,
                hostnames=hostname_text,
                os_description=os_description,
                port="",
                protocol="",
                test_element=test_element,
                vulnerability_lookup=vulnerability_lookup,
                vulnerability_matrix=vulnerability_matrix,
            )
            if entry:
                findings.append(entry)
            if missing_row:
                key = (missing_row.get("Vulnerability") or "").strip().lower()
                if key:
                    missing_matrix_rows[key] = missing_row

        for endpoint in node.findall("./endpoints/endpoint"):
            port = _collapse_whitespace(_get_element_field(endpoint, "port"))
            protocol = _collapse_whitespace(_get_element_field(endpoint, "protocol")).upper()
            for service in endpoint.findall("./services/service"):
                for test_element in service.findall("./tests/test"):
                    entry, missing_row = _build_nexpose_finding_entry(
                        ip_address=ip_address,
                        hostnames=hostname_text,
                        os_description=os_description,
                        port=port,
                        protocol=protocol,
                        test_element=test_element,
                        vulnerability_lookup=vulnerability_lookup,
                        vulnerability_matrix=vulnerability_matrix,
                    )
                    if entry:
                        findings.append(entry)
                    if missing_row:
                        key = (missing_row.get("Vulnerability") or "").strip().lower()
                        if key:
                            missing_matrix_rows[key] = missing_row

        software_fingerprints = node.findall("./software/fingerprint")
        if not software_fingerprints:
            software_fingerprints = node.findall("./software/softwareFingerprint")
        system_label = ip_address or hostname_text or "Unknown System"
        display_system = system_label
        if hostname_text:
            if ip_address:
                display_system = f"{ip_address} ({hostname_text})"
            else:
                display_system = hostname_text
        for fingerprint in software_fingerprints:
            product = _collapse_whitespace(_get_element_field(fingerprint, "product"))
            version = _collapse_whitespace(_get_element_field(fingerprint, "version"))
            if not (product or version):
                continue
            software_entries.append(
                {"System": display_system, "Software": product, "Version": version}
            )

    missing_entries = sorted(
        missing_matrix_rows.values(),
        key=lambda row: (row.get("Vulnerability") or "").lower(),
    )
    return {
        "findings": findings,
        "software": software_entries,
        "missing_matrix_entries": missing_entries,
    }


NEXPOSE_ARTIFACT_DEFINITIONS: Dict[str, Dict[str, str]] = {
    "external_nexpose_csv.csv": {
        "artifact_key": "external_nexpose_vulnerabilities",
        "label": "External Nexpose Vulnerabilities",
    },
    "internal_nexpose_csv.csv": {
        "artifact_key": "internal_nexpose_vulnerabilities",
        "label": "Internal Nexpose Vulnerabilities",
    },
    "iot_nexpose_csv.csv": {
        "artifact_key": "iot_iomt_nexpose_vulnerabilities",
        "label": "IoT/IoMT Nexpose Vulnerabilities",
    },
}

LEGACY_NEXPOSE_ARTIFACT_ALIASES: Dict[str, str] = {
    "iot_nexpose_vulnerabilities": "iot_iomt_nexpose_vulnerabilities",
}

NEXPOSE_ARTIFACT_KEYS = {
    definition["artifact_key"] for definition in NEXPOSE_ARTIFACT_DEFINITIONS.values()
}.union(LEGACY_NEXPOSE_ARTIFACT_ALIASES.keys())


NEXPOSE_TEST_STATUS_MAP = {
    "potential": "VP",
    "vulnerable-exploited": "VE",
    "vulnerable-version": "VV",
}

NEXPOSE_XML_REQUIREMENT_MAP = {
    _normalize_nexpose_identifier("external_nexpose_xml.xml"): "external_nexpose_findings",
    _normalize_nexpose_identifier("required_external_nexpose_xml-xml"): "external_nexpose_findings",
    _normalize_nexpose_identifier("required_external-nexpose-xml-xml"): "external_nexpose_findings",
    _normalize_nexpose_identifier("external nexpose xml"): "external_nexpose_findings",
    _normalize_nexpose_identifier("internal_nexpose_xml.xml"): "internal_nexpose_findings",
    _normalize_nexpose_identifier("required_internal_nexpose_xml-xml"): "internal_nexpose_findings",
    _normalize_nexpose_identifier("required_internal-nexpose-xml-xml"): "internal_nexpose_findings",
    _normalize_nexpose_identifier("internal nexpose xml"): "internal_nexpose_findings",
    _normalize_nexpose_identifier("iot_nexpose_xml.xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("iot_iomt_nexpose_xml.xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("required_iot_nexpose_xml-xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("required_iot_nexpose-xml-xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("required_iot_iomt_nexpose_xml-xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("required_iot-iomt_nexpose_xml-xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("iot nexpose xml"): "iot_iomt_nexpose_findings",
    _normalize_nexpose_identifier("iot iomt nexpose xml"): "iot_iomt_nexpose_findings",
}

NEXPOSE_XML_ARTIFACT_MAP = {
    "external": "external_nexpose_findings",
    "internal": "internal_nexpose_findings",
    "iot": "iot_iomt_nexpose_findings",
    "iomt": "iot_iomt_nexpose_findings",
}

NEXPOSE_FINDINGS_VULNERABILITY_MAP = {
    "external_nexpose_findings": "external_nexpose_vulnerabilities",
    "internal_nexpose_findings": "internal_nexpose_vulnerabilities",
    "iot_iomt_nexpose_findings": "iot_iomt_nexpose_vulnerabilities",
}

NEXPOSE_FILENAME_KEY_MAP = {
    "external_nexpose_findings": "external_nexpose_file_name",
    "internal_nexpose_findings": "internal_nexpose_file_name",
    "iot_iomt_nexpose_findings": "iot_iomt_nexpose_file_name",
}

NEXPOSE_METRICS_KEY_MAP = {
    "external_nexpose_findings": "external_nexpose_metrics",
    "internal_nexpose_findings": "internal_nexpose_metrics",
    "iot_iomt_nexpose_findings": "iot_iomt_nexpose_metrics",
}

NEXPOSE_METRICS_LABELS = {
    "external_nexpose_metrics": "External Nexpose",
    "internal_nexpose_metrics": "Internal Nexpose",
    "iot_iomt_nexpose_metrics": "IoT/IoMT Nexpose",
}

NEXPOSE_UPLOAD_REQUIREMENTS = {
    "external_nexpose_metrics": {
        "slug": "external_nexpose_xlsx",
        "label": "External Nexpose Data file",
        "filename_template": "{client_name} Detailed External System Vulnerability Findings.xlsx",
    },
    "internal_nexpose_metrics": {
        "slug": "internal_nexpose_xlsx",
        "label": "Internal Nexpose Data file",
        "filename_template": "{client_name} Detailed Internal System Vulnerability Findings.xlsx",
    },
    "iot_iomt_nexpose_metrics": {
        "slug": "iot_iomt_nexpose_xlsx",
        "label": "IoT/IoMT Nexpose Data file",
        "filename_template": "{client_name} Detailed IoT-IoMT Device Vulnerability Findings.xlsx",
    },
}

NEXPOSE_UPLOAD_REQUIREMENTS_BY_SLUG = {
    definition["slug"]: definition
    for definition in NEXPOSE_UPLOAD_REQUIREMENTS.values()
    if definition.get("slug")
}

NEXPOSE_TAB_INDEX_ENTRIES = [
    "Unique Issues  -:-  Unique issues found across all scanned systems",
    "Issues by Majority Type  -:-  From the Unique Issues, a listing of those that are the same 'type' (missing patch, configuration item, etc) that represent the majority of the issues found",
    "Subset of Majority Items  -:-  From the Majority Type, a listing of those that are the same application, vendor, service, etc that are responsible for the bulk of the Majority issues",
    "All Issues  -:-  All issues identified. May include 'duplicate' findings (same issue/system, different ports)",
    "High Risk Issues  -:-  All 'High' risk issues identified",
    "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
    "Low Risk Issues  -:-  All 'Low' risk issues identified",
]


def _derive_risk_from_score(score: Optional[int]) -> str:
    """Convert a Nexpose score into a High/Medium/Low risk bucket."""

    if score is None:
        return "Low"
    if score >= 8:
        return "High"
    if score <= 3:
        return "Low"
    return "Medium"


def _build_host_identifier(ip_address: str, hostnames: str) -> str:
    """Return a combined identifier for an asset."""

    ip_text = (ip_address or "").strip()
    hostname_text = (hostnames or "").strip()
    if ip_text and hostname_text:
        return f"{ip_text} ({hostname_text})"
    if ip_text:
        return ip_text
    if hostname_text:
        return hostname_text
    return "Unknown Host"


def _format_port_display(port_value: str, protocol: str) -> str:
    """Render the combined port/protocol string for workbook tables."""

    port_text = (port_value or "").strip()
    proto_text = (protocol or "").strip().upper()
    if not port_text:
        return "N/A"
    if proto_text:
        return f"{port_text}.{proto_text}"
    return port_text


def _build_nexpose_metrics_payload(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Build summary metrics, top lists, and workbook bytes for Nexpose findings."""

    risk_priority = {"High": 0, "Medium": 1, "Low": 2}

    def _sort_by_risk(entries: Iterable[Dict[str, Any]]) -> List[Dict[str, Any]]:
        return sorted(
            entries,
            key=lambda entry: (
                risk_priority.get(entry.get("risk", ""), len(risk_priority)),
                -entry.get("severity", 0),
                (entry.get("issue") or "").lower(),
                (entry.get("ip") or ""),
                (entry.get("hostnames") or ""),
            ),
        )

    total_entries: List[Dict[str, Any]] = []
    unique_entries: "OrderedDict[Tuple[int, str], Dict[str, Any]]" = OrderedDict()
    seen_total_keys: Set[Tuple[str, str, str, int]] = set()
    host_counters: Dict[str, Dict[str, int]] = {}
    impact_counter: Counter[str] = Counter()
    high_issues: List[Dict[str, Any]] = []
    med_issues: List[Dict[str, Any]] = []
    low_issues: List[Dict[str, Any]] = []

    for entry in findings or []:
        ip_address = (entry.get("Asset IP Address") or "").strip()
        hostnames = (entry.get("Hostname(s)") or "").strip()
        port = (entry.get("Service Port") or "").strip()
        protocol = (entry.get("Protocol") or "").strip()
        title = (entry.get("Vulnerability Title") or entry.get("Vulnerability ID") or "").strip()
        if not title:
            title = "Untitled Vulnerability"
        severity = _coerce_int(entry.get("Vulnerability Severity Level")) or 0
        impact = (entry.get("Impact") or "").strip()
        solution = (entry.get("Solution") or "").strip()
        category = (entry.get("Category") or "").strip()
        details = (entry.get("Details") or "").strip()
        evidence = (entry.get("Evidence") or "").strip()
        remediation = (entry.get("Detailed Remediation") or solution or "").strip()
        host_identifier = _build_host_identifier(ip_address, hostnames)
        risk = _derive_risk_from_score(severity)
        port_display = _format_port_display(port, protocol)

        normalized_entry = {
            "ip": ip_address,
            "hostnames": hostnames,
            "host_id": host_identifier,
            "port": port_display,
            "issue": title,
            "impact": impact,
            "details": details,
            "evidence": evidence,
            "remediation": remediation,
            "risk": risk,
            "category": category,
            "severity": severity,
        }

        total_key = (ip_address, hostnames, title.lower(), severity)
        if total_key not in seen_total_keys:
            total_entries.append(normalized_entry)
            seen_total_keys.add(total_key)

        unique_key = (severity, title.lower())
        if unique_key not in unique_entries:
            unique_entries[unique_key] = {
                "risk": risk,
                "issue": title,
                "impact": impact,
                "remediation": solution or remediation,
                "category": category,
                "severity": severity,
            }

        bucket = host_counters.setdefault(host_identifier, {"high": 0, "med": 0, "low": 0})
        if severity >= 8:
            bucket["high"] += 1
            high_issues.append(normalized_entry)
        elif severity >= 4:
            bucket["med"] += 1
            med_issues.append(normalized_entry)
        else:
            bucket["low"] += 1
            low_issues.append(normalized_entry)

        if impact:
            impact_counter[impact] += 1

    total_entries = _sort_by_risk(total_entries)

    total_count = len(total_entries)
    unique_values = _sort_by_risk(unique_entries.values())
    unique_count = len(unique_values)
    unique_high = sum(1 for entry in unique_values if entry.get("severity", 0) >= 8)
    unique_med = sum(1 for entry in unique_values if 4 <= entry.get("severity", 0) <= 7)
    unique_low = sum(1 for entry in unique_values if entry.get("severity", 0) <= 3)
    category_counter: Counter[str] = Counter(
        (entry.get("category") or "").strip() for entry in unique_values if entry.get("category")
    )
    candidate_order = {"OOD": 0, "ISC": 1, "IWC": 2}
    candidate_counts = [
        (candidate, category_counter.get(candidate, 0)) for candidate in candidate_order
    ]
    candidate_counts.sort(key=lambda item: (-item[1], candidate_order[item[0]]))

    top_count = candidate_counts[0][1] if candidate_counts else 0
    second_count = candidate_counts[1][1] if len(candidate_counts) > 1 else 0

    if top_count > 0 and top_count == second_count:
        majority_type = "Even"
        minority_type = "Even"
        majority_count = top_count
        minority_count = second_count
    else:
        majority_type = candidate_counts[0][0] if candidate_counts and top_count > 0 else None
        minority_type = (
            candidate_counts[1][0]
            if len(candidate_counts) > 1 and second_count > 0
            else None
        )
        majority_count = top_count
        minority_count = second_count

    summary = {
        "total": total_count,
        "total_high": len(high_issues),
        "total_med": len(med_issues),
        "total_low": len(low_issues),
        "unique": unique_count,
        "unique_high": unique_high,
        "unique_med": unique_med,
        "unique_low": unique_low,
        "unique_high_med": unique_high + unique_med,
        "total_ood": category_counter.get("OOD", 0),
        "total_isc": category_counter.get("ISC", 0),
        "total_iwc": category_counter.get("IWC", 0),
        "majority_count": majority_count,
        "minority_count": minority_count,
    }

    host_rows = [
        {
            "host": host,
            "high": counts.get("high", 0),
            "med": counts.get("med", 0),
            "low": counts.get("low", 0),
        }
        for host, counts in sorted(host_counters.items(), key=lambda item: item[0].lower())
    ]

    top_hosts = []
    for host in host_rows:
        total_count = host["high"] + host["med"] + host["low"]
        score = host["high"] * 3 + host["med"] * 2 + host["low"]
        top_hosts.append({**host, "total": total_count, "score": score})
    top_hosts.sort(
        key=lambda item: (-item["score"], -item["total"], item["host"].lower())
    )
    top_hosts = top_hosts[:10]

    top_impacts = [
        {"impact": impact, "count": count}
        for impact, count in impact_counter.most_common(10)
    ]

    majority_unique = [
        entry
        for entry in unique_values
        if majority_type and (entry.get("category") or "").strip() == majority_type
    ]
    majority_subset = [
        entry
        for entry in total_entries
        if majority_type and (entry.get("category") or "").strip() == majority_type
    ]

    metrics_payload: Dict[str, Any] = {
        "summary": summary,
        "host_counts": host_rows,
        "top_hosts": top_hosts,
        "top_hosts_high": sum(host.get("high", 0) for host in top_hosts),
        "top_hosts_med": sum(host.get("med", 0) for host in top_hosts),
        "top_hosts_low": sum(host.get("low", 0) for host in top_hosts),
        "top_hosts_total": sum(host.get("total", 0) for host in top_hosts),
        "top_impacts": top_impacts,
        "tab_index_entries": NEXPOSE_TAB_INDEX_ENTRIES,
        "unique_issues": unique_values,
        "majority_type": majority_type,
        "minority_type": minority_type,
        "majority_unique": majority_unique,
        "majority_subset": majority_subset,
        "all_issues": total_entries,
        "high_issues": high_issues,
        "med_issues": med_issues,
        "low_issues": low_issues,
        "xlsx_filename": "nexpose_data.xlsx",
    }

    workbook_bytes = _render_nexpose_metrics_workbook(metrics_payload)
    if workbook_bytes:
        metrics_payload["xlsx_base64"] = base64.b64encode(workbook_bytes).decode("ascii")

    return metrics_payload


def _render_nexpose_metrics_workbook(metrics: Dict[str, Any]) -> Optional[bytes]:
    """Create an XLSX workbook for the processed Nexpose metrics."""

    buffer = io.BytesIO()
    workbook = Workbook(buffer, {"in_memory": True})

    def header_format(color: str):
        fmt = workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "font_color": "#000000",
                "bg_color": color,
                "pattern": 1,
            }
        )
        return fmt

    summary_header_cache: Dict[str, Any] = {}

    def get_header(color: str):
        if color not in summary_header_cache:
            summary_header_cache[color] = header_format(color)
        return summary_header_cache[color]

    summary_data_fmt = workbook.add_format({"border": 1, "font_color": "#000000"})
    summary_band_fmt = workbook.add_format({"border": 1, "bg_color": "#99CCFF", "font_color": "#000000"})
    text_data_fmt = workbook.add_format({"border": 1, "text_wrap": True, "font_color": "#000000"})
    text_band_fmt = workbook.add_format({"border": 1, "text_wrap": True, "bg_color": "#99CCFF", "font_color": "#000000"})

    def _calc_text_width(value: Any) -> int:
        if value is None:
            return 0
        text = str(value)
        lines = text.splitlines() or [text]
        return max(len(line) for line in lines)

    def write_table(
        worksheet,
        *,
        start_row: int,
        start_col: int,
        headers: List[str],
        rows: List[List[Any]],
        header_colors: Optional[List[str]] = None,
        data_format=text_data_fmt,
        band_format=text_band_fmt,
        width_tracker: Optional[Dict[int, int]] = None,
    ) -> None:
        for idx, header in enumerate(headers):
            color = (header_colors[idx] if header_colors and idx < len(header_colors) else (header_colors[0] if header_colors else "#0066CC"))
            worksheet.write(start_row, start_col + idx, header, get_header(color))
            if width_tracker is not None:
                column_index = start_col + idx
                width_tracker[column_index] = max(
                    width_tracker.get(column_index, 0),
                    _calc_text_width(header),
                )
        for row_index, row in enumerate(rows):
            fmt = band_format if row_index % 2 == 1 else data_format
            for col_index, value in enumerate(row):
                worksheet.write(start_row + 1 + row_index, start_col + col_index, value, fmt)
                if width_tracker is not None:
                    column_index = start_col + col_index
                    width_tracker[column_index] = max(
                        width_tracker.get(column_index, 0),
                        _calc_text_width(value),
                    )

    def apply_autofit(worksheet, width_tracker: Dict[int, int], columns: Iterable[int]) -> None:
        for column in columns:
            width = width_tracker.get(column, 10)
            worksheet.set_column(column, column, min(width + 2, 60))

    exec_ws = workbook.add_worksheet("Executive Summary")
    exec_width_tracker: Dict[int, int] = {}

    host_rows = [
        [row["host"], row["high"], row["med"], row["low"]]
        for row in metrics.get("host_counts", [])
    ]
    write_table(
        exec_ws,
        start_row=0,
        start_col=0,
        headers=["Host", "High", "Medium", "Low"],
        rows=host_rows,
        header_colors=["#0066CC", "#0066CC", "#0066CC", "#0066CC"],
        data_format=summary_data_fmt,
        band_format=summary_band_fmt,
        width_tracker=exec_width_tracker,
    )

    summary = metrics.get("summary") or {}
    totals_rows = [[
        summary.get("total", 0),
        summary.get("total_high", 0),
        summary.get("total_med", 0),
        summary.get("total_low", 0),
    ]]
    write_table(
        exec_ws,
        start_row=0,
        start_col=5,
        headers=["Total", "Total High", "Total Medium", "Total Low"],
        rows=totals_rows,
        header_colors=["#0066CC", "#FF0000", "#FF9900", "#99CC00"],
        data_format=summary_data_fmt,
        band_format=summary_band_fmt,
        width_tracker=exec_width_tracker,
    )

    unique_rows = [[
        summary.get("unique", 0),
        summary.get("unique_high", 0),
        summary.get("unique_med", 0),
        summary.get("unique_low", 0),
    ]]
    write_table(
        exec_ws,
        start_row=3,
        start_col=5,
        headers=["Unique Total", "Unique High", "Unique Medium", "Unique Low"],
        rows=unique_rows,
        header_colors=["#0066CC", "#FF0000", "#FF9900", "#99CC00"],
        data_format=summary_data_fmt,
        band_format=summary_band_fmt,
        width_tracker=exec_width_tracker,
    )

    top_host_rows = [
        [row.get("host"), row.get("high"), row.get("med"), row.get("low")]
        for row in metrics.get("top_hosts", [])
    ]
    write_table(
        exec_ws,
        start_row=6,
        start_col=5,
        headers=["Top Risk Hosts", "High", "Medium", "Low"],
        rows=top_host_rows,
        header_colors=["#FF0000", "#FF0000", "#FF9900", "#99CC00"],
        data_format=summary_data_fmt,
        band_format=summary_band_fmt,
        width_tracker=exec_width_tracker,
    )

    impact_rows = [
        [item.get("impact"), item.get("count", 0)]
        for item in metrics.get("top_impacts", [])
    ]
    impact_headers = ["Top 10 Issue Impacts", "Count"]
    write_table(
        exec_ws,
        start_row=0,
        start_col=10,
        headers=impact_headers,
        rows=impact_rows,
        header_colors=["#0066CC", "#0066CC"],
        data_format=text_data_fmt,
        band_format=text_band_fmt,
        width_tracker=exec_width_tracker,
    )

    tab_index_rows = [[entry] for entry in metrics.get("tab_index_entries", [])]
    write_table(
        exec_ws,
        start_row=16,
        start_col=10,
        headers=["Tab Index"],
        rows=tab_index_rows,
        header_colors=["#CCFFFF"],
        data_format=text_data_fmt,
        band_format=text_band_fmt,
        width_tracker=exec_width_tracker,
    )

    exec_columns_to_fit = list(range(0, 4)) + list(range(5, 9)) + [10, 11]
    if hasattr(exec_ws, "autofit"):
        exec_ws.autofit()
    else:
        apply_autofit(exec_ws, exec_width_tracker, exec_columns_to_fit)

    def write_issue_sheet(name: str, data_rows: List[List[Any]], headers: List[str]) -> None:
        ws = workbook.add_worksheet(name)
        ws.set_column(0, len(headers) - 1, 35)
        write_table(
            ws,
            start_row=0,
            start_col=0,
            headers=headers,
            rows=data_rows,
            header_colors=["#0066CC"] * len(headers),
            data_format=text_data_fmt,
            band_format=text_band_fmt,
        )

    unique_headers = ["Risk", "Issue", "Impact", "Remediation", "Category"]
    unique_rows_table = [
        [entry.get("risk"), entry.get("issue"), entry.get("impact"), entry.get("remediation"), entry.get("category")]
        for entry in metrics.get("unique_issues", [])
    ]
    write_issue_sheet("Unique Issues", unique_rows_table, unique_headers)

    majority_rows = [
        [entry.get("risk"), entry.get("issue"), entry.get("impact"), entry.get("remediation"), entry.get("category")]
        for entry in metrics.get("majority_unique", [])
    ]
    write_issue_sheet("Issues by Majority Type", majority_rows, unique_headers)

    def build_full_rows(items: List[Dict[str, Any]]) -> List[List[Any]]:
        rows = []
        for item in items:
            rows.append(
                [
                    item.get("ip"),
                    item.get("hostnames"),
                    item.get("port"),
                    item.get("issue"),
                    item.get("impact"),
                    item.get("details"),
                    item.get("evidence"),
                    item.get("remediation"),
                    item.get("risk"),
                    item.get("category"),
                ]
            )
        return rows

    full_headers = [
        "IP Address",
        "Hostname(s)",
        "Port",
        "Issue",
        "Impact",
        "Issue Details",
        "Evidence",
        "Remediation",
        "Risk",
        "Category",
    ]

    workbook.add_worksheet("Subset of Majority Issues")

    all_rows = build_full_rows(metrics.get("all_issues", []))
    write_issue_sheet("All Issues", all_rows, full_headers)

    high_rows = build_full_rows(metrics.get("high_issues", []))
    write_issue_sheet("High Risk Issues", high_rows, full_headers)

    med_rows = build_full_rows(metrics.get("med_issues", []))
    write_issue_sheet("Medium Risk Issues", med_rows, full_headers)

    low_rows = build_full_rows(metrics.get("low_issues", []))
    write_issue_sheet("Low Risk Issues", low_rows, full_headers)

    workbook.close()
    buffer.seek(0)
    return buffer.getvalue()


def _build_web_metrics_payload(findings: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate metrics and an XLSX workbook for Burp web findings."""

    if not findings:
        return {}

    total_entries: List[Dict[str, Any]] = []
    unique_entries: Dict[Tuple[str, str, str], Dict[str, Any]] = {}
    impact_counter: Counter[str] = Counter()
    host_risk_counts: Dict[str, Dict[str, int]] = {}
    host_unique_keys: Set[Tuple[str, str, str]] = set()

    for finding in findings:
        issue = (finding.get("Issue") or "").strip()
        impact = (finding.get("Impact") or "").strip()
        background = finding.get("Background")
        fix = finding.get("Fix")
        risk = (finding.get("Risk") or "").strip()
        host = (finding.get("Host") or "").strip()
        score = finding.get("Score")
        try:
            numeric_score = float(score) if score is not None else 0.0
        except (TypeError, ValueError):  # pragma: no cover - defensive guard
            numeric_score = 0.0

        entry = {
            "Issue": issue,
            "Impact": impact,
            "Background": background,
            "Fix": fix,
            "Host": host,
            "Path": finding.get("Path"),
            "Evidence": finding.get("Evidence"),
            "Detailed Remediation": finding.get("Detailed Remediation"),
            "Risk": risk,
            "Score": numeric_score,
        }
        total_entries.append(entry)
        impact_counter[impact] += 1

        if host:
            unique_host_key = (issue, risk, host)
            if unique_host_key not in host_unique_keys:
                host_unique_keys.add(unique_host_key)
                risk_bucket = risk.lower()
                host_entry = host_risk_counts.setdefault(
                    host, {"high": 0, "medium": 0, "low": 0}
                )
                if risk_bucket == "high":
                    host_entry["high"] += 1
                elif risk_bucket == "medium":
                    host_entry["medium"] += 1
                else:
                    host_entry["low"] += 1

        unique_key = (risk, issue, impact)
        existing = unique_entries.get(unique_key)
        if existing:
            if numeric_score > existing.get("Score", 0):
                existing["Score"] = numeric_score
            continue
        unique_entries[unique_key] = {
            "Issue": issue,
            "Impact": impact,
            "Background": background,
            "Fix": fix,
            "Risk": risk,
            "Score": numeric_score,
        }

    unique_values = list(unique_entries.values())
    summary = {
        "total": len(total_entries),
        "unique": len(unique_values),
        "total_high": sum(1 for entry in total_entries if entry.get("Score", 0) >= 8.0),
        "total_med": sum(
            1 for entry in total_entries if 5.0 <= entry.get("Score", 0) <= 7.9
        ),
        "total_low": sum(1 for entry in total_entries if entry.get("Score", 0) <= 4.9),
        "unique_high": sum(1 for entry in unique_values if entry.get("Score", 0) >= 8.0),
        "unique_med": sum(
            1 for entry in unique_values if 5.0 <= entry.get("Score", 0) <= 7.9
        ),
        "unique_low": sum(1 for entry in unique_values if entry.get("Score", 0) <= 4.9),
        "uniquelow": None,  # populated below for legacy naming
        "host_risk_counts": [
            {
                "host": host,
                "high": counts.get("high", 0),
                "medium": counts.get("medium", 0),
                "low": counts.get("low", 0),
            }
            for host, counts in sorted(host_risk_counts.items())
        ],
    }
    summary["uniquelow"] = summary["unique_low"]

    top_impacts = [
        {"impact": impact, "count": count}
        for impact, count in impact_counter.most_common(10)
    ]

    metrics_payload: Dict[str, Any] = {
        "summary": summary,
        "unique_issues": sorted(
            unique_values, key=lambda entry: (entry.get("Risk", ""), entry.get("Issue", ""), entry.get("Impact", ""))
        ),
        "all_issues": total_entries,
        "high_issues": [entry for entry in total_entries if entry.get("Score", 0) >= 8.0],
        "med_issues": [
            entry for entry in total_entries if 5.0 <= entry.get("Score", 0) <= 7.9
        ],
        "low_issues": [entry for entry in total_entries if entry.get("Score", 0) <= 4.9],
        "top_impacts": top_impacts,
        "tab_index_entries": [
            "Unique Issues  -:-  Unique issues found across all scanned systems",
            "All Issues  -:-  All issues identified. May include 'duplicate' findings (same issue/system, different ports)",
            "High Risk Issues  -:-  All 'High' risk issues identified",
            "Medium Risk Issues  -:-  All 'Medium' risk issues identified",
            "Low Risk Issues  -:-  All 'Low' risk issues identified",
        ],
        "xlsx_filename": "burp_data.xlsx",
    }

    workbook_bytes = _render_web_metrics_workbook(metrics_payload)
    if workbook_bytes:
        metrics_payload["xlsx_base64"] = base64.b64encode(workbook_bytes).decode("ascii")

    return metrics_payload


def _render_firewall_metrics_workbook(metrics: Dict[str, Any]) -> Optional[bytes]:
    """Create an XLSX workbook for processed firewall findings."""

    buffer = io.BytesIO()
    workbook = Workbook(buffer, {"in_memory": True})

    def header_format(color: str):
        return workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "font_color": "#000000",
                "bg_color": color,
                "pattern": 1,
            }
        )

    header_cache: Dict[str, Any] = {}

    def get_header(color: str):
        if color not in header_cache:
            header_cache[color] = header_format(color)
        return header_cache[color]

    data_fmt = workbook.add_format({"border": 1, "text_wrap": True, "font_color": "#000000"})
    band_fmt = workbook.add_format(
        {"border": 1, "text_wrap": True, "bg_color": "#99CCFF", "font_color": "#000000"}
    )

    def _calc_text_width(value: Any) -> int:
        if value is None:
            return 0
        text = str(value)
        lines = text.splitlines() or [text]
        return max(len(line) for line in lines)

    def write_table(
        worksheet,
        *,
        start_row: int,
        start_col: int,
        headers: List[str],
        rows: List[List[Any]],
        header_colors: Optional[List[str]] = None,
        width_tracker: Optional[Dict[int, int]] = None,
    ) -> None:
        for idx, header in enumerate(headers):
            color = header_colors[idx] if header_colors and idx < len(header_colors) else "#0066CC"
            worksheet.write(start_row, start_col + idx, header, get_header(color))
            if width_tracker is not None:
                column_index = start_col + idx
                width_tracker[column_index] = max(width_tracker.get(column_index, 0), _calc_text_width(header))
        for row_index, row in enumerate(rows):
            fmt = band_fmt if row_index % 2 == 1 else data_fmt
            for col_index, value in enumerate(row):
                worksheet.write(start_row + 1 + row_index, start_col + col_index, value, fmt)
                if width_tracker is not None:
                    column_index = start_col + col_index
                    width_tracker[column_index] = max(width_tracker.get(column_index, 0), _calc_text_width(value))

    def apply_autofit(worksheet, width_tracker: Dict[int, int], columns: Iterable[int]) -> None:
        for column in columns:
            width = width_tracker.get(column, 10)
            worksheet.set_column(column, column, min(width + 2, 80))

    summary = metrics.get("summary") or {}
    exec_ws = workbook.add_worksheet("Executive Summary")
    exec_tracker: Dict[int, int] = {}

    summary_headers = ["Total", "Total High", "Total Medium", "Total Low"]
    summary_colors = ["#0066CC", "#FF0000", "#FF9900", "#99CC00"]
    summary_rows = [
        [
            summary.get("unique", 0),
            summary.get("unique_high", 0),
            summary.get("unique_med", 0),
            summary.get("unique_low", 0),
        ]
    ]
    write_table(
        exec_ws,
        start_row=0,
        start_col=0,
        headers=summary_headers,
        rows=summary_rows,
        header_colors=summary_colors,
        width_tracker=exec_tracker,
    )

    top_impacts = metrics.get("top_impacts") or []
    impact_rows = [[entry.get("impact", ""), entry.get("count", 0)] for entry in top_impacts]
    write_table(
        exec_ws,
        start_row=0,
        start_col=5,
        headers=["Top 10 Issue Impacts", "Count"],
        rows=impact_rows,
        header_colors=["#0066CC", "#0066CC"],
        width_tracker=exec_tracker,
    )

    tab_index_rows = [
        ["All Issues  -:-  All issues identified"],
        ["High Risk Issues  -:-  All 'High' risk issues identified"],
        ["Medium Risk Issues  -:-  All 'Medium' risk issues identified"],
        ["Low Risk Issues  -:-  All 'Low' risk issues identified"],
        ["Vulnerability Issues  -:-  All issues related to known vulnerabilities identified"],
        ["Rule Issues  -:-  All issues related to rules identified"],
        ["Config Issues  -:-  All issues related to configuration settings identified"],
        ["Complexity Issues  -:-  All issues related to rules/configuration settings that add to the firewall complexity identified"],
    ]
    write_table(
        exec_ws,
        start_row=16,
        start_col=5,
        headers=["Tab Index"],
        rows=tab_index_rows,
        header_colors=["#CCFFFF"],
        width_tracker=exec_tracker,
    )

    apply_autofit(exec_ws, exec_tracker, range(0, 7))

    issue_headers = [
        "Issue",
        "Impact",
        "Devices",
        "Details",
        "Solution",
        "Reference",
        "Risk",
        "Accepted",
        "Score",
    ]
    issue_colors = ["#0066CC"] * len(issue_headers)

    def _issue_rows(entries: Iterable[Dict[str, Any]]) -> List[List[Any]]:
        rows: List[List[Any]] = []
        for entry in entries or []:
            if not isinstance(entry, dict):
                continue
            rows.append(
                [
                    entry.get("Issue", ""),
                    entry.get("Impact", ""),
                    entry.get("Devices", ""),
                    entry.get("Details", ""),
                    entry.get("Solution", ""),
                    entry.get("Reference", ""),
                    entry.get("Risk", ""),
                    entry.get("Accepted", ""),
                    entry.get("Score", ""),
                ]
            )
        return rows

    def write_issue_sheet(name: str, entries: Iterable[Dict[str, Any]]):
        worksheet = workbook.add_worksheet(name)
        width_tracker: Dict[int, int] = {}
        rows = _issue_rows(entries)
        write_table(
            worksheet,
            start_row=0,
            start_col=0,
            headers=issue_headers,
            rows=rows,
            header_colors=issue_colors,
            width_tracker=width_tracker,
        )
        apply_autofit(worksheet, width_tracker, range(len(issue_headers)))

    write_issue_sheet("All Issues", metrics.get("all_issues"))
    write_issue_sheet("High Risk Issues", metrics.get("high_issues"))
    write_issue_sheet("Medium Risk Issues", metrics.get("med_issues"))
    write_issue_sheet("Low Risk Issues", metrics.get("low_issues"))
    write_issue_sheet("Rule Issues", metrics.get("rule_issues"))
    write_issue_sheet("Config Issues", metrics.get("config_issues"))
    write_issue_sheet("Complexity Issues", metrics.get("complexity_issues"))
    write_issue_sheet("Vulnerability Issues", metrics.get("vuln_issues"))

    workbook.close()
    return buffer.getvalue()


def _build_web_cap_entries_from_metrics(
    metrics: Optional[Dict[str, Any]]
) -> List[Dict[str, Any]]:
    """Create CAP-style web entries derived from web metrics."""

    if not isinstance(metrics, dict):
        return []

    unique_issues = metrics.get("unique_issues")
    all_issues = metrics.get("all_issues")
    if not isinstance(unique_issues, list) or not isinstance(all_issues, list):
        return []

    host_map: Dict[str, Set[str]] = {}
    for entry in all_issues:
        if not isinstance(entry, dict):
            continue
        issue = (entry.get("Issue") or "").strip()
        if not issue:
            continue
        host = (entry.get("Host") or "").strip()
        path = (entry.get("Path") or "").strip()
        host_path = f"{host}{path}".strip()
        if not host_path:
            continue
        host_map.setdefault(issue, set()).add(host_path)

    cap_entries: List[Dict[str, Any]] = []
    for entry in unique_issues:
        if not isinstance(entry, dict):
            continue
        issue = (entry.get("Issue") or "").strip()
        if not issue:
            continue
        hosts = "\n".join(sorted(host_map.get(issue, set())))
        cap_entries.append(
            {
                "issue": issue,
                "hosts": hosts,
                "score": entry.get("Score"),
                "action": entry.get("Fix"),
                "severity": entry.get("Risk"),
            }
        )

    return cap_entries


def _render_web_metrics_workbook(metrics: Dict[str, Any]) -> Optional[bytes]:
    """Create an XLSX workbook for Burp web findings."""

    buffer = io.BytesIO()
    workbook = Workbook(buffer, {"in_memory": True})

    def header_format(color: str):
        return workbook.add_format(
            {
                "bold": True,
                "border": 1,
                "font_color": "#000000",
                "bg_color": color,
                "pattern": 1,
            }
        )

    header_cache: Dict[str, Any] = {}

    def get_header(color: str = "#0066CC"):
        if color not in header_cache:
            header_cache[color] = header_format(color)
        return header_cache[color]

    data_fmt = workbook.add_format({"border": 1, "font_color": "#000000", "text_wrap": True})
    band_fmt = workbook.add_format(
        {"border": 1, "bg_color": "#99CCFF", "font_color": "#000000", "text_wrap": True}
    )

    def write_table(
        worksheet,
        *,
        start_row: int,
        start_col: int,
        headers: List[str],
        rows: List[List[Any]],
        header_colors: Optional[List[str]] = None,
        width_tracker: Optional[Dict[int, int]] = None,
    ) -> None:
        for idx, header in enumerate(headers):
            color = header_colors[idx] if header_colors and idx < len(header_colors) else (
                header_colors[0] if header_colors else "#0066CC"
            )
            worksheet.write(start_row, start_col + idx, header, get_header(color))
            if width_tracker is not None:
                width_tracker[start_col + idx] = max(width_tracker.get(start_col + idx, 0), len(str(header)))

        for row_idx, row in enumerate(rows):
            fmt = band_fmt if row_idx % 2 == 1 else data_fmt
            for col_idx, value in enumerate(row):
                worksheet.write(start_row + 1 + row_idx, start_col + col_idx, value, fmt)
                if width_tracker is not None:
                    width_tracker[start_col + col_idx] = max(
                        width_tracker.get(start_col + col_idx, 0), len(str(value or ""))
                    )

    # Executive Summary
    summary_ws = workbook.add_worksheet("Executive Summary")
    width_tracker: Dict[int, int] = {}
    summary = metrics.get("summary", {}) if isinstance(metrics.get("summary"), dict) else {}

    write_table(
        summary_ws,
        start_row=0,
        start_col=0,
        headers=["Total", "Total High", "Total Medium", "Total Low"],
        header_colors=["#0066CC", "#FF0000", "#FF9900", "#99CC00"],
        rows=[
            [
                summary.get("total", 0),
                summary.get("total_high", 0),
                summary.get("total_med", 0),
                summary.get("total_low", 0),
            ]
        ],
        width_tracker=width_tracker,
    )

    write_table(
        summary_ws,
        start_row=3,
        start_col=0,
        headers=["Unique Total", "Unique High", "Unique Medium", "Unique Low"],
        header_colors=["#0066CC", "#FF0000", "#FF9900", "#99CC00"],
        rows=[
            [
                summary.get("unique", 0),
                summary.get("unique_high", 0),
                summary.get("unique_med", 0),
                summary.get("unique_low", 0),
            ]
        ],
        width_tracker=width_tracker,
    )

    impact_rows = [
        [row.get("impact"), row.get("count")] for row in metrics.get("top_impacts", []) or []
    ]
    write_table(
        summary_ws,
        start_row=0,
        start_col=5,
        headers=["Top 10 Issue Impacts", "Count"],
        header_colors=["#0066CC", "#0066CC"],
        rows=impact_rows,
        width_tracker=width_tracker,
    )

    tab_index_rows = [[row] for row in metrics.get("tab_index_entries", []) or []]
    write_table(
        summary_ws,
        start_row=16,
        start_col=5,
        headers=["Tab Index"],
        header_colors=["#CCFFFF"],
        rows=tab_index_rows,
        width_tracker=width_tracker,
    )

    for col, width in width_tracker.items():
        summary_ws.set_column(col, col, width + 2)

    unique_headers = ["Issue", "Impact", "Background", "Fix", "Risk"]
    unique_rows = [
        [
            entry.get("Issue"),
            entry.get("Impact"),
            entry.get("Background"),
            entry.get("Fix"),
            entry.get("Risk"),
        ]
        for entry in metrics.get("unique_issues", []) or []
    ]

    unique_ws = workbook.add_worksheet("Unique Issues")
    write_table(unique_ws, start_row=0, start_col=0, headers=unique_headers, rows=unique_rows)
    unique_ws.set_column(0, len(unique_headers) - 1, 30)

    full_headers = [
        "Issue",
        "Impact",
        "Background",
        "Host",
        "Path",
        "Evidence",
        "Fix",
        "Detailed Remediation",
        "Risk",
    ]

    def write_issue_sheet(title: str, entries: List[Dict[str, Any]]):
        sheet = workbook.add_worksheet(title)
        rows: List[List[Any]] = []
        for entry in entries:
            rows.append(
                [
                    entry.get("Issue"),
                    entry.get("Impact"),
                    entry.get("Background"),
                    entry.get("Host"),
                    entry.get("Path"),
                    entry.get("Evidence"),
                    entry.get("Fix"),
                    entry.get("Detailed Remediation"),
                    entry.get("Risk"),
                ]
            )
        write_table(sheet, start_row=0, start_col=0, headers=full_headers, rows=rows)
        sheet.set_column(0, len(full_headers) - 1, 35)

    write_issue_sheet("All Issues", metrics.get("all_issues", []) or [])
    write_issue_sheet("High Risk Issues", metrics.get("high_issues", []) or [])
    write_issue_sheet("Medium Risk Issues", metrics.get("med_issues", []) or [])
    write_issue_sheet("Low Risk Issues", metrics.get("low_issues", []) or [])

    workbook.close()
    buffer.seek(0)
    return buffer.getvalue()


def _build_web_summary_from_findings(
    findings: List[Dict[str, Any]], web_issue_matrix: Optional[Dict[str, Dict[str, str]]]
) -> Optional[Dict[str, Any]]:
    """Construct the web issue summary from parsed Burp findings."""

    if not findings:
        return None

    low_issue_counter: Counter[str] = Counter()
    med_impact_counter: Counter[str] = Counter()
    aggregated_severity: Dict[str, Counter[Tuple[str, str]]] = {
        "high": Counter(),
        "med": Counter(),
        "low": Counter(),
    }

    for finding in findings:
        severity_key = _categorize_web_risk(finding.get("Risk", ""))
        if not severity_key:
            continue
        issue_value = (finding.get("Issue") or "").strip()
        impact_value = (finding.get("Impact") or "").strip()
        aggregated_severity[severity_key][(issue_value, impact_value)] += 1

        if severity_key == "low" and issue_value:
            low_issue_counter[issue_value] += 1
        elif severity_key == "med":
            sample = _clean_impact_sample(impact_value)
            if sample:
                med_impact_counter[sample] += 1

    if not any(counter for counter in aggregated_severity.values()):
        return None

    severity_summaries = {
        severity_key: _summarize_severity_counter(counter, web_issue_matrix=web_issue_matrix)
        for severity_key, counter in aggregated_severity.items()
    }

    web_summary = {
        "low_sample_string": _format_sample_string(_select_top_samples(low_issue_counter)),
        "med_sample_string": _format_sample_string(_select_top_samples(med_impact_counter)),
        **severity_summaries,
    }
    web_summary["ai_response"] = None
    ai_response = _build_web_issue_ai_response(web_summary, require_web_data=bool(findings))
    if ai_response:
        web_summary["ai_response"] = ai_response
    return web_summary


def _categorize_web_risk(raw_value: str) -> Optional[str]:
    """Return the severity bucket for a Burp risk string."""

    text = (raw_value or "").strip()
    if not text:
        return None

    normalized = text.upper().replace("-", " ")
    if "(" in normalized:
        normalized = normalized.split("(", 1)[0]
    normalized = normalized.strip()

    if normalized in {"CRITICAL", "HIGH"}:
        return "high"
    if normalized in {"MEDIUM", "MODERATE"}:
        return "med"
    if normalized in {"LOW", "INFO", "INFORMATION", "INFORMATIONAL"}:
        return "low"

    try:
        score = float(text)
    except (TypeError, ValueError):  # pragma: no cover - defensive guard
        return None

    if score >= 8:
        return "high"
    if score >= 4:
        return "med"
    if score >= 0:
        return "low"
    return None


def _apply_web_issue_matrix_fields(
    entry: Dict[str, Any], web_issue_matrix: Optional[Dict[str, Dict[str, str]]]
) -> Dict[str, Any]:
    """Populate impact/fix fields using the web issue matrix when available."""

    metadata: Optional[Dict[str, str]] = None
    if web_issue_matrix:
        key = _normalize_matrix_key(entry.get("issue"))
        if key:
            metadata = web_issue_matrix.get(key)
    if metadata:
        if metadata.get("impact"):
            entry["impact"] = metadata["impact"]
        entry["fix"] = metadata.get("fix", "")
    else:
        entry.setdefault("fix", "")
    return entry


def _apply_vulnerability_matrix_fields(
    entry: Dict[str, Any], vulnerability_matrix: Optional[Dict[str, Dict[str, str]]]
) -> Dict[str, Any]:
    """Populate vulnerability metadata fields when available."""

    defaults = {
        "action_required": "",
        "remediation_impact": "",
        "vulnerability_threat": "",
        "category": "",
    }
    metadata: Optional[Dict[str, str]] = None
    if vulnerability_matrix:
        key = _normalize_matrix_key(entry.get("title"))
        if key:
            metadata = vulnerability_matrix.get(key)
    if metadata:
        entry.update({**defaults, **metadata})
    else:
        for field, default in defaults.items():
            entry.setdefault(field, default)
    return entry


def _summarize_severity_counter(
    counter: Counter[Tuple[str, str]],
    *,
    web_issue_matrix: Optional[Dict[str, Dict[str, str]]] = None,
) -> _SeverityGroup:
    """Convert a counter of issue/impact pairs into a severity summary."""

    ordered = sorted(
        counter.items(),
        key=lambda item: (
            -item[1],
            (item[0][0] or "").lower(),
            (item[0][1] or "").lower(),
        ),
    )
    items: List[Dict[str, Any]] = []
    for (issue, impact), count in ordered[:5]:
        entry = {"issue": issue, "impact": impact, "count": count}
        _apply_web_issue_matrix_fields(entry, web_issue_matrix)
        items.append(entry)

    return _SeverityGroup(total_unique=len(counter), items=items)


def _clean_impact_sample(raw_value: Any) -> str:
    """Return an impact sample with helper phrases removed."""

    text = str(raw_value or "").strip()
    lowered = text.lower()
    for prefix in ("this may", "this can"):
        if lowered.startswith(prefix):
            text = text[len(prefix) :].lstrip(" \t-:,;")
            break
    return text


def _select_top_samples(counter: Counter[str]) -> List[str]:
    """Return up to three samples ordered by descending frequency then alphabetically."""

    ordered = sorted(
        (
            (sample, count)
            for sample, count in counter.items()
            if sample
        ),
        key=lambda item: (-item[1], item[0].lower()),
    )
    return [sample for sample, _count in ordered[:3]]


def _format_sample_string(samples: List[str]) -> str:
    """Return a grammatically correct representation of the provided samples."""

    samples = [sample for sample in samples if sample]
    if not samples:
        return ""
    quoted = [f"'{sample}'" for sample in samples]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return ", ".join(quoted[:-1]) + f" and {quoted[-1]}"


def _format_slash_separated_string(values: Iterable[str]) -> str:
    """Return a slash-delimited string of single-quoted values."""

    entries = [str(value).strip() for value in values if str(value).strip()]
    if not entries:
        return ""
    quoted = [f"'{entry}'" for entry in entries]
    return "/".join(quoted)


def _format_oxford_quoted_list(values: List[str]) -> str:
    """Return a quoted list that includes an Oxford comma when needed."""

    entries = [str(value).strip() for value in values if str(value).strip()]
    if not entries:
        return ""
    quoted = [f"'{entry}'" for entry in entries]
    if len(quoted) == 1:
        return quoted[0]
    if len(quoted) == 2:
        return f"{quoted[0]} and {quoted[1]}"
    return ", ".join(quoted[:-1]) + f", and {quoted[-1]}"


def _format_plain_list(values: List[str]) -> str:
    """Return a human-readable string for a list of pre-formatted values."""

    entries = [value for value in values if value]
    if not entries:
        return ""
    if len(entries) == 1:
        return entries[0]
    if len(entries) == 2:
        return f"{entries[0]} and {entries[1]}"
    return ", ".join(entries[:-1]) + f" and {entries[-1]}"


def summarize_password_cap_details(
    domain_values: Dict[str, Dict[str, Any]]
) -> Tuple[List[str], Dict[str, Any]]:
    """Return ordered password CAP fields and associated context values."""

    unique_fields: List[str] = []
    seen_fields: Set[str] = set()
    context: Dict[str, Any] = {}

    for domain, values in domain_values.items():
        if not isinstance(values, dict):
            continue

        domain_context: Dict[str, Any] = {}

        policy_fields = values.get("policy_cap_fields")
        policy_values = values.get("policy_cap_values")
        if isinstance(policy_fields, list) and policy_fields:
            policy_context: Dict[str, Any] = {}
            for field in policy_fields:
                if field not in seen_fields:
                    seen_fields.add(field)
                    unique_fields.append(field)
                field_value = (
                    policy_values.get(field)
                    if isinstance(policy_values, dict)
                    else None
                )
                policy_context[field] = field_value
            if policy_context:
                domain_context["policy"] = policy_context

        fgpp_fields = values.get("fgpp_cap_fields")
        fgpp_values = values.get("fgpp_cap_values")
        if isinstance(fgpp_fields, dict) and fgpp_fields:
            fgpp_context: Dict[str, Dict[str, Any]] = {}
            for name, field_list in fgpp_fields.items():
                if not isinstance(field_list, list) or not field_list:
                    continue
                per_policy_context: Dict[str, Any] = {}
                for field in field_list:
                    if field not in seen_fields:
                        seen_fields.add(field)
                        unique_fields.append(field)
                    value_map = (
                        fgpp_values.get(name)
                        if isinstance(fgpp_values, dict)
                        else None
                    )
                    per_policy_context[field] = (
                        value_map.get(field) if isinstance(value_map, dict) else None
                    )
                if per_policy_context:
                    fgpp_context[name] = per_policy_context
            if fgpp_context:
                domain_context["fgpp"] = fgpp_context

        if domain_context:
            context[domain] = domain_context

    return unique_fields, context


def _stringify_cap_value(value: Any) -> str:
    """Return a string representation suitable for CAP placeholder substitution."""

    if value is None:
        return ""
    if isinstance(value, str):
        return value
    return str(value)


def _render_cap_template(template: str, values: Dict[str, Any]) -> str:
    """Render ``template`` by replacing ``{{ key }}`` placeholders with ``values``."""

    if not template:
        return ""

    def _replace(match: "re.Match[str]") -> str:
        key = match.group(1)
        for candidate in (key, key.lower(), key.upper()):
            if candidate in values:
                return _stringify_cap_value(values[candidate])
        return ""

    return _CAP_PLACEHOLDER_PATTERN.sub(_replace, template)


def build_password_cap_display_map(
    context: Dict[str, Any], template_map: Dict[str, str]
) -> Dict[str, Any]:
    """Return domain-scoped CAP guidance using ``template_map`` and ``context`` values."""

    domain_map: Dict[str, Any] = {}

    for domain, domain_context in context.items():
        if not isinstance(domain_context, dict):
            continue

        domain_entry: Dict[str, Any] = {}

        policy_values = domain_context.get("policy")
        if isinstance(policy_values, dict) and policy_values:
            policy_map: Dict[str, str] = {}
            for field, value in policy_values.items():
                template = template_map.get(field, "")
                replacements = {
                    field: value,
                    field.lower(): value,
                    field.upper(): value,
                }
                policy_map[field] = _render_cap_template(template, replacements)
            if policy_map:
                domain_entry["policy"] = {"score": 4, **policy_map}

        fgpp_values = domain_context.get("fgpp")
        if isinstance(fgpp_values, dict) and fgpp_values:
            fgpp_map: Dict[str, Dict[str, str]] = {}
            for name, fgpp_field_values in fgpp_values.items():
                if not isinstance(fgpp_field_values, dict) or not fgpp_field_values:
                    continue
                per_policy_map: Dict[str, str] = {}
                for field, value in fgpp_field_values.items():
                    template = template_map.get(field, "")
                    replacements = {
                        field: value,
                        field.lower(): value,
                        field.upper(): value,
                    }
                    per_policy_map[field] = _render_cap_template(template, replacements)
                if per_policy_map:
                    fgpp_map[name] = {"score": 4, **per_policy_map}
            if fgpp_map:
                domain_entry["fgpp"] = fgpp_map

        if domain_entry:
            domain_map[domain] = domain_entry

    return domain_map


def _format_integer_value(value: Optional[int]) -> str:
    """Normalize integer-like values to strings while preserving zeroes."""

    if value in (None, ""):
        return "0"
    return str(value)


def _format_percentage_text(value: Optional[float]) -> str:
    """Render a percentage value with up to one decimal place."""

    if value is None:
        return "0%"

    text = f"{value:.1f}".rstrip("0").rstrip(".")
    return f"{text}%"


def parse_web_report(file_obj: File) -> Dict[str, Dict[str, Counter[Tuple[str, str]]]]:
    """Parse a burp.csv export into counters grouped by site and severity bucket."""

    results: Dict[str, Dict[str, Counter[Tuple[str, str]]]] = {}
    for row in _decode_file(file_obj):
        host = (row.get("Host") or row.get("host") or "").strip() or "Unknown Site"
        risk_raw = (row.get("Risk") or row.get("risk") or "").strip()
        severity_bucket = _categorize_web_risk(risk_raw)
        if not severity_bucket:
            continue

        issue = (row.get("Issue") or row.get("issue") or "").strip()
        impact = (row.get("Impact") or row.get("impact") or "").strip()
        if not issue and not impact:
            continue

        host_entry = results.setdefault(host, {})
        counter = host_entry.setdefault(severity_bucket, Counter())
        counter[(issue, impact)] += 1

    return results


def build_project_artifacts(project: "Project") -> Dict[str, Any]:
    """Aggregate parsed artifacts for the provided project."""

    artifacts: Dict[str, Any] = {}
    dns_results: Dict[str, List[Dict[str, str]]] = {}
    dns_findings: Dict[str, List[Dict[str, str]]] = {}
    ip_results: Dict[str, List[str]] = {
        definition.artifact_key: [] for definition in IP_ARTIFACT_DEFINITIONS.values()
    }

    missing_matrix_tracker: Dict[str, Dict[str, Dict[str, str]]] = {}
    nexpose_definitions_by_key: Dict[str, str] = {
        definition["artifact_key"]: definition["label"]
        for definition in NEXPOSE_ARTIFACT_DEFINITIONS.values()
    }
    nexpose_results: Dict[str, Dict[str, Any]] = {
        artifact_key: _default_nexpose_artifact(label)
        for artifact_key, label in nexpose_definitions_by_key.items()
    }

    def _resolve_project_type() -> Optional[str]:
        attribute_type = (getattr(project, "type", None) or "").strip()
        if attribute_type:
            return attribute_type

        workbook_data = getattr(project, "workbook_data", None)
        if isinstance(workbook_data, Mapping):
            direct_type = (workbook_data.get("type") or "").strip()
            if direct_type:
                return direct_type

            workbook_project = workbook_data.get("project")
            if isinstance(workbook_project, Mapping):
                project_type = (workbook_project.get("type") or "").strip()
                if project_type:
                    return project_type

        extra_fields = getattr(project, "extra_fields", None)
        if isinstance(extra_fields, Mapping):
            project_type = (extra_fields.get("type") or "").strip()
            if project_type:
                return project_type

        project_type_obj = getattr(project, "project_type", None)
        if project_type_obj:
            project_type = (getattr(project_type_obj, "project_type", None) or "").strip()
            if project_type:
                return project_type
        return None

    project_type_value = _resolve_project_type()

    vulnerability_matrix = load_vulnerability_matrix()
    web_issue_matrix = load_web_issue_matrix()
    parsed_web_findings: List[Dict[str, Any]] = []
    missing_web_issue_matrix: Set[str] = set()

    for data_file in project.data_files.all():
        file_label = (data_file.requirement_label or "").strip()
        if not file_label:
            file_name = os.path.basename(getattr(data_file.file, "name", ""))
            file_label = file_name or file_label

        label = file_label.lower()
        xml_artifact_key = _resolve_nexpose_xml_artifact_key(data_file)
        if label == "dns_report.csv":
            domain = (data_file.requirement_context or data_file.description or data_file.filename).strip()
            domain = domain or "Unknown Domain"
            try:
                content = data_file.file.read().decode("utf-8-sig")
            except Exception:
                content = ""

            if content:
                parsed_dns = parse_dns_report(io.StringIO(content))
            else:
                parsed_dns = parse_dns_report(data_file.file)

            if parsed_dns:
                dns_results.setdefault(domain, []).extend(parsed_dns)

            if content:
                reader = csv.DictReader(io.StringIO(content))
                normalized_rows: List[Dict[str, str]] = []
                for row in reader:
                    normalized_rows.append(
                        {
                            header.strip(): (row.get(header) or "").strip()
                            for header in (reader.fieldnames or [])
                        }
                    )
                if normalized_rows:
                    dns_findings[domain] = normalized_rows

            if hasattr(data_file.file, "seek"):
                try:
                    data_file.file.seek(0)
                except Exception:
                    pass
        elif label == "burp_xml.xml":
            artifacts[BURP_XML_FILE_NAME_KEY] = data_file.filename
            burp_payload = parse_burp_xml_report(data_file.file, web_issue_matrix)
            findings = burp_payload.get("findings") if isinstance(burp_payload, dict) else burp_payload
            if findings:
                parsed_web_findings.extend(findings)
            missing_entries = (
                burp_payload.get("missing_matrix_entries", [])
                if isinstance(burp_payload, dict)
                else []
            )
            for entry in missing_entries:
                issue_name = (entry.get("issue") or "").strip() if isinstance(entry, dict) else ""
                if issue_name:
                    missing_web_issue_matrix.add(issue_name)
        elif label == "firewall_xml.xml":
            logger.info(
                "Processing firewall XML upload '%s' for project ID=%s", file_label, getattr(project, "id", "?")
            )
            artifacts[FIREWALL_XML_FILE_NAME_KEY] = data_file.filename
            parsed_firewall_xml = parse_nipper_firewall_report(
                data_file.file, project_type_value
            )
            logger.info(
                "Firewall XML parsing completed with %s findings",
                len(parsed_firewall_xml) if parsed_firewall_xml is not None else "no",
            )
            if parsed_firewall_xml is not None:
                artifacts["firewall_findings"] = parsed_firewall_xml
        elif label in NEXPOSE_ARTIFACT_DEFINITIONS:
            parsed_vulnerabilities = parse_nexpose_vulnerability_report(
                data_file.file, vulnerability_matrix=vulnerability_matrix
            )
            if any(details.get("items") for details in parsed_vulnerabilities.values()):
                definition = NEXPOSE_ARTIFACT_DEFINITIONS[label]
                artifact_key = definition["artifact_key"]
                nexpose_results[artifact_key] = {
                    "label": definition["label"],
                    **parsed_vulnerabilities,
                }
        elif xml_artifact_key:
            file_name_key = NEXPOSE_FILENAME_KEY_MAP.get(xml_artifact_key)
            if file_name_key:
                artifacts[file_name_key] = data_file.filename
            parsed_xml = parse_nexpose_xml_report(
                data_file.file, vulnerability_matrix=vulnerability_matrix
            )
            existing_entry = artifacts.get(xml_artifact_key)
            combined_findings: List[Dict[str, str]] = []
            combined_software: List[Dict[str, str]] = []
            if isinstance(existing_entry, dict):
                existing_findings = existing_entry.get("findings")
                existing_software = existing_entry.get("software")
                if isinstance(existing_findings, list):
                    combined_findings.extend(existing_findings)
                if isinstance(existing_software, list):
                    combined_software.extend(existing_software)
            parsed_findings = parsed_xml.get("findings") if isinstance(parsed_xml, dict) else []
            parsed_software = parsed_xml.get("software") if isinstance(parsed_xml, dict) else []
            parsed_missing = (
                parsed_xml.get("missing_matrix_entries")
                if isinstance(parsed_xml, dict)
                else []
            )
            if isinstance(parsed_findings, list):
                combined_findings.extend(parsed_findings)
            if isinstance(parsed_software, list):
                combined_software.extend(parsed_software)
            if isinstance(parsed_missing, list) and parsed_missing:
                tracker = missing_matrix_tracker.setdefault(xml_artifact_key, {})
                for row in parsed_missing:
                    if not isinstance(row, dict):
                        continue
                    title = (row.get("Vulnerability") or "").strip()
                    if not title:
                        continue
                    tracker[title.lower()] = {
                        "Vulnerability": title,
                        "Action Required": row.get("Action Required", ""),
                        "Remediation Impact": row.get("Remediation Impact", ""),
                        "Vulnerability Threat": row.get("Vulnerability Threat", ""),
                        "Category": row.get("Category", ""),
                        "CVE": row.get("CVE", ""),
                    }
            artifacts[xml_artifact_key] = {
                "findings": combined_findings,
                "software": combined_software,
            }
            metrics_key = NEXPOSE_METRICS_KEY_MAP.get(xml_artifact_key)
            if metrics_key:
                artifacts[metrics_key] = _build_nexpose_metrics_payload(combined_findings)
        else:
            requirement_slug = (data_file.requirement_slug or "").strip()
            if requirement_slug:
                for definition in IP_ARTIFACT_DEFINITIONS.values():
                    if requirement_slug != definition.slug:
                        continue
                    parsed_ips = _parse_ip_list(data_file.file)
                    if not parsed_ips:
                        break
                    entries = ip_results.setdefault(definition.artifact_key, [])
                    for ip in parsed_ips:
                        if ip not in entries:
                            entries.append(ip)
                    break

    if dns_results:
        artifacts["dns_issues"] = []
        for domain, issues in dns_results.items():
            entry: Dict[str, Any] = {"domain": domain, "issues": issues}
            soa_fields: List[str] = []
            for issue in issues:
                if not isinstance(issue, dict):
                    continue
                if (issue.get("issue") or "") != "One or more SOA fields are outside recommended ranges":
                    continue
                for field in issue.get("soa_fields", []) or []:
                    if field and field not in soa_fields:
                        soa_fields.append(field)
            if soa_fields:
                entry["soa_fields"] = soa_fields
            artifacts["dns_issues"].append(entry)

    if dns_findings:
        artifacts["dns_findings"] = dns_findings

    web_summary = _build_web_summary_from_findings(
        parsed_web_findings, web_issue_matrix
    )
    if web_summary:
        artifacts["web_issues"] = web_summary

    if parsed_web_findings:
        artifacts["web_findings"] = parsed_web_findings
        metrics_payload = _build_web_metrics_payload(parsed_web_findings)
        if metrics_payload:
            artifacts["web_metrics"] = metrics_payload
            cap_entries = _build_web_cap_entries_from_metrics(metrics_payload)
            if cap_entries:
                artifacts["web_cap_map"] = cap_entries

    if missing_web_issue_matrix:
        artifacts["web_issue_matrix_gaps"] = {
            "entries": [
                {"issue": issue, "impact": "", "fix": ""}
                for issue in sorted(missing_web_issue_matrix, key=str.lower)
            ]
        }

    for artifact_key, values in ip_results.items():
        if values:
            artifacts[artifact_key] = values

    firewall_findings = artifacts.get("firewall_findings")
    if isinstance(firewall_findings, dict):
        firewall_entries = firewall_findings.get("findings") if isinstance(firewall_findings.get("findings"), list) else []
    elif isinstance(firewall_findings, list):
        firewall_entries = firewall_findings
    else:
        firewall_entries = []

    if firewall_entries:
        artifacts["firewall_metrics"] = _build_firewall_metrics_payload(firewall_entries)
        artifacts["firewall_vulnerabilities"] = _summarize_firewall_vulnerabilities(
            firewall_entries
        )

    for findings_key, vulnerability_key in NEXPOSE_FINDINGS_VULNERABILITY_MAP.items():
        findings_entry = artifacts.get(findings_key)
        findings = (
            findings_entry.get("findings")
            if isinstance(findings_entry, dict)
            else None
        )
        if not findings:
            continue

        summary = _build_nexpose_vulnerability_summary_from_findings(
            findings, vulnerability_matrix=vulnerability_matrix
        )
        if summary:
            nexpose_results[vulnerability_key] = {
                "label": nexpose_definitions_by_key.get(
                    vulnerability_key,
                    vulnerability_key.replace("_", " ").title(),
                ),
                **summary,
            }

    for artifact_key, details in nexpose_results.items():
        artifacts[artifact_key] = {
            "label": details.get(
                "label", nexpose_definitions_by_key.get(artifact_key, artifact_key.replace("_", " ").title())
            ),
            "high": _coerce_severity_group(details.get("high")),
            "med": _coerce_severity_group(details.get("med")),
            "low": _coerce_severity_group(details.get("low")),
        }

    if missing_matrix_tracker:
        missing_by_artifact: Dict[str, Dict[str, Any]] = {}
        for artifact_key, rows in missing_matrix_tracker.items():
            if not rows:
                continue
            ordered = sorted(
                rows.values(), key=lambda row: (row.get("Vulnerability") or "").lower()
            )
            if ordered:
                missing_by_artifact[artifact_key] = {"entries": ordered}
        if missing_by_artifact:
            artifacts["nexpose_matrix_gaps"] = {
                "missing_by_artifact": missing_by_artifact
            }

    return artifacts


def build_workbook_ad_response(workbook_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate Active Directory response data sourced from workbook details."""

    if not isinstance(workbook_data, dict):
        return {}

    ad_data = workbook_data.get("ad", {})
    domains = ad_data.get("domains", []) if isinstance(ad_data, dict) else []
    if not isinstance(domains, list):
        return {}

    legacy_domains: List[str] = []
    domain_metrics: List[Dict[str, Any]] = []
    disabled_counts: List[str] = []
    disabled_percentages: List[str] = []
    old_password_counts: List[str] = []
    old_password_percentages: List[str] = []
    inactive_counts: List[str] = []
    inactive_percentages: List[str] = []
    domain_admins_counts: List[str] = []
    ent_admins_counts: List[str] = []
    exp_password_counts: List[str] = []
    never_expire_counts: List[str] = []
    generic_account_counts: List[str] = []
    generic_login_counts: List[str] = []

    for entry in domains:
        if isinstance(entry, dict):
            domain_value = entry.get("domain") or entry.get("name") or ""
            functionality_value = entry.get("functionality_level")
            total_accounts = _coerce_int(entry.get("total_accounts"))
            enabled_accounts = _coerce_int(entry.get("enabled_accounts"))
            old_passwords = _coerce_int(entry.get("old_passwords"))
            inactive_accounts = _coerce_int(entry.get("inactive_accounts"))
            domain_admins = _coerce_int(entry.get("domain_admins"))
            ent_admins = _coerce_int(entry.get("ent_admins"))
            exp_passwords = _coerce_int(entry.get("exp_passwords"))
            never_expires = _coerce_int(entry.get("passwords_never_exp"))
            generic_accounts = _coerce_int(entry.get("generic_accounts"))
            generic_logins = _coerce_int(entry.get("generic_logins"))
        else:
            domain_value = entry
            functionality_value = None
            total_accounts = None
            enabled_accounts = None
            old_passwords = None
            inactive_accounts = None
            domain_admins = None
            ent_admins = None
            exp_passwords = None
            never_expires = None
            generic_accounts = None
            generic_logins = None

        domain_text = str(domain_value).strip() if domain_value else ""
        if not domain_text:
            continue

        disabled_count: Optional[int] = None
        if total_accounts is not None and enabled_accounts is not None:
            disabled_count = max(total_accounts - enabled_accounts, 0)

        disabled_counts.append(_format_integer_value(disabled_count))
        disabled_percentages.append(
            _format_percentage_text(_calculate_percentage(disabled_count, total_accounts))
        )

        old_password_counts.append(_format_integer_value(old_passwords))
        old_password_percentages.append(
            _format_percentage_text(_calculate_percentage(old_passwords, enabled_accounts))
        )

        inactive_counts.append(_format_integer_value(inactive_accounts))
        inactive_percentages.append(
            _format_percentage_text(_calculate_percentage(inactive_accounts, enabled_accounts))
        )

        domain_admins_counts.append(_format_integer_value(domain_admins))
        ent_admins_counts.append(_format_integer_value(ent_admins))
        exp_password_counts.append(_format_integer_value(exp_passwords))
        never_expire_counts.append(_format_integer_value(never_expires))
        generic_account_counts.append(_format_integer_value(generic_accounts))
        generic_login_counts.append(_format_integer_value(generic_logins))

        domain_metrics.append(
            {
                "domain_name": domain_text,
                "disabled_count": disabled_count,
                "disabled_pct": _calculate_percentage(disabled_count, total_accounts),
                "old_pass_pct": _calculate_percentage(old_passwords, enabled_accounts),
                "ia_pct": _calculate_percentage(inactive_accounts, enabled_accounts),
            }
        )

        functionality_text = ""
        if functionality_value is not None:
            functionality_text = str(functionality_value)

        if "2000" in functionality_text or "2003" in functionality_text:
            if domain_text not in legacy_domains:
                legacy_domains.append(domain_text)

    response: Dict[str, Any] = {
        "old_domains_count": len(legacy_domains),
        "old_domains_str": None,
    }

    if legacy_domains:
        response["old_domains_string"] = _format_sample_string(legacy_domains)
        old_domains_str = _format_slash_separated_string(legacy_domains)
        response["old_domains_str"] = old_domains_str if old_domains_str else None

    if domain_metrics:
        response["domain_metrics"] = domain_metrics

    if domain_metrics:
        response.update(
            {
                "disabled_account_string": _format_plain_list(disabled_counts),
                "disabled_account_pct_string": _format_plain_list(disabled_percentages),
                "old_password_string": _format_plain_list(old_password_counts),
                "old_password_pct_string": _format_plain_list(old_password_percentages),
                "inactive_accounts_string": _format_plain_list(inactive_counts),
                "inactive_accounts_pct_string": _format_plain_list(inactive_percentages),
                "domain_admins_string": _format_plain_list(domain_admins_counts),
                "ent_admins_string": _format_plain_list(ent_admins_counts),
                "exp_passwords_string": _format_plain_list(exp_password_counts),
                "never_expire_string": _format_plain_list(never_expire_counts),
                "generic_accounts_string": _format_plain_list(generic_account_counts),
                "generic_logins_string": _format_plain_list(generic_login_counts),
            }
        )

    return response


def build_workbook_password_response(
    workbook_data: Optional[Dict[str, Any]]
) -> Tuple[Dict[str, Any], Dict[str, Dict[str, Any]], List[str]]:
    """Generate password policy summary data sourced from workbook details."""

    if not isinstance(workbook_data, dict):
        return {"bad_pass_count": 0}, {}, []

    password_data = workbook_data.get("password", {})
    policies = password_data.get("policies", []) if isinstance(password_data, dict) else []
    if not isinstance(policies, list):
        return {"bad_pass_count": 0}, {}, []

    ad_data = workbook_data.get("ad", {})
    ad_domains = ad_data.get("domains", []) if isinstance(ad_data, dict) else []
    ad_domain_order: List[str] = []
    if isinstance(ad_domains, list):
        for record in ad_domains:
            if isinstance(record, dict):
                domain_value = record.get("domain") or record.get("name")
            else:
                domain_value = record
            domain_text = str(domain_value).strip() if domain_value else ""
            if domain_text and domain_text not in ad_domain_order:
                ad_domain_order.append(domain_text)

    domain_values: Dict[str, Dict[str, Any]] = {}
    policy_domain_order: List[str] = []
    domain_bad_flags: Dict[str, bool] = {}
    bad_pass_total = 0
    total_cracked = 0

    def _is_yes(value: Any) -> bool:
        if isinstance(value, str):
            return value.strip().lower() == "yes"
        if isinstance(value, bool):
            return value
        return False

    def _normalize_admin_count(entry: Dict[str, Any]) -> Optional[int]:
        raw_admin = entry.get("admin_cracked")
        if isinstance(raw_admin, dict):
            confirm_value = raw_admin.get("confirm")
            count_value = raw_admin.get("count")
        else:
            confirm_value = entry.get("admin_cracked_confirm")
            count_value = raw_admin
        if not _is_yes(confirm_value):
            return 0
        coerced = _coerce_int(count_value)
        return coerced if coerced is not None else 0

    def _normalize_fgpp(entry: Dict[str, Any]) -> bool:
        raw_fgpp = entry.get("fgpp")
        if isinstance(raw_fgpp, dict):
            fgpp_count = _coerce_int(raw_fgpp.get("count"))
        else:
            fgpp_count = _coerce_int(raw_fgpp)
        return fgpp_count is not None and fgpp_count < 1

    compliance_matrix = load_password_compliance_matrix()
    policy_field_order: List[str] = list(compliance_matrix.keys())
    policy_fields: Set[str] = set(policy_field_order)
    numeric_policy_fields: Set[str] = {
        field
        for field, definition in compliance_matrix.items()
        if definition.get("data_type") == "numeric"
    }

    rich_text_policy_fields: Set[str] = {
        "history",
        "max_age",
        "min_age",
        "min_length",
        "lockout_reset",
        "lockout_duration",
        "lockout_threshold",
        "complexity_enabled",
    }

    def _normalize_policy_value(entry: Dict[str, Any], key: str) -> Any:
        value = entry.get(key)
        if key in numeric_policy_fields:
            return _coerce_int(value)
        return _normalize_policy_string(value)

    def _value_is_non_compliant(setting: str, normalized_value: Any) -> bool:
        definition = compliance_matrix.get(setting) or {}
        data_type = definition.get("data_type", "numeric")
        rule = definition.get("rule")
        return _evaluate_compliance_rule(rule, normalized_value, data_type)

    def _collect_policy_failures(entry: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(entry, dict):
            return {}

        failures: Dict[str, Any] = {}

        for setting in policy_field_order:
            normalized_value = _normalize_policy_value(entry, setting)
            if setting in numeric_policy_fields and normalized_value is None:
                continue
            if _value_is_non_compliant(setting, normalized_value):
                failures[setting] = normalized_value

        return failures

    def _format_policy_rich_text(
        raw_value: Any, is_non_compliant: bool, setting: str
    ) -> Optional[str]:
        if raw_value in (None, ""):
            return None

        text_value = str(raw_value).strip()
        if not text_value:
            return None

        if is_non_compliant:
            highlight_color = "#ed7d31" if setting == "complexity_enabled" else "#ee0000"
            return (
                f'<p><span class="bold" style="color: {highlight_color};">{text_value}</span></p>'
            )

        return f"<p>{text_value}</p>"

    def _apply_policy_rich_text(entry: Dict[str, Any]) -> None:
        if not isinstance(entry, dict):
            return

        for field in rich_text_policy_fields:
            raw_value = entry.get(field)
            normalized_value = _normalize_policy_value(entry, field)
            matches_rule = False

            if normalized_value is not None:
                matches_rule = _value_is_non_compliant(field, normalized_value)

            rich_text_value = _format_policy_rich_text(raw_value, matches_rule, field)
            if rich_text_value is not None:
                entry[f"{field}_rt"] = rich_text_value

    def _iter_fgpp_entries(entry: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        raw_fgpp = entry.get("fgpp")
        if isinstance(raw_fgpp, list):
            for item in raw_fgpp:
                if isinstance(item, dict):
                    yield item
        elif isinstance(raw_fgpp, dict):
            if any(key in raw_fgpp for key in policy_fields):
                yield raw_fgpp

    for policy in policies:
        if isinstance(policy, dict):
            domain_value = (
                policy.get("domain_name")
                or policy.get("domain")
                or policy.get("name")
                or ""
            )
            entry = policy
        else:
            domain_value = policy
            entry = {}

        domain_text = str(domain_value).strip()
        if not domain_text:
            domain_text = "Unnamed Domain"

        if domain_text not in policy_domain_order:
            policy_domain_order.append(domain_text)

        normalized_entry = entry if isinstance(entry, dict) else {}
        domain_entry = domain_values.setdefault(domain_text, {})

        _apply_policy_rich_text(normalized_entry)

        cracked_value = _coerce_int(normalized_entry.get("passwords_cracked"))
        if cracked_value is not None:
            total_cracked += cracked_value
        enabled_value = _coerce_int(normalized_entry.get("enabled_accounts"))
        admin_cracked_value = _normalize_admin_count(normalized_entry)

        policy_failures = _collect_policy_failures(normalized_entry)
        policy_is_bad = bool(policy_failures)
        if policy_is_bad:
            bad_pass_total += 1
            policy_field_list = domain_entry.setdefault("policy_cap_fields", [])
            for field in policy_failures:
                if field not in policy_field_list:
                    policy_field_list.append(field)
            domain_entry.setdefault("policy_cap_values", {}).update(policy_failures)

        fgpp_is_bad = False
        for index, fgpp_entry in enumerate(
            _iter_fgpp_entries(normalized_entry), start=1
        ):
            _apply_policy_rich_text(fgpp_entry)
            fgpp_failures = _collect_policy_failures(fgpp_entry)
            if not fgpp_failures:
                continue
            bad_pass_total += 1
            fgpp_is_bad = True
            fgpp_name_value = (
                fgpp_entry.get("fgpp_name")
                or fgpp_entry.get("name")
                or fgpp_entry.get("policy_name")
            )
            fgpp_name = str(fgpp_name_value).strip() if fgpp_name_value else ""
            if not fgpp_name:
                fgpp_name = f"Policy {index}"
            fgpp_fields_map = domain_entry.setdefault("fgpp_cap_fields", {})
            fgpp_field_list = fgpp_fields_map.setdefault(fgpp_name, [])
            for field in fgpp_failures:
                if field not in fgpp_field_list:
                    fgpp_field_list.append(field)
            fgpp_values_map = domain_entry.setdefault("fgpp_cap_values", {})
            fgpp_value_entry = fgpp_values_map.setdefault(fgpp_name, {})
            fgpp_value_entry.update(fgpp_failures)

        combined_bad = policy_is_bad or fgpp_is_bad
        if combined_bad or domain_text not in domain_bad_flags:
            domain_bad_flags[domain_text] = domain_bad_flags.get(domain_text, False) or combined_bad

        domain_entry.update(
            {
                "passwords_cracked": _format_integer_value(cracked_value),
                "enabled_accounts": _format_integer_value(enabled_value),
                "admin_cracked": _format_integer_value(admin_cracked_value),
                "lanman": _is_yes(normalized_entry.get("lanman_stored")),
                "no_fgpp": _normalize_fgpp(normalized_entry),
                "bad_pass": domain_bad_flags.get(domain_text, False),
            }
        )

    summary_domains: List[str] = []
    for domain in ad_domain_order:
        if domain in domain_values and domain not in summary_domains:
            summary_domains.append(domain)
    for domain in policy_domain_order:
        if domain in domain_values and domain not in summary_domains:
            summary_domains.append(domain)

    policy_cap_fields, policy_cap_context = summarize_password_cap_details(domain_values)
    password_cap_templates = load_password_cap_map() if policy_cap_fields else {}

    def _inject_cap_details(summary_dict: Dict[str, Any]) -> Dict[str, Any]:
        if policy_cap_fields:
            summary_dict["policy_cap_fields"] = list(policy_cap_fields)
            if policy_cap_context:
                summary_dict["policy_cap_context"] = policy_cap_context
                domain_cap_map = build_password_cap_display_map(
                    policy_cap_context, password_cap_templates
                )
                if domain_cap_map:
                    summary_dict["policy_cap_map"] = domain_cap_map
                else:
                    summary_dict.pop("policy_cap_map", None)
            else:
                summary_dict.pop("policy_cap_context", None)
                summary_dict.pop("policy_cap_map", None)
        else:
            summary_dict.pop("policy_cap_fields", None)
            summary_dict.pop("policy_cap_map", None)
            summary_dict.pop("policy_cap_context", None)
        return summary_dict

    summary: Dict[str, Any] = {"bad_pass_count": bad_pass_total, "total_cracked": total_cracked}

    if not summary_domains:
        return _inject_cap_details(summary), domain_values, summary_domains

    cracked_counts = [domain_values[domain]["passwords_cracked"] for domain in summary_domains]
    enabled_counts = [domain_values[domain]["enabled_accounts"] for domain in summary_domains]
    admin_cracked_counts = [domain_values[domain]["admin_cracked"] for domain in summary_domains]
    lanman_domains = [domain for domain in summary_domains if domain_values[domain]["lanman"]]
    no_fgpp_domains = [domain for domain in summary_domains if domain_values[domain]["no_fgpp"]]

    summary_domains_str = _format_slash_separated_string(summary_domains)
    summary.update(
        {
            "domains_str": summary_domains_str,
            "cracked_count_str": "/".join(cracked_counts),
            "cracked_finding_string": _format_plain_list(cracked_counts),
            "enabled_count_string": _format_plain_list(enabled_counts),
            "admin_cracked_string": _format_plain_list(admin_cracked_counts),
            "admin_cracked_doms": _format_sample_string(summary_domains),
            "lanman_list_string": _format_sample_string(lanman_domains),
            "no_fgpp_string": _format_sample_string(no_fgpp_domains),
        }
    )

    return _inject_cap_details(summary), domain_values, summary_domains


def build_workbook_dns_response(workbook_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate supplemental DNS details derived from workbook metadata."""

    if not isinstance(workbook_data, dict):
        return {}

    dns_data = workbook_data.get("dns", {})
    if not isinstance(dns_data, dict):
        return {}

    records = dns_data.get("records")
    if not isinstance(records, list) or not records:
        return {}

    def _is_yes(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        return str(value).strip().lower() in {"yes", "y", "true", "1"}

    total_records = 0
    zone_transfer_count = 0

    for record in records:
        if not isinstance(record, dict):
            continue
        total_records += 1
        if _is_yes(record.get("zone_transfer")):
            zone_transfer_count += 1

    if total_records == 0:
        return {}

    return {"zone_trans": zone_transfer_count}


def build_workbook_firewall_response(workbook_data: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """Generate supplemental firewall details derived from workbook metadata."""

    if not isinstance(workbook_data, dict):
        return {}

    firewall_data = workbook_data.get("firewall", {})
    if not isinstance(firewall_data, dict):
        return {}

    response: Dict[str, Any] = {"ood_count": 0, "ood_name_list": ""}

    periodic_reviews = firewall_data.get("firewall_periodic_reviews")
    if periodic_reviews not in (None, ""):
        reviews_text = str(periodic_reviews).strip()
        if reviews_text:
            response["firewall_periodic_reviews"] = reviews_text

    devices = firewall_data.get("devices", [])
    if not isinstance(devices, list):
        devices = []

    def _normalize_name(raw_value: Any, index: int) -> str:
        if raw_value is None:
            return f"Device {index}"
        text = str(raw_value).strip()
        return text or f"Device {index}"

    def _normalize_bool(value: Any) -> bool:
        if isinstance(value, bool):
            return value
        if value is None:
            return False
        text = str(value).strip().lower()
        return text in {"yes", "true", "1", "y"}

    ood_names: List[str] = []
    seen_names: set[str] = set()

    for index, record in enumerate(devices, start=1):
        if not isinstance(record, dict):
            continue
        if not _normalize_bool(record.get("ood")):
            continue
        name_value = record.get("name") or record.get("device") or record.get("hostname")
        normalized_name = _normalize_name(name_value, index)
        if normalized_name not in seen_names:
            seen_names.add(normalized_name)
            ood_names.append(normalized_name)

    formatted_names = _format_oxford_quoted_list(ood_names)
    if formatted_names:
        response["ood_name_list"] = formatted_names
        response["ood_count"] = len(ood_names)

    return response
