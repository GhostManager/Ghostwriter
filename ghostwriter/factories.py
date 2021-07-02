# Standard Libraries
from datetime import date, datetime, timedelta

# Django Imports
from django.contrib.auth import get_user_model

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
    password = factory.PostGenerationMethodCall("set_password", "mysecret")


# Rolodex Factories


class ClientFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.Client"

    name = Faker("company")
    short_name = Faker("name")
    codename = Faker("name")
    note = "A note about a client"


class ClientContactFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ClientContact"

    name = Faker("name")
    job_title = Faker("job")
    email = Faker("email")
    phone = Faker("phone_number")
    note = "A note about a client"
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
    end_date = datetime.now() + timedelta(days=20)
    note = "A project note"
    slack_channel = "#ghostwriter"
    complete = False
    client = factory.SubFactory(ClientFactory)
    project_type = factory.SubFactory(ProjectTypeFactory)
    operator = factory.SubFactory(UserFactory)


class ProjectAssignmentFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectAssignment"

    project = factory.SubFactory(
        ProjectFactory,
        start_date=date.today(),
        end_date=datetime.now() + timedelta(days=20),
    )
    start_date = date.today()
    end_date = datetime.now() + timedelta(days=20)
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
    complete = False
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
    disallowed = False
    requires_caution = False
    project = factory.SubFactory(ProjectFactory)


class ProjectTargetFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = "rolodex.ProjectTarget"

    ip_address = Faker("ipv4_private")
    hostname = Faker("hostname")
    note = Faker("sentence")
    compromised = False
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
