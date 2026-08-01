# Standard Libraries
from datetime import date, datetime, time, timedelta
from datetime import timezone as datetime_timezone

# Django Imports
from django.contrib.auth import get_user_model
from django.contrib.auth.hashers import make_password
from django.db.models.signals import post_save
from django.utils import timezone

# 3rd Party Libraries
import factory
import zoneinfo
from factory import Faker
from faker.providers import BaseProvider
from faker.providers.lorem.en_US import Provider as LoremProvider

# Ghostwriter Libraries
from ghostwriter.reporting.models import EvidenceImageAlignment, EvidenceImageAlignmentOverride

# Couple of timezones to test with
TIMEZONES = [
    zoneinfo.ZoneInfo("America/Los_Angeles"),
    zoneinfo.ZoneInfo("Europe/Berlin"),
    zoneinfo.ZoneInfo("America/New_York"),
    zoneinfo.ZoneInfo("US/Michigan"),
    zoneinfo.ZoneInfo("GB-Eire"),
]
EXTRA_FIELD_TYPES = [
    "checkbox",
    "single_line_text",
    "rich_text",
    "integer",
    "float",
]

DEFAULT_TEMPLATE_LINT_RESULT = {
    "result": "success",
    "warnings": [],
    "errors": [],
}

# Add faker provider for rich text (html)
class RichTextProvider(BaseProvider):
    text_provider: LoremProvider

    def __init__(self, generator):
        super().__init__(generator)
        self.text_provider = LoremProvider(generator)

    def rich_text(self):
        para = self.text_provider.paragraph()
        return f"<p>{para}</p>"

Faker.add_provider(RichTextProvider)


# Users Factories


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()

    username = factory.Sequence(lambda n: f"user-{n}")
    email = factory.Sequence(lambda n: f"user-{n}@example.com")
    name = Faker("name")
    phone = Faker("phone_number")
    timezone = TIMEZONES[0]
    password = factory.PostGenerationMethodCall("set_password", "mysecret")
    role = "user"
    is_active = True
    is_staff = False
    is_superuser = False
    enable_finding_create = False
    enable_finding_edit = False
    enable_finding_delete = False
    enable_observation_create = False
    enable_observation_edit = False
    enable_observation_delete = False
    enable_template_management = False
    require_mfa = False

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                self.groups.add(group)


class MgrFactory(UserFactory):
    role = "manager"
    is_staff = False
    is_superuser = False


class AdminFactory(UserFactory):
    role = "admin"
    is_staff = True
    is_superuser = True


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "auth.Group"

    name = factory.Sequence(lambda n: f"Group {n}")


# Rolodex Factories


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Client"

    name = factory.Sequence(lambda n: f"Client {n}")
    short_name = Faker("name")
    codename = Faker("name")
    description = Faker("rich_text")
    timezone = TIMEZONES[0]
    address = Faker("address")

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ClientContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientContact"

    name = factory.Sequence(lambda n: f"Client Contact {n}")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    description = Faker("rich_text")
    primary = False
    timezone = TIMEZONES[0]
    client = factory.SubFactory(ClientFactory)


class ProjectTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectType"

    project_type = factory.Sequence(lambda n: "Type %s" % n)


class ProjectRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectRole"

    project_role = factory.Sequence(lambda n: "Type %s" % n)
    position = factory.Sequence(lambda n: n + 1)


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Project"

    codename = factory.Sequence(lambda n: "GHOST-%s" % n)
    start_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    description = Faker("rich_text")
    slack_channel = "#ghostwriter"
    complete = False
    client = factory.SubFactory(ClientFactory)
    project_type = factory.SubFactory(ProjectTypeFactory)
    operator = factory.SubFactory(UserFactory)
    timezone = TIMEZONES[0]
    start_time = time(hour=9)
    end_time = time(hour=17)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ProjectAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectAssignment"

    project = factory.SubFactory(
        ProjectFactory,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=20),
    )
    start_date = factory.SelfAttribute("project.start_date")
    end_date = factory.SelfAttribute("project.end_date")
    description = Faker("rich_text")
    operator = factory.SubFactory(UserFactory)
    role = factory.SubFactory(ProjectRoleFactory)


class ObjectiveStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ObjectiveStatus"

    objective_status = factory.Sequence(lambda n: "Status %s" % n)


class ObjectivePriorityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ObjectivePriority"

    priority = factory.Sequence(lambda n: "Priority %s" % n)
    weight = factory.Sequence(lambda n: n)


class ProjectObjectiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectObjective"

    objective = Faker("sentence")
    description = Faker("rich_text")
    complete = False
    position = factory.Sequence(lambda n: n)
    project = factory.SubFactory(ProjectFactory)
    deadline = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    status = factory.SubFactory(ObjectiveStatusFactory)
    priority = factory.SubFactory(ObjectivePriorityFactory)
    result = Faker("rich_text")

class ProjectSubtaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectSubtask"

    task = Faker("sentence")
    complete = False
    status = factory.SubFactory(ObjectiveStatusFactory)
    parent = factory.SubFactory(ProjectObjectiveFactory)
    deadline = factory.LazyFunction(lambda: date.today() + timedelta(days=30))


class ProjectScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectScope"

    name = Faker("word")
    scope = Faker("ipv4")
    description = Faker("sentence")
    disallowed = False
    requires_caution = False
    project = factory.SubFactory(ProjectFactory)


class ProjectTargetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectTarget"

    ip_address = factory.Sequence(
        lambda n: f"10.{(n // 65536) % 256}.{(n // 256) % 256}.{n % 256}"
    )
    hostname = Faker("hostname")
    description = Faker("sentence")
    compromised = False
    project = factory.SubFactory(ProjectFactory)


class ProjectContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectContact"

    name = factory.Sequence(lambda n: f"Project Contact {n}")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    description = Faker("rich_text")
    primary = False
    timezone = TIMEZONES[0]
    project = factory.SubFactory(ProjectFactory)


# Reporting Factories


class SeverityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Severity"

    severity = factory.Sequence(lambda n: "Severity %s" % n)
    weight = factory.Sequence(lambda n: n)


class FindingTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.FindingType"

    finding_type = factory.Sequence(lambda n: "Type %s" % n)


class FindingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Finding"

    title = factory.Sequence(lambda n: "Finding %s" % n)
    severity = factory.SubFactory(SeverityFactory)
    finding_type = factory.SubFactory(FindingTypeFactory)
    cvss_score = 5.0
    cvss_vector = factory.Sequence(lambda n: "Vector %s" % n)
    description = Faker("rich_text")
    impact = Faker("rich_text")
    mitigation = Faker("rich_text")
    replication_steps = Faker("rich_text")
    host_detection_techniques = Faker("rich_text")
    network_detection_techniques = Faker("rich_text")
    references = Faker("rich_text")
    finding_guidance = Faker("rich_text")

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ObservationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Observation"

    title = factory.Sequence(lambda n: "Observation %s" % n)
    description = Faker("rich_text")

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class DocTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.DocType"
        django_get_or_create = ("doc_type", "extension", "name")


@factory.django.mute_signals(post_save)
class ReportTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = factory.LazyFunction(lambda: DEFAULT_TEMPLATE_LINT_RESULT.copy())
    protected = False
    client = None
    bloodhound_heading_offset = 0
    contains_bloodhound_data = False
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx", extension="docx", name="docx")
    uploaded_by = factory.SubFactory(UserFactory)
    p_style = "Normal"
    evidence_image_width = None
    evidence_image_alignment = EvidenceImageAlignmentOverride.USE_GLOBAL

    class Params:
        docx = factory.Trait(
            document=factory.django.FileField(from_path="DOCS/sample_reports/template.docx"),
            doc_type=factory.SubFactory(DocTypeFactory, doc_type="docx", extension="docx", name="docx"),
        )
        pptx = factory.Trait(
            document=factory.django.FileField(from_path="DOCS/sample_reports/template.pptx"),
            doc_type=factory.SubFactory(DocTypeFactory, doc_type="pptx", extension="pptx", name="pptx"),
        )

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


@factory.django.mute_signals(post_save)
class ReportDocxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = factory.LazyFunction(lambda: DEFAULT_TEMPLATE_LINT_RESULT.copy())
    protected = False
    client = None
    bloodhound_heading_offset = 0
    contains_bloodhound_data = False
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx", extension="docx", name="docx")
    uploaded_by = factory.SubFactory(UserFactory)
    p_style = "Normal"
    evidence_image_width = None
    evidence_image_alignment = EvidenceImageAlignmentOverride.USE_GLOBAL


@factory.django.mute_signals(post_save)
class ReportPptxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.pptx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = factory.LazyFunction(lambda: DEFAULT_TEMPLATE_LINT_RESULT.copy())
    protected = False
    client = None
    bloodhound_heading_offset = 0
    contains_bloodhound_data = False
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="pptx", extension="pptx", name="pptx")
    uploaded_by = factory.SubFactory(UserFactory)
    p_style = "Normal"
    evidence_image_width = None
    evidence_image_alignment = EvidenceImageAlignmentOverride.USE_GLOBAL

class ReportFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Report"

    title = factory.Sequence(lambda n: "Report %s" % n)
    complete = False
    archived = False
    project = factory.SubFactory(ProjectFactory)
    docx_template = factory.SubFactory(ReportDocxTemplateFactory)
    pptx_template = factory.SubFactory(ReportPptxTemplateFactory)
    delivered = False
    include_bloodhound_data = False
    created_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ReportFindingLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportFindingLink"

    title = factory.Sequence(lambda n: "Local Finding %s" % n)
    position = 1
    affected_entities = Faker("rich_text")
    severity = factory.SubFactory(SeverityFactory)
    finding_type = factory.SubFactory(FindingTypeFactory)
    cvss_score = 5.0
    cvss_vector = factory.Sequence(lambda n: "Vector %s" % n)
    report = factory.SubFactory(ReportFactory)
    assigned_to = factory.SubFactory(UserFactory)
    description = Faker("rich_text")
    impact = Faker("rich_text")
    mitigation = Faker("rich_text")
    replication_steps = Faker("rich_text")
    host_detection_techniques = Faker("rich_text")
    network_detection_techniques = Faker("rich_text")
    references = Faker("rich_text")
    finding_guidance = Faker("rich_text")
    added_as_blank = False

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class ReportObservationLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportObservationLink"

    title = factory.Sequence(lambda n: "Local Observation %s" % n)
    position = 1
    description = Faker("rich_text")
    added_as_blank = False

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class BlankReportFindingLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportFindingLink"

    title = factory.Sequence(lambda n: "Blank Finding %s" % n)
    position = 1
    added_as_blank = True
    assigned_to = factory.SubFactory(UserFactory)
    severity = factory.SubFactory(SeverityFactory)
    finding_type = factory.SubFactory(FindingTypeFactory)
    report = factory.SubFactory(ReportFactory)


class BaseEvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Evidence"

    document = factory.django.FileField(filename="evidence.png", data=b"lorem ipsum")
    friendly_name = factory.Sequence(lambda n: "Evidence %s" % n)
    caption = Faker("sentence")
    description = Faker("sentence")
    uploaded_by = factory.SubFactory(UserFactory)

    class Params:
        img = factory.Trait(document=factory.django.FileField(filename="evidence.png", data=b"lorem ipsum"))
        txt = factory.Trait(document=factory.django.FileField(filename="evidence.txt", data=b"lorem ipsum"))
        unknown = factory.Trait(document=factory.django.FileField(filename="evidence.tar", data=b"lorem ipsum"))

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class EvidenceFactory(BaseEvidenceFactory):
    report = factory.SubFactory(ReportFactory)


class ArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Archive"

    report_archive = factory.django.FileField(filename="archive.zip")
    project = factory.SubFactory(ProjectFactory)


class FindingNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.FindingNote"

    note = Faker("rich_text")
    finding = factory.SubFactory(FindingFactory)
    operator = factory.SubFactory(UserFactory)


class LocalFindingNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.LocalFindingNote"

    note = Faker("rich_text")
    finding = factory.SubFactory(ReportFindingLinkFactory)
    operator = factory.SubFactory(UserFactory)


class ClientNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientNote"

    note = Faker("rich_text")
    client = factory.SubFactory(ClientFactory)
    operator = factory.SubFactory(UserFactory)


class ProjectNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectNote"

    note = Faker("rich_text")
    project = factory.SubFactory(ProjectFactory)
    operator = factory.SubFactory(UserFactory)


class ClientInviteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientInvite"

    comment = Faker("rich_text")
    client = factory.SubFactory(ClientFactory)
    user = factory.SubFactory(UserFactory)


class ProjectInviteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectInvite"

    comment = Faker("rich_text")
    project = factory.SubFactory(ProjectFactory)
    user = factory.SubFactory(UserFactory)


# Oplog Factories


class OplogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.Oplog"

    name = Faker("sentence")
    project = factory.SubFactory(ProjectFactory)


class OplogEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.OplogEntry"

    entry_identifier = factory.Sequence(lambda n: "%s" % n)
    start_date = timezone.now()
    end_date = timezone.now()
    source_ip = Faker("ipv4")
    dest_ip = Faker("ipv4")
    tool = Faker("name")
    user_context = Faker("user_name")
    command = Faker("sentence")
    description = Faker("sentence")
    output = Faker("sentence")
    comments = Faker("sentence")
    operator_name = Faker("name")
    oplog_id = factory.SubFactory(OplogFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class OplogEntryEvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.OplogEntryEvidence"

    oplog_entry = factory.SubFactory(OplogEntryFactory)
    evidence = factory.SubFactory(EvidenceFactory)


class OplogEntryRecordingFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.OplogEntryRecording"

    oplog_entry = factory.SubFactory(OplogEntryFactory)
    recording_file = factory.django.FileField(
        filename="test.cast",
        data=b'{"version": 3, "term": {"cols": 80, "rows": 24}}\n[0.5, "o", "Hello, world!"]\n',
    )


class ServicePrincipalFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "api.ServicePrincipal"

    name = Faker("sentence")
    service_type = "integration"
    created_by = factory.SubFactory(UserFactory)


class ServiceTokenFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "api.ServiceToken"

    name = Faker("sentence")
    token_prefix = factory.Sequence(lambda n: f"prefix{n}")
    secret_hash = factory.LazyFunction(lambda: make_password("service-secret"))
    created_by = factory.SubFactory(UserFactory)
    service_principal = factory.SubFactory(ServicePrincipalFactory)


class ServiceTokenPermissionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "api.ServiceTokenPermission"

    token = factory.SubFactory(ServiceTokenFactory)
    resource_type = "oplog"
    resource_id = factory.Sequence(lambda n: n + 1)
    action = "read"
    constraints = {}


# Shepherd Factories


class HealthStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.HealthStatus"

    health_status = factory.Sequence(lambda n: "Status %s" % n)


class DomainStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.DomainStatus"

    domain_status = factory.Sequence(lambda n: "Status %s" % n)


class WhoisStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.WhoisStatus"

    whois_status = factory.Sequence(lambda n: "Status %s" % n)


class ActivityTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ActivityType"

    activity = factory.Sequence(lambda n: "Activity %s" % n)


class DomainFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.Domain"

    name = factory.Sequence(lambda n: f"domain-{n}.example.com")
    registrar = Faker("company")
    dns = Faker("json")
    creation = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    expiration = factory.LazyFunction(lambda: date.today() + timedelta(days=335))
    vt_permalink = Faker("url")
    categorization = Faker("pydict", value_types=(str,))
    description = Faker("rich_text")
    burned_explanation = Faker("rich_text")
    auto_renew = False
    expired = False
    reset_dns = False
    whois_status = factory.SubFactory(WhoisStatusFactory)
    health_status = factory.SubFactory(HealthStatusFactory)
    domain_status = factory.SubFactory(DomainStatusFactory)
    last_used_by = factory.SubFactory(UserFactory)

    @factory.post_generation
    def tags(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for tag in extracted:
                self.tags.add(tag)


class HistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.History"

    start_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    description = Faker("rich_text")
    domain = factory.SubFactory(DomainFactory)
    client = factory.SubFactory(ClientFactory)
    project = factory.SubFactory(ProjectFactory)
    operator = factory.SubFactory(UserFactory)
    activity_type = factory.SubFactory(ActivityTypeFactory)


class ServerStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerStatus"

    server_status = factory.Sequence(lambda n: "Status %s" % n)


class ServerProviderFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerProvider"

    server_provider = factory.Sequence(lambda n: "Provider %s" % n)


class ServerRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerRole"

    server_role = factory.Sequence(lambda n: "Role %s" % n)


class StaticServerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.StaticServer"

    ip_address = factory.Sequence(
        lambda n: f"10.{(n // 65536) % 256}.{(n // 256) % 256}.{n % 256}"
    )
    description = Faker("rich_text")
    name = Faker("hostname")
    server_status = factory.SubFactory(ServerStatusFactory)
    server_provider = factory.SubFactory(ServerProviderFactory)
    last_used_by = factory.SubFactory(UserFactory)


class ServerHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerHistory"

    start_date = factory.LazyFunction(lambda: date.today() - timedelta(days=30))
    end_date = factory.LazyFunction(lambda: date.today() + timedelta(days=30))
    description = Faker("rich_text")
    server = factory.SubFactory(StaticServerFactory)
    client = factory.SubFactory(ClientFactory)
    project = factory.SubFactory(ProjectFactory)
    operator = factory.SubFactory(UserFactory)
    server_role = factory.SubFactory(ServerRoleFactory)
    activity_type = factory.SubFactory(ActivityTypeFactory)


class TransientServerFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.TransientServer"

    ip_address = Faker("ipv4")
    aux_address = factory.List([Faker("ipv4") for _ in range(3)])
    name = Faker("hostname")
    description = Faker("rich_text")
    project = factory.SubFactory(ProjectFactory)
    operator = factory.SubFactory(UserFactory)
    server_provider = factory.SubFactory(ServerProviderFactory)
    server_role = factory.SubFactory(ServerRoleFactory)
    activity_type = factory.SubFactory(ActivityTypeFactory)


class DomainServerConnectionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.DomainServerConnection"

    endpoint = Faker("domain_name")
    subdomain = Faker("word")
    project = factory.SubFactory(ProjectFactory)
    domain = factory.SubFactory(HistoryFactory)
    static_server = factory.SubFactory(ServerHistoryFactory)
    transient_server = None


class AuxServerAddressFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.AuxServerAddress"

    ip_address = Faker("ipv4")
    primary = False
    static_server = factory.SubFactory(StaticServerFactory)


class DomainNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.DomainNote"

    note = Faker("rich_text")
    domain = factory.SubFactory(DomainFactory)
    operator = factory.SubFactory(UserFactory)


class ServerNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerNote"

    note = Faker("rich_text")
    server = factory.SubFactory(StaticServerFactory)
    operator = factory.SubFactory(UserFactory)


class NamecheapConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.NamecheapConfiguration"

    enable = False
    api_key = Faker("credit_card_number")
    username = Faker("user_name")
    api_username = Faker("user_name")
    client_ip = Faker("ipv4_private")
    page_size = 100


class ReportConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.ReportConfiguration"
        django_get_or_create = ["pk"]

    pk = 1
    enable_borders = False
    border_weight = 2700
    border_color = "2D2B6B"
    prefix_figure = Faker("word")
    label_figure = Faker("word")
    figure_caption_location = "bottom"
    evidence_image_alignment = EvidenceImageAlignment.CENTER
    evidence_image_width = None
    prefix_table = Faker("word")
    label_table = Faker("word")
    table_caption_location = "top"
    report_filename = '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report'
    project_filename = '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report'
    title_case_captions = False
    title_case_exceptions = str(Faker("csv"))[:255]
    target_delivery_date = Faker("pyint")
    default_cvss_version = "3.1"
    outline_tags = "report,evidence"
    default_docx_template = factory.SubFactory(ReportDocxTemplateFactory)
    default_pptx_template = factory.SubFactory(ReportPptxTemplateFactory)


class SlackConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.SlackConfiguration"

    enable = False
    webhook_url = Faker("url")
    slack_emoji = Faker("word")
    slack_channel = Faker("user_name")
    slack_username = Faker("user_name")
    slack_alert_target = Faker("user_name")


class CompanyInformationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.CompanyInformation"

    company_name = Faker("company")
    company_twitter = Faker("user_name")
    company_email = Faker("email")


class CloudServicesConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.CloudServicesConfiguration"

    enable = False
    aws_key = Faker("credit_card_number")
    aws_secret = Faker("credit_card_number")
    do_api_key = Faker("credit_card_number")
    ignore_tag = Faker("word")


class VirusTotalConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.VirusTotalConfiguration"

    enable = False
    api_key = Faker("credit_card_number")
    sleep_time = 20


class GeneralConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.GeneralConfiguration"

    default_timezone = TIMEZONES[0]


class BannerConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.BannerConfiguration"

    pk = 1
    enable_banner = False
    banner_title = Faker("word")
    banner_message = Faker("sentence")
    banner_link = Faker("url")
    public_banner = False
    expiry_date = factory.LazyFunction(
        lambda: datetime.combine(
            date.today() + timedelta(days=30),
            time(hour=17),
            tzinfo=datetime_timezone.utc,
        )
    )


class DeconflictionStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.DeconflictionStatus"

    status = factory.Sequence(lambda n: "Status %s" % n)
    weight = factory.Sequence(lambda n: n)


class DeconflictionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Deconfliction"

    alert_timestamp = factory.LazyFunction(
        lambda: datetime.combine(
            date.today(),
            time(hour=9),
            tzinfo=datetime_timezone.utc,
        )
    )
    report_timestamp = factory.LazyFunction(
        lambda: datetime.combine(
            date.today(),
            time(hour=10),
            tzinfo=datetime_timezone.utc,
        )
    )
    response_timestamp = factory.LazyFunction(
        lambda: datetime.combine(
            date.today(),
            time(hour=11),
            tzinfo=datetime_timezone.utc,
        )
    )
    title = Faker("sentence")
    description = Faker("rich_text")
    alert_source = Faker("word")
    status = factory.SubFactory(DeconflictionStatusFactory)
    project = factory.SubFactory(ProjectFactory)


class WhiteCardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.WhiteCard"

    issued = factory.LazyFunction(
        lambda: datetime.combine(
            date.today(),
            time(hour=12),
            tzinfo=datetime_timezone.utc,
        )
    )
    title = Faker("user_name")
    description = Faker("rich_text")
    project = factory.SubFactory(ProjectFactory)


class ExtraFieldModelFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.ExtraFieldModel"

    @factory.lazy_attribute
    def model_internal_name(self):
        raise ValueError("Value for `model_internal_name` is required")

    @factory.lazy_attribute
    def model_display_name(self):
        raise ValueError("Value for `model_display_name` is required")


class ExtraFieldSpecFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.ExtraFieldSpec"

    internal_name = factory.Sequence(lambda n: f"extra_field_{n}")
    display_name = Faker("word")
    type = EXTRA_FIELD_TYPES[0]
    user_default_value = Faker("sentence")

    @factory.lazy_attribute
    def target_model(self):
        raise ValueError("Value for `target_model` (instance of `ExtraFieldModelFactory`) is required")
