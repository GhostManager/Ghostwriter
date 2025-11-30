"""This contains all the database models used by the Rolodex application."""

# Standard Libraries
import os
import re
from collections import OrderedDict
from datetime import time, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.db.models import Q

# 3rd Party Libraries
from taggit.managers import TaggableManager
from timezone_field import TimeZoneField

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink, ScopingWeightCategory
from ghostwriter.rolodex.validators import validate_ip_range
from ghostwriter.rolodex.workbook_defaults import normalize_workbook_payload

User = get_user_model()


PROJECT_SCOPING_CONFIGURATION: "OrderedDict[str, Dict[str, Any]]" = OrderedDict(
    [
        (
            "external",
            {
                "label": "External",
                "options": OrderedDict(
                    [
                        ("osint", "OSINT"),
                        ("dns", "DNS"),
                        ("nexpose", "Nexpose"),
                        ("web", "Web"),
                    ]
                ),
            },
        ),
        (
            "internal",
            {
                "label": "Internal",
                "options": OrderedDict(
                    [
                        ("nexpose", "Nexpose"),
                        ("iot_iomt", "IoT/IoMT"),
                        ("endpoint", "Endpoint"),
                        ("snmp", "SNMP"),
                        ("sql", "SQL"),
                    ]
                ),
            },
        ),
        (
            "iam",
            {
                "label": "IAM",
                "options": OrderedDict(
                    [
                        ("ad", "AD"),
                        ("password", "Password"),
                    ]
                ),
            },
        ),
        (
            "wireless",
            {
                "label": "Wireless",
                "options": OrderedDict(
                    [
                        ("walkthru", "Walkthru"),
                        ("segmentation", "Segmentation"),
                    ]
                ),
            },
        ),
        (
            "firewall",
            {
                "label": "Firewall",
                "options": OrderedDict(
                    [
                        ("os", "OS"),
                        ("configuration", "Configuration"),
                    ]
                ),
            },
        ),
        (
            "cloud",
            {
                "label": "Cloud",
                "options": OrderedDict(
                    [
                        ("cloud_management", "Cloud Management"),
                        ("iam_management", "IAM Management"),
                        ("system_configuration", "System Configuration"),
                    ]
                ),
            },
        ),
    ]
)


def default_project_scoping() -> Dict[str, Dict[str, bool]]:
    """Return a default payload for project scoping selections."""

    defaults: "OrderedDict[str, Dict[str, bool]]" = OrderedDict()
    for category_key, category_data in PROJECT_SCOPING_CONFIGURATION.items():
        category_defaults: Dict[str, bool] = {"selected": False}
        for option_key in category_data.get("options", {}):
            category_defaults[option_key] = False
        defaults[category_key] = category_defaults
    return defaults


def normalize_project_scoping(payload: Optional[Dict[str, Any]]) -> Dict[str, Dict[str, bool]]:
    """Normalize arbitrary payloads into the canonical project scoping structure."""

    normalized = default_project_scoping()
    if not isinstance(payload, dict):
        return normalized
    for category_key, category_payload in payload.items():
        if category_key not in normalized or not isinstance(category_payload, dict):
            continue
        normalized_category = normalized[category_key]
        normalized_category["selected"] = bool(category_payload.get("selected"))
        for option_key in normalized_category.keys():
            if option_key == "selected":
                continue
            normalized_category[option_key] = bool(category_payload.get(option_key))

        if (
            category_key == "cloud"
            and normalized_category.get("selected")
            and "system_configuration" in normalized_category
            and "system_configuration" not in category_payload
        ):
            normalized_category["system_configuration"] = True
    return normalized


def build_scoping_weight_distribution(
    payload: Optional[Dict[str, Any]]
) -> "OrderedDict[str, OrderedDict[str, Decimal]]":
    """Return the configured scoping weights for the provided ``payload``."""

    normalized = normalize_project_scoping(payload)
    configured_weights = ScopingWeightCategory.get_weight_map()
    distribution: "OrderedDict[str, OrderedDict[str, Decimal]]" = OrderedDict()

    for category_key, category_config in PROJECT_SCOPING_CONFIGURATION.items():
        category_state = normalized.get(category_key, {})
        if not category_state.get("selected"):
            continue

        option_order = list(category_config.get("options", {}).keys())
        selected_options: List[str] = [
            option_key for option_key in option_order if bool(category_state.get(option_key))
        ]
        for option_key, option_value in category_state.items():
            if option_key in {"selected", *option_order}:
                continue
            if bool(option_value):
                selected_options.append(option_key)

        if not selected_options:
            continue

        category_weights = configured_weights.get(category_key, OrderedDict())
        weighted_entries: List[Tuple[str, Decimal]] = []
        for option_key in selected_options:
            weight_value = category_weights.get(option_key, Decimal("0"))
            weighted_entries.append((option_key, weight_value))

        total_weight = sum(weight for _, weight in weighted_entries)
        if total_weight > 0:
            scale = Decimal("1") / total_weight
            option_distribution = OrderedDict(
                (option_key, weight * scale) for option_key, weight in weighted_entries
            )
        else:
            equal_share = Decimal("1") / Decimal(len(weighted_entries))
            option_distribution = OrderedDict(
                (option_key, equal_share) for option_key, _ in weighted_entries
            )

        distribution[category_key] = option_distribution

    return distribution


class Client(models.Model):
    """Stores an individual client."""

    name = models.CharField(
        "Client Name",
        max_length=255,
        unique=True,
        help_text="Provide the client's full name as you want it to appear in a report",
    )
    short_name = models.CharField(
        "Client Short Name",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide an abbreviated name to be used in reports",
    )
    codename = models.CharField(
        "Client Codename",
        max_length=255,
        default="",
        blank=True,
        help_text="Give the client a codename (might be a ticket number, CMS reference, or something else)",
    )
    note = models.TextField(
        "Client Note",
        default="",
        blank=True,
        help_text="Describe the client or provide some additional information",
    )
    timezone = TimeZoneField(
        "Client Timezone",
        default="America/Los_Angeles",
        help_text="Primary timezone of the client",
    )
    address = models.TextField(
        "Client Business Address",
        default="",
        blank=True,
        help_text="An address to be used for reports or shipping",
    )
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ["name"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def get_absolute_url(self):
        return reverse("rolodex:client_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"

    @classmethod
    def for_user(cls, user):
        """
        Retrieve a filtered list of :model:`rolodex.Client` entries based on the user's role.

        Privileged users will receive all entries. Non-privileged users will receive only those entries to which they
        have access.
        """
        if user.is_privileged:
            return cls.objects.all().order_by("name")
        return (
            cls.objects.filter(
                Q(clientinvite__user=user)
                | Q(project__projectinvite__user=user)
                | Q(project__projectassignment__operator=user)
            )
            .order_by("name")
            .distinct()
        )

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged

    def user_can_view(self, user) -> bool:
        return self in self.for_user(user)

    def user_can_edit(self, user) -> bool:
        return self.user_can_view(user)

    def user_can_delete(self, user) -> bool:
        return self.user_can_view(user)

class ClientContact(models.Model):
    """Stores an individual point of contact, related to :model:`rolodex.Client`."""

    name = models.CharField("Name", help_text="Enter the contact's full name", max_length=255)
    job_title = models.CharField(
        "Title or Role",
        max_length=255,
        help_text="Enter the contact's job title or project role as you want it to appear in a report",
    )
    email = models.CharField(
        "Email",
        max_length=255,
        help_text="Enter an email address for this contact",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would involve human involvement
    # The `max_length` allows for people adding spaces, other chars, and extension numbers
    phone = models.CharField(
        "Phone",
        max_length=50,
        default="",
        blank=True,
        help_text="Enter a phone number for this contact",
    )
    timezone = TimeZoneField(
        "Timezone",
        default="America/Los_Angeles",
        help_text="The contact's timezone",
    )
    note = models.TextField(
        "Contact Note",
        default="",
        blank=True,
        help_text="Provide additional information about the contact",
    )
    # Foreign keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        unique_together = ["name", "client"]
        ordering = ["client", "id"]
        verbose_name = "Client POC"
        verbose_name_plural = "Client POCs"

    def __str__(self):
        return f"{self.name} ({self.client})"


class ProjectType(models.Model):
    """Stores an individual project type, related to :model:`rolodex.Project`."""

    project_type = models.CharField(
        "Project Type",
        max_length=255,
        unique=True,
        help_text="Enter a project type (e.g. red team, penetration test)",
    )

    class Meta:
        ordering = ["project_type"]
        verbose_name = "Project type"
        verbose_name_plural = "Project types"

    def __str__(self):
        return f"{self.project_type}"


class DNSFindingMapping(models.Model):
    """Store curated finding summaries for DNS scanner issues."""

    issue_text = models.TextField(
        "DNS issue",
        unique=True,
        help_text="Exact text of the DNS check failure (matches dns_report.csv entries).",
    )
    finding_text = models.TextField(
        "Finding summary",
        help_text="Short description used when summarizing the issue in reports.",
    )

    class Meta:
        ordering = ["issue_text"]
        verbose_name = "DNS finding mapping"
        verbose_name_plural = "DNS finding mappings"

    def __str__(self):
        return f"{self.issue_text}"


class DNSRecommendationMapping(models.Model):
    """Store remediation guidance for DNS scanner issues."""

    issue_text = models.TextField(
        "DNS issue",
        unique=True,
        help_text="Exact text of the DNS check failure (matches dns_report.csv entries).",
    )
    recommendation_text = models.TextField(
        "Recommendation",
        help_text="Remediation guidance presented alongside the DNS finding.",
    )

    class Meta:
        ordering = ["issue_text"]
        verbose_name = "DNS recommendation mapping"
        verbose_name_plural = "DNS recommendation mappings"

    def __str__(self):
        return f"{self.issue_text}"


class GeneralCapMapping(models.Model):
    """Store general corrective action plan guidance and scoring."""

    issue_text = models.TextField(
        "Issue",
        unique=True,
        help_text="Exact text describing the issue that needs remediation.",
    )
    recommendation_text = models.TextField(
        "Recommendation",
        help_text="Corrective action guidance presented for this issue.",
    )
    score = models.PositiveSmallIntegerField(
        "Score",
        default=0,
        help_text="Numeric score representing the severity or priority of the issue.",
    )

    class Meta:
        ordering = ["issue_text"]
        verbose_name = "General CAP mapping"
        verbose_name_plural = "General CAP mappings"

    def __str__(self):
        return f"{self.issue_text}"


class DNSCapMapping(models.Model):
    """Store corrective action plan (CAP) entries for DNS scanner issues."""

    issue_text = models.TextField(
        "DNS issue",
        unique=True,
        help_text="Exact text of the DNS check failure (matches dns_report.csv entries).",
    )
    cap_text = models.TextField(
        "Corrective action plan",
        help_text="Prescribed DNS CAP guidance displayed with the DNS finding.",
    )

    class Meta:
        ordering = ["issue_text"]
        verbose_name = "DNS CAP mapping"
        verbose_name_plural = "DNS CAP mappings"

    def __str__(self):
        return f"{self.issue_text}"


class DNSSOACapMapping(models.Model):
    """Store CAP guidance for individual DNS SOA fields."""

    soa_field = models.CharField(
        "SOA field",
        max_length=64,
        unique=True,
        help_text="Name of the SOA field flagged as outside the recommended range.",
    )
    cap_text = models.TextField(
        "Corrective action plan",
        help_text="Guidance presented when the SOA field is selected in DNS responses.",
    )

    class Meta:
        ordering = ["soa_field"]
        verbose_name = "DNS SOA CAP mapping"
        verbose_name_plural = "DNS SOA CAP mappings"

    def __str__(self):
        return f"{self.soa_field}"


class PasswordCapMapping(models.Model):
    """Store CAP guidance for workbook password policy settings."""

    setting = models.CharField(
        "Password setting",
        max_length=64,
        unique=True,
        help_text="Name of the password policy setting captured from workbook data.",
    )
    cap_text = models.TextField(
        "Corrective action plan",
        help_text="Guidance presented when the setting is outside recommended bounds.",
    )

    class Meta:
        ordering = ["setting"]
        verbose_name = "Password CAP mapping"
        verbose_name_plural = "Password CAP mappings"

    def __str__(self):
        return f"{self.setting}"


class VulnerabilityMatrixEntry(models.Model):
    """Store reusable remediation context for recurring Nexpose findings."""

    vulnerability = models.TextField(
        "Vulnerability",
        unique=True,
        help_text="Exact vulnerability title as presented in scanner CSV exports.",
    )
    action_required = models.TextField(
        "Action required",
        blank=True,
        default="",
        help_text="Guidance describing the remediation action that must be taken.",
    )
    remediation_impact = models.TextField(
        "Remediation impact",
        blank=True,
        default="",
        help_text="Business or technical impact associated with the remediation effort.",
    )
    vulnerability_threat = models.TextField(
        "Vulnerability threat",
        blank=True,
        default="",
        help_text="Threat statement explaining the risk posed by the vulnerability.",
    )
    category = models.CharField(
        "Category",
        max_length=255,
        blank=True,
        default="",
        help_text="Optional grouping or category for the vulnerability.",
    )

    class Meta:
        ordering = ["vulnerability"]
        verbose_name = "Vulnerability matrix entry"
        verbose_name_plural = "Vulnerability matrix"

    def __str__(self):
        return self.vulnerability


class WebIssueMatrixEntry(models.Model):
    """Store curated impact and fix guidance for recurring web issues."""

    title = models.TextField(
        "Issue title",
        unique=True,
        help_text="Exact issue title as presented in burp.csv exports.",
    )
    impact = models.TextField(
        "Impact",
        blank=True,
        default="",
        help_text="Standardized impact statement for the issue.",
    )
    fix = models.TextField(
        "Fix",
        blank=True,
        default="",
        help_text="Recommended fix or remediation guidance for the issue.",
    )

    class Meta:
        ordering = ["title"]
        verbose_name = "Web issue matrix entry"
        verbose_name_plural = "Web issue matrix"

    def __str__(self):
        return self.title


class Project(models.Model):
    """
    Stores an individual project, related to :model:`rolodex.Client`,
    :model:`rolodex.ProjectType`, and :model:`users.User`.
    """

    codename = models.CharField(
        "Project Codename",
        max_length=255,
        default="",
        blank=True,
        help_text="Give the project a codename (might be a ticket number, PMO reference, or something else)",
    )
    start_date = models.DateField("Start Date", max_length=12, help_text="Enter the start date of this project")
    end_date = models.DateField("End Date", max_length=12, help_text="Enter the end date of this project")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the project and planning",
    )
    workbook_file = models.FileField(
        "Workbook",
        upload_to="project_workbooks/",
        blank=True,
        null=True,
        help_text="Upload the JSON workbook that will be used to drive reporting questions",
    )
    workbook_data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parsed workbook data used to dynamically generate reporting questions",
    )
    data_artifacts = models.JSONField(
        default=dict,
        blank=True,
        help_text="Parsed supporting data derived from uploaded artifacts",
    )
    cap = models.JSONField(
        default=dict,
        blank=True,
        help_text="Corrective action plan values derived from workbook responses and supporting data",
    )
    data_responses = models.JSONField(
        default=dict,
        blank=True,
        help_text="Responses collected from the dynamic reporting data form",
    )
    risks = models.JSONField(
        default=dict,
        blank=True,
        help_text="Risk ratings derived from the uploaded workbook",
    )
    scoping = models.JSONField(
        default=default_project_scoping,
        blank=True,
        help_text="Track the selected scoping categories and their sub-options",
    )
    slack_channel = models.CharField(
        "Project Slack Channel",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide an Slack channel to be used for project notifications",
    )
    complete = models.BooleanField("Completed", default=False, help_text="Mark this project as complete")
    timezone = TimeZoneField(
        "Project Timezone",
        default="America/Los_Angeles",
        help_text="Timezone of the project / working hours",
    )
    start_time = models.TimeField(
        "Start Time",
        default=time(9, 00),
        null=True,
        blank=True,
        help_text="Select the start time for each day",
    )
    end_time = models.TimeField(
        "End Time",
        default=time(17, 00),
        null=True,
        blank=True,
        help_text="Select the end time for each day",
    )
    tags = TaggableManager(blank=True)
    # Foreign keys
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client to which this project should be attached",
    )
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    project_type = models.ForeignKey(
        "ProjectType",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select a category for this project that best describes the work being performed",
    )

    extra_fields = models.JSONField(default=dict)

    def count_findings(self):
        """
        Count and return the number of findings across all reports associated with
        an individual :model:`rolodex.Project`.
        """
        finding_queryset = ReportFindingLink.objects.select_related("report", "report__project").filter(
            report__project=self.pk
        )
        return finding_queryset.count()

    count = property(count_findings)

    def get_scoping_weights(self):
        """Return the weighted scoping distribution for this project."""

        return build_scoping_weight_distribution(getattr(self, "scoping", None))

    scoping_weights = property(get_scoping_weights)

    class Meta:
        ordering = ["-start_date", "end_date", "client", "project_type"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def get_absolute_url(self):
        return reverse("rolodex:project_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.start_date} {self.client} {self.project_type} ({self.codename})"

    @classmethod
    def for_user(cls, user):
        """
        Retrieve a filtered list of :model:`rolodex.Project` entries based on the user's role.

        Privileged users will receive all entries. Non-privileged users will receive only those entries to which they
        have access.
        """
        if user.is_privileged:
            return cls.objects.select_related("client").all().order_by("complete", "client")
        return (
            cls.objects.select_related("client")
            .filter(
                Q(client__clientinvite__user=user)
                | Q(projectinvite__user=user)
                | Q(projectassignment__operator=user)
            )
            .order_by("complete", "client")
        )

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged

    def user_can_view(self, user) -> bool:
        return self in self.for_user(user)

    @classmethod
    def user_viewable(cls, user):
        return cls.for_user(user)

    def user_can_edit(self, user) -> bool:
        return self.user_can_view(user)

    def user_can_delete(self, user) -> bool:
        return self.user_can_view(user)

    def update_risks_from_workbook(self) -> Dict[str, str]:
        """Update ``risks`` based on the current ``workbook_data`` contents."""

        from ghostwriter.rolodex.risk import build_project_risk_summary

        summary = build_project_risk_summary(getattr(self, "workbook_data", {}))
        self.risks = summary
        return summary

    def save(self, *args, **kwargs):  # type: ignore[override]
        update_fields = kwargs.get("update_fields")
        update_field_set = set(update_fields) if update_fields is not None else None
        should_refresh = update_fields is None or (
            update_field_set is not None and "workbook_data" in update_field_set
        )

        if should_refresh:
            self.update_risks_from_workbook()
            if update_fields is not None:
                updated = set(update_fields)
                updated.add("risks")
                kwargs["update_fields"] = list(updated)

        super().save(*args, **kwargs)

    def rebuild_data_artifacts(self) -> None:
        """Rebuild supporting data artifacts derived from uploaded files."""

        from ghostwriter.rolodex.data_parsers import (
            NEXPOSE_ARTIFACT_KEYS,
            NEXPOSE_METRICS_KEY_MAP,
            build_ad_risk_contrib,
            build_project_artifacts,
            build_workbook_ad_response,
            build_workbook_dns_response,
            build_workbook_firewall_response,
            build_workbook_password_response,
            coerce_cap_score,
            load_dns_soa_cap_map,
            load_general_cap_map,
        )

        artifacts = build_project_artifacts(self)

        existing_responses = dict(self.data_responses or {})
        existing_cap = dict(self.cap or {})
        for key in NEXPOSE_ARTIFACT_KEYS:
            existing_responses.pop(key, None)

        workbook_payload = normalize_workbook_payload(
            getattr(self, "workbook_data", None)
        )

        def _safe_int(value: Any) -> int:
            if value in (None, ""):
                return 0
            if isinstance(value, bool):
                return int(value)
            if isinstance(value, (int, float)):
                return int(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return 0
                try:
                    return int(float(text))
                except ValueError:
                    return 0
            return 0

        def _normalize_cap_value(value: Any) -> str:
            if value in (None, ""):
                return ""
            return str(value).strip()

        def _is_truthy(value: Any) -> bool:
            if isinstance(value, bool):
                return value
            if value in (None, ""):
                return False
            if isinstance(value, str):
                text = value.strip().lower()
                if not text:
                    return False
                return text in {"true", "1", "yes", "y"}
            if isinstance(value, (int, float)):
                return bool(value)
            return bool(value)

        def _normalize_issue_key(value: Any) -> str:
            if value in (None, ""):
                return ""
            return str(value).strip().lower()

        def _format_system_label(finding: Dict[str, Any]) -> str:
            ip_address = (finding.get("Asset IP Address") or "").strip()
            hostnames = (finding.get("Hostname(s)") or "").strip()
            if ip_address:
                label = ip_address
                if hostnames:
                    label = f"{label} [{hostnames}]"
            elif hostnames:
                label = hostnames
            else:
                return ""
            status_code = (finding.get("Vulnerability Test Result Code") or "").strip().upper()
            if status_code == "VP":
                label = f"{label} (P)"
            return label

        def _apply_nexpose_metrics(metrics_key: str, workbook_key: str) -> None:
            metrics_payload = artifacts.get(metrics_key)
            if not isinstance(metrics_payload, dict):
                return

            summary = metrics_payload.get("summary")
            summary = summary if isinstance(summary, dict) else {}

            majority_type_raw = (metrics_payload.get("majority_type") or "").strip().upper()
            majority_label_map = {
                "OOD": "OOD Software or Missing Patches",
                "ISC": "Insecure System Configurations",
                "IWC": "Insecure Web Configurations",
            }
            majority_label = majority_label_map.get(majority_type_raw)
            majority_summary_map = {
                "OOD": "total_ood",
                "ISC": "total_isc",
                "IWC": "total_iwc",
            }

            area_payload = workbook_payload.get(workbook_key)
            if not isinstance(area_payload, dict):
                area_payload = {}

            area_payload.update(
                {
                    "total": _safe_int(summary.get("total")),
                    "total_high": _safe_int(summary.get("total_high")),
                    "total_med": _safe_int(summary.get("total_med")),
                    "total_low": _safe_int(summary.get("total_low")),
                    "unique": _safe_int(summary.get("unique")),
                    "unique_high_med": _safe_int(summary.get("unique_high_med")),
                }
            )

            if majority_label:
                area_payload["majority_type"] = majority_label
                summary_key = majority_summary_map.get(majority_type_raw)
                if summary_key:
                    area_payload["unique_majority"] = _safe_int(summary.get(summary_key))

            workbook_payload[workbook_key] = area_payload

        def _apply_web_metrics() -> None:
            metrics_payload = artifacts.get("web_metrics")
            if not isinstance(metrics_payload, dict):
                return

            summary = metrics_payload.get("summary")
            if not isinstance(summary, dict):
                return

            web_payload = workbook_payload.get("web")
            if not isinstance(web_payload, dict):
                web_payload = {}

            web_payload.update(
                {
                    "combined_unique": _safe_int(summary.get("unique")),
                    "combined_unique_high": _safe_int(summary.get("unique_high")),
                    "combined_unique_med": _safe_int(summary.get("unique_med")),
                    "combined_unique_low": _safe_int(summary.get("unique_low")),
                }
            )

            host_counts = summary.get("host_risk_counts")
            sites: list[dict[str, Any]] = []
            if isinstance(host_counts, list):
                for entry in host_counts:
                    if not isinstance(entry, dict):
                        continue
                    url_value = (entry.get("host") or "").strip()
                    if not url_value:
                        continue
                    sites.append(
                        {
                            "url": url_value,
                            "unique_high": _safe_int(entry.get("high")),
                            "unique_med": _safe_int(entry.get("medium")),
                            "unique_low": _safe_int(entry.get("low")),
                        }
                    )

            web_payload["sites"] = sites
            workbook_payload["web"] = web_payload

        def _apply_firewall_metrics() -> None:
            metrics_payload = artifacts.get("firewall_metrics")
            if not isinstance(metrics_payload, dict):
                return

            summary = metrics_payload.get("summary")
            devices = metrics_payload.get("devices")

            firewall_payload = workbook_payload.get("firewall")
            if not isinstance(firewall_payload, dict):
                firewall_payload = {}

            if isinstance(summary, dict):
                def _normalize_type(value: Any) -> Optional[str]:
                    if value in (None, ""):
                        return None
                    text = str(value).strip()
                    normalized = text.lower()
                    if normalized == "config":
                        return "Configuration"
                    if normalized == "rules":
                        return "Rules"
                    if normalized == "even":
                        return "Even"
                    return text

                firewall_payload.update(
                    {
                        "unique": _safe_int(summary.get("unique")),
                        "unique_high": _safe_int(summary.get("unique_high")),
                        "unique_med": _safe_int(summary.get("unique_med")),
                        "unique_low": _safe_int(summary.get("unique_low")),
                        "majority_type": _normalize_type(summary.get("majority_type")),
                        "majority_count": _safe_int(summary.get("majority_count")),
                        "minority_type": _normalize_type(summary.get("minority_type")),
                        "minority_count": _safe_int(summary.get("minority_count")),
                        "complexity_count": _safe_int(summary.get("complexity_count")),
                    }
                )

            if isinstance(devices, list):
                normalized_devices: list[Dict[str, Any]] = []
                for device in devices:
                    if not isinstance(device, dict):
                        continue
                    entry: Dict[str, Any] = {}
                    name_value = (device.get("device") or device.get("name") or "").strip()
                    if name_value:
                        entry["device"] = name_value
                    for field in ("total_high", "total_med", "total_low"):
                        if field in device:
                            entry[field] = _safe_int(device.get(field))
                    if "ood" in device:
                        ood_value = str(device.get("ood") or "").strip().lower()
                        entry["ood"] = "yes" if ood_value in {"yes", "true", "1", "y"} else "no"
                    if entry:
                        normalized_devices.append(entry)
                firewall_payload["devices"] = normalized_devices

            workbook_payload["firewall"] = firewall_payload

        def _build_nexpose_cap_entries_from_metrics() -> List[Dict[str, Any]]:
            issue_map: "OrderedDict[str, Dict[str, Any]]" = OrderedDict()
            findings_lookup: Dict[str, List[Dict[str, Any]]] = {}

            for artifact_key in NEXPOSE_METRICS_KEY_MAP.keys():
                artifact_entry = artifacts.get(artifact_key)
                if not isinstance(artifact_entry, dict):
                    continue
                findings = artifact_entry.get("findings")
                if not isinstance(findings, list):
                    continue
                for finding in findings:
                    if not isinstance(finding, dict):
                        continue
                    title = (finding.get("Vulnerability Title") or finding.get("Vulnerability ID") or "").strip()
                    key = _normalize_issue_key(title)
                    if not key:
                        continue
                    findings_lookup.setdefault(key, []).append(finding)

            for metrics_key in NEXPOSE_METRICS_KEY_MAP.values():
                metrics_payload = artifacts.get(metrics_key)
                if not isinstance(metrics_payload, dict):
                    continue
                unique_issues = metrics_payload.get("unique_issues")
                if not isinstance(unique_issues, list):
                    continue
                for issue_entry in unique_issues:
                    if not isinstance(issue_entry, dict):
                        continue
                    title = (issue_entry.get("issue") or "").strip()
                    key = _normalize_issue_key(title)
                    if not key:
                        continue
                    issue_record = issue_map.setdefault(key, {"issue": title})
                    if not issue_record.get("issue"):
                        issue_record["issue"] = title
                    severity = _safe_int(issue_entry.get("severity"))
                    current_score = issue_record.get("score")
                    if severity is not None and (current_score is None or severity > current_score):
                        issue_record["score"] = severity
                    remediation = (issue_entry.get("remediation") or "").strip()
                    if remediation and not issue_record.get("action"):
                        issue_record["action"] = remediation

            cap_entries: List[Dict[str, Any]] = []
            for key, meta in issue_map.items():
                systems: List[str] = []
                seen_hosts: Set[str] = set()
                for finding in findings_lookup.get(key, []):
                    label = _format_system_label(finding)
                    if not label or label in seen_hosts:
                        continue
                    seen_hosts.add(label)
                    systems.append(label)

                entry: Dict[str, Any] = {}
                issue_text = (meta.get("issue") or "").strip()
                if issue_text:
                    entry["issue"] = issue_text
                action_text = (meta.get("action") or "").strip()
                if action_text:
                    entry["action"] = action_text
                systems_text = "\n".join(systems)
                if systems_text:
                    entry["systems"] = systems_text
                score_value = coerce_cap_score(meta.get("score"))
                if score_value is not None:
                    entry["score"] = score_value
                if entry:
                    cap_entries.append(entry)

            return cap_entries

        nexpose_cap_entries = _build_nexpose_cap_entries_from_metrics()

        _apply_nexpose_metrics("external_nexpose_metrics", "external_nexpose")
        _apply_nexpose_metrics("internal_nexpose_metrics", "internal_nexpose")
        _apply_nexpose_metrics("iot_iomt_nexpose_metrics", "iot_iomt_nexpose")
        _apply_web_metrics()
        _apply_firewall_metrics()

        def _is_explicit_no(value: Any) -> bool:
            if isinstance(value, bool):
                return value is False
            if not isinstance(value, str):
                return False
            text = value.strip().lower()
            if not text:
                return False
            return text in {"no", "false", "0", "n"}

        def _extract_domains(value: Any) -> List[str]:
            if not isinstance(value, str):
                return []

            domains: List[str] = []
            seen: Set[str] = set()
            for token in re.split(r"[\\/,]", value):
                text = token.strip()
                if not text:
                    continue
                text = text.strip("'\" ")
                if not text or text.lower() == "and":
                    continue
                if text not in seen:
                    seen.add(text)
                    domains.append(text)
            return domains

        # General CAP guidance is database managed, so always load the latest
        # definitions regardless of whether workbook data is present. This
        # allows CAP generation to respect admin overrides (for example, the
        # "Weak PSK's in use" guidance comes from the General CAP mappings).
        general_cap_map: Dict[str, Dict[str, Any]] = load_general_cap_map()

        def _clone_cap_entry(issue: str) -> Dict[str, Any]:
            entry = (
                general_cap_map.get(issue)
                if isinstance(general_cap_map, dict)
                else None
            )
            if not isinstance(entry, dict):
                return {}
            payload: Dict[str, Any] = {}
            recommendation = entry.get("recommendation")
            score = entry.get("score")
            if recommendation is not None:
                payload["recommendation"] = recommendation
            if score is not None:
                payload["score"] = score
            return payload

        workbook_ad_response = build_workbook_ad_response(workbook_payload)
        if workbook_ad_response:
            existing_ad_section = existing_responses.get("ad")
            if isinstance(existing_ad_section, dict):
                combined_ad_section = dict(existing_ad_section)
            elif isinstance(existing_ad_section, list):
                combined_ad_section = {"entries": list(existing_ad_section)}
            else:
                combined_ad_section = {}

            combined_ad_section.update(workbook_ad_response)
            combined_ad_section["risk_contrib"] = build_ad_risk_contrib(
                workbook_payload,
                combined_ad_section.get("entries"),
            )
            existing_responses["ad"] = combined_ad_section

        ad_cap_section = existing_cap.get("ad")
        if isinstance(ad_cap_section, dict):
            ad_cap_section = dict(ad_cap_section)
        else:
            ad_cap_section = {}

        ad_cap_map: Dict[str, Dict[str, Any]] = {}

        combined_ad_section = existing_responses.get("ad")
        if isinstance(combined_ad_section, dict):
            for domain in _extract_domains(
                combined_ad_section.get("old_domains_str")
            ):
                entry = _clone_cap_entry("Domain Functionality Level less than 2008")
                if entry:
                    domain_entries = ad_cap_map.setdefault(domain, {})
                    domain_entries[
                        "Domain Functionality Level less than 2008"
                    ] = entry

        workbook_ad_data = (
            workbook_payload.get("ad") if isinstance(workbook_payload, dict) else None
        )
        workbook_ad_domains = (
            workbook_ad_data.get("domains")
            if isinstance(workbook_ad_data, dict)
            else None
        )
        if isinstance(workbook_ad_domains, list):
            for domain_entry in workbook_ad_domains:
                if not isinstance(domain_entry, dict):
                    continue

                domain_value = domain_entry.get("domain") or domain_entry.get("name")
                domain = str(domain_value).strip() if domain_value else ""
                if not domain:
                    continue

                def _record_ad_issue(issue: str) -> None:
                    entry = _clone_cap_entry(issue)
                    if entry:
                        domain_issues = ad_cap_map.setdefault(domain, {})
                        domain_issues[issue] = entry

                total_accounts = _safe_int(domain_entry.get("total_accounts"))
                enabled_accounts = _safe_int(domain_entry.get("enabled_accounts"))
                if total_accounts > 0:
                    enabled_ratio = enabled_accounts / float(total_accounts)
                    if enabled_ratio < 0.9:
                        _record_ad_issue("Number of Disabled Accounts")

                enabled_for_threshold = max(enabled_accounts, 0)
                threshold = enabled_for_threshold * 0.05
                domain_admin_threshold = enabled_for_threshold * 0.005

                if _safe_int(domain_entry.get("generic_accounts")) > threshold:
                    _record_ad_issue("Number of 'Generic Accounts'")

                if _safe_int(domain_entry.get("generic_logins")) > threshold:
                    _record_ad_issue(
                        "Number of Systems with Logged in Generic Accounts"
                    )

                if _safe_int(domain_entry.get("inactive_accounts")) > threshold:
                    _record_ad_issue("Potentially Inactive Accounts")

                if _safe_int(domain_entry.get("passwords_never_exp")) > threshold:
                    _record_ad_issue("Accounts with Passwords that Never Expire")

                if _safe_int(domain_entry.get("exp_passwords")) > threshold:
                    _record_ad_issue("Accounts with Expired Passwords")

                if _safe_int(domain_entry.get("domain_admins")) > domain_admin_threshold:
                    _record_ad_issue("Number of Domain Admins")

                if _safe_int(domain_entry.get("ent_admins")) > 1:
                    _record_ad_issue("Number of Enterprise Admins")

        if ad_cap_map:
            ad_cap_section["ad_cap_map"] = ad_cap_map
        else:
            ad_cap_section.pop("ad_cap_map", None)

        if ad_cap_section:
            existing_cap["ad"] = ad_cap_section
        else:
            existing_cap.pop("ad", None)

        (
            workbook_password_response,
            workbook_password_domain_values,
            workbook_password_domains,
        ) = build_workbook_password_response(workbook_payload)
        existing_password_section = (
            existing_responses.get("password")
            if isinstance(existing_responses.get("password"), dict)
            else {}
        )
        existing_responses.pop("password", None)
        existing_cap.pop("password", None)

        if workbook_password_domain_values and workbook_password_domains:

            combined_password_section: Dict[str, Any] = dict(existing_password_section)

            if isinstance(workbook_password_response, dict):
                combined_password_section.update(workbook_password_response)

            existing_additional_controls = existing_password_section.get(
                "password_additional_controls"
            )
            existing_enforce_mfa = existing_password_section.get(
                "password_enforce_mfa_all_accounts"
            )

            existing_entries = existing_password_section.get("entries")
            existing_entry_map: Dict[str, Dict[str, Any]] = {}
            if isinstance(existing_entries, list):
                for entry in existing_entries:
                    if not isinstance(entry, dict):
                        continue
                    domain_value = entry.get("domain") or entry.get("name")
                    domain_text = str(domain_value).strip() if domain_value else ""
                    if not domain_text:
                        continue
                    existing_entry_map[domain_text] = dict(entry)

            workbook_password_entries: List[Dict[str, Any]] = []
            if isinstance(workbook_password_domain_values, dict):
                for domain, values in workbook_password_domain_values.items():
                    if not isinstance(values, dict):
                        continue
                    domain_text = str(domain).strip()
                    if not domain_text:
                        continue

                    entry_payload: Dict[str, Any] = dict(
                        existing_entry_map.get(domain_text, {})
                    )
                    entry_payload["domain"] = domain_text

                    for key in (
                        "policy_cap_values",
                        "policy_cap_fields",
                        "fgpp_cap_fields",
                        "fgpp_cap_values",
                    ):
                        value = values.get(key)
                        if isinstance(value, dict) and value:
                            entry_payload[key] = dict(value)
                        elif isinstance(value, list) and value:
                            entry_payload[key] = list(value)
                        else:
                            entry_payload.pop(key, None)

                    workbook_password_entries.append(entry_payload)

            if workbook_password_entries:
                combined_password_section["entries"] = workbook_password_entries
            else:
                combined_password_section.pop("entries", None)

            existing_responses["password"] = combined_password_section

            password_cap_section = existing_cap.get("password")
            if isinstance(password_cap_section, dict):
                password_cap_section = dict(password_cap_section)
            else:
                password_cap_section = {}

            cap_fields = combined_password_section.get("policy_cap_fields")
            if isinstance(cap_fields, list) and cap_fields:
                password_cap_section["policy_cap_fields"] = list(cap_fields)
            else:
                password_cap_section.pop("policy_cap_fields", None)

            cap_context = combined_password_section.get("policy_cap_context")
            if isinstance(cap_context, dict) and cap_context:
                password_cap_section["policy_cap_context"] = dict(cap_context)
            else:
                password_cap_section.pop("policy_cap_context", None)

            cap_map = combined_password_section.get("policy_cap_map")
            if isinstance(cap_map, dict) and cap_map:
                password_cap_section["policy_cap_map"] = dict(cap_map)
            else:
                password_cap_section.pop("policy_cap_map", None)

            cap_entries: List[Dict[str, Any]] = []
            existing_cap_entries = password_cap_section.get("entries")
            if isinstance(existing_cap_entries, list):
                for entry in existing_cap_entries:
                    if not isinstance(entry, dict):
                        continue
                    domain_value = entry.get("domain") or entry.get("name")
                    domain = str(domain_value).strip() if domain_value else ""
                    if not domain:
                        continue
                    entry_payload: Dict[str, Any] = {}
                    stored_values = entry.get("policy_cap_values")
                    if isinstance(stored_values, dict) and stored_values:
                        entry_payload["policy_cap_values"] = dict(stored_values)
                    if entry_payload:
                        entry_payload["domain"] = domain
                        cap_entries.append(entry_payload)

            entry_index: Dict[str, Dict[str, Any]] = {
                entry["domain"]: entry
                for entry in cap_entries
                if isinstance(entry, dict) and entry.get("domain")
            }

            password_entries = combined_password_section.get("entries")
            current_password_domains: Set[str] = set()
            if isinstance(password_entries, list):
                for entry in password_entries:
                    if not isinstance(entry, dict):
                        continue
                    domain_value = entry.get("domain") or entry.get("name")
                    domain = str(domain_value).strip() if domain_value else ""
                    if not domain:
                        continue
                    current_password_domains.add(domain)
                    policy_values = entry.get("policy_cap_values")
                    if not isinstance(policy_values, dict) or not policy_values:
                        # fall back to workbook derived values when missing from entry
                        workbook_values = (
                            workbook_password_domain_values.get(domain, {})
                            if isinstance(workbook_password_domain_values, dict)
                            else {}
                        )
                        policy_values = workbook_values.get("policy_cap_values")
                    if not isinstance(policy_values, dict) or not policy_values:
                        entry_index.pop(domain, None)
                        continue
                    stored_entry = entry_index.get(domain)
                    if stored_entry is None:
                        stored_entry = {"domain": domain}
                        entry_index[domain] = stored_entry
                    stored_entry["policy_cap_values"] = dict(policy_values)

            if entry_index:
                stale_domains = set(entry_index.keys()) - current_password_domains
                for domain in stale_domains:
                    entry_index.pop(domain, None)

            if entry_index:
                password_cap_section["entries"] = [entry_index[key] for key in sorted(entry_index.keys())]
            else:
                password_cap_section.pop("entries", None)

            workbook_additional_controls = (
                workbook_password_response.get("password_additional_controls")
                if isinstance(workbook_password_response, dict)
                else None
            )
            workbook_enforce_mfa = (
                workbook_password_response.get("password_enforce_mfa_all_accounts")
                if isinstance(workbook_password_response, dict)
                else None
            )

            def _coalesce_flag(primary: Any, secondary: Any) -> Any:
                if primary not in (None, ""):
                    return primary
                return secondary

            def _is_no(value: Any) -> bool:
                if isinstance(value, str):
                    return value.strip().lower() == "no"
                if isinstance(value, bool):
                    return value is False
                return False

            additional_controls_missing = _is_no(
                _coalesce_flag(existing_additional_controls, workbook_additional_controls)
            )
            enforce_mfa_missing = _is_no(
                _coalesce_flag(existing_enforce_mfa, workbook_enforce_mfa)
            )

            badpass_cap_map: Dict[str, Any] = {}
            global_badpass_entries: Dict[str, Any] = {}
            if isinstance(workbook_password_domain_values, dict):
                for domain, values in workbook_password_domain_values.items():
                    if not isinstance(values, dict):
                        continue
                    domain_entries: Dict[str, Dict[str, Any]] = {}
                    if _safe_int(values.get("passwords_cracked")) > 0:
                        entry = _clone_cap_entry("Weak passwords in use")
                        if entry:
                            domain_entries["Weak passwords in use"] = entry
                    if _is_truthy(values.get("lanman")):
                        entry = _clone_cap_entry("LANMAN password hashing enabled")
                        if entry:
                            domain_entries["LANMAN password hashing enabled"] = entry
                    if _is_truthy(values.get("no_fgpp")):
                        entry = _clone_cap_entry("Fine-grained Password Policies not defined")
                        if entry:
                            domain_entries["Fine-grained Password Policies not defined"] = entry
                    if domain_entries:
                        badpass_cap_map[domain] = domain_entries
            if additional_controls_missing:
                entry = _clone_cap_entry("Additional password controls not implemented")
                if entry:
                    global_badpass_entries["Additional password controls not implemented"] = entry
            if enforce_mfa_missing:
                entry = _clone_cap_entry("MFA not enforced for all accounts")
                if entry:
                    global_badpass_entries["MFA not enforced for all accounts"] = entry
            if global_badpass_entries:
                badpass_cap_map["global"] = global_badpass_entries
            if badpass_cap_map:
                password_cap_section["badpass_cap_map"] = badpass_cap_map
            else:
                password_cap_section.pop("badpass_cap_map", None)

            if password_cap_section:
                existing_cap["password"] = password_cap_section
            else:
                existing_cap.pop("password", None)

        workbook_firewall_response = build_workbook_firewall_response(workbook_payload)
        if workbook_firewall_response:
            existing_firewall_section = existing_responses.get("firewall")
            if isinstance(existing_firewall_section, dict):
                combined_firewall_section = dict(existing_firewall_section)
            elif isinstance(existing_firewall_section, list):
                combined_firewall_section = {"entries": list(existing_firewall_section)}
            else:
                combined_firewall_section = {}

            combined_firewall_section.update(workbook_firewall_response)
            existing_responses["firewall"] = combined_firewall_section

        firewall_response_section = existing_responses.get("firewall")
        if isinstance(firewall_response_section, dict):
            firewall_periodic_reviews = firewall_response_section.get(
                "firewall_periodic_reviews"
            )
        else:
            firewall_periodic_reviews = None

        firewall_cap_section = existing_cap.get("firewall")
        if isinstance(firewall_cap_section, dict):
            firewall_cap_section = dict(firewall_cap_section)
        else:
            firewall_cap_section = {}

        firewall_cap_entries: List[Dict[str, Any]] = []
        firewall_artifact = artifacts.get("firewall_findings")
        if isinstance(firewall_artifact, dict):
            firewall_findings = firewall_artifact.get("findings")
        elif isinstance(firewall_artifact, list):
            firewall_findings = firewall_artifact
        else:
            firewall_findings = None

        if not firewall_findings:
            firewall_alt = artifacts.get("firewall_cap_findings")
            if isinstance(firewall_alt, list):
                firewall_findings = firewall_alt
            elif isinstance(firewall_alt, dict):
                firewall_findings = firewall_alt.get("findings")

        def _normalize_firewall_value(value: Any) -> Optional[str]:
            if value in (None, ""):
                return None
            if isinstance(value, str):
                text = value.strip()
                return text or None
            return str(value)

        def _coerce_finding_score(value: Any) -> Optional[Any]:
            if isinstance(value, (int, float)):
                return float(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return None
                normalized = text.replace(",", "")
                try:
                    return float(normalized)
                except ValueError:
                    return text
            return None

        if isinstance(firewall_findings, list):
            for entry in firewall_findings:
                if not isinstance(entry, dict):
                    continue

                normalized_entry: Dict[str, Any] = {}
                cap_defaults = _clone_cap_entry(
                    "Business justification for firewall rules"
                )
                if cap_defaults:
                    normalized_entry.update(cap_defaults)

                for key, value in entry.items():
                    if key == "score":
                        score_value = _coerce_finding_score(value)
                        if score_value is not None:
                            normalized_entry["finding_score"] = score_value
                        continue

                    normalized_value = _normalize_firewall_value(value)
                    if normalized_value is not None:
                        normalized_entry[key] = normalized_value

                if normalized_entry:
                    firewall_cap_entries.append(normalized_entry)

        global_firewall_entries: Dict[str, Dict[str, Any]] = {}
        if firewall_periodic_reviews not in (None, ""):
            normalized_reviews = str(firewall_periodic_reviews).strip().lower()
        else:
            normalized_reviews = ""
        if normalized_reviews == "no":
            entry = _clone_cap_entry("Business justification for firewall rules")
            if entry:
                global_firewall_entries["Business justification for firewall rules"] = entry

        if firewall_cap_entries:
            firewall_cap_section["firewall_cap_map"] = firewall_cap_entries
        else:
            firewall_cap_section.pop("firewall_cap_map", None)

        if global_firewall_entries:
            firewall_cap_section["global"] = global_firewall_entries
        else:
            firewall_cap_section.pop("global", None)

        if firewall_cap_section:
            existing_cap["firewall"] = firewall_cap_section
        else:
            existing_cap.pop("firewall", None)

        if isinstance(firewall_artifact, dict):
            firewall_artifact.pop("findings", None)

        workbook_dns_response = build_workbook_dns_response(workbook_payload)
        if workbook_dns_response:
            existing_dns_section = existing_responses.get("dns")
            if isinstance(existing_dns_section, dict):
                combined_dns_section = dict(existing_dns_section)
            elif isinstance(existing_dns_section, list):
                combined_dns_section = {"entries": list(existing_dns_section)}
            else:
                combined_dns_section = {}

            combined_dns_section.update(workbook_dns_response)
            existing_responses["dns"] = combined_dns_section

        def _collect_domain_soa_fields(entries: Any) -> Dict[str, List[str]]:
            domain_fields: Dict[str, List[str]] = {}
            if not isinstance(entries, list):
                return domain_fields
            for entry in entries:
                if not isinstance(entry, dict):
                    continue
                fields = entry.get("soa_fields")
                if not isinstance(fields, list):
                    continue
                domain_value = (
                    entry.get("domain")
                    or entry.get("name")
                    or entry.get("zone")
                    or entry.get("fqdn")
                )
                domain_text = str(domain_value).strip() if domain_value else ""
                if not domain_text:
                    continue
                domain_entry = domain_fields.setdefault(domain_text, [])
                seen_fields = set(domain_entry)
                for field in fields:
                    if field is None:
                        continue
                    text = str(field).strip()
                    if not text or text in seen_fields:
                        continue
                    seen_fields.add(text)
                    domain_entry.append(text)
            return domain_fields

        dns_section_created = False
        dns_section = existing_responses.get("dns")
        if isinstance(dns_section, dict):
            pass
        elif isinstance(dns_section, list):
            dns_section = {"entries": list(dns_section)}
            existing_responses["dns"] = dns_section
        else:
            dns_section = {}
            existing_responses["dns"] = dns_section
            dns_section_created = True

        def _merge_soa_fields_from_artifacts(section: Dict[str, Any]) -> None:
            artifact_entries = artifacts.get("dns_issues")
            if not isinstance(artifact_entries, list):
                return

            detected_fields: Dict[str, List[str]] = {}
            target_issue = "One or more SOA fields are outside recommended ranges"

            for artifact_entry in artifact_entries:
                if not isinstance(artifact_entry, dict):
                    continue

                domain_value = artifact_entry.get("domain")
                domain_text = str(domain_value).strip() if domain_value else ""
                if not domain_text:
                    continue

                combined_fields: List[str] = []
                for field in artifact_entry.get("soa_fields", []) or []:
                    if field and field not in combined_fields:
                        combined_fields.append(field)

                issues = artifact_entry.get("issues")
                if isinstance(issues, list):
                    for issue in issues:
                        if not isinstance(issue, dict):
                            continue
                        if (issue.get("issue") or "") != target_issue:
                            continue
                        for field in issue.get("soa_fields", []) or []:
                            if field and field not in combined_fields:
                                combined_fields.append(field)

                if combined_fields:
                    detected_fields[domain_text] = combined_fields

            if not detected_fields:
                return

            entries = section.get("entries")
            if isinstance(entries, list):
                normalized_entries = list(entries)
            else:
                normalized_entries = []

            entry_lookup: Dict[str, Dict[str, Any]] = {}
            for entry in normalized_entries:
                if not isinstance(entry, dict):
                    continue
                domain_value = entry.get("domain") or entry.get("name")
                domain_text = str(domain_value).strip() if domain_value else ""
                if domain_text:
                    entry_lookup[domain_text.lower()] = entry

            changed = False
            for domain, fields in detected_fields.items():
                normalized = domain.lower()
                entry = entry_lookup.get(normalized)
                if entry is None:
                    entry = {"domain": domain}
                    normalized_entries.append(entry)
                    entry_lookup[normalized] = entry
                    changed = True
                elif not entry.get("domain"):
                    entry["domain"] = domain
                existing_fields = entry.setdefault("soa_fields", [])
                for field in fields:
                    if field not in existing_fields:
                        existing_fields.append(field)
                        changed = True

            if changed or normalized_entries:
                section["entries"] = [
                    entry for entry in normalized_entries if isinstance(entry, dict)
                ]

        _merge_soa_fields_from_artifacts(dns_section)

        domain_soa_cap_map: Dict[str, Dict[str, str]] = {}

        if isinstance(dns_section, dict):
            entries = dns_section.get("entries")
            if isinstance(entries, list):
                domain_soa_fields = _collect_domain_soa_fields(entries)
                unique_fields: List[str] = []
                for field_list in domain_soa_fields.values():
                    for field in field_list:
                        if field not in unique_fields:
                            unique_fields.append(field)
                if unique_fields:
                    dns_section["unique_soa_fields"] = unique_fields
                else:
                    dns_section.pop("unique_soa_fields", None)

                if domain_soa_fields:
                    cap_map = load_dns_soa_cap_map()
                    domain_soa_cap_map = {
                        domain: {
                            field: cap_map.get(field, "")
                            for field in fields
                        }
                        for domain, fields in domain_soa_fields.items()
                    }
                    dns_section["soa_field_cap_map"] = domain_soa_cap_map
                else:
                    dns_section.pop("soa_field_cap_map", None)
                    domain_soa_cap_map = {}
            else:
                dns_section.pop("unique_soa_fields", None)
                dns_section.pop("soa_field_cap_map", None)
                domain_soa_cap_map = {}

            dns_artifact_entries = artifacts.get("dns_issues")
            dns_cap_map: Dict[str, Dict[str, str]] = {}
            if isinstance(dns_artifact_entries, list):
                for artifact_entry in dns_artifact_entries:
                    if not isinstance(artifact_entry, dict):
                        continue
                    domain_value = artifact_entry.get("domain")
                    domain_text = str(domain_value).strip() if domain_value else ""
                    if not domain_text:
                        continue
                    issues = artifact_entry.get("issues")
                    if not isinstance(issues, list) or not issues:
                        continue
                    domain_map = dns_cap_map.setdefault(domain_text, {})
                    for issue_entry in issues:
                        if not isinstance(issue_entry, dict):
                            continue
                        issue_text = str(issue_entry.get("issue") or "").strip()
                        if not issue_text:
                            continue
                        cap_text = issue_entry.get("cap")
                        resolved_cap = (
                            str(cap_text) if cap_text is not None else ""
                        )
                        if (
                            issue_text
                            == "One or more SOA fields are outside recommended ranges"
                        ):
                            domain_field_map = domain_soa_cap_map.get(domain_text)
                            if not domain_field_map:
                                soa_cap_map_section = dns_section.get(
                                    "soa_field_cap_map", {}
                                )
                                if isinstance(soa_cap_map_section, dict):
                                    potential_map = soa_cap_map_section.get(domain_text)
                                    if isinstance(potential_map, dict):
                                        domain_field_map = potential_map
                            if domain_field_map:
                                cap_lines: List[str] = []
                                for field_name, field_cap in domain_field_map.items():
                                    field_name_text = str(field_name)
                                    field_cap_text = (
                                        "" if field_cap is None else str(field_cap)
                                    )
                                    cap_lines.append(
                                        f"{field_name_text} - {field_cap_text}"
                                    )
                                if cap_lines:
                                    resolved_cap = "\n".join(cap_lines)
                        domain_map[issue_text] = {
                            "score": 2,
                            "recommendation": resolved_cap,
                        }
            if dns_cap_map:
                dns_section["dns_cap_map"] = dns_cap_map
            else:
                dns_section.pop("dns_cap_map", None)

            dns_cap_section = existing_cap.get("dns")
            if isinstance(dns_cap_section, dict):
                dns_cap_section = dict(dns_cap_section)
            else:
                dns_cap_section = {}

            soa_cap_map = dns_section.get("soa_field_cap_map")
            if isinstance(soa_cap_map, dict) and soa_cap_map:
                dns_cap_section["soa_field_cap_map"] = {
                    domain: dict(fields)
                    for domain, fields in soa_cap_map.items()
                    if isinstance(fields, dict) and fields
                }
            else:
                dns_cap_section.pop("soa_field_cap_map", None)

            dns_cap_values = dns_section.get("dns_cap_map")
            if isinstance(dns_cap_values, dict) and dns_cap_values:
                dns_cap_section["dns_cap_map"] = {
                    domain: dict(issues)
                    for domain, issues in dns_cap_values.items()
                    if isinstance(issues, dict) and issues
                }
            else:
                dns_cap_section.pop("dns_cap_map", None)

            if dns_cap_section:
                existing_cap["dns"] = dns_cap_section
            else:
                existing_cap.pop("dns", None)

        if not dns_section:
            if dns_section_created:
                existing_responses.pop("dns", None)
            else:
                dns_section.pop("unique_soa_fields", None)
                dns_section.pop("soa_field_cap_map", None)
                dns_section.pop("dns_cap_map", None)

        osint_section = existing_cap.get("osint")
        if isinstance(osint_section, dict):
            osint_section = dict(osint_section)
        else:
            osint_section = {}

        osint_cap_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(workbook_payload, dict):
            osint_data = workbook_payload.get("osint")
        else:
            osint_data = None

        if isinstance(osint_data, dict):
            total_assets = (
                _safe_int(osint_data.get("total_ips"))
                + _safe_int(osint_data.get("total_domains"))
                + _safe_int(osint_data.get("total_hostnames"))
            )
            if total_assets >= 2:
                entry = _clone_cap_entry("OSINT identified assets")
                if entry:
                    osint_cap_map["OSINT identified assets"] = entry

            if _safe_int(osint_data.get("total_buckets")) > 0:
                entry = _clone_cap_entry("Exposed buckets identified")
                if entry:
                    osint_cap_map["Exposed buckets identified"] = entry

            if _safe_int(osint_data.get("total_leaks")) > 0:
                entry = _clone_cap_entry("Exposed Credentials identified")
                if entry:
                    osint_cap_map["Exposed Credentials identified"] = entry

            if _safe_int(osint_data.get("total_squat")) > 0:
                entry = _clone_cap_entry("Potential domain squatters identified")
                if entry:
                    osint_cap_map["Potential domain squatters identified"] = entry

        if osint_cap_map:
            osint_section["osint_cap_map"] = osint_cap_map
        else:
            osint_section.pop("osint_cap_map", None)

        if osint_section:
            existing_cap["osint"] = osint_section
        else:
            existing_cap.pop("osint", None)

        endpoint_section = existing_cap.get("endpoint")
        if isinstance(endpoint_section, dict):
            endpoint_section = dict(endpoint_section)
        else:
            endpoint_section = {}

        endpoint_cap_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(workbook_payload, dict):
            endpoint_data = workbook_payload.get("endpoint")
        else:
            endpoint_data = None

        if isinstance(endpoint_data, dict):
            endpoint_domains = endpoint_data.get("domains")
        else:
            endpoint_domains = None

        if isinstance(endpoint_domains, list):
            for domain_entry in endpoint_domains:
                if not isinstance(domain_entry, dict):
                    continue

                domain_value = domain_entry.get("domain") or domain_entry.get("name")
                domain = str(domain_value).strip() if domain_value else ""
                if not domain:
                    continue

                domain_cap_entries: Dict[str, Dict[str, Any]] = {}

                if _safe_int(domain_entry.get("systems_ood")) > 0:
                    entry = _clone_cap_entry(
                        "Systems without active up-to-date security software"
                    )
                    if entry:
                        domain_cap_entries[
                            "Systems without active up-to-date security software"
                        ] = entry

                if _safe_int(domain_entry.get("open_wifi")) > 0:
                    entry = _clone_cap_entry("Systems connecting to Open WiFi networks")
                    if entry:
                        domain_cap_entries[
                            "Systems connecting to Open WiFi networks"
                        ] = entry

                if domain_cap_entries:
                    endpoint_cap_map[domain] = domain_cap_entries

        if endpoint_cap_map:
            endpoint_section["endpoint_cap_map"] = endpoint_cap_map
        else:
            endpoint_section.pop("endpoint_cap_map", None)

        if endpoint_section:
            existing_cap["endpoint"] = endpoint_section
        else:
            existing_cap.pop("endpoint", None)

        wireless_section = existing_cap.get("wireless")
        if isinstance(wireless_section, dict):
            wireless_section = dict(wireless_section)
        else:
            wireless_section = {}

        wireless_cap_map: Dict[str, Dict[str, Any]] = {}

        if isinstance(workbook_payload, dict):
            wireless_data = workbook_payload.get("wireless")
        else:
            wireless_data = None

        base_wireless_values = (
            wireless_data if isinstance(wireless_data, dict) else {}
        )

        if isinstance(existing_responses.get("wireless"), dict):
            existing_wireless_section = existing_responses.get("wireless")
        else:
            existing_wireless_section = None

        domain_sources: Dict[str, Dict[str, Any]] = {}

        if isinstance(wireless_data, dict):
            wireless_domains = wireless_data.get("domains")
        else:
            wireless_domains = None

        if isinstance(wireless_domains, list):
            for domain_entry in wireless_domains:
                if not isinstance(domain_entry, dict):
                    continue
                domain_value = domain_entry.get("domain") or domain_entry.get("name")
                domain = str(domain_value).strip() if domain_value else ""
                if not domain:
                    continue
                domain_sources[domain] = domain_entry

        if not domain_sources and isinstance(existing_wireless_section, dict):
            for domain in _extract_domains(existing_wireless_section.get("domains_str")):
                domain_sources.setdefault(domain, {})

        def _resolve_wireless_value(
            domain_entry: Optional[Dict[str, Any]], key: str
        ) -> Any:
            if isinstance(domain_entry, dict):
                if key in domain_entry and domain_entry[key] is not None:
                    return domain_entry[key]
            if key in base_wireless_values:
                return base_wireless_values.get(key)
            if isinstance(domain_entry, dict):
                return domain_entry.get(key)
            return None

        def _collect_wireless_cap_entries(
            domain_entry: Optional[Dict[str, Any]]
        ) -> Dict[str, Dict[str, Any]]:
            domain_cap_entries: Dict[str, Dict[str, Any]] = {}

            if _safe_int(_resolve_wireless_value(domain_entry, "psk_count")) > 0:
                entry = _clone_cap_entry("PSK’s in use on wireless networks")
                if entry:
                    domain_cap_entries["PSK’s in use on wireless networks"] = entry

            if _safe_int(_resolve_wireless_value(domain_entry, "rogue_count")) > 0:
                entry = _clone_cap_entry("Potentially Rogue Access Points")
                if entry:
                    domain_cap_entries["Potentially Rogue Access Points"] = entry

            wep_values = _resolve_wireless_value(domain_entry, "wep_inuse")
            if isinstance(wep_values, dict):
                wep_confirm = wep_values.get("confirm")
            else:
                wep_confirm = wep_values
            if _is_truthy(wep_confirm):
                entry = _clone_cap_entry("WEP in use on wireless networks")
                if entry:
                    domain_cap_entries["WEP in use on wireless networks"] = entry

            if _is_truthy(_resolve_wireless_value(domain_entry, "internal_access")):
                entry = _clone_cap_entry(
                    "Open wireless network connected to the Internal network"
                )
                if entry:
                    domain_cap_entries[
                        "Open wireless network connected to the Internal network"
                    ] = entry

            if _is_explicit_no(_resolve_wireless_value(domain_entry, "802_1x_used")):
                entry = _clone_cap_entry(
                    "802.1x authentication not implemented for wireless networks"
                )
                if entry:
                    domain_cap_entries[
                        "802.1x authentication not implemented for wireless networks"
                    ] = entry

            if _is_truthy(_resolve_wireless_value(domain_entry, "weak_psks")):
                entry = _clone_cap_entry("Weak PSK's in use")
                if entry:
                    domain_cap_entries["Weak PSK's in use"] = entry

            return domain_cap_entries

        for domain, domain_entry in domain_sources.items():
            domain_cap_entries = _collect_wireless_cap_entries(domain_entry)
            if domain_cap_entries:
                wireless_cap_map[domain] = domain_cap_entries

        if wireless_cap_map:
            wireless_section["wireless_cap_map"] = {
                domain: dict(entries)
                for domain, entries in sorted(wireless_cap_map.items())
            }
        else:
            global_cap_entries = _collect_wireless_cap_entries(None)
            if global_cap_entries:
                wireless_section["wireless_cap_map"] = {
                    issue: dict(entry)
                    for issue, entry in sorted(global_cap_entries.items())
                }
            else:
                wireless_section.pop("wireless_cap_map", None)

        if wireless_section:
            existing_cap["wireless"] = wireless_section
        else:
            existing_cap.pop("wireless", None)

        sql_section = existing_cap.get("sql")
        if isinstance(sql_section, dict):
            sql_section = dict(sql_section)
        else:
            sql_section = {}

        sql_cap_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(workbook_payload, dict):
            sql_data = workbook_payload.get("sql")
        else:
            sql_data = None

        if isinstance(sql_data, dict):
            if _safe_int(sql_data.get("total_open")) > 0:
                entry = _clone_cap_entry("Databases allowing open access")
                if entry:
                    sql_cap_map["Databases allowing open access"] = entry

        if sql_cap_map:
            sql_section["sql_cap_map"] = sql_cap_map
        else:
            sql_section.pop("sql_cap_map", None)

        if sql_section:
            existing_cap["sql"] = sql_section
        else:
            existing_cap.pop("sql", None)

        snmp_section = existing_cap.get("snmp")
        if isinstance(snmp_section, dict):
            snmp_section = dict(snmp_section)
        else:
            snmp_section = {}

        snmp_cap_map: Dict[str, Dict[str, Any]] = {}
        if isinstance(workbook_payload, dict):
            snmp_data = workbook_payload.get("snmp")
        else:
            snmp_data = None

        if isinstance(snmp_data, dict):
            if _safe_int(snmp_data.get("total_strings")) > 0:
                entry = _clone_cap_entry(
                    "Default SNMP community strings & default credentials in use"
                )
                if entry:
                    snmp_cap_map[
                        "Default SNMP community strings & default credentials in use"
                    ] = entry

        if snmp_cap_map:
            snmp_section["snmp_cap_map"] = snmp_cap_map
        else:
            snmp_section.pop("snmp_cap_map", None)

        if snmp_section:
            existing_cap["snmp"] = snmp_section
        else:
            existing_cap.pop("snmp", None)

        web_section = existing_cap.get("web")
        if isinstance(web_section, dict):
            web_section = dict(web_section)
        else:
            web_section = {}

        web_cap_entries = artifacts.get("web_cap_map")
        if web_cap_entries is None:
            web_cap_entries = artifacts.get("web_cap_entries")
        normalized_web_entries: List[Dict[str, Any]] = []
        if isinstance(web_cap_entries, list):
            for entry in web_cap_entries:
                if not isinstance(entry, dict):
                    continue

                normalized_entry: Dict[str, Any] = {}
                for field in ("issue", "hosts", "action", "ecfirst", "severity"):
                    value = entry.get(field)
                    if value in (None, ""):
                        continue
                    text = str(value).strip()
                    if text:
                        normalized_entry[field] = text

                score_value = entry.get("score")
                if isinstance(score_value, (int, float)):
                    normalized_entry["score"] = int(score_value)
                elif isinstance(score_value, str):
                    score_text = score_value.strip()
                    if score_text:
                        normalized_entry["score"] = score_text

                if normalized_entry:
                    normalized_web_entries.append(normalized_entry)

        if normalized_web_entries:
            web_section["web_cap_map"] = normalized_web_entries
        else:
            web_section.pop("web_cap_map", None)
        # Clean up any legacy key so stored CAP data remains normalized.
        web_section.pop("web_cap_entries", None)

        if web_section:
            existing_cap["web"] = web_section
        else:
            existing_cap.pop("web", None)

        web_response_section = existing_responses.get("web")
        if isinstance(web_response_section, dict):
            web_response_section.pop("web_cap_entries", None)
            web_response_section.pop("web_cap_map", None)

        nexpose_section = existing_cap.get("nexpose")
        if isinstance(nexpose_section, dict):
            nexpose_section = dict(nexpose_section)
        else:
            nexpose_section = {}

        raw_nexpose_entries = nexpose_cap_entries
        normalized_nexpose_entries: List[Dict[str, Any]] = []
        if isinstance(raw_nexpose_entries, list):
            for entry in raw_nexpose_entries:
                if not isinstance(entry, dict):
                    continue
                normalized_entry: Dict[str, Any] = {}
                for key in ("systems", "action", "issue", "ecfirst"):
                    text = _normalize_cap_value(entry.get(key))
                    if text:
                        normalized_entry[key] = text
                score_value = entry.get("score")
                if score_value is None:
                    score_value = entry.get("severity")
                score = coerce_cap_score(score_value)
                if score is not None:
                    normalized_entry["score"] = score
                if normalized_entry:
                    normalized_nexpose_entries.append(normalized_entry)

        if normalized_nexpose_entries:
            nexpose_section["nexpose_cap_map"] = normalized_nexpose_entries
        else:
            nexpose_section.pop("nexpose_cap_map", None)

        if "distilled" in nexpose_section:
            nexpose_section["distilled"] = bool(
                _is_truthy(nexpose_section.get("distilled"))
            )
        else:
            nexpose_section["distilled"] = False

        existing_cap["nexpose"] = nexpose_section

        # CAP data for Burp/Nexpose uploads lives exclusively under ``project.cap``.
        # Remove the intermediate artifacts so ``project.data_artifacts`` only
        # contains fields required by reporting templates and views.
        artifacts.pop("web_cap_map", None)
        artifacts.pop("web_cap_entries", None)
        artifacts.pop("nexpose_cap_map", None)
        artifacts.pop("firewall_cap_findings", None)

        self.data_artifacts = artifacts
        self.data_responses = existing_responses
        self.cap = existing_cap
        self.workbook_data = workbook_payload

        self.save(update_fields=["data_artifacts", "data_responses", "cap", "workbook_data"])


class ProjectDataFile(models.Model):
    """Stores additional data files uploaded to support report generation."""

    project = models.ForeignKey(
        Project,
        related_name="data_files",
        on_delete=models.CASCADE,
    )
    file = models.FileField(
        "Supporting Data File",
        upload_to="project_data/",
        max_length=255,
    )
    description = models.CharField(
        "Description",
        max_length=255,
        blank=True,
        default="",
    )
    requirement_slug = models.CharField(
        "Requirement Key",
        max_length=255,
        blank=True,
        default="",
    )
    requirement_label = models.CharField(
        "Requirement Label",
        max_length=255,
        blank=True,
        default="",
    )
    requirement_context = models.CharField(
        "Requirement Context",
        max_length=255,
        blank=True,
        default="",
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-uploaded_at"]
        verbose_name = "Project data file"
        verbose_name_plural = "Project data files"

    def __str__(self):
        return f"{self.project} - {self.filename}"

    def rebuild_project_artifacts(self) -> None:
        """Rebuild parsed artifacts for the related project."""

        project = self.project
        project.rebuild_data_artifacts()

    @property
    def filename(self):
        return os.path.basename(self.file.name)


class ProjectRole(models.Model):
    """Stores an individual project role."""

    project_role = models.CharField(
        "Project Role",
        max_length=255,
        unique=True,
        help_text="Enter an operator role used for project assignments",
    )

    class Meta:
        ordering = ["project_role"]
        verbose_name = "Project role"
        verbose_name_plural = "Project roles"

    def __str__(self):
        return f"{self.project_role}"


class ProjectAssignment(models.Model):
    """
    Stores an individual project assignment, related to :model:`users.User`,
    :model:`rolodex.Project`, and :model:`rolodex.ProjectRole`.
    """

    start_date = models.DateField(
        "Start Date",
        null=True,
        blank=True,
        help_text="Enter the start date of the project",
    )
    end_date = models.DateField(
        "End Date",
        null=True,
        blank=True,
        help_text="Enter the end date of the project",
    )
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the project role and assignment",
    )
    # Foreign keys
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Select a user to assign to this project",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.PROTECT,
        null=True,
        blank=True,
        help_text="Select a role that best describes the selected user's role in this project",
    )

    class Meta:
        ordering = ["project", "start_date", "operator"]
        verbose_name = "Project assignment"
        verbose_name_plural = "Project assignments"

    def get_absolute_url(self):
        return reverse("rolodex:project_detail", args=[str(self.project.id)])

    def __str__(self):
        return f"{self.operator} - {self.project} {self.end_date})"


class ProjectContact(models.Model):
    """Stores an individual point of contact, related to :model:`rolodex.Project`."""

    name = models.CharField("Name", help_text="Enter the contact's full name", max_length=255)
    job_title = models.CharField(
        "Title or Role",
        max_length=255,
        help_text="Enter the contact's job title or project role as you want it to appear in a report",
    )
    email = models.CharField(
        "Email",
        max_length=255,
        help_text="Enter an email address for this contact",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would involve human involvement
    # The `max_length` allows for people adding spaces, other chars, and extension numbers
    phone = models.CharField(
        "Phone",
        max_length=50,
        default="",
        blank=True,
        help_text="Enter a phone number for this contact",
    )
    timezone = TimeZoneField(
        "Timezone",
        default="America/Los_Angeles",
        help_text="The contact's timezone",
    )
    note = models.TextField(
        "Contact Note",
        default="",
        blank=True,
        help_text="Provide additional information about the contact",
    )
    primary = models.BooleanField(
        "Primary Contact",
        default=False,
        help_text="Flag this contact as the primary point of contact / report recipient for the project",
    )
    # Foreign keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        unique_together = ["name", "project"]
        ordering = ["project", "id"]
        verbose_name = "Project POC"
        verbose_name_plural = "Project POCs"

    def __str__(self):
        return f"{self.name}"


class ObjectiveStatus(models.Model):
    """Stores an individual objective status."""

    objective_status = models.CharField(
        "Objective Status",
        max_length=255,
        unique=True,
        help_text="Objective's status",
    )

    class Meta:
        ordering = ["objective_status"]
        verbose_name = "Objective status"
        verbose_name_plural = "Objective status"

    def __str__(self):
        return f"{self.objective_status}"


class ObjectivePriority(models.Model):
    """Stores an individual objective priority category."""

    weight = models.IntegerField(
        "Priority Weight",
        default=1,
        help_text="Weight for sorting this priority when viewing objectives (lower numbers are higher priority)",
    )
    priority = models.CharField(
        "Objective Priority",
        max_length=255,
        unique=True,
        help_text="Objective's priority",
    )

    class Meta:
        ordering = ["weight", "priority"]
        verbose_name = "Objective priority"
        verbose_name_plural = "Objective priorities"

    def __str__(self):
        return f"{self.priority}"


def _get_default_status():
    """Get the default status for the status field."""
    try:
        active_status = ObjectiveStatus.objects.get(objective_status="Active")
        return active_status.id
    except ObjectiveStatus.DoesNotExist:
        return 1


class ProjectObjective(models.Model):
    """
    Stores an individual project objective, related to an individual :model:`rolodex.Project`
    and :model:`rolodex.ObjectiveStatus`.
    """

    objective = models.CharField(
        "Objective",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide a high-level objective – add sub-tasks later for planning or as you discover obstacles",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a more detailed description, purpose, or context",
    )
    complete = models.BooleanField("Completed", default=False, help_text="Mark the objective as complete")
    deadline = models.DateField(
        "Due Date",
        max_length=12,
        null=True,
        blank=True,
        help_text="Objective's deadline/due date",
    )
    marked_complete = models.DateField(
        "Marked Complete",
        null=True,
        blank=True,
        help_text="Date the objective was marked complete",
    )
    position = models.IntegerField(
        "List Position",
        default=1,
    )
    result = models.TextField(
        "Result",
        default="",
        blank=True,
        help_text="Provide a detailed result or outcome for this objective",
    )
    # Foreign Keys
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=False,
    )
    status = models.ForeignKey(
        ObjectiveStatus,
        on_delete=models.PROTECT,
        default=_get_default_status,
        help_text="Set the status for this objective",
    )
    priority = models.ForeignKey(
        ObjectivePriority,
        on_delete=models.PROTECT,
        null=True,
        help_text="Assign a priority category",
    )

    class Meta:
        ordering = [
            "project",
            "position",
            "complete",
            "priority__weight",
            "deadline",
            "status",
            "objective",
        ]
        verbose_name = "Project objective"
        verbose_name_plural = "Project objectives"

    def __str__(self):
        return f"{self.project} - {self.objective} {self.status})"

    def calculate_status(self):
        """
        Calculate and return a percentage complete estimate based on ``complete`` value
        and any status of related :model:`ProjectSubTask` entries.
        """
        total_tasks = self.projectsubtask_set.all().count()
        completed_tasks = 0
        if self.complete:
            return 100.0

        if total_tasks > 0:
            for task in self.projectsubtask_set.all():
                if task.complete:
                    completed_tasks += 1
            return round(completed_tasks / total_tasks * 100, 1)

        return 0


class ProjectSubTask(models.Model):
    """
    Stores an individual sub-task, related to an individual :model:`rolodex.ProjectObjective`
    and :model:`rolodex.ObjectiveStatus`.
    """

    task = models.TextField("Task", blank=True, default="", help_text="Provide a concise objective")
    complete = models.BooleanField("Completed", default=False, help_text="Mark the objective as complete")
    deadline = models.DateField(
        "Due Date",
        max_length=12,
        null=True,
        blank=True,
        help_text="Provide a deadline for this objective",
    )
    marked_complete = models.DateField(
        "Marked Complete",
        null=True,
        blank=True,
        help_text="Date the task was marked complete",
    )
    # Foreign Keys
    parent = models.ForeignKey(ProjectObjective, on_delete=models.CASCADE, null=False)
    status = models.ForeignKey(
        ObjectiveStatus,
        on_delete=models.PROTECT,
        default=_get_default_status,
        help_text="Set the status for this objective",
    )

    class Meta:
        ordering = ["parent", "complete", "deadline", "status", "task"]
        verbose_name = "Objective sub-task"
        verbose_name_plural = "Objective sub-tasks"

    def __str__(self):
        return f"{self.parent.project} : {self.task} ({self.status})"


class ClientNote(models.Model):
    """Stores an individual note, related to an individual :model:`rolodex.Client` and :model:`users.User`."""

    # This field is automatically filled with the current date
    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Leave the client or related projects",
    )
    # Foreign Keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["client", "timestamp"]
        verbose_name = "Client note"
        verbose_name_plural = "Client notes"

    def __str__(self):
        return f"{self.client}: {self.timestamp} - {self.note}"


class ProjectNote(models.Model):
    """Stores an individual note, related to :model:`rolodex.Project` and :model:`users.User`."""

    # This field is automatically filled with the current date
    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Leave a note about the project or related client",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["project", "timestamp"]
        verbose_name = "Project note"
        verbose_name_plural = "Project notes"

    def __str__(self):
        return f"{self.project}: {self.timestamp} - {self.note}"


class ProjectScope(models.Model):
    """Stores an individual scope list, related to an individual :model:`rolodex.Project`."""

    name = models.CharField(
        "Scope Name",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide a descriptive name for this list (e.g., External IPs, Cardholder Data Environment)",
    )
    scope = models.TextField(
        "Scope",
        default="",
        blank=True,
        help_text="Provide a list of IP addresses, ranges, hostnames, or a mix with each entry on a new line",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a brief description of this list",
    )
    disallowed = models.BooleanField(
        "Disallowed",
        default=False,
        help_text="Flag this list as off limits / not to be touched",
    )
    requires_caution = models.BooleanField(
        "Requires Caution",
        default=False,
        help_text="Flag this list as requiring caution or prior warning before testing",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project", "name"]
        verbose_name = "Project scope list"
        verbose_name_plural = "Project scope lists"

    def __str__(self):
        return f"{self.project}: {self.name}"

    def count_lines(self):
        """Returns the number of lines in the scope list."""
        return len(self.scope.splitlines())

    def count_lines_str(self):
        """Returns the number of lines in the scope list as a string."""
        count = len(self.scope.splitlines())
        if count > 1:
            return f"{count} Lines"
        return f"{count} Line"


class ProjectTarget(models.Model):
    """Stores an individual target host, related to an individual :model:`rolodex.Project`."""

    ip_address = models.CharField(
        "IP Address",
        max_length=45,
        default="",
        blank=True,
        validators=[validate_ip_range],
        help_text="Enter the IP address or range of the target host(s)",
    )
    hostname = models.CharField(
        "Hostname / FQDN",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide the target's hostname, fully qualified domain name, or other identifier",
    )
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the target(s) or the environment",
    )
    compromised = models.BooleanField("Compromised", default=False, help_text="Flag this target as compromised")
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project", "compromised", "ip_address", "hostname"]
        verbose_name = "Project target"
        verbose_name_plural = "Project targets"

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class ClientInvite(models.Model):
    """
    Links an individual :model:`users.User` to a :model:`rolodex.Client` to
    which they have been granted access.
    """

    comment = models.TextField(
        "Comment",
        default="",
        blank=True,
        help_text="Optional explanation for this invite",
    )
    # Foreign Keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["client_id", "user_id"]
        verbose_name = "Client invite"
        verbose_name_plural = "Client invites"

    def __str__(self):
        return f"{self.user} ({self.client})"


class ProjectInvite(models.Model):
    """
    Links an individual :model:`users.User` to a :model:`rolodex.Project` to
    which they have been granted access.
    """

    comment = models.TextField(
        "Comment",
        default="",
        blank=True,
        help_text="Optional explanation for this invite",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project_id", "user_id"]
        verbose_name = "Project invite"
        verbose_name_plural = "Project invites"

    def __str__(self):
        return f"{self.user} ({self.project})"


class DeconflictionStatus(models.Model):
    """Stores an individual deconfliction status."""

    status = models.CharField(
        "Status",
        max_length=255,
        unique=True,
        help_text="Status for a deconfliction request (e.g., Undetermined, Confirmed, Unrelated)",
    )
    weight = models.IntegerField(
        "Status Weight",
        default=1,
        help_text="Weight for sorting status",
    )

    class Meta:
        ordering = ["weight", "status"]
        verbose_name = "Deconfliction status"
        verbose_name_plural = "Deconfliction status"

    def __str__(self):
        return f"{self.status}"


class Deconfliction(models.Model):
    """Stores an individual deconfliction, related to an individual :model:`rolodex.Project`."""

    created_at = models.DateTimeField(
        "Timestamp",
        auto_now_add=True,
        help_text="Date and time this deconfliction was created",
    )
    report_timestamp = models.DateTimeField(
        "Report Timestamp",
        help_text="Date and time the client informed you and requested deconfliction",
    )
    alert_timestamp = models.DateTimeField(
        "Alert Timestamp",
        null=True,
        blank=True,
        help_text="Date and time the alert fired",
    )
    response_timestamp = models.DateTimeField(
        "Response Timestamp",
        null=True,
        blank=True,
        help_text="Date and time you responded to the report",
    )
    title = models.CharField(
        "Deconfliction Title",
        max_length=255,
        help_text="Provide a descriptive title or headline for this deconfliction",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a brief description of this deconfliction request",
    )
    alert_source = models.CharField(
        "Alert Source",
        max_length=255,
        default="",
        blank=True,
        help_text="Source of the alert (e.g., user reported, EDR, MDR, etc.)",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    status = models.ForeignKey(
        "DeconflictionStatus",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a status that best reflects the current state of this deconfliction (e.g., undetermined, confirmed assessment activity, or unrelated to assessment activity)",
    )

    class Meta:
        ordering = ["project", "-created_at", "status__weight", "title"]
        verbose_name = "Project deconfliction"
        verbose_name_plural = "Project deconflictions"

    @property
    def log_entries(self):
        """Get log entries that precede the alert by one hour."""
        from ghostwriter.oplog.models import OplogEntry
        logs = None
        if self.alert_timestamp:
            one_hour_ago = self.alert_timestamp - timedelta(hours=1)
            logs = OplogEntry.objects.filter(
                models.Q(oplog_id__project=self.project)
                & models.Q(start_date__range=(one_hour_ago, self.alert_timestamp))
            )
        return logs

    def __str__(self):
        return f"{self.project}: {self.title}"


class WhiteCard(models.Model):
    """Stores an individual white card, related to an individual :model:`rolodex.Project`."""

    issued = models.DateTimeField(
        "Issued",
        blank=True,
        null=True,
        help_text="Date and time the client issued this white card",
    )
    title = models.CharField(
        "Title",
        max_length=255,
        blank=True,
        default="",
        help_text="Provide a descriptive headline for this white card (e.g., a username, hostname, or short sentence",
    )
    description = models.TextField(
        "Description",
        blank=True,
        default="",
        help_text="Provide a brief description of this white card",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project", "-issued", "title"]
        verbose_name = "Project white card"
        verbose_name_plural = "Project white cards"

    def __str__(self):
        return f"{self.project}: {self.title}"
