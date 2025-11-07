"""This contains customizations for `rest_framework.serializers` classes used by Ghostwriter."""

# IF YOU EDIT THIS FILE: also update `linting_utils.py`

# Standard Libraries
from datetime import datetime
import zoneinfo

# Django Imports
from django.conf import settings
from django.utils import dateformat

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
    Severity,
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
                # Convert empty paragraph HTML to empty string
                elif isinstance(value, str) and value.strip() in ("<p></p>", "<p> </p>"):
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
