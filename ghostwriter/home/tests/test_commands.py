# Standard Libraries
import shutil
import tempfile
from datetime import date
from io import StringIO
from pathlib import Path
from unittest.mock import patch

# Django Imports
from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import TransactionTestCase, override_settings
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import (
    BloodHoundConfiguration,
    CompanyInformation,
    ExtraFieldSpec,
    ReportConfiguration,
)
from ghostwriter.home.models import UserProfile
from ghostwriter.home.management.commands.generate_test_data import (
    COMPANY_INFORMATION,
    DEMO_EVIDENCE_TEXT_SAMPLES,
    EXTRA_FIELD_MODELS,
    EXTRA_FIELD_SPECS,
    EXTRA_FIELD_SPECS_BY_MODEL,
    REPORT_CONFIGURATION,
    Command as GenerateTestDataCommand,
)
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.reporting.models import (
    DocType,
    Evidence,
    Finding,
    FindingType,
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
    DeconflictionStatus,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectObjective,
    ProjectRole,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    ProjectType,
    WhiteCard,
)
from ghostwriter.shepherd.models import (
    ActivityType,
    Domain,
    DomainServerConnection,
    DomainStatus,
    HealthStatus,
    History,
    ServerProvider,
    ServerHistory,
    ServerRole,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)


class GenerateTestDataCommandTests(TransactionTestCase):
    """Tests for the realistic demo database seed command."""

    reset_sequences = True

    def setUp(self):
        self.media_root = tempfile.mkdtemp()
        self.override = override_settings(MEDIA_ROOT=self.media_root)
        self.override.enable()
        call_command(
            "loaddata", "ghostwriter/commandcenter/fixtures/initial.json", verbosity=0
        )
        call_command(
            "loaddata", "ghostwriter/reporting/fixtures/initial.json", verbosity=0
        )
        call_command(
            "loaddata", "ghostwriter/rolodex/fixtures/initial.json", verbosity=0
        )
        call_command(
            "loaddata", "ghostwriter/shepherd/fixtures/initial.json", verbosity=0
        )

    def tearDown(self):
        self.override.disable()
        shutil.rmtree(self.media_root, ignore_errors=True)

    def call_seed(self, *args):
        stdout = StringIO()
        call_command("generate_test_data", *args, stdout=stdout)
        return stdout.getvalue()

    def test_seed_creates_representative_demo_database(self):
        output = self.call_seed("--quick")

        self.assertIn("Demo data seed complete", output)
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 1)
        self.assertGreaterEqual(ClientContact.objects.count(), 3)
        self.assertTrue(ClientContact.objects.filter(primary=True).exists())
        self.assertGreaterEqual(ProjectContact.objects.count(), 2)
        self.assertEqual(ProjectAssignment.objects.count(), 4)
        self.assertGreaterEqual(ProjectScope.objects.count(), 2)
        self.assertGreaterEqual(ProjectTarget.objects.count(), 3)
        self.assertGreaterEqual(ProjectObjective.objects.count(), 3)
        self.assertGreaterEqual(ProjectSubTask.objects.count(), 9)
        self.assertGreaterEqual(Deconfliction.objects.count(), 2)
        self.assertGreaterEqual(WhiteCard.objects.count(), 3)
        self.assertTrue(
            WhiteCard.objects.filter(
                title="Client-provided VPN account enabled"
            ).exists()
        )
        self.assertTrue(
            WhiteCard.objects.filter(
                description__icontains="bootstrap the assumed-breach scenario"
            ).exists()
        )
        self.assertGreaterEqual(History.objects.count(), 3)
        self.assertGreaterEqual(ServerHistory.objects.count(), 3)
        self.assertGreaterEqual(TransientServer.objects.count(), 2)
        self.assertGreaterEqual(DomainServerConnection.objects.count(), 3)
        self.assertEqual(Report.objects.count(), 1)
        self.assertGreaterEqual(ReportFindingLink.objects.count(), 3)
        self.assertGreaterEqual(Observation.objects.count(), 2)
        self.assertGreaterEqual(ReportObservationLink.objects.count(), 2)
        self.assertEqual(Evidence.objects.count(), len(DEMO_EVIDENCE_TEXT_SAMPLES))
        evidence_names = set(Evidence.objects.values_list("friendly_name", flat=True))
        self.assertIn("Nmap Service Scan - portal.gbi.example", evidence_names)
        self.assertIn("Burp Response - GBI Profile Notes", evidence_names)
        self.assertIn("Rubeus Ticket Request - GBI.LOCAL", evidence_names)
        nmap_evidence = Evidence.objects.get(
            friendly_name="Nmap Service Scan - portal.gbi.example"
        )
        with nmap_evidence.document.open("r") as evidence_file:
            self.assertIn("10.40.20.20", evidence_file.read())
        self.assertEqual(Oplog.objects.count(), 1)
        self.assertGreaterEqual(OplogEntry.objects.count(), 8)
        report = Report.objects.get()
        docx_template = ReportTemplate.objects.get(name="Default Word Template")
        exporter = ExportReportDocx(report, report_template=docx_template)
        document = exporter.run()
        self.assertGreater(len(document.getvalue()), 0)
        self.assertIn("Red Team Report", exporter.render_filename(REPORT_CONFIGURATION["report_filename"]))
        self.assertFalse(
            any("demo-seed" in entry.tags.names() for entry in OplogEntry.objects.all())
        )
        self.assertFalse(
            OplogEntry.objects.filter(command="uploaded evidence artifact").exists()
        )
        self.assertTrue(
            OplogEntry.objects.filter(
                command="Reviewed captured evidence against reporting criteria."
            ).exists()
        )
        for entry in OplogEntry.objects.all():
            self.assertTrue(
                all(
                    tag.startswith("att&ck:")
                    or tag in {"creds", "detection", "discovery"}
                    for tag in entry.tags.names()
                )
            )

    def test_seed_default_size_runs_without_options(self):
        output = self.call_seed()

        self.assertIn("Demo data seed complete", output)
        self.assertEqual(Client.objects.count(), 3)
        self.assertEqual(Project.objects.count(), 6)
        today = date.today()
        self.assertEqual(
            Project.objects.filter(
                start_date__lte=today, end_date__gte=today, complete=False
            ).count(),
            2,
        )
        self.assertEqual(
            Project.objects.filter(end_date__lt=today, complete=True).count(),
            2,
        )
        self.assertFalse(
            Project.objects.filter(end_date__lt=today, complete=False).exists()
        )
        self.assertFalse(
            Project.objects.filter(end_date__gte=today, complete=True).exists()
        )
        self.assertEqual(
            Project.objects.filter(start_date__gt=today, complete=False).count(),
            2,
        )

    def test_seed_restores_optional_templates_and_clears_media(self):
        media_root = Path(self.media_root)
        media_root_inode = media_root.stat().st_ino
        stale_file = media_root / "evidence" / "stale-demo-file.txt"
        stale_file.parent.mkdir(parents=True)
        stale_file.write_text("old demo data")
        ReportTemplate.objects.all()._raw_delete(ReportTemplate.objects.db)

        output = self.call_seed("--quick", "--reset")

        self.assertIn("--reset is only needed with --append", output)
        self.assertEqual(media_root.stat().st_ino, media_root_inode)
        self.assertFalse(stale_file.exists())
        self.assertEqual(ReportTemplate.objects.count(), 2)
        self.assertTrue((media_root / "templates" / "template.docx").exists())
        self.assertTrue((media_root / "templates" / "template.pptx").exists())

    def test_media_reset_failure_does_not_flush_database(self):
        command = GenerateTestDataCommand()

        with patch.object(command, "_validate_media_reset"), patch.object(
            command, "_reset_media", side_effect=CommandError("busy media")
        ), patch(
            "ghostwriter.home.management.commands.generate_test_data.call_command"
        ) as mocked_call_command:
            with self.assertRaisesMessage(CommandError, "busy media"):
                command._reinstall_database()

        mocked_call_command.assert_not_called()

    def test_seed_uses_fixture_lookups_without_creating_more(self):
        lookup_counts = {
            "severities": Severity.objects.count(),
            "finding_types": FindingType.objects.count(),
            "doc_types": DocType.objects.count(),
            "project_types": ProjectType.objects.count(),
            "project_roles": ProjectRole.objects.count(),
            "objective_statuses": ObjectiveStatus.objects.count(),
            "objective_priorities": ObjectivePriority.objects.count(),
            "deconfliction_statuses": DeconflictionStatus.objects.count(),
            "whois_statuses": WhoisStatus.objects.count(),
            "health_statuses": HealthStatus.objects.count(),
            "domain_statuses": DomainStatus.objects.count(),
            "activity_types": ActivityType.objects.count(),
            "server_statuses": ServerStatus.objects.count(),
            "server_providers": ServerProvider.objects.count(),
            "server_roles": ServerRole.objects.count(),
        }

        self.call_seed("--quick")

        self.assertEqual(Severity.objects.count(), lookup_counts["severities"])
        self.assertEqual(FindingType.objects.count(), lookup_counts["finding_types"])
        self.assertEqual(DocType.objects.count(), lookup_counts["doc_types"])
        self.assertEqual(ProjectType.objects.count(), lookup_counts["project_types"])
        self.assertEqual(ProjectRole.objects.count(), lookup_counts["project_roles"])
        self.assertEqual(
            ObjectiveStatus.objects.count(), lookup_counts["objective_statuses"]
        )
        self.assertEqual(
            ObjectivePriority.objects.count(), lookup_counts["objective_priorities"]
        )
        self.assertEqual(
            DeconflictionStatus.objects.count(), lookup_counts["deconfliction_statuses"]
        )
        self.assertEqual(WhoisStatus.objects.count(), lookup_counts["whois_statuses"])
        self.assertEqual(HealthStatus.objects.count(), lookup_counts["health_statuses"])
        self.assertEqual(DomainStatus.objects.count(), lookup_counts["domain_statuses"])
        self.assertEqual(ActivityType.objects.count(), lookup_counts["activity_types"])
        self.assertEqual(ServerStatus.objects.count(), lookup_counts["server_statuses"])
        self.assertEqual(
            ServerProvider.objects.count(), lookup_counts["server_providers"]
        )
        self.assertEqual(ServerRole.objects.count(), lookup_counts["server_roles"])

    def test_seed_creates_required_users_with_shared_password(self):
        self.call_seed("--quick")

        User = get_user_model()
        cmaddalena = User.objects.get(username="cmaddalena")
        self.assertEqual(cmaddalena.name, "Christopher Maddalena")
        self.assertEqual(cmaddalena.email, "cmaddalena@getghostwriter.io")
        self.assertTrue(cmaddalena.check_password("SuperNaturalReporting!"))
        self.assertTrue(cmaddalena.is_active)
        self.assertTrue(UserProfile.objects.filter(user=cmaddalena).exists())

        for username in ["pstanz", "rstantz", "espengler", "wzeddemore"]:
            user = User.objects.get(username=username)
            self.assertTrue(user.name)
            self.assertTrue(user.email)
            self.assertTrue(user.check_password("SuperNaturalReporting!"))
            self.assertTrue(UserProfile.objects.filter(user=user).exists())

        for username in ["pstanz", "rstantz", "espengler"]:
            user = User.objects.get(username=username)
            self.assertTrue(ProjectAssignment.objects.filter(operator=user).exists())

        project = Project.objects.first()
        role_counts = {
            role: ProjectAssignment.objects.filter(
                project=project, role__project_role=role
            ).count()
            for role in ("Assessment Lead", "Assessment Oversight", "Operator")
        }
        self.assertEqual(
            role_counts,
            {"Assessment Lead": 1, "Assessment Oversight": 1, "Operator": 2},
        )

    def test_seed_creates_required_domains_and_realistic_findings(self):
        self.call_seed("--quick")

        self.assertTrue(Domain.objects.filter(name="ghostwriter.wiki").exists())
        self.assertTrue(Domain.objects.filter(name="getghostwriter.io").exists())
        self.assertTrue(Domain.objects.filter(name="specterops.io").exists())
        self.assertTrue(Domain.objects.filter(name="docs.mythic-c2.net").exists())

        finding = Finding.objects.get(
            title="Kerberoastable Service Accounts with Excessive Privileges"
        )
        self.assertIn("service accounts", finding.description)
        self.assertIn("https://attack.mitre.org", finding.references)
        self.assertGreater(finding.cvss_score, 0)
        self.assertTrue(finding.tags.filter(name="credential-access").exists())

    def test_seed_creates_extra_field_specs_and_values(self):
        self.call_seed("--quick")

        for model in EXTRA_FIELD_MODELS:
            expected_specs = EXTRA_FIELD_SPECS_BY_MODEL.get(model, EXTRA_FIELD_SPECS)
            expected_names = {spec["internal_name"] for spec in expected_specs}
            specs = ExtraFieldSpec.objects.filter(target_model=model._meta.label)
            self.assertEqual(specs.count(), len(expected_specs))
            self.assertSetEqual(
                set(specs.values_list("internal_name", flat=True)),
                expected_names,
            )

        demo_objects = [
            Client.objects.first(),
            Project.objects.first(),
            Domain.objects.first(),
            StaticServer.objects.first(),
            Finding.objects.first(),
            Report.objects.first(),
            ReportFindingLink.objects.first(),
            Observation.objects.first(),
            ReportObservationLink.objects.first(),
            OplogEntry.objects.first(),
        ]
        for obj in demo_objects:
            self.assertIsNotNone(obj)
            self.assertEqual(obj.extra_fields["demo_seed"], "ghostbusters")
            expected_specs = EXTRA_FIELD_SPECS_BY_MODEL.get(
                type(obj), EXTRA_FIELD_SPECS
            )
            for spec in expected_specs:
                self.assertIn(spec["internal_name"], obj.extra_fields)

        project = Project.objects.first()
        self.assertEqual(
            project.extra_fields["entity_tested"],
            "Enterprise identity and external attack surface",
        )
        self.assertIs(project.extra_fields["include_cvss"], True)

        report = Report.objects.first()
        self.assertIs(report.extra_fields["reviewed"], True)
        self.assertIn("<p>", report.extra_fields["attack_path_narrative"])
        self.assertIn("<p>", report.extra_fields["executive_summary"])

    def test_seed_rebuilds_database_by_default(self):
        unrelated_client = Client.objects.create(
            name="Unrelated Client", short_name="UNRELATED"
        )

        self.call_seed("--quick")

        self.assertFalse(Client.objects.filter(name=unrelated_client.name).exists())
        self.assertEqual(Client.objects.count(), 1)
        self.assertEqual(Project.objects.count(), 1)

    def test_append_seed_is_idempotent_and_reset_preserves_non_demo_rows(self):
        unrelated_client = Client.objects.create(
            name="Unrelated Client", short_name="UNRELATED"
        )
        self.call_seed("--quick", "--append")
        counts_after_first_run = {
            "users": get_user_model().objects.count(),
            "clients": Client.objects.count(),
            "projects": Project.objects.count(),
            "deconflictions": Deconfliction.objects.count(),
            "whitecards": WhiteCard.objects.count(),
            "domains": Domain.objects.count(),
            "findings": Finding.objects.count(),
            "observations": Observation.objects.count(),
            "reports": Report.objects.count(),
            "report_observations": ReportObservationLink.objects.count(),
            "evidence": Evidence.objects.count(),
            "oplog_entries": OplogEntry.objects.count(),
        }

        self.call_seed("--quick", "--append")
        counts_after_second_run = {
            "users": get_user_model().objects.count(),
            "clients": Client.objects.count(),
            "projects": Project.objects.count(),
            "deconflictions": Deconfliction.objects.count(),
            "whitecards": WhiteCard.objects.count(),
            "domains": Domain.objects.count(),
            "findings": Finding.objects.count(),
            "observations": Observation.objects.count(),
            "reports": Report.objects.count(),
            "report_observations": ReportObservationLink.objects.count(),
            "evidence": Evidence.objects.count(),
            "oplog_entries": OplogEntry.objects.count(),
        }
        self.assertEqual(counts_after_first_run, counts_after_second_run)

        self.call_seed("--quick", "--append", "--reset")
        self.assertTrue(Client.objects.filter(pk=unrelated_client.pk).exists())
        self.assertEqual(Project.objects.count(), 1)
        self.assertEqual(Report.objects.count(), 1)
        for evidence in Evidence.objects.all():
            self.assertTrue((Path(self.media_root) / evidence.document.name).is_file())

    def test_append_rejects_collision_with_unrelated_data(self):
        client = Client.objects.create(
            name="Ghostbusters International", short_name="EXISTING"
        )

        with self.assertRaisesMessage(
            CommandError,
            "an unrelated row already uses name='Ghostbusters International'",
        ):
            self.call_seed("--quick", "--append")

        client.refresh_from_db()
        self.assertEqual(client.short_name, "EXISTING")
        self.assertFalse(Project.objects.exists())

    def test_seed_configures_install_admin_and_demo_settings(self):
        with patch.dict(
            "os.environ",
            {
                "DJANGO_SUPERUSER_USERNAME": "demo-admin",
                "DJANGO_SUPERUSER_EMAIL": "demo-admin@example.com",
                "DJANGO_SUPERUSER_PASSWORD": "patched-demo-password",
            },
        ):
            output = self.call_seed()

        self.assertIn("Demo data seed complete", output)
        User = get_user_model()
        admin = User.objects.get(username="demo-admin")
        self.assertEqual(admin.email, "demo-admin@example.com")
        self.assertTrue(admin.check_password("patched-demo-password"))
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_staff)
        self.assertTrue(UserProfile.objects.filter(user=admin).exists())
        active_projects = Project.objects.filter(
            start_date__lte=date.today(),
            end_date__gte=date.today(),
            complete=False,
        )
        self.assertEqual(
            ProjectAssignment.objects.filter(
                operator=admin,
                project__in=active_projects,
            ).count(),
            active_projects.count(),
        )
        for project in Project.objects.all():
            self.assertEqual(
                ProjectAssignment.objects.filter(
                    project=project, role__project_role="Assessment Lead"
                ).count(),
                1,
            )
            self.assertEqual(
                ProjectAssignment.objects.filter(
                    project=project, role__project_role="Assessment Oversight"
                ).count(),
                1,
            )
            self.assertEqual(
                ProjectAssignment.objects.filter(
                    project=project, role__project_role="Operator"
                ).count(),
                2,
            )

        self.assertTrue(
            History.objects.filter(
                operator=admin,
                domain__domain_status__domain_status="Unavailable",
            ).exists()
        )
        self.assertTrue(
            ServerHistory.objects.filter(
                operator=admin,
                server__server_status__server_status="Unavailable",
            ).exists()
        )
        self.client.force_login(admin)
        response = self.client.get(reverse("shepherd:user_assets"))
        self.assertGreaterEqual(len(response.context["domains"]), 1)
        self.assertGreaterEqual(len(response.context["servers"]), 1)

        company_config = CompanyInformation.get_solo()
        for field, value in COMPANY_INFORMATION.items():
            self.assertEqual(getattr(company_config, field), value)

        report_config = ReportConfiguration.get_solo()
        for field, value in REPORT_CONFIGURATION.items():
            self.assertEqual(getattr(report_config, field), value)

        bloodhound_config = BloodHoundConfiguration.get_solo()
        self.assertTrue(bloodhound_config.allow_project_fallback)
        self.assertTrue(bloodhound_config.has_bloodhound_api())
        self.assertEqual(
            bloodhound_config.bloodhound_api_root_url,
            "https://bloodhound.demo.local",
        )
        self.assertFalse(bloodhound_config.bloodhound_results["empty"])
        self.assertIn("domains", bloodhound_config.bloodhound_results)
        self.assertIn("findings", bloodhound_config.bloodhound_results)
        self.assertTrue(Report.objects.filter(include_bloodhound_data=True).exists())
