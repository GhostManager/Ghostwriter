# Standard Libraries
import random
from datetime import date, timedelta

# Django Imports
from django.contrib.auth import get_user_model
from django.utils import timezone

# 3rd Party Libraries
import factory
from factory import Faker

# Users Factories


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = get_user_model()
        django_get_or_create = ["username"]

    username = Faker("user_name")
    email = Faker("email")
    name = Faker("name")
    phone = Faker("phone_number")
    timezone = Faker("timezone")
    password = factory.PostGenerationMethodCall("set_password", "mysecret")

    @factory.post_generation
    def groups(self, create, extracted, **kwargs):
        if not create:
            return

        if extracted:
            for group in extracted:
                self.groups.add(group)


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
    note = "A note about a client"
    timezone = Faker("timezone")
    address = Faker("address")


class ClientContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientContact"

    name = Faker("name")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    note = "A note about a client"
    timezone = Faker("timezone")
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
    start_date = date.today()
    end_date = date.today() + timedelta(days=20)
    note = "A project note"
    slack_channel = "#ghostwriter"
    complete = False
    client = factory.SubFactory(ClientFactory)
    project_type = factory.SubFactory(ProjectTypeFactory)
    operator = factory.SubFactory(UserFactory)
    timezone = Faker("timezone")
    start_time = Faker("time_object")
    end_time = Faker("time_object")


class ProjectAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectAssignment"

    project = factory.SubFactory(
        ProjectFactory,
        start_date=date.today(),
        end_date=date.today() + timedelta(days=20),
    )
    start_date = date.today()
    end_date = date.today() + timedelta(days=20)
    note = "Note about this person's assignment"
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
    description = Faker("paragraph")
    complete = Faker("boolean")
    position = factory.Sequence(lambda n: n)
    project = factory.SubFactory(ProjectFactory)
    deadline = Faker("date")
    status = factory.SubFactory(ObjectiveStatusFactory)
    priority = factory.SubFactory(ObjectivePriorityFactory)


class ProjectSubtaskFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectSubtask"

    task = Faker("sentence")
    complete = Faker("boolean")
    status = factory.SubFactory(ObjectiveStatusFactory)
    parent = factory.SubFactory(ProjectObjectiveFactory)
    deadline = Faker("date")


class ProjectScopeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectScope"

    name = Faker("name")
    scope = Faker("sentence")
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


# Reporting Factories


class SeverityFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Severity"

    severity = factory.Sequence(lambda n: "Severity %s" % n)
    weight = 1


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
    description = Faker("paragraph")
    impact = Faker("paragraph")
    mitigation = Faker("paragraph")
    replication_steps = Faker("paragraph")
    host_detection_techniques = Faker("paragraph")
    network_detection_techniques = Faker("paragraph")
    references = Faker("paragraph")
    finding_guidance = Faker("paragraph")


class DocTypeFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.DocType"
        django_get_or_create = ("doc_type",)


class ReportTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("paragraph")
    changelog = Faker("paragraph")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx")
    uploaded_by = factory.SubFactory(UserFactory)


class ReportDocxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.docx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("paragraph")
    changelog = Faker("paragraph")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="docx")
    uploaded_by = factory.SubFactory(UserFactory)


class ReportPptxTemplateFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportTemplate"

    document = factory.django.FileField(from_path="DOCS/sample_reports/template.pptx")
    name = factory.Sequence(lambda n: "Template %s" % n)
    description = Faker("paragraph")
    changelog = Faker("paragraph")
    lint_result = ""
    protected = False
    client = None
    doc_type = factory.SubFactory(DocTypeFactory, doc_type="pptx")
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


class ReportFindingLinkFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.ReportFindingLink"

    title = factory.Sequence(lambda n: "Local Finding %s" % n)
    position = 1
    affected_entities = Faker("hostname")
    severity = factory.SubFactory(SeverityFactory)
    finding_type = factory.SubFactory(FindingTypeFactory)
    report = factory.SubFactory(ReportFactory)
    assigned_to = factory.SubFactory(UserFactory)
    description = Faker("paragraph")
    impact = Faker("paragraph")
    mitigation = Faker("paragraph")
    replication_steps = Faker("paragraph")
    host_detection_techniques = Faker("paragraph")
    network_detection_techniques = Faker("paragraph")
    references = Faker("paragraph")
    finding_guidance = Faker("paragraph")


class EvidenceFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Evidence"

    document = factory.django.FileField(filename="evidence.png", data=b"lorem ipsum")
    friendly_name = Faker("name")
    caption = Faker("sentence")
    description = Faker("sentence")
    finding = factory.SubFactory(ReportFindingLinkFactory)
    uploaded_by = factory.SubFactory(UserFactory)


class ArchiveFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.Archive"

    report_archive = factory.django.FileField(filename="archive.zip")
    project = factory.SubFactory(ProjectFactory)


class FindingNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.FindingNote"

    note = Faker("paragraph")
    finding = factory.SubFactory(FindingFactory)
    operator = factory.SubFactory(UserFactory)


class LocalFindingNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "reporting.LocalFindingNote"

    note = Faker("paragraph")
    finding = factory.SubFactory(ReportFindingLinkFactory)
    operator = factory.SubFactory(UserFactory)


class ClientNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientNote"

    note = Faker("paragraph")
    client = factory.SubFactory(ClientFactory)
    operator = factory.SubFactory(UserFactory)


class ProjectNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectNote"

    note = Faker("paragraph")
    project = factory.SubFactory(ProjectFactory)
    operator = factory.SubFactory(UserFactory)


# Oplog Factories


class OplogFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.Oplog"

    name = Faker("sentence")
    project = factory.SubFactory(ProjectFactory)


class OplogEntryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "oplog.OplogEntry"

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

    name = Faker("domain_name")
    registrar = Faker("company")
    dns_record = Faker("json")
    health_dns = Faker("word")
    creation = Faker("date")
    expiration = Faker("date")
    vt_permalink = Faker("url")
    all_cat = Faker("pylist")
    ibm_xforce_cat = Faker("word")
    talos_cat = Faker("word")
    bluecoat_cat = Faker("word")
    fortiguard_cat = Faker("word")
    opendns_cat = Faker("word")
    trendmicro_cat = Faker("word")
    mx_toolbox_status = Faker("word")
    note = Faker("paragraph")
    burned_explanation = Faker("paragraph")
    auto_renew = Faker("boolean")
    expired = Faker("boolean")
    reset_dns = Faker("boolean")
    whois_status = factory.SubFactory(WhoisStatusFactory)
    health_status = factory.SubFactory(HealthStatusFactory)
    domain_status = factory.SubFactory(DomainStatusFactory)
    last_used_by = factory.SubFactory(UserFactory)


class HistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.History"

    start_date = date.today()
    end_date = date.today() + timedelta(days=20)
    note = Faker("paragraph")
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
    note = Faker("paragraph")
    name = Faker("hostname")
    server_status = factory.SubFactory(ServerStatusFactory)
    server_provider = factory.SubFactory(ServerProviderFactory)
    last_used_by = factory.SubFactory(UserFactory)


class ServerHistoryFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerHistory"

    start_date = date.today()
    end_date = date.today() + timedelta(days=20)
    note = Faker("paragraph")
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
    note = Faker("paragraph")
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

    note = Faker("paragraph")
    domain = factory.SubFactory(DomainFactory)


class ServerNoteFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "shepherd.ServerNote"

    note = Faker("paragraph")
    server = factory.SubFactory(StaticServerFactory)


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

    enable_borders = Faker("boolean")
    border_weight = 2700
    border_color = "2D2B6B"
    prefix_figure = Faker("word")
    label_figure = Faker("word")
    prefix_table = Faker("word")
    label_table = Faker("word")
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
    assignments = ProjectAssignmentFactory.create_batch(
        num_of_assignments, project=project
    )

    # Generate severity categories and randomly assign them to findings
    severities = []
    severities.append(SeverityFactory(severity="Critical", weight=0))
    severities.append(SeverityFactory(severity="High", weight=1))
    severities.append(SeverityFactory(severity="Medium", weight=2))
    severities.append(SeverityFactory(severity="Low", weight=3))
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
    obj_priorities = []
    obj_priorities.append(ObjectivePriorityFactory(priority="Primary", weight=0))
    obj_priorities.append(ObjectivePriorityFactory(priority="Secondary", weight=1))
    obj_priorities.append(ObjectivePriorityFactory(priority="Tertiary", weight=2))

    obj_status = []
    obj_status.append(ObjectiveStatusFactory(objective_status="Done"))
    obj_status.append(ObjectiveStatusFactory(objective_status="Missed"))
    obj_status.append(ObjectiveStatusFactory(objective_status="In Progress"))

    objectives = ProjectObjectiveFactory.create_batch(
        num_of_objectives,
        project=project,
        priority=random.choice(obj_priorities),
        status=random.choice(obj_status),
    )

    # Generate subtasks for each objective
    for obj in objectives:
        ProjectSubtaskFactory.create_batch(
            num_of_subtasks, parent=obj, status=random.choice(obj_status)
        )

    # Generate random domain names and servers used for this project
    domains = HistoryFactory.create_batch(num_of_domains, project=project)
    servers = ServerHistoryFactory.create_batch(num_of_servers, project=project)
    cloud = TransientServerFactory.create_batch(num_of_servers, project=project)

    for index, domain in enumerate(domains):
        if index % 2 == 0:
            DomainServerConnectionFactory(
                domain=domain, static_server=random.choice(servers), transient_server=None
            )
        else:
            DomainServerConnectionFactory(
                domain=domain, transient_server=random.choice(cloud), static_server=None
            )

    # Return the higher level objects to be used in the tests
    return client, project, report
