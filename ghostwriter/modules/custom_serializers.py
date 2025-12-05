"""This contains customizations for `rest_framework.serializers` classes used by Ghostwriter."""

# IF YOU EDIT THIS FILE: also update `linting_utils.py`

# Standard Libraries
from datetime import datetime
import zoneinfo

# Standard Libraries
from typing import Any, Dict, List, Optional, Set

# Django Imports
from django.conf import settings
from django.utils import dateformat
from django.utils.text import slugify

# 3rd Party Libraries
from bs4 import BeautifulSoup
from rest_framework import serializers
from rest_framework.serializers import (
    RelatedField,
    SerializerMethodField,
    StringRelatedField,
)
from taggit.serializers import TaggitSerializer, TagListSerializerField
from timezone_field.rest_framework import TimeZoneSerializerField

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import CompanyInformation, ExtraFieldSpec
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.reporting.models import (
    Evidence,
    Finding,
    Observation,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    ReportTemplate,
    RiskScoreRangeMapping,
    Severity,
)
from ghostwriter.rolodex.data_parsers import (
    build_ad_risk_contrib,
    build_password_cap_display_map,
    build_workbook_ad_response,
    build_workbook_dns_response,
    build_workbook_firewall_response,
    build_workbook_password_response,
    load_dns_soa_cap_map,
    load_password_cap_map,
    normalize_nexpose_artifacts_map,
    summarize_password_cap_details,
)
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    Deconfliction,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    WhiteCard,
)
from ghostwriter.rolodex.workbook import AD_DOMAIN_METRICS
from ghostwriter.shepherd.models import (
    AuxServerAddress,
    Domain,
    DomainServerConnection,
    History,
    ServerHistory,
    StaticServer,
    TransientServer,
)
from ghostwriter.users.models import User


def strip_html(value):
    """Strip HTML from a string."""
    if value is None:
        return None
    return BeautifulSoup(value, "html.parser").text


GENERAL_RESPONSE_KEYS = {
    "assessment_scope",
    "assessment_scope_cloud_on_prem",
    "general_first_ca",
    "general_scope_changed",
    "general_anonymous_ephi",
}

INTELLIGENCE_RESPONSE_KEYS = {
    "osint_squat_concern",
    "osint_bucket_risk",
    "osint_leaked_creds_risk",
}


class CustomModelSerializer(serializers.ModelSerializer):
    """
    Modified version of ``ModelSerializer`` that adds an ``exclude`` argument for
    excluding specific fields based on needs of the serializer.
    """

    def __init__(self, *args, exclude=None, **kwargs):
        if exclude:
            exclude = set(exclude)
            for field in exclude:
                self.fields.pop(field)
        super().__init__(*args, **kwargs)

    def to_representation(self, instance):
        """
        Override the default method to ensure empty strings are returned for null values. The null values will
        cause Jinja2 rendering errors with filters and expressions like `sort()`.
        """
        data = super().to_representation(instance)
        for key, value in data.items():
            try:
                if value is None:
                    data[key] = ""
            except KeyError:
                pass
        return data


class OperatorNameField(RelatedField):
    """Customize the string representation of a :model:`users.User` entry."""

    def to_representation(self, value):
        return value.name


class DomainField(RelatedField):
    """Customize the string representation of a :model:`shepherd.DomainHistory` entry."""

    def to_representation(self, value):
        return value.domain.name


class StaticServerField(RelatedField):
    """Customize the string representation of a :model:`shepherd.ServerHistory` entry."""

    def to_representation(self, value):
        string_value = value.ip_address
        return string_value


class CloudServerField(RelatedField):
    """Customize the string representation of a :model:`shepherd.TransientServer` entry."""

    def to_representation(self, value):
        return value.ip_address


class ExtraFieldsSerField(serializers.Field):
    """Fills out defaults in the `extra_fields` field from the definitions in :model:`commandcenter.ExtraFieldSpec`"""

    def __init__(self, model_name, **kwargs):
        self.model_name = model_name
        self.root_ser = None
        kwargs["read_only"] = True
        super().__init__(**kwargs)

    def bind(self, field_name, parent):
        super().bind(field_name, parent)
        root_ser = parent
        while getattr(root_ser, "parent", None) is not None:
            root_ser = root_ser.parent
        self.root_ser = root_ser

    def to_representation(self, value):
        out = {}

        # Fetch field specs, and cache them at the root serializer
        if not hasattr(self.root_ser, "_extra_fields_specs") or self.root_ser._extra_fields_specs is None:
            self.root_ser._extra_fields_specs = {}
        if self.model_name not in self.root_ser._extra_fields_specs:
            self.root_ser._extra_fields_specs[self.model_name] = ExtraFieldSpec.objects.filter(
                target_model=self.model_name
            )

        # Populate output
        for field in self.root_ser._extra_fields_specs[self.model_name]:
            out[field.internal_name] = field.value_of(value)
        return out


class UserSerializer(CustomModelSerializer):
    """Serialize :model:`users.User` entries."""

    name = SerializerMethodField("get_name")

    timezone = TimeZoneSerializerField()

    class Meta:
        model = User
        fields = ["id", "name", "username", "email", "phone", "timezone"]

    def get_name(self, obj):
        return obj.get_display_name()


class CompanyInfoSerializer(CustomModelSerializer):
    """Serialize :model:`commandcenter:CompanyInformation` entries."""

    name = serializers.CharField(source="company_name")
    short_name = serializers.CharField(source="company_short_name")
    address = serializers.CharField(source="company_address")
    twitter = serializers.CharField(source="company_twitter")
    email = serializers.CharField(source="company_email")

    class Meta:
        model = CompanyInformation
        exclude = ["id", "company_name", "company_short_name", "company_address", "company_twitter", "company_email"]


class EvidenceSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Evidence` entries."""

    path = SerializerMethodField("get_path")
    tags = TagListSerializerField()

    class Meta:
        model = Evidence
        exclude = ["document"]

    def get_path(self, obj):
        return str(obj.document)


class FindingSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Finding` entries."""

    finding_type = StringRelatedField()
    severity = StringRelatedField()
    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")
    tags = TagListSerializerField()
    extra_fields = ExtraFieldsSerField(Finding._meta.label)

    class Meta:
        model = Finding
        fields = "__all__"

    def get_severity_color(self, obj):
        return obj.severity.color

    def get_severity_color_rgb(self, obj):
        return obj.severity.color_rgb

    def get_severity_color_hex(self, obj):
        return obj.severity.color_hex


class FindingLinkSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:ReportFindingLink` entries."""

    assigned_to = SerializerMethodField("get_assigned_to")
    finding_type = StringRelatedField()
    severity = StringRelatedField()
    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")
    extra_fields = ExtraFieldsSerField(Finding._meta.label)
    cvss_data = SerializerMethodField("get_cvss_data")
    tags = TagListSerializerField()

    # Include a copy of the ``mitigation`` field as ``recommendation`` to match legacy JSON output
    recommendation = serializers.CharField(source="mitigation")

    evidence = EvidenceSerializer(
        source="evidence_set",
        many=True,
        exclude=[
            "report",
            "finding",
            "uploaded_by",
        ],
    )

    class Meta:
        model = ReportFindingLink
        fields = "__all__"

    def get_assigned_to(self, obj):
        if obj.assigned_to:
            return obj.assigned_to.name
        return "TBD"

    def get_severity_color(self, obj):
        return obj.severity.color

    def get_severity_color_rgb(self, obj):
        return obj.severity.color_rgb

    def get_severity_color_hex(self, obj):
        return obj.severity.color_hex

    def get_cvss_data(self, obj):
        return obj.cvss_data


class ObservationLinkSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:ObservationLinkSerializer` entries."""

    tags = TagListSerializerField()

    extra_fields = ExtraFieldsSerField(Observation._meta.label)

    class Meta:
        model = ReportObservationLink
        fields = "__all__"


class ReportTemplateSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:ReportTemplate` entries."""

    class Meta:
        model = ReportTemplate
        fields = "__all__"


class ReportSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Report` entries."""

    created_by = StringRelatedField()

    last_update = SerializerMethodField("get_creation")
    creation = SerializerMethodField("get_last_update")
    total_findings = SerializerMethodField("get_total_findings")

    findings = FindingLinkSerializer(source="reportfindinglink_set", many=True, exclude=["id", "report"])
    observations = ObservationLinkSerializer(source="reportobservationlink_set", many=True, exclude=["id", "report"])

    tags = TagListSerializerField()

    class Meta:
        model = Report
        fields = "__all__"

    def get_creation(self, obj):
        return dateformat.format(obj.creation, settings.DATE_FORMAT)

    def get_last_update(self, obj):
        return dateformat.format(obj.last_update, settings.DATE_FORMAT)

    def get_total_findings(self, obj):
        return len(obj.reportfindinglink_set.all())


class ClientContactSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ClientContact` entries."""

    timezone = TimeZoneSerializerField()

    class Meta:
        model = ClientContact
        fields = "__all__"


class ClientSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`rolodex:Client` entries."""

    short_name = SerializerMethodField("get_short_name")
    address = SerializerMethodField("get_address")

    contacts = ClientContactSerializer(
        source="clientcontact_set",
        many=True,
        exclude=[
            "client",
        ],
    )

    timezone = TimeZoneSerializerField()

    tags = TagListSerializerField()

    extra_fields = ExtraFieldsSerField(Client._meta.label)

    class Meta:
        model = Client
        fields = "__all__"

    def get_short_name(self, obj):
        if obj.short_name:
            return obj.short_name
        return obj.name

    def get_address(self, obj):
        return strip_html(obj.address)


class ProjectNoteSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectNote` entries."""

    name = SerializerMethodField("get_operator")
    timestamp = SerializerMethodField("get_timestamp")

    class Meta:
        model = ProjectNote
        exclude = ["operator"]
        depth = 1

    def get_operator(self, obj):
        return obj.operator.name

    def get_timestamp(self, obj):
        return dateformat.format(obj.timestamp, settings.DATE_FORMAT)


class ProjectAssignmentSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectAssignment` entries."""

    role = StringRelatedField()

    name = SerializerMethodField("get_operator")
    email = SerializerMethodField("get_email")
    start_date = SerializerMethodField("get_start_date")
    end_date = SerializerMethodField("get_end_date")
    phone = SerializerMethodField("get_phone")
    timezone = SerializerMethodField("get_timezone")

    class Meta:
        model = ProjectAssignment
        exclude = [
            "operator",
        ]
        depth = 1

    def get_operator(self, obj):
        return obj.operator.name

    def get_email(self, obj):
        return obj.operator.email

    def get_start_date(self, obj):
        return dateformat.format(obj.start_date, settings.DATE_FORMAT)

    def get_end_date(self, obj):
        return dateformat.format(obj.end_date, settings.DATE_FORMAT)

    def get_phone(self, obj):
        return obj.operator.phone

    def get_timezone(self, obj):
        tz = zoneinfo.ZoneInfo(str(obj.operator.timezone))
        return str(tz)


class ProjectSubTaskSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectSubTask` entries."""

    deadline = SerializerMethodField("get_deadline")
    marked_complete = SerializerMethodField("get_marked_complete")

    class Meta:
        model = ProjectSubTask
        fields = "__all__"

    def get_deadline(self, obj):
        return dateformat.format(obj.deadline, settings.DATE_FORMAT)

    def get_marked_complete(self, obj):
        if obj.marked_complete:
            return dateformat.format(obj.marked_complete, settings.DATE_FORMAT)
        return False


class ProjectObjectiveSerializer(CustomModelSerializer):
    """
    Serialize :model:`rolodex:ProjectObjective` and all related
    :model:`rolodex:ProjectSubTask` entries.
    """

    priority = StringRelatedField()
    status = StringRelatedField()

    deadline = SerializerMethodField("get_deadline")
    percent_complete = SerializerMethodField("get_percent_complete")

    tasks = ProjectSubTaskSerializer(
        source="projectsubtask_set",
        many=True,
        exclude=[
            "status",
            "parent",
        ],
    )

    class Meta:
        model = ProjectObjective
        fields = "__all__"
        depth = 1

    def get_deadline(self, obj):
        return dateformat.format(obj.deadline, settings.DATE_FORMAT)

    def get_percent_complete(self, obj):
        return obj.calculate_status()


class ProjectScopeSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectScope` entries."""

    total = serializers.SerializerMethodField("get_total")
    scope = serializers.SerializerMethodField("get_scope_list")

    class Meta:
        model = ProjectScope
        fields = "__all__"

    def get_total(self, obj):
        total = obj.count_lines()
        return total

    def get_scope_list(self, obj):
        return obj.scope.split("\r\n")


class ProjectTargetSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectTarget` entries."""

    class Meta:
        model = ProjectTarget
        fields = "__all__"


class AuxServerAddressSerializer(CustomModelSerializer):
    """Serialize :model:`shepherd:AuxServerAddress` entries."""

    class Meta:
        model = AuxServerAddress
        fields = "__all__"


class DomainServerConnectionSerializer(CustomModelSerializer):
    """Serialize :model:`shepherd:DomainServerConnection` entries."""

    domain = DomainField(read_only=True)
    static_server = StaticServerField(read_only=True)
    transient_server = CloudServerField(read_only=True)

    class Meta:
        model = DomainServerConnection
        fields = "__all__"


class DomainHistorySerializer(CustomModelSerializer):
    """
    Serialize :model:`shepherd:History` entries for a specific
    :model:`rolodex.Project`
    """

    activity = serializers.CharField(source="activity_type")
    domain = SerializerMethodField("get_domain_name")

    start_date = SerializerMethodField("get_start_date")
    end_date = SerializerMethodField("get_end_date")

    dns = DomainServerConnectionSerializer(
        source="domainserverconnection_set",
        many=True,
        exclude=["id", "project", "domain"],
    )

    extra_fields = ExtraFieldsSerField(Domain._meta.label, source="domain.extra_fields")

    class Meta:
        model = History
        exclude = [
            "activity_type",
        ]

    def get_domain_name(self, obj):
        return obj.domain.name

    def get_start_date(self, obj):
        return dateformat.format(obj.start_date, settings.DATE_FORMAT)

    def get_end_date(self, obj):
        return dateformat.format(obj.end_date, settings.DATE_FORMAT)


class StaticServerSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`shepherd.StaticServer` entries."""

    provider = serializers.CharField(source="server_provider")
    status = serializers.CharField(source="server_status")
    last_used_by = StringRelatedField()
    tags = TagListSerializerField()
    extra_fields = ExtraFieldsSerField(StaticServer._meta.label)

    class Meta:
        model = StaticServer
        fields = "__all__"


class ServerHistorySerializer(CustomModelSerializer):
    """Serialize :model:`shepherd.ServerHistory` entries."""

    name = SerializerMethodField("get_server_name")
    ip_address = SerializerMethodField("get_server_address")
    provider = SerializerMethodField("get_server_provider")
    activity = serializers.CharField(source="activity_type")
    role = serializers.CharField(source="server_role")

    start_date = SerializerMethodField("get_start_date")
    end_date = SerializerMethodField("get_end_date")

    dns = DomainServerConnectionSerializer(
        source="domainserverconnection_set",
        many=True,
        exclude=["id", "project", "static_server", "transient_server"],
    )

    extra_fields = ExtraFieldsSerField(StaticServer._meta.label, source="server.extra_fields")

    class Meta:
        model = ServerHistory
        exclude = [
            "server",
            "activity_type",
            "server_role",
        ]

    def get_start_date(self, obj):
        return dateformat.format(obj.start_date, settings.DATE_FORMAT)

    def get_end_date(self, obj):
        return dateformat.format(obj.end_date, settings.DATE_FORMAT)

    def get_server_address(self, obj):
        return obj.server.ip_address

    def get_server_provider(self, obj):
        return obj.server.server_provider.server_provider

    def get_server_name(self, obj):
        return obj.server.name


class TransientServerSerializer(CustomModelSerializer):
    """Serialize :model:`shepherd:TransientServer` entries."""

    activity = serializers.CharField(source="activity_type")
    role = serializers.CharField(source="server_role")
    provider = serializers.CharField(source="server_provider")

    dns = DomainServerConnectionSerializer(
        source="domainserverconnection_set",
        many=True,
        exclude=["id", "project", "static_server", "transient_server"],
    )

    class Meta:
        model = TransientServer
        exclude = [
            "server_provider",
            "server_role",
            "activity_type",
        ]


class ProjectContactSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectContact` entries."""

    timezone = TimeZoneSerializerField()

    class Meta:
        model = ProjectContact
        fields = "__all__"


class ProjectSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`rolodex:Project` entries."""

    name = SerializerMethodField("get_name")
    type = serializers.CharField(source="project_type")
    start_date = SerializerMethodField("get_start_date")
    start_month = SerializerMethodField("get_start_month")
    start_day = SerializerMethodField("get_start_day")
    start_year = SerializerMethodField("get_start_year")
    end_date = SerializerMethodField("get_end_date")
    end_month = SerializerMethodField("get_end_month")
    end_day = SerializerMethodField("get_end_day")
    end_year = SerializerMethodField("get_end_year")

    timezone = TimeZoneSerializerField()

    notes = ProjectNoteSerializer(source="projectnote_set", many=True, exclude=["id", "project"])

    tags = TagListSerializerField()
    extra_fields = ExtraFieldsSerField(Project._meta.label)

    class Meta:
        model = Project
        exclude = [
            "project_type",
        ]

    def get_name(self, obj):
        return str(obj)

    def get_start_date(self, obj):
        return dateformat.format(obj.start_date, settings.DATE_FORMAT)

    def get_end_date(self, obj):
        return dateformat.format(obj.end_date, settings.DATE_FORMAT)

    def get_start_month(self, obj):
        return dateformat.format(obj.start_date, "E")

    def get_start_day(self, obj):
        return obj.start_date.day

    def get_start_year(self, obj):
        return obj.start_date.year

    def get_end_month(self, obj):
        return dateformat.format(obj.end_date, "E")

    def get_end_day(self, obj):
        return obj.end_date.day

    def get_end_year(self, obj):
        return obj.end_date.year

    def to_representation(self, instance):
        data = super().to_representation(instance)
        if isinstance(data.get("data_artifacts"), dict):
            data["data_artifacts"] = normalize_nexpose_artifacts_map(data["data_artifacts"])
        raw_responses = instance.data_responses or {}
        workbook_data = instance.workbook_data or {}
        data["data_responses"] = self._format_data_responses(raw_responses, workbook_data)
        risk_rich_text_map = RiskScoreRangeMapping.get_risk_rich_text_map()
        self._apply_project_risk_rich_text(data.get("risks"), risk_rich_text_map)
        self._apply_workbook_risk_rich_text(data.get("workbook_data"), risk_rich_text_map)
        return data

    @staticmethod
    def _format_data_responses(raw_responses, workbook_data):
        if not isinstance(raw_responses, dict):
            return raw_responses or {}

        source: Dict[str, Any] = dict(raw_responses)
        result: Dict[str, Any] = {}

        def _is_empty(value: Any) -> bool:
            if value in (None, "", [], (), {}):
                return True
            return False

        def _extract_simple_section(section_key: str, keys: Any) -> Dict[str, Any]:
            section_values: Dict[str, Any] = {}
            raw_section = source.pop(section_key, None)
            if isinstance(raw_section, dict):
                section_values.update(raw_section)
            for key in keys:
                if key not in source:
                    continue
                value = source.pop(key)
                if not _is_empty(value):
                    section_values[key] = value
            return section_values

        general_section = _extract_simple_section("general", GENERAL_RESPONSE_KEYS)
        scope_count = source.pop("scope_count", None)
        scope_string = source.pop("scope_string", None)
        if scope_count is not None:
            general_section["scope_count"] = scope_count
        if scope_string not in (None, ""):
            general_section["scope_string"] = scope_string
        if general_section:
            result["general"] = ProjectSerializer._strip_internal_metadata(general_section)

        intelligence_section = _extract_simple_section("intelligence", INTELLIGENCE_RESPONSE_KEYS)
        if intelligence_section:
            result["intelligence"] = ProjectSerializer._strip_internal_metadata(intelligence_section)

        iot_section = _extract_simple_section("iot_iomt", set())
        iot_section.setdefault("iot_testing_confirm", "no")
        iot_confirm_raw = source.pop("iot_testing_confirm", None)
        if isinstance(iot_confirm_raw, str):
            normalized_confirm = iot_confirm_raw.strip().lower()
            if normalized_confirm == "yes":
                iot_section["iot_testing_confirm"] = "yes"
            elif normalized_confirm == "no":
                iot_section["iot_testing_confirm"] = "no"
            elif normalized_confirm:
                iot_section["iot_testing_confirm"] = iot_confirm_raw
        elif isinstance(iot_confirm_raw, bool):
            iot_section["iot_testing_confirm"] = "yes" if iot_confirm_raw else "no"
        elif iot_confirm_raw is not None:
            iot_section["iot_testing_confirm"] = iot_confirm_raw
        if iot_section:
            result["iot_iomt"] = ProjectSerializer._strip_internal_metadata(iot_section)

        overall_risk_section = _extract_simple_section("overall_risk", set())
        major_issues = source.pop("overall_risk_major_issues", None)
        if major_issues:
            overall_risk_section["major_issues"] = major_issues
        if overall_risk_section:
            result["overall_risk"] = ProjectSerializer._strip_internal_metadata(overall_risk_section)

        ad_entries = ProjectSerializer._collect_ad_responses(source, workbook_data)
        if ad_entries:
            result["ad"] = ProjectSerializer._strip_internal_metadata(ad_entries)
        source.pop("ad", None)

        password_entries = ProjectSerializer._collect_password_responses(source, workbook_data)
        if password_entries:
            result["password"] = ProjectSerializer._strip_internal_metadata(password_entries)
        source.pop("password", None)

        endpoint_entries = ProjectSerializer._collect_endpoint_responses(source, workbook_data)
        if endpoint_entries:
            result["endpoint"] = ProjectSerializer._strip_internal_metadata(endpoint_entries)
        source.pop("endpoint", None)

        firewall_entries = ProjectSerializer._collect_firewall_responses(source, workbook_data)
        if firewall_entries:
            result["firewall"] = ProjectSerializer._strip_internal_metadata(firewall_entries)
        source.pop("firewall", None)

        dns_entries = ProjectSerializer._collect_dns_responses(source, workbook_data)
        if dns_entries:
            result["dns"] = ProjectSerializer._strip_internal_metadata(dns_entries)
        source.pop("dns", None)

        wireless_entries = ProjectSerializer._collect_wireless_responses(source)
        if wireless_entries:
            result["wireless"] = ProjectSerializer._strip_internal_metadata(wireless_entries)
        source.pop("wireless", None)

        legacy_prefixes = ("ad_", "password_", "endpoint_", "wireless_")
        keys_to_remove = [
            key
            for key in list(source.keys())
            if isinstance(key, str)
            and (
                any(key.startswith(prefix) for prefix in legacy_prefixes)
                or (key.startswith("firewall_") and key.endswith("_type"))
            )
        ]
        for legacy_key in keys_to_remove:
            source.pop(legacy_key, None)

        for key, value in source.items():
            if key in result:
                continue
            result[key] = ProjectSerializer._strip_internal_metadata(value)

        intelligence_defaults = {key: None for key in INTELLIGENCE_RESPONSE_KEYS}
        intelligence_section = result.get("intelligence")
        if isinstance(intelligence_section, dict):
            for key, default in intelligence_defaults.items():
                intelligence_section.setdefault(key, default)
        else:
            result["intelligence"] = dict(intelligence_defaults)

        for key in ("general", "iot_iomt", "overall_risk", "dns", "wireless"):
            section_value = result.get(key)
            if not isinstance(section_value, dict):
                result[key] = {}

        ad_section = result.get("ad")
        if not isinstance(ad_section, dict):
            ad_section = {"entries": []}
            result["ad"] = ad_section
        else:
            ad_section.setdefault("entries", [])

        password_section = result.get("password")
        if not isinstance(password_section, dict):
            password_section = {"entries": [], "bad_pass_count": 0, "total_cracked": 0}
            result["password"] = password_section
        else:
            password_section.setdefault("entries", [])
            password_section.setdefault("bad_pass_count", 0)
            password_section.setdefault("total_cracked", 0)

        endpoint_section = result.get("endpoint")
        if not isinstance(endpoint_section, dict):
            endpoint_section = {"entries": []}
            result["endpoint"] = endpoint_section
        else:
            endpoint_section.setdefault("entries", [])

        firewall_section = result.get("firewall")
        if not isinstance(firewall_section, dict):
            firewall_section = {"entries": []}
            result["firewall"] = firewall_section
        else:
            firewall_section.setdefault("entries", [])

        return result

    @staticmethod
    def _strip_internal_metadata(value: Any) -> Any:
        if isinstance(value, dict):
            cleaned: Dict[str, Any] = {}
            for key, inner in value.items():
                if key == "_slug":
                    continue
                cleaned[key] = ProjectSerializer._strip_internal_metadata(inner)
            return cleaned
        if isinstance(value, list):
            cleaned_list = [ProjectSerializer._strip_internal_metadata(item) for item in value]
            return [item for item in cleaned_list if item not in (None, {})]
        return value

    @staticmethod
    def _risk_rich_text(value: Any, risk_rich_text_map: Dict[str, str]) -> Optional[str]:
        if value in (None, ""):
            return None
        normalized = str(value).strip()
        if not normalized:
            return None
        return risk_rich_text_map.get(normalized, normalized)

    @classmethod
    def _apply_project_risk_rich_text(
        cls, risks: Any, risk_rich_text_map: Dict[str, str]
    ) -> None:
        if not isinstance(risks, dict):
            return
        for key, value in list(risks.items()):
            rich_text_value = cls._risk_rich_text(value, risk_rich_text_map)
            if rich_text_value is not None:
                risks[f"{key}_rt"] = rich_text_value

    @classmethod
    def _apply_workbook_risk_rich_text(
        cls, workbook_data: Any, risk_rich_text_map: Dict[str, str]
    ) -> None:
        if not isinstance(workbook_data, dict):
            return

        report_card = workbook_data.get("report_card")
        if isinstance(report_card, dict):
            for key, value in list(report_card.items()):
                rich_text_value = cls._risk_rich_text(value, risk_rich_text_map)
                if rich_text_value is not None:
                    report_card[f"{key}_rt"] = rich_text_value

        grades = workbook_data.get("external_internal_grades")
        if isinstance(grades, dict):
            for category_data in grades.values():
                if not isinstance(category_data, dict):
                    continue

                grade_value = category_data.get("grade")
                rich_text_grade = cls._risk_rich_text(grade_value, risk_rich_text_map)
                if rich_text_grade is not None:
                    category_data["grade_rt"] = rich_text_grade

                for subkey, subvalue in category_data.items():
                    if not isinstance(subvalue, dict):
                        continue
                    risk_value = subvalue.get("risk")
                    rich_text_risk = cls._risk_rich_text(risk_value, risk_rich_text_map)
                    if rich_text_risk is not None:
                        subvalue["risk_rt"] = rich_text_risk

    @staticmethod
    def _collect_firewall_responses(raw_responses, workbook_data):
        firewall_data = (workbook_data or {}).get("firewall", {})
        devices = firewall_data.get("devices", []) if isinstance(firewall_data, dict) else []

        existing_section = raw_responses.get("firewall")
        section: Dict[str, Any] = {}
        if isinstance(existing_section, dict):
            section.update(existing_section)
        elif isinstance(existing_section, list):
            section["entries"] = list(existing_section)

        slug_map = {}
        if isinstance(devices, list):
            for index, record in enumerate(devices, start=1):
                if isinstance(record, dict):
                    device_name = (
                        record.get("name")
                        or record.get("device")
                        or record.get("hostname")
                    )
                else:
                    device_name = record
                display_name = str(device_name).strip() if device_name else ""
                if not display_name:
                    display_name = f"Device {index}"
                base_slug = ProjectSerializer._build_slug("firewall", display_name)
                candidates = [base_slug] if base_slug else []
                fallback_slug = f"firewall_device_{index}"
                candidates.append(fallback_slug)
                for candidate in candidates:
                    if not candidate:
                        continue
                    slug_map[candidate] = display_name
                    slug_map[candidate.replace("-", "")] = display_name

        entries = {}
        order = []
        for key, value in raw_responses.items():
            if not key.startswith("firewall_") or not key.endswith("_type"):
                continue
            base_slug = key[: -len("_type")]
            device_name = slug_map.get(base_slug) or slug_map.get(base_slug.replace("-", ""))
            if not device_name:
                slug_fragment = base_slug[len("firewall_") :]
                fallback_name = slug_fragment.replace("_", " ").replace("-", " ").strip()
                device_name = fallback_name.title() if fallback_name else "Firewall Device"
            entry = entries.setdefault(device_name, {"name": device_name})
            entry["type"] = value
            if device_name not in order:
                order.append(device_name)

        if entries:
            section["entries"] = [entries[name] for name in order if len(entries[name]) > 1]

        workbook_firewall_details = build_workbook_firewall_response(workbook_data)
        for key, value in workbook_firewall_details.items():
            if key not in section or not section.get(key):
                section[key] = value

        if not section.get("entries"):
            section.pop("entries", None)

        return section

    @staticmethod
    def _collect_dns_responses(raw_responses, workbook_data):
        existing_section = raw_responses.get("dns")
        section: Dict[str, Any] = {}
        if isinstance(existing_section, dict):
            section.update(existing_section)
        elif isinstance(existing_section, list):
            section["entries"] = list(existing_section)

        workbook_dns_details = build_workbook_dns_response(workbook_data)
        for key, value in workbook_dns_details.items():
            if key not in section or not section.get(key):
                section[key] = value

        if not section:
            return {}

        entries = section.get("entries")
        domain_soa_fields: Dict[str, List[str]] = {}
        unique_soa_fields: List[str] = []
        if isinstance(entries, list):
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
                domain_entry = domain_soa_fields.setdefault(domain_text, [])
                seen_fields = set(domain_entry)
                for field in fields:
                    if field is None:
                        continue
                    text = str(field).strip()
                    if not text or text in seen_fields:
                        continue
                    seen_fields.add(text)
                    domain_entry.append(text)
                    if text not in unique_soa_fields:
                        unique_soa_fields.append(text)

        if isinstance(entries, list):
            if unique_soa_fields:
                section["unique_soa_fields"] = unique_soa_fields
            else:
                section.pop("unique_soa_fields", None)

            if domain_soa_fields:
                cap_map = load_dns_soa_cap_map()
                section["soa_field_cap_map"] = {
                    domain: {
                        field: cap_map.get(field, "")
                        for field in fields
                    }
                    for domain, fields in domain_soa_fields.items()
                }
            else:
                section.pop("soa_field_cap_map", None)
        else:
            section.pop("unique_soa_fields", None)
            section.pop("soa_field_cap_map", None)

        if not entries:
            section.pop("entries", None)

        return section

    @staticmethod
    def _collect_wireless_responses(raw_responses):
        entries = {}
        existing_group = raw_responses.get("wireless")
        if isinstance(existing_group, dict):
            entries.update(existing_group)

        prefix = "wireless_"
        for key, value in raw_responses.items():
            if not isinstance(key, str) or not key.startswith(prefix):
                continue
            entries[key[len(prefix) :]] = value

        return entries

    @staticmethod
    def _collect_ad_responses(raw_responses, workbook_data):
        ad_data = (workbook_data or {}).get("ad", {})
        domains = ad_data.get("domains", []) if isinstance(ad_data, dict) else []
        domain_entries = {}
        domain_order = []
        domain_details = {}
        legacy_domains: List[str] = []
        workbook_response = build_workbook_ad_response(workbook_data)

        slug_map = {}
        total_field_map = {
            "total_da_count": "domain_admins",
            "total_ea_count": "ent_admins",
            "total_ep_count": "exp_passwords",
            "total_ne_count": "passwords_never_exp",
            "total_ia_count": "inactive_accounts",
            "total_ga_count": "generic_accounts",
            "total_gl_count": "generic_logins",
            "total_op_count": "old_passwords",
        }
        totals = {key: 0 for key in total_field_map}
        domain_data_found = False

        def _coerce_int(value: Any) -> Optional[int]:
            if value in (None, ""):
                return None
            if isinstance(value, bool):
                return None
            if isinstance(value, int):
                return value
            if isinstance(value, float):
                return int(value)
            if isinstance(value, str):
                text = value.strip()
                if not text:
                    return None
                text = text.replace(",", "")
                try:
                    return int(text)
                except ValueError:
                    return None
            return None

        for record in domains:
            if not isinstance(record, dict):
                continue
            domain_name = record.get("domain") or record.get("name")
            if not domain_name:
                continue
            domain_data_found = True
            domain_text = str(domain_name)
            slug = ProjectSerializer._build_slug("ad", domain_text)
            if slug:
                slug_map[slug] = domain_text
                slug_map[slug.replace("-", "")] = domain_text
            domain_details[domain_text] = record
            domain_entries[domain_text] = {"domain": domain_text}
            domain_order.append(domain_text)

            functionality_value = record.get("functionality_level")
            functionality_text = str(functionality_value).strip() if functionality_value is not None else ""
            if functionality_text and any(version in functionality_text for version in ("2000", "2003")):
                if domain_text not in legacy_domains:
                    legacy_domains.append(domain_text)

            for total_key, field in total_field_map.items():
                coerced = _coerce_int(record.get(field))
                if coerced is not None:
                    totals[total_key] += coerced

        ad_metrics = [metric for metric, _ in AD_DOMAIN_METRICS]

        def assign(domain_key, metric, value):
            if value is None:
                return
            entry = domain_entries.setdefault(domain_key, {"domain": domain_key})
            if domain_key not in domain_order:
                domain_order.append(domain_key)
            entry[metric] = value

        for slug, domain_key in slug_map.items():
            for metric in ad_metrics:
                value = ProjectSerializer._consume_metric(raw_responses, slug, metric)
                if value is not None:
                    assign(domain_key, metric, value)

        existing_ad_entries = raw_responses.get("ad")
        existing_items = []
        if isinstance(existing_ad_entries, list):
            existing_items = existing_ad_entries
        elif isinstance(existing_ad_entries, dict):
            entries_value = existing_ad_entries.get("entries")
            if isinstance(entries_value, list):
                existing_items = entries_value

        for item in existing_items:
            if not isinstance(item, dict):
                continue
            domain = item.get("domain") or item.get("name")
            if not domain:
                continue
            domain = str(domain)
            entry = domain_entries.setdefault(domain, {"domain": domain})
            if domain not in domain_order:
                domain_order.append(domain)
            for metric in ad_metrics:
                value = item.get(metric)
                if value is not None:
                    entry[metric] = value

        for key, value in raw_responses.items():
            if not key.startswith("ad_"):
                continue
            for metric in ad_metrics:
                suffix = f"_{metric}"
                if key.endswith(suffix):
                    domain_slug = key[len("ad_") : -len(suffix)]
                    domain_key = slug_map.get(f"ad_{domain_slug}") or slug_map.get(f"ad_{domain_slug}".replace("-", ""))
                    if not domain_key:
                        domain_key = domain_slug.replace("-", ".")
                    assign(domain_key, metric, value)
                    break

        summary = dict(workbook_response) if isinstance(workbook_response, dict) else {}

        ordered = [domain_entries[name] for name in domain_order if len(domain_entries[name]) > 1]
        if ordered:
            domains_str_parts = []
            count_fields = {
                "enabled_count_str": "enabled_accounts",
                "da_count_str": "domain_admins",
                "ea_count_str": "ent_admins",
                "ep_count_str": "exp_passwords",
                "ne_count_str": "passwords_never_exp",
                "ia_count_str": "inactive_accounts",
                "ga_count_str": "generic_accounts",
                "gl_count_str": "generic_logins",
            }
            count_parts = {field: [] for field in count_fields}

            risk_fields = {
                "da_risk_string": "domain_admins",
                "ea_risk_string": "enterprise_admins",
                "ep_risk_string": "expired_passwords",
                "ne_risk_string": "passwords_never_expire",
                "ia_risk_string": "inactive_accounts",
                "ga_risk_string": "generic_accounts",
                "gl_risk_string": "generic_logins",
            }
            risk_parts = {field: [] for field in risk_fields}

            def _format_count(value):
                if value in (None, ""):
                    return "0"
                return str(value)

            def _format_risk_value(value):
                if value is None:
                    return ""
                text = str(value).strip()
                return text.capitalize() if text else ""

            def _format_domains(values):
                entries = [value for value in values if value]
                if not entries:
                    return ""
                return "/".join(f"'{entry}'" for entry in entries)

            for entry in ordered:
                domain = entry.get("domain", "")
                domains_str_parts.append(domain)
                details = domain_details.get(domain, {})
                if not isinstance(details, dict):
                    details = {}

                for output_field, workbook_key in count_fields.items():
                    count_parts[output_field].append(_format_count(details.get(workbook_key)))

                for output_field, metric in risk_fields.items():
                    risk_parts[output_field].append(_format_risk_value(entry.get(metric)))

            summary.update(
                {
                    "entries": ordered,
                    "domains_str": _format_domains(domains_str_parts),
                }
            )

            for field, parts in count_parts.items():
                summary[field] = "/".join(parts)

            for field, parts in risk_parts.items():
                summary[field] = "/".join(parts)

            if legacy_domains:
                summary["old_domains_str"] = _format_domains(legacy_domains)
            else:
                summary.setdefault("old_domains_str", None)

        risk_contrib = build_ad_risk_contrib(workbook_data, ordered)
        if domain_data_found:
            for field, value in totals.items():
                summary[field] = value

        if summary or risk_contrib:
            summary["risk_contrib"] = risk_contrib

        return summary if summary else {}

    @staticmethod
    def _collect_password_responses(raw_responses, workbook_data):
        (
            workbook_summary,
            workbook_domain_values,
            workbook_domains,
        ) = build_workbook_password_response(workbook_data)
        bad_pass_count = workbook_summary.get("bad_pass_count", 0)
        total_cracked = workbook_summary.get("total_cracked", 0)

        entries = {}
        domain_order = []
        slug_map = {}

        extra_fields: Dict[str, Any] = {}
        existing_password_section = raw_responses.get("password")
        candidate_sections = []
        if isinstance(existing_password_section, dict):
            candidate_sections.append(existing_password_section)
        candidate_sections.append(raw_responses)
        for section in candidate_sections:
            if not isinstance(section, dict):
                continue
            for extra_key in (
                "password_additional_controls",
                "password_enforce_mfa_all_accounts",
                "hashes_obtained",
            ):
                value = section.get(extra_key)
                if value not in (None, ""):
                    extra_fields[extra_key] = value
                section.pop(extra_key, None)

        cap_fields, cap_context = summarize_password_cap_details(workbook_domain_values)
        password_cap_templates = load_password_cap_map() if cap_fields else {}

        def _inject_cap_details(summary_dict: Dict[str, Any]) -> Dict[str, Any]:
            if cap_fields:
                summary_dict["policy_cap_fields"] = list(cap_fields)
                if cap_context:
                    summary_dict["policy_cap_context"] = cap_context
                    domain_cap_map = build_password_cap_display_map(
                        cap_context, password_cap_templates
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

        for domain_name in workbook_domain_values.keys():
            entry = entries.setdefault(domain_name, {"domain": domain_name})

            slug = ProjectSerializer._build_slug("password", domain_name)
            if slug:
                slug_map[slug] = domain_name
                slug_map[slug.replace("-", "")] = domain_name
                value = ProjectSerializer._consume_metric(raw_responses, slug, "risk")
                if value is not None:
                    entry["risk"] = value

        for domain_name in workbook_domains:
            if domain_name not in domain_order:
                domain_order.append(domain_name)

        existing_password_entries = raw_responses.get("password")
        existing_items = []
        if isinstance(existing_password_entries, list):
            existing_items = existing_password_entries
        elif isinstance(existing_password_entries, dict):
            entries_value = existing_password_entries.get("entries")
            if isinstance(entries_value, list):
                existing_items = entries_value

        for item in existing_items:
            if not isinstance(item, dict):
                continue
            domain = item.get("domain") or item.get("name")
            if not domain:
                continue
            domain = str(domain)
            entry = entries.setdefault(domain, {"domain": domain})
            if domain not in domain_order:
                domain_order.append(domain)
            value = item.get("risk")
            if value is not None:
                entry["risk"] = value

        for key, value in raw_responses.items():
            if not isinstance(key, str) or not key.startswith("password_") or not key.endswith("_risk"):
                continue
            domain_slug = key[len("password_") : -len("_risk")]
            slug_key = f"password_{domain_slug}"
            domain_name = (
                slug_map.get(slug_key)
                or slug_map.get(slug_key.replace("-", ""))
                or domain_slug.replace("-", ".")
            )
            entry = entries.setdefault(domain_name, {"domain": domain_name})
            if domain_name not in domain_order:
                domain_order.append(domain_name)
            entry["risk"] = value

        populated_domains = [name for name in domain_order if len(entries[name]) > 1]
        if not populated_domains:
            summary = {"bad_pass_count": bad_pass_count, "total_cracked": total_cracked}
            summary.update(extra_fields)
            return _inject_cap_details(summary)

        summary_domains = []
        for domain in workbook_domains:
            if domain in entries and len(entries[domain]) > 1 and domain not in summary_domains:
                summary_domains.append(domain)
        for domain in populated_domains:
            if domain not in summary_domains:
                summary_domains.append(domain)

        if not summary_domains:
            return _inject_cap_details(
                {"bad_pass_count": bad_pass_count, "total_cracked": total_cracked}
            )

        def _format_risk(value):
            if value is None:
                return ""
            text = str(value).strip()
            return text.capitalize() if text else ""

        def _format_plain(values):
            items = [value for value in values if value not in (None, "")]
            if not items:
                return ""
            if len(items) == 1:
                return items[0]
            if len(items) == 2:
                return f"{items[0]} and {items[1]}"
            return ", ".join(items[:-1]) + f" and {items[-1]}"

        def _format_sample(values):
            entries_list = [value for value in values if value]
            if not entries_list:
                return ""
            quoted = [f"'{value}'" for value in entries_list]
            if len(quoted) == 1:
                return quoted[0]
            if len(quoted) == 2:
                return f"{quoted[0]} and {quoted[1]}"
            return ", ".join(quoted[:-1]) + f" and {quoted[-1]}"

        def _format_domains(values):
            entries = [value for value in values if value]
            if not entries:
                return ""
            return "/".join(f"'{entry}'" for entry in entries)

        domains_str_parts = []
        cracked_count_parts = []
        cracked_risk_parts = []
        enabled_count_parts = []
        admin_cracked_parts = []
        lanman_domains = []
        no_fgpp_domains = []
        ordered_entries = []

        for domain in summary_domains:
            entry = entries.get(domain)
            if not entry:
                continue
            ordered_entries.append(entry)
            domains_str_parts.append(domain)

            domain_values = workbook_domain_values.get(domain, {})
            cracked_value = domain_values.get("passwords_cracked", "0")
            enabled_value = domain_values.get("enabled_accounts", "0")
            admin_cracked_value = domain_values.get("admin_cracked", "0")

            entry["bad_pass"] = bool(domain_values.get("bad_pass"))

            policy_fields = domain_values.get("policy_cap_fields")
            if isinstance(policy_fields, list) and policy_fields:
                entry["bad_policy_fields"] = list(policy_fields)
            fgpp_fields = domain_values.get("fgpp_cap_fields")
            if isinstance(fgpp_fields, dict) and fgpp_fields:
                entry["fgpp_bad_fields"] = {
                    name: list(fields)
                    for name, fields in fgpp_fields.items()
                    if isinstance(fields, list) and fields
                }
            policy_values = domain_values.get("policy_cap_values")
            if isinstance(policy_values, dict) and policy_values:
                entry["policy_cap_values"] = dict(policy_values)
            fgpp_values = domain_values.get("fgpp_cap_values")
            if isinstance(fgpp_values, dict) and fgpp_values:
                entry["fgpp_cap_values"] = {
                    name: dict(values)
                    for name, values in fgpp_values.items()
                    if isinstance(values, dict) and values
                }

            cracked_count_parts.append(cracked_value or "0")
            enabled_count_parts.append(enabled_value or "0")
            admin_cracked_parts.append(admin_cracked_value or "0")

            if domain_values.get("lanman"):
                lanman_domains.append(domain)
            if domain_values.get("no_fgpp"):
                no_fgpp_domains.append(domain)

            cracked_risk_parts.append(_format_risk(entry.get("risk")))

        if not ordered_entries:
            return {"bad_pass_count": bad_pass_count, "total_cracked": total_cracked}

        summary = {
            "entries": ordered_entries,
            "domains_str": _format_domains(domains_str_parts),
            "cracked_count_str": "/".join(cracked_count_parts),
            "cracked_risk_string": "/".join(cracked_risk_parts),
            "cracked_finding_string": _format_plain(cracked_count_parts),
            "enabled_count_string": _format_plain(enabled_count_parts),
            "admin_cracked_string": _format_plain(admin_cracked_parts),
            "admin_cracked_doms": _format_sample(domains_str_parts),
            "lanman_list_string": _format_sample(lanman_domains),
            "no_fgpp_string": _format_sample(no_fgpp_domains),
            "bad_pass_count": bad_pass_count,
            "total_cracked": total_cracked,
        }

        if not summary.get("cracked_count_str") and workbook_summary.get("cracked_count_str"):
            summary["cracked_count_str"] = workbook_summary["cracked_count_str"]

        summary.update(extra_fields)
        return _inject_cap_details(summary)

    @staticmethod
    def _collect_endpoint_responses(raw_responses, workbook_data):
        endpoint_data = (workbook_data or {}).get("endpoint", {})
        domains = endpoint_data.get("domains", []) if isinstance(endpoint_data, dict) else []
        entries = {}
        order = []
        endpoint_metrics = ("av_gap", "open_wifi")
        slug_map = {}
        domain_details = {}

        existing_summary = raw_responses.get("endpoint")
        if isinstance(existing_summary, dict):
            entry_list = existing_summary.get("entries") if isinstance(existing_summary, dict) else None
            if isinstance(entry_list, list) and entry_list:
                return existing_summary

        for record in domains:
            if not isinstance(record, dict):
                continue
            domain_name = record.get("domain") or record.get("name")
            if not domain_name:
                continue
            domain_name = str(domain_name)
            domain_details[domain_name] = record
            slug = ProjectSerializer._build_slug("endpoint", domain_name)
            if slug:
                slug_map[slug] = domain_name
                slug_map[slug.replace("-", "")] = domain_name
            for metric in endpoint_metrics:
                value = ProjectSerializer._consume_metric(raw_responses, slug, metric)
                if value is not None:
                    entry = entries.setdefault(domain_name, {"domain": domain_name})
                    entry[metric] = value
                    if domain_name not in order:
                        order.append(domain_name)

        existing_endpoint_entries = raw_responses.get("endpoint")
        if isinstance(existing_endpoint_entries, list):
            for item in existing_endpoint_entries:
                if not isinstance(item, dict):
                    continue
                domain = item.get("domain") or item.get("name")
                if not domain:
                    continue
                domain = str(domain)
                entry = entries.setdefault(domain, {"domain": domain})
                for metric in endpoint_metrics:
                    value = item.get(metric)
                    if value is not None:
                        entry[metric] = value
                if domain not in order:
                    order.append(domain)

        for key, value in raw_responses.items():
            if not key.startswith("endpoint_"):
                continue
            for metric in endpoint_metrics:
                suffix = f"_{metric}"
                if key.endswith(suffix):
                    domain_slug = key[len("endpoint_") : -len(suffix)]
                    slug_key = f"endpoint_{domain_slug}"
                    domain_name = (
                        slug_map.get(slug_key)
                        or slug_map.get(slug_key.replace("-", ""))
                        or domain_slug.replace("-", ".")
                    )
                    entry = entries.setdefault(domain_name, {"domain": domain_name})
                    entry[metric] = value
                    if domain_name not in order:
                        order.append(domain_name)
                    break

        ordered_entries = [entries[name] for name in order if len(entries[name]) > 1]
        if not ordered_entries:
            return {}

        domains_str_parts = []
        ood_count_parts = []
        wifi_count_parts = []
        ood_risk_parts = []
        wifi_risk_parts = []

        def _format_risk_value(value):
            if value is None:
                return ""
            text = str(value).strip()
            return text.capitalize() if text else ""

        for entry in ordered_entries:
            domain = entry.get("domain", "")
            domains_str_parts.append(domain)
            details = domain_details.get(domain, {})

            systems_ood = details.get("systems_ood") if isinstance(details, dict) else None
            ood_count_parts.append("0" if systems_ood in (None, "") else str(systems_ood))

            open_wifi_count = details.get("open_wifi") if isinstance(details, dict) else None
            wifi_count_parts.append("0" if open_wifi_count in (None, "") else str(open_wifi_count))

            ood_risk_parts.append(_format_risk_value(entry.get("av_gap")))
            wifi_risk_parts.append(_format_risk_value(entry.get("open_wifi")))

        return {
            "entries": ordered_entries,
            "domains_str": "/".join(domains_str_parts),
            "ood_count_str": "/".join(ood_count_parts),
            "wifi_count_str": "/".join(wifi_count_parts),
            "ood_risk_string": "/".join(ood_risk_parts),
            "wifi_risk_string": "/".join(wifi_risk_parts),
        }

    @staticmethod
    def _build_slug(prefix, value):
        if not value:
            return ""
        text = slugify(str(value))
        if not text:
            return ""
        return f"{prefix}_{text}"

    @staticmethod
    def _consume_metric(raw_responses, slug, metric):
        if not slug:
            return None
        candidates = [f"{slug}_{metric}"]
        if "-" in slug:
            candidates.append(f"{slug.replace('-', '')}_{metric}")
        for candidate in candidates:
            if candidate in raw_responses:
                return raw_responses[candidate]
        return None


class ProjectInfrastructureSerializer(CustomModelSerializer):
    """
    Serialize infrastructure information for an individual :model:`rolodex.Project` that
    includes all related :model:`shepherd.ServerHistory`, :model:`shepherd.History`, and
    :model:`shepherd.TransientServer` entries.
    """

    domains = DomainHistorySerializer(
        source="history_set",
        many=True,
        exclude=["id", "project", "operator", "client"],
    )
    cloud = TransientServerSerializer(source="transientserver_set", many=True, exclude=["id", "project", "operator"])
    servers = ServerHistorySerializer(
        source="serverhistory_set",
        many=True,
        exclude=["id", "project", "operator", "client"],
    )

    class Meta:
        model = Project
        fields = [
            "domains",
            "servers",
            "cloud",
        ]
        depth = 1


class DeconflictionSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:Deconfliction` entries."""

    status = StringRelatedField()

    class Meta:
        model = Deconfliction
        fields = "__all__"


class WhiteCardSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:WhiteCard` entries."""

    class Meta:
        model = WhiteCard
        fields = "__all__"


class OplogEntrySerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`oplog.OplogEntry` entries."""

    tags = TagListSerializerField()
    extra_fields = ExtraFieldsSerField(OplogEntry._meta.label)

    class Meta:
        model = OplogEntry
        fields = "__all__"


class OplogSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`oplog.Oplog` entries."""

    entries = OplogEntrySerializer(
        many=True,
        exclude=["id", "oplog_id"],
    )

    class Meta:
        model = Oplog
        fields = "__all__"


class FullProjectSerializer(serializers.Serializer):
    """Serialize :model:`rolodex:Project` and related entries."""

    # IF YOU EDIT THIS CLASS:
    # Also edit `linting_utils.py` and the `generate_lint_data` method in `reportwriter/project/base.py`.

    project = ProjectSerializer(source="*")
    client = ClientSerializer()
    contacts = ProjectContactSerializer(source="projectcontact_set", many=True, exclude=["id", "project"])
    team = ProjectAssignmentSerializer(source="projectassignment_set", many=True, exclude=["id", "project"])
    objectives = ProjectObjectiveSerializer(source="projectobjective_set", many=True, exclude=["id", "project"])
    targets = ProjectTargetSerializer(source="projecttarget_set", many=True, exclude=["id", "project"])
    scope = ProjectScopeSerializer(source="projectscope_set", many=True, exclude=["id", "project"])
    deconflictions = DeconflictionSerializer(source="deconfliction_set", many=True, exclude=["id", "project"])
    whitecards = WhiteCardSerializer(source="whitecard_set", many=True, exclude=["id", "project"])
    infrastructure = ProjectInfrastructureSerializer(source="*")
    logs = OplogSerializer(source="oplog_set", many=True, exclude=["id", "mute_notifications", "project"])
    report_date = SerializerMethodField("get_report_date")
    company = SerializerMethodField("get_company_info")
    tools = SerializerMethodField("get_tools")
    recipient = SerializerMethodField("get_recipient")

    def get_report_date(self, obj):
        return dateformat.format(datetime.now(), settings.DATE_FORMAT)

    def get_company_info(self, obj):
        serializer = CompanyInfoSerializer(CompanyInformation.get_solo())
        return serializer.data

    def get_tools(self, obj):
        tools = []
        for oplog in obj.oplog_set.all():
            for entry in oplog.entries.all():
                if entry.tool and entry.tool.lower() not in tools:
                    tools.append(entry.tool.lower())
        return tools

    def get_recipient(self, obj):
        primary = None
        for contact in obj.projectcontact_set.all():
            if contact.primary:
                primary = contact
                break
        return ProjectContactSerializer(primary, exclude=["id", "project"]).data


class SeveritySerializer(CustomModelSerializer):
    """Serialize :model:`reporting.Severity` entries."""

    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")

    class Meta:
        model = Severity
        fields = ["id", "severity", "severity_color", "severity_color_rgb", "severity_color_hex", "weight", "color"]

    def get_severity_color(self, obj):
        return obj.color

    def get_severity_color_rgb(self, obj):
        return obj.color_rgb

    def get_severity_color_hex(self, obj):
        return obj.color_hex


class ReportDataSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:Project` and all related entries."""

    tags = TagListSerializerField()
    report_date = SerializerMethodField("get_report_date")
    project = ProjectSerializer(
        exclude=[
            "operator",
            "client",
        ]
    )
    client = ClientSerializer(source="project.client")
    recipient = SerializerMethodField("get_recipient")
    contacts = ProjectContactSerializer(source="project.projectcontact_set", many=True, exclude=["id", "project"])
    team = ProjectAssignmentSerializer(source="project.projectassignment_set", many=True, exclude=["id", "project"])
    objectives = ProjectObjectiveSerializer(source="project.projectobjective_set", many=True, exclude=["id", "project"])
    targets = ProjectTargetSerializer(source="project.projecttarget_set", many=True, exclude=["id", "project"])
    scope = ProjectScopeSerializer(source="project.projectscope_set", many=True, exclude=["id", "project"])
    deconflictions = DeconflictionSerializer(source="project.deconfliction_set", many=True, exclude=["id", "project"])
    whitecards = WhiteCardSerializer(source="project.whitecard_set", many=True, exclude=["id", "project"])
    infrastructure = ProjectInfrastructureSerializer(source="project")
    evidence = EvidenceSerializer(source="evidence_set", many=True, exclude=["report", "finding"])
    severities = SerializerMethodField("get_severities")
    findings = FindingLinkSerializer(
        source="reportfindinglink_set",
        many=True,
        exclude=[
            "report",
        ],
    )
    observations = ObservationLinkSerializer(
        source="reportobservationlink_set",
        many=True,
        exclude=[
            "report",
        ],
    )
    docx_template = ReportTemplateSerializer(
        exclude=[
            "upload_date",
            "last_update",
            "description",
            "protected",
            "lint_result",
            "changelog",
            "uploaded_by",
            "client",
        ]
    )
    pptx_template = ReportTemplateSerializer(
        exclude=[
            "upload_date",
            "last_update",
            "description",
            "protected",
            "lint_result",
            "changelog",
            "uploaded_by",
            "client",
        ]
    )
    logs = OplogSerializer(source="project.oplog_set", many=True, exclude=["id", "mute_notifications", "project"])
    company = SerializerMethodField("get_company_info")
    tools = SerializerMethodField("get_tools")
    extra_fields = ExtraFieldsSerField(Report._meta.label)

    class Meta:
        model = Report
        exclude = ["created_by", "creation", "last_update"]
        depth = 1

    def get_report_date(self, obj):
        return dateformat.format(datetime.now(), settings.DATE_FORMAT)

    def get_company_info(self, obj):
        serializer = CompanyInfoSerializer(CompanyInformation.get_solo())
        return serializer.data

    def get_tools(self, obj):
        tools = []
        for oplog in obj.project.oplog_set.all():
            for entry in oplog.entries.all():
                if entry.tool and entry.tool.lower() not in tools:
                    tools.append(entry.tool.lower())
        return tools

    def get_recipient(self, obj):
        primary = None
        for contact in obj.project.projectcontact_set.all():
            if contact.primary:
                primary = contact
                break
        return ProjectContactSerializer(primary, exclude=["id", "project"]).data

    def get_severities(self, obj):
        severities = Severity.objects.all()
        serializer = SeveritySerializer(severities, many=True, exclude=["id"])
        return serializer.data

    def to_representation(self, instance):
        # Get the standard JSON from ``super()``
        rep = super().to_representation(instance)

        # Calculate totals for various values
        total_findings = len(rep["findings"])
        total_objectives = len(rep["objectives"])
        total_team = len(rep["team"])
        total_targets = len(rep["targets"])

        completed_objectives = 0
        for objective in rep["objectives"]:
            if objective["complete"]:
                completed_objectives += 1

        total_scope_lines = 0
        for scope in rep["scope"]:
            total_scope_lines += scope["total"]

        finding_order = 0
        critical_findings = 0
        high_findings = 0
        medium_findings = 0
        low_findings = 0
        info_findings = 0
        for finding in rep["findings"]:
            finding["ordering"] = finding_order
            if finding["severity"].lower() == "critical":
                critical_findings += 1
            elif finding["severity"].lower() == "high":
                high_findings += 1
            elif finding["severity"].lower() == "medium":
                medium_findings += 1
            elif finding["severity"].lower() == "low":
                low_findings += 1
            elif finding["severity"].lower() == "informational":
                info_findings += 1
            finding_order += 1

        # Add a ``totals`` key to track the values
        rep["totals"] = {}
        rep["totals"]["objectives"] = total_objectives
        rep["totals"]["objectives_completed"] = completed_objectives
        rep["totals"]["findings"] = total_findings
        rep["totals"]["findings_critical"] = critical_findings
        rep["totals"]["findings_high"] = high_findings
        rep["totals"]["findings_medium"] = medium_findings
        rep["totals"]["findings_low"] = low_findings
        rep["totals"]["findings_info"] = info_findings
        rep["totals"]["scope"] = total_scope_lines
        rep["totals"]["team"] = total_team
        rep["totals"]["targets"] = total_targets

        return rep


class ExtraFieldsSpecSerializer(CustomModelSerializer):
    class Meta:
        model = ExtraFieldSpec
        exclude = ["target_model"]
