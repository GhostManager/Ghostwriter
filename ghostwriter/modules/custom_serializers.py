"""This contains customizations for `rest_framework.serializers` classes used by Ghostwriter."""

# Standard Libraries
from datetime import datetime

# Django Imports
from django.conf import settings
from django.utils import dateformat

# 3rd Party Libraries
from rest_framework import serializers
from rest_framework.serializers import (
    RelatedField,
    SerializerMethodField,
    StringRelatedField,
)

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import CompanyInformation
from ghostwriter.reporting.models import (
    Evidence,
    Finding,
    Report,
    ReportFindingLink,
    ReportTemplate,
)
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    Project,
    ProjectAssignment,
    ProjectObjective,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
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
        string_value = value.ip_address()
        return string_value


class CloudServerField(RelatedField):
    """Customize the string representation of a :model:`shepherd.TransientServer` entry."""

    def to_representation(self, value):
        return value.ip_address


class UserSerializer(CustomModelSerializer):
    """Serialize :model:`users:User` entries."""

    name = SerializerMethodField("get_name")

    class Meta:
        model = User
        fields = ["id", "name", "username", "email"]

    def get_name(self, obj):
        return obj.get_display_name()


class CompanyInfoSerializer(CustomModelSerializer):
    """Serialize :model:`commandcenter:CompanyInformation` entries."""

    name = serializers.CharField(source="company_name")
    twitter = serializers.CharField(source="company_twitter")
    email = serializers.CharField(source="company_email")

    class Meta:
        model = CompanyInformation
        exclude = ["id", "company_name", "company_twitter", "company_email"]


class EvidenceSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:Evidence` entries."""

    path = SerializerMethodField("get_path")
    url = SerializerMethodField("get_url")

    class Meta:
        model = Evidence
        exclude = [
            "document",
        ]

    def get_path(self, obj):
        return str(obj.document)

    def get_url(self, obj):
        return obj.document.url


class FindingSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:Finding` entries."""

    finding_type = StringRelatedField()
    severity = StringRelatedField()
    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")

    class Meta:
        model = Finding
        fields = "__all__"

    def get_severity_color(self, obj):
        return obj.severity.color

    def get_severity_color_rgb(self, obj):
        return obj.severity.color_rgb

    def get_severity_color_hex(self, obj):
        return obj.severity.color_hex


class FindingLinkSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:ReportFindingLink` entries."""

    assigned_to = SerializerMethodField()
    finding_type = StringRelatedField()
    severity = StringRelatedField()
    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")

    # Include a copy of the ``mitigation`` field as ``recommendation`` to match legacy JSON output
    recommendation = serializers.CharField(source="mitigation")

    evidence = EvidenceSerializer(
        source="evidence_set",
        many=True,
        exclude=[
            "finding",
            "uploaded_by",
        ],
    )

    class Meta:
        model = ReportFindingLink
        fields = "__all__"

    def get_assigned_to(self, obj):
        return obj.assigned_to.name

    def get_severity_color(self, obj):
        return obj.severity.color

    def get_severity_color_rgb(self, obj):
        return obj.severity.color_rgb

    def get_severity_color_hex(self, obj):
        return obj.severity.color_hex


class ReportTemplateSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:ReportTemplate` entries."""

    class Meta:
        model = ReportTemplate
        fields = "__all__"


class ReportSerializer(CustomModelSerializer):
    """Serialize :model:`reporting:Report` entries."""

    created_by = StringRelatedField()

    last_update = SerializerMethodField("get_creation")
    creation = SerializerMethodField("get_last_update")
    total_findings = SerializerMethodField("get_total_findings")

    findings = FindingLinkSerializer(
        source="reportfindinglink_set", many=True, exclude=["id", "report"]
    )

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

    class Meta:
        model = ClientContact
        fields = "__all__"


class ClientSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:Client` entries."""

    contacts = ClientContactSerializer(
        source="clientcontact_set",
        many=True,
        exclude=[
            "client",
        ],
    )

    class Meta:
        model = Client
        fields = "__all__"


class ProjectAssignmentSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:ProjectAssignment` entries."""

    role = StringRelatedField()

    name = SerializerMethodField("get_operator")
    email = SerializerMethodField("get_email")
    start_date = SerializerMethodField("get_start_date")
    end_date = SerializerMethodField("get_end_date")

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


class DomainSerializer(CustomModelSerializer):
    """Serialize :model:`shepherd:Domain` entries."""

    class Meta:
        model = Domain
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


class StaticServerSerializer(CustomModelSerializer):
    """Serialize :model:`shepherd.StaticServer` entries."""

    provider = serializers.CharField(source="server_provider")
    status = serializers.CharField(source="server_status")
    last_used_by = StringRelatedField()

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


class ProjectSerializer(CustomModelSerializer):
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
    cloud = TransientServerSerializer(
        source="transientserver_set", many=True, exclude=["id", "project", "operator"]
    )
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


class ReportDataSerializer(CustomModelSerializer):
    """Serialize :model:`rolodex:Project` and all related entries."""

    report_date = SerializerMethodField("get_report_date")
    project = ProjectSerializer(
        exclude=[
            "operator",
            "client",
        ]
    )
    client = ClientSerializer(source="project.client")
    team = ProjectAssignmentSerializer(
        source="project.projectassignment_set", many=True, exclude=["id", "project"]
    )
    objectives = ProjectObjectiveSerializer(
        source="project.projectobjective_set", many=True, exclude=["id", "project"]
    )
    targets = ProjectTargetSerializer(
        source="project.projecttarget_set", many=True, exclude=["id", "project"]
    )
    scope = ProjectScopeSerializer(
        source="project.projectscope_set", many=True, exclude=["id", "project"]
    )
    infrastructure = ProjectInfrastructureSerializer(source="project")
    findings = FindingLinkSerializer(
        source="reportfindinglink_set",
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
    company = SerializerMethodField("get_company_info")

    class Meta:
        model = Report
        exclude = ["created_by", "creation", "last_update"]
        depth = 1

    def get_report_date(self, obj):
        return dateformat.format(datetime.now(), settings.DATE_FORMAT)

    def get_company_info(self, obj):
        serializer = CompanyInfoSerializer(CompanyInformation.get_solo())
        return serializer.data

    def to_representation(self, instance):
        # Get the standard JSON from ``super()``
        rep = super(ReportDataSerializer, self).to_representation(instance)

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

        # Add a ``totals`` key to track the values
        rep["totals"] = {}
        rep["totals"]["objectives"] = total_objectives
        rep["totals"]["objectives_completed"] = completed_objectives
        rep["totals"]["findings"] = total_findings
        rep["totals"]["scope"] = total_scope_lines
        rep["totals"]["team"] = total_team
        rep["totals"]["targets"] = total_targets

        return rep
