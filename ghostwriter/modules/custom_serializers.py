"""This contains customizations for `rest_framework.serializers` classes used by Ghostwriter."""

# Standard Libraries
from datetime import datetime

# Django Imports
from django.conf import settings
from django.utils import dateformat

# 3rd Party Libraries
import pytz
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
from ghostwriter.commandcenter.models import CompanyInformation
from ghostwriter.oplog.models import OplogEntry
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
    Deconfliction,
    Project,
    ProjectAssignment,
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
from ghostwriter.stratum.enums import FindingStatusColor, Severity
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


class UserSerializer(CustomModelSerializer):
    """Serialize :model:`users:User` entries."""

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
    twitter = serializers.CharField(source="company_twitter")
    email = serializers.CharField(source="company_email")

    class Meta:
        model = CompanyInformation
        exclude = ["id", "company_name", "company_twitter", "company_email"]


class EvidenceSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Evidence` entries."""

    path = SerializerMethodField("get_path")
    url = SerializerMethodField("get_url")
    tags = TagListSerializerField()

    class Meta:
        model = Evidence
        exclude = [
            "document",
        ]

    def get_path(self, obj):
        return str(obj.document)

    def get_url(self, obj):
        return obj.document.url


class FindingSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Finding` entries."""

    finding_type = StringRelatedField()
    severity = StringRelatedField()
    severity_color = SerializerMethodField("get_severity_color")
    severity_color_rgb = SerializerMethodField("get_severity_color_rgb")
    severity_color_hex = SerializerMethodField("get_severity_color_hex")
    tags = TagListSerializerField()

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
    tags = TagListSerializerField()

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
        if obj.assigned_to:
            return obj.assigned_to.name
        return "TBD"

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


class ReportSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`reporting:Report` entries."""

    created_by = StringRelatedField()

    last_update = SerializerMethodField("get_creation")
    creation = SerializerMethodField("get_last_update")
    total_findings = SerializerMethodField("get_total_findings")

    findings = FindingLinkSerializer(source="reportfindinglink_set", many=True, exclude=["id", "report"])

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
        tz = pytz.timezone(str(obj.operator.timezone))
        return tz.zone


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


class DomainSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`shepherd:Domain` entries."""

    tags = TagListSerializerField()

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


class StaticServerSerializer(TaggitSerializer, CustomModelSerializer):
    """Serialize :model:`shepherd.StaticServer` entries."""

    provider = serializers.CharField(source="server_provider")
    status = serializers.CharField(source="server_status")
    last_used_by = StringRelatedField()
    tags = TagListSerializerField()

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

    class Meta:
        model = OplogEntry
        fields = "__all__"


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
    team = ProjectAssignmentSerializer(source="project.projectassignment_set", many=True, exclude=["id", "project"])
    objectives = ProjectObjectiveSerializer(source="project.projectobjective_set", many=True, exclude=["id", "project"])
    targets = ProjectTargetSerializer(source="project.projecttarget_set", many=True, exclude=["id", "project"])
    scope = ProjectScopeSerializer(source="project.projectscope_set", many=True, exclude=["id", "project"])
    deconflictions = DeconflictionSerializer(source="project.deconfliction_set", many=True, exclude=["id", "project"])
    whitecards = WhiteCardSerializer(source="project.whitecard_set", many=True, exclude=["id", "project"])
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
        rep = super().to_representation(instance)

        # Filter findings that are marked as complete
        # This field is used for publishing findings to a report when they are ready
        # This field is also used to exclude findings from a report - according to netsec experience with customers
        findings = list(filter(lambda finding: finding["complete"], rep["findings"]))
        # Reassigns to make sure the findings ref in templates will be the filtered completed findings
        rep["findings"] = findings

        # Calculate totals for various values
        total_findings = len(findings)
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

        open_critical_findings = 0
        open_high_findings = 0
        open_medium_findings = 0
        open_low_findings = 0
        open_info_findings = 0

        for finding in findings:
            finding["ordering"] = finding_order
            severity = finding["severity"].lower()
            finding_status = strip_html(finding["network_detection_techniques"]).lower()
            open_status = FindingStatusColor.OPEN.value[0].lower()
            accepted_status = FindingStatusColor.ACCEPTED.value[0].lower()

            def _increment_open_finding(
                count, finding_status, open_status, accepted_status
            ):
                if finding_status == open_status or finding_status == accepted_status:
                    count += 1
                return count

            if severity == Severity.CRIT.value.lower():
                critical_findings += 1
                open_critical_findings = _increment_open_finding(
                    open_critical_findings, finding_status, open_status, accepted_status
                )
            elif severity == Severity.HIGH.value.lower():
                high_findings += 1
                open_high_findings = _increment_open_finding(
                    open_high_findings, finding_status, open_status, accepted_status
                )
            elif severity == Severity.MED.value.lower():
                medium_findings += 1
                open_medium_findings = _increment_open_finding(
                    open_medium_findings, finding_status, open_status, accepted_status
                )
            elif severity == Severity.LOW.value.lower():
                low_findings += 1
                open_low_findings = _increment_open_finding(
                    open_low_findings, finding_status, open_status, accepted_status
                )
            elif severity == Severity.BP.value.lower():
                info_findings += 1
                open_info_findings = _increment_open_finding(
                    open_info_findings, finding_status, open_status, accepted_status
                )
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
        rep["totals"]["open_findings_critical"] = open_critical_findings
        rep["totals"]["open_findings_high"] = open_high_findings
        rep["totals"]["open_findings_medium"] = open_medium_findings
        rep["totals"]["open_findings_low"] = open_low_findings
        rep["totals"]["open_findings_info"] = open_info_findings
        rep["totals"]["open_findings"] = (
            open_critical_findings
            + open_high_findings
            + open_medium_findings
            + open_low_findings
            + open_info_findings
        )
        rep["totals"]["scope"] = total_scope_lines
        rep["totals"]["team"] = total_team
        rep["totals"]["targets"] = total_targets

        def _get_total(crit_findings, high_findings, med_findings, low_findings, info_findings):
            return crit_findings * 25 + high_findings * 10 + med_findings * 5 + low_findings * 3 + info_findings * 1

        def _get_score(total, mean, std):
            return (mean - total) / std

        def _get_findings_by_type(findings, type):
            return list(filter(lambda finding: finding["finding_type"].lower() == type, findings))

        def _get_open_findings(findings):
            open_status = FindingStatusColor.OPEN.value[0].lower()
            accepted_status = FindingStatusColor.ACCEPTED.value[0].lower()

            def _is_open(status):
                return status.lower() == open_status or status.lower() == accepted_status
            return list(filter(lambda f: _is_open(strip_html(f["network_detection_techniques"])), findings,))

        def _get_findings_by_severity(findings, severity):
            return list(filter(lambda f: f["severity"].lower() == severity.lower(), findings))

        # Calculate SD Score - in statistics this is called Z-Score
        # This one is the total for all findings in the report
        # Netsec needs separate totals for internal and external in the combo reports
        findings_score_total = _get_total(
            open_critical_findings,
            open_high_findings,
            open_medium_findings,
            open_low_findings,
            open_info_findings,
        )

        netsec_internal = "internal"
        netsec_external = "external"

        netsec_internal_findings = _get_findings_by_type(findings, netsec_internal)
        netsec_external_findings = _get_findings_by_type(findings, netsec_external)

        netsec_internal_open_findings = _get_open_findings(netsec_internal_findings)
        netsec_external_open_findings = _get_open_findings(netsec_external_findings)

        netsec_internal_total = _get_total(
            len(_get_findings_by_severity(netsec_internal_open_findings, Severity.CRIT.value)),
            len(_get_findings_by_severity(netsec_internal_open_findings, Severity.HIGH.value)),
            len(_get_findings_by_severity(netsec_internal_open_findings, Severity.MED.value)),
            len(_get_findings_by_severity(netsec_internal_open_findings, Severity.LOW.value)),
            len(_get_findings_by_severity(netsec_internal_open_findings, Severity.BP.value)),
        )
        netsec_external_total = _get_total(
            len(_get_findings_by_severity(netsec_external_open_findings, Severity.CRIT.value)),
            len(_get_findings_by_severity(netsec_external_open_findings, Severity.HIGH.value)),
            len(_get_findings_by_severity(netsec_external_open_findings, Severity.MED.value)),
            len(_get_findings_by_severity(netsec_external_open_findings, Severity.LOW.value)),
            len(_get_findings_by_severity(netsec_external_open_findings, Severity.BP.value)),
        )

        # Service label, total, mean, and standard deviation
        # The hardcoded literals need to be updated once in a while to update the rolling average
        # Mean and STDs should be based off the past three years as the security landscape changes
        score_type_data = [
            ("appsec", findings_score_total, 39.44715447, 33.86162857),
            ("wireless", findings_score_total, 37.33802817, 47.06631332),
            (netsec_internal, netsec_internal_total, 64.30909091, 56.55371468),
            (netsec_external, netsec_external_total, 37.33802817, 47.06631332),
            ("cloud", findings_score_total, 124.48, 63.49810706),
            ("physical", findings_score_total, 64.30909091, 56.55371468),
        ]
        for d in score_type_data:
            mean = d[2]
            std = d[3]
            best_score = _get_score(0, mean, std)
            score = _get_score(d[1], mean, std)

            # Convert the score to a percentage based on the range of the SD graph max value (3 STD)
            # Negatives we are graphing as a score whereas positive as a percentage
            # since we don't know the worst score but do know the best score
            if score > 0:
                score = score / best_score * 3
            rep["totals"]["sd_score_" + d[0]] = score

        # Calculate the findings chart data variable
        def _get_chart_data(findings):
            chart_data = []
            severity_indexes = list(reversed([e.value.lower() for e in Severity]))
            for finding in findings:
                # Have to strip HTML because it's in a field that takes HTML
                category = strip_html(finding["replication_steps"])
                # Replace spaces with newlines to wrap x-axis labels
                category = category.replace(" ", "\n")

                severity = finding["severity"].lower()
                category_found = False

                for data in chart_data:
                    if data[0] == category:
                        # Update the finding count for the severity
                        # # +1 in the index is to adjust as the label is in the first index
                        data[severity_indexes.index(severity) + 1] += 1
                        category_found = True
                        break

                if not category_found:
                    # Add new entry with category label and all zeros
                    data = [category] + [0] * 5
                    data[severity_indexes.index(severity) + 1] += 1
                    chart_data.append(data)
            return chart_data

        rep["totals"]["chart_data"] = _get_chart_data(findings)

        # Check if there are any netsec findings, GW will hit this on report generation
        # for appsec reports where both are empty arrays and throw an error on report generation
        # Use all findings marked in report for these values in those cases
        rep["totals"]["chart_data_internal"] = _get_chart_data(
            netsec_internal_findings if netsec_internal_findings else findings
        )
        rep["totals"]["chart_data_external"] = _get_chart_data(
            netsec_external_findings if netsec_external_findings else findings
        )
        return rep
