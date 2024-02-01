# Standard Libraries
import random

# Django Imports
from django.core.management.base import BaseCommand
from django.db import transaction

# Ghostwriter Libraries
from ghostwriter.factories import (
    ClientContactFactory,
    ClientFactory,
    DomainFactory,
    DomainServerConnectionFactory,
    EvidenceOnFindingFactory,
    FindingFactory,
    HistoryFactory,
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ProjectScopeFactory,
    ProjectSubtaskFactory,
    ProjectTargetFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ServerHistoryFactory,
    StaticServerFactory,
    TransientServerFactory,
    UserFactory,
)
from ghostwriter.reporting.models import Finding, FindingType, Severity
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectRole,
    ProjectType,
)
from ghostwriter.shepherd.models import (
    ActivityType,
    Domain,
    DomainStatus,
    HealthStatus,
    ServerProvider,
    ServerRole,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)
from ghostwriter.users.models import User

# Mock user data
NUM_USERS = 10

# Mock domain data
NUM_DOMAINS = 10
REGISTRARS = ["Hover", "Namecheap", "GoDaddy", "Google", "Dynadot"]

# Mock server data
NUM_SERVERS = 10
ACTIVITY_TYPES = ActivityType.objects.all()
SERVER_ROLES = ServerRole.objects.all()

# Mock finding data
NUM_FINDINGS = 15

# Mock client data
NUM_CLIENTS = 5
NUM_POCS = 3

# Mock project data
NUM_PROJECTS = 10
USERS_PER_PROJECT = 3
ASSETS_PER_PROJECT = 3
OBJS_PER_PROJECT = 5
TASKS_PER_OBJ = 3
SCOPES_PER_PROJECT = 3
TARGETS_PER_PROJECT = 10
OPLOGS_PER_PROJECT = 1
ENTRIES_PER_OPLOG = 20
REPORTS_PER_PROJECT = 1
FINDINGS_PER_REPORT = 5

# Pull seeded and existing data from the database
WHOIS_STATUS = WhoisStatus.objects.all()
HEALTH_STATUS = HealthStatus.objects.all()
DOMAIN_STATUS = DomainStatus.objects.all()
SERVER_STATUS = ServerStatus.objects.all()
PROVIDERS = ServerProvider.objects.all()
PROJECT_ROLES = ProjectRole.objects.all()
PROJECT_TYPES = ProjectType.objects.all()
SEVERITIES = Severity.objects.all()
FINDING_TYPES = FindingType.objects.all()
OBJ_PRIORITIES = ObjectivePriority.objects.all()
OBJ_STATUS = ObjectiveStatus.objects.all()
USERS = User.objects.all()


class Command(BaseCommand):
    help = "Generates a test database"

    @transaction.atomic
    def handle(self, *args, **kwargs):
        self.stdout.write(self.style.SUCCESS("Clearing out old data..."))
        models = [Domain, StaticServer, TransientServer, Project, Client, ClientContact, Finding]
        for m in models:
            m.objects.all().delete()

        self.stdout.write(self.style.SUCCESS("Creating users..."))
        # Create all the users
        people = []
        for _ in range(NUM_USERS):
            person = UserFactory()
            people.append(person)

        # Populate domain library
        self.stdout.write(self.style.SUCCESS("Creating domains..."))
        domains = []
        for _ in range(NUM_DOMAINS):
            d = DomainFactory(
                registrar=random.choice(REGISTRARS),
                whois_status=random.choice(WHOIS_STATUS),
                health_status=random.choice(HEALTH_STATUS),
                domain_status=random.choice(DOMAIN_STATUS),
                last_used_by=random.choice(USERS),
            )
            domains.append(d)

        # Populate server library
        self.stdout.write(self.style.SUCCESS("Creating servers..."))
        servers = []
        for _ in range(NUM_SERVERS):
            s = StaticServerFactory(
                server_provider=random.choice(PROVIDERS),
                server_status=random.choice(SERVER_STATUS),
                last_used_by=random.choice(USERS),
            )
            servers.append(s)

        # Populate findings library
        self.stdout.write(self.style.SUCCESS("Creating findings..."))
        findings = []
        for _ in range(NUM_FINDINGS):
            f = FindingFactory.create_batch(
                NUM_FINDINGS,
                finding_type=random.choice(FINDING_TYPES),
                severity=random.choice(SEVERITIES),
            )
            findings.append(f)

        # Populate client list + client POCs
        self.stdout.write(self.style.SUCCESS("Creating clients and contacts..."))
        clients = ClientFactory.create_batch(NUM_CLIENTS)

        for c in clients:
            ClientContactFactory.create_batch(NUM_POCS, client=c)

        # Populate project list + project members
        self.stdout.write(self.style.SUCCESS("Creating projects and assignments..."))
        projects = []
        for _ in range(NUM_PROJECTS):
            p = ProjectFactory(
                client=random.choice(clients),
                project_type=random.choice(PROJECT_TYPES),
                operator=random.choice(USERS),
            )
            projects.append(p)

        # Populate projects with activities
        self.stdout.write(self.style.SUCCESS("[+] Populating %s projects with data..." % NUM_PROJECTS))
        for p in projects:
            assignments = []
            objectives = []
            reports = []
            project_domains = []
            project_servers = []
            project_cloud = []
            targets = []
            oplogs = []

            for _ in range(USERS_PER_PROJECT):
                a = ProjectAssignmentFactory(
                    project=p, operator=random.choice(USERS), role=random.choice(PROJECT_ROLES)
                )
                assignments.append(a)

            # Populate project infrastructure
            for _ in range(ASSETS_PER_PROJECT):
                d = HistoryFactory(
                    client=p.client,
                    project=p,
                    operator=random.choice(assignments).operator,
                    activity_type=random.choice(ACTIVITY_TYPES),
                    domain=random.choice(domains),
                )
                project_domains.append(d)
                s = ServerHistoryFactory(
                    client=p.client,
                    project=p,
                    operator=random.choice(assignments).operator,
                    activity_type=random.choice(ACTIVITY_TYPES),
                    server_role=random.choice(SERVER_ROLES),
                    server=random.choice(servers),
                )
                project_servers.append(s)
                c = TransientServerFactory(
                    project=p,
                    operator=random.choice(assignments).operator,
                    activity_type=random.choice(ACTIVITY_TYPES),
                    server_role=random.choice(SERVER_ROLES),
                    server_provider=random.choice(PROVIDERS),
                )
                project_cloud.append(c)

            # Randomly assign domains to servers
            for index, d in enumerate(project_domains):
                if index % 2 == 0:
                    DomainServerConnectionFactory(
                        domain=d,
                        static_server=random.choice(project_servers),
                        transient_server=None,
                        project=p,
                    )
                else:
                    DomainServerConnectionFactory(
                        domain=d,
                        transient_server=random.choice(project_cloud),
                        static_server=None,
                        project=p,
                    )

            # Populate project scope lists
            ProjectScopeFactory.create_batch(SCOPES_PER_PROJECT, project=p)

            # Populate project targets
            targets = ProjectTargetFactory.create_batch(TARGETS_PER_PROJECT, project=p)

            # Populate project objectives + subtasks
            for _ in range(OBJS_PER_PROJECT):
                o = ProjectObjectiveFactory(
                    project=p, status=random.choice(OBJ_STATUS), priority=random.choice(OBJ_PRIORITIES)
                )
                objectives.append(o)

            for obj in objectives:
                for _ in range(TASKS_PER_OBJ):
                    ProjectSubtaskFactory(parent=obj, status=random.choice(OBJ_STATUS))

            # Create some reports
            reports = ReportFactory.create_batch(REPORTS_PER_PROJECT, project=p)

            # Assign some findings to reports
            for r in reports:
                report_findings = []
                for _ in range(FINDINGS_PER_REPORT):
                    f = ReportFindingLinkFactory(
                        report=r,
                        severity=random.choice(SEVERITIES),
                        finding_type=random.choice(FINDING_TYPES),
                        assigned_to=random.choice(assignments).operator,
                    )
                    report_findings.append(f)

                # Create fake evidence
                for f in report_findings:
                    EvidenceOnFindingFactory(
                        finding=f,
                        uploaded_by=random.choice(assignments).operator,
                    )

            # Create oplogs
            oplogs = OplogFactory.create_batch(OPLOGS_PER_PROJECT, project=p)

            # Populate oplogs with entries
            for log in oplogs:
                for _ in range(ENTRIES_PER_OPLOG):
                    OplogEntryFactory(
                        oplog_id=log,
                        operator_name=random.choice(assignments).operator.username,
                        source_ip=random.choice(targets).ip_address,
                        dest_ip=random.choice(targets).ip_address,
                    )
