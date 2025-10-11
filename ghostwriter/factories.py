# Standard Libraries
import random
from datetime import date, timedelta, timezone

# Django Imports
from django.contrib.auth import get_user_model
from django.utils import timezone

# 3rd Party Libraries
import factory
import zoneinfo
from factory import Faker
from faker.providers import BaseProvider
from faker.providers.lorem.en_US import Provider as LoremProvider

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
        django_get_or_create = ["username"]

    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")
    phone = Faker("phone_number")
    timezone = random.choice(TIMEZONES)
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
    is_staff = True
    is_superuser = False


class AdminFactory(UserFactory):
    role = "admin"
    is_staff = True
    is_superuser = True


class GroupFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "auth.Group"

    name = Faker("name")


# Rolodex Factories


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Client"
        django_get_or_create = ("name",)

    name = Faker("company")
    short_name = Faker("name")
    codename = Faker("name")
    note = Faker("rich_text")
    timezone = random.choice(TIMEZONES)
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

    name = Faker("name")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    note = Faker("rich_text")
    timezone = random.choice(TIMEZONES)
    client = factory.SubFactory(ClientFactory)


class ProjectTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectType"

    project_type = factory.Sequence(lambda n: "Type %s" % n)


class ProjectRoleFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectRole"

    project_role = factory.Sequence(lambda n: "Type %s" % n)


class ProjectFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Project"

    codename = factory.Sequence(lambda n: "GHOST-%s" % n)
    # Random dates within a year of each other and at least 7 days apart
    start_date = Faker("date_between", start_date="-365d", end_date="-182d")
    end_date = Faker("date_between", start_date="-190d", end_date="+182d")
    note = Faker("rich_text")
    slack_channel = "#ghostwriter"
    complete = False
    client = factory.SubFactory(ClientFactory)
    project_type = factory.SubFactory(ProjectTypeFactory)
    operator = factory.SubFactory(UserFactory)
    timezone = random.choice(TIMEZONES)
    start_time = Faker("time_object")
    end_time = Faker("time_object")

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
    note = Faker("rich_text")
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
    complete = Faker("boolean")
    position = factory.Sequence(lambda n: n)
    project = factory.SubFactory(ProjectFactory)
    deadline = Faker("date_between", start_date="-305d", end_date="+60d")
    status = factory.SubFactory(ObjectiveStatusFactory)
    priority = factory.SubFactory(ObjectivePriorityFactory)
    result = Faker("rich_text")

class ProjectSubtaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectSubtask"

    task = Faker("sentence")
    complete = Faker("boolean")
    status = factory.SubFactory(ObjectiveStatusFactory)
    parent = factory.SubFactory(ProjectObjectiveFactory)
    deadline = Faker("date_between", start_date="-305d", end_date="+60d")


class ProjectScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectScope"

    name = Faker("word")
    scope = Faker("ipv4")
    description = Faker("sentence")
    disallowed = Faker("boolean")
    requires_caution = Faker("boolean")
    project = factory.SubFactory(ProjectFactory)


class ProjectTargetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectTarget"

    ip_address = Faker("ipv4_private")
    hostname = Faker("hostname")
    note = Faker("sentence")
    compromised = Faker("boolean")
    project = factory.SubFactory(ProjectFactory)


class ProjectContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectContact"

    name = Faker("name")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    note = Faker("rich_text")
    primary = False
    timezone = random.choice(TIMEZONES)
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
    cvss_score = factory.LazyFunction(lambda: round(random.uniform(0, 10), 1))
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


class ReportTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx", extension="docx", name="docx")
    uploaded_by = factory.SubFactory(UserFactory)

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


class ReportDocxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx", extension="docx", name="docx")
    uploaded_by = factory.SubFactory(UserFactory)


class ReportPptxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.pptx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("rich_text")
    changelog = Faker("rich_text")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="pptx", extension="pptx", name="pptx")
    uploaded_by = factory.SubFactory(UserFactory)


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
    cvss_score = factory.LazyFunction(lambda: round(random.uniform(0, 10), 1))
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
    added_as_blank = Faker("boolean")

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
    added_as_blank = Faker("boolean")

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


class EvidenceOnFindingFactory(BaseEvidenceFactory):
    finding = factory.SubFactory(ReportFindingLinkFactory)


class EvidenceOnReportFactory(BaseEvidenceFactory):
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
        django_get_or_create = ("name",)

    name = Faker("domain_name")
    registrar = Faker("company")
    dns = Faker("json")
    creation = Faker("past_date")
    expiration = Faker("future_date")
    vt_permalink = Faker("url")
    categorization = Faker("pydict", value_types=(str,))
    note = Faker("rich_text")
    burned_explanation = Faker("rich_text")
    auto_renew = Faker("boolean")
    expired = Faker("boolean")
    reset_dns = Faker("boolean")
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

    start_date = Faker("past_date")
    end_date = Faker("future_date")
    note = Faker("rich_text")
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

    ip_address = Faker("ipv4")
    note = Faker("rich_text")
    name = Faker("hostname")
    server_status = factory.SubFactory(ServerStatusFactory)
    server_provider = factory.SubFactory(ServerProviderFactory)
    last_used_by = factory.SubFactory(UserFactory)


class ServerHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerHistory"

    start_date = Faker("past_date")
    end_date = Faker("future_date")
    note = Faker("rich_text")
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
    note = Faker("rich_text")
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
    primary = Faker("boolean")
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

    enable = Faker("boolean")
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
    enable_borders = Faker("boolean")
    border_weight = 2700
    border_color = "2D2B6B"
    prefix_figure = Faker("word")
    label_figure = Faker("word")
    prefix_table = Faker("word")
    label_table = Faker("word")
    report_filename = '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report'
    project_filename = '{{now|format_datetime("Y-m-d_His")}} {{company.name}} - {{client.name}} {{project.project_type}} Report'
    title_case_captions = Faker("boolean")
    title_case_exceptions = str(Faker("csv"))[:255]
    target_delivery_date = Faker("pyint")
    default_docx_template = factory.SubFactory(ReportDocxTemplateFactory)
    default_pptx_template = factory.SubFactory(ReportPptxTemplateFactory)


class SlackConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.SlackConfiguration"

    enable = Faker("boolean")
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

    enable = Faker("boolean")
    aws_key = Faker("credit_card_number")
    aws_secret = Faker("credit_card_number")
    do_api_key = Faker("credit_card_number")
    ignore_tag = Faker("word")


class VirusTotalConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.VirusTotalConfiguration"

    enable = Faker("boolean")
    api_key = Faker("credit_card_number")
    sleep_time = 20


class GeneralConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.GeneralConfiguration"

    default_timezone = random.choice(TIMEZONES)


class BannerConfigurationFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "commandcenter.BannerConfiguration"

    pk = 1
    enable_banner = Faker("boolean")
    banner_title = Faker("word")
    banner_message = Faker("sentence")
    banner_link = Faker("url")
    public_banner = Faker("boolean")
    expiry_date = Faker("date_time", tzinfo=timezone.utc)


class DeconflictionStatusFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.DeconflictionStatus"

    status = factory.Sequence(lambda n: "Status %s" % n)
    weight = factory.Sequence(lambda n: n)


class DeconflictionFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Deconfliction"

    report_timestamp = Faker("date_time", tzinfo=timezone.utc)
    alert_timestamp = Faker("date_time", tzinfo=timezone.utc)
    response_timestamp = Faker("date_time", tzinfo=timezone.utc)
    title = Faker("sentence")
    description = Faker("rich_text")
    alert_source = Faker("word")
    status = factory.SubFactory(DeconflictionStatusFactory)
    project = factory.SubFactory(ProjectFactory)


class WhiteCardFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.WhiteCard"

    issued = Faker("date_time", tzinfo=timezone.utc)
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

    internal_name = Faker("username")
    display_name = Faker("word")
    type = random.choice(EXTRA_FIELD_TYPES)
    user_default_value = Faker("sentence")

    @factory.lazy_attribute
    def target_model(self):
        raise ValueError("Value for `target_model` (instance of `ExtraFieldModelFactory`) is required")


def GenerateMockProject(
    num_of_contacts=3,
    num_of_assignments=3,
    num_of_findings=10,
    num_of_scopes=5,
    num_of_targets=10,
    num_of_objectives=3,
    num_of_subtasks=5,
    num_of_domains=5,
    num_of_servers=5,
    num_of_deconflictions=3,
    num_of_whitecards=3,
):
    # Generate a random client and project
    client = ClientFactory(name="SpecterOps, Inc.")
    project = ProjectFactory(
        client=client,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=20),
    )

    # Add a report to the project
    report = ReportFactory(
        project=project,
        docx_template=ReportDocxTemplateFactory(),
        pptx_template=ReportPptxTemplateFactory(),
    )

    # Generate a batch of client contacts and project assignments
    ClientContactFactory.create_batch(num_of_contacts, client=client)
    assignments = ProjectAssignmentFactory.create_batch(num_of_assignments, project=project)

    # Generate severity categories and randomly assign them to findings
    severities = [
        SeverityFactory(severity="Critical", weight=0),
        SeverityFactory(severity="High", weight=1),
        SeverityFactory(severity="Medium", weight=2),
        SeverityFactory(severity="Low", weight=3),
    ]
    ReportFindingLinkFactory.create_batch(
        num_of_findings,
        report=report,
        severity=random.choice(severities),
        assigned_to=random.choice(assignments).operator,
    )

    # Generate several permutations of scopes
    ProjectScopeFactory.create_batch(num_of_scopes, project=project)

    # Generate random targets
    ProjectTargetFactory.create_batch(num_of_targets, project=project)

    # Generate objective priorities and status and randomly assign them to objectives
    obj_priorities = [
        ObjectivePriorityFactory(priority="Primary", weight=0),
        ObjectivePriorityFactory(priority="Secondary", weight=1),
        ObjectivePriorityFactory(priority="Tertiary", weight=2),
    ]

    obj_status = [
        ObjectiveStatusFactory(objective_status="Done"),
        ObjectiveStatusFactory(objective_status="Missed"),
        ObjectiveStatusFactory(objective_status="In Progress"),
    ]

    objectives = ProjectObjectiveFactory.create_batch(
        num_of_objectives,
        project=project,
        priority=random.choice(obj_priorities),
        status=random.choice(obj_status),
    )

    # Generate subtasks for each objective
    for obj in objectives:
        ProjectSubtaskFactory.create_batch(num_of_subtasks, parent=obj, status=random.choice(obj_status))

    # Generate random domain names and servers used for this project
    domains = HistoryFactory.create_batch(num_of_domains, project=project)
    servers = ServerHistoryFactory.create_batch(num_of_servers, project=project)
    cloud = TransientServerFactory.create_batch(num_of_servers, project=project)

    # Generate deconflictions
    deconfliction_status = [
        DeconflictionStatusFactory(status="Undetermined", weight=0),
        DeconflictionStatusFactory(status="Confirmed", weight=1),
        DeconflictionStatusFactory(status="Unrelated", weight=2),
    ]
    DeconflictionFactory.create_batch(
        num_of_deconflictions,
        project=project,
        status=random.choice(deconfliction_status),
    )

    # Generate white cards
    WhiteCardFactory.create_batch(
        num_of_whitecards,
        project=project,
    )

    for index, domain in enumerate(domains):
        if index % 2 == 0:
            DomainServerConnectionFactory(domain=domain, static_server=random.choice(servers), transient_server=None)
        else:
            DomainServerConnectionFactory(domain=domain, transient_server=random.choice(cloud), static_server=None)

    # Return the higher level objects to be used in the tests
    return client, project, report
