# Standard Libraries
import logging
from datetime import date, datetime, timedelta
from datetime import timezone as datetime_timezone
from io import StringIO
from unittest.mock import patch
from zoneinfo import ZoneInfo

# Django Imports
from django.conf import settings
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models import Q
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

# 3rd Party Libraries
from allauth.mfa.totp.internal.auth import TOTP, generate_totp_secret

# Ghostwriter Libraries
from ghostwriter.factories import (
    ClientInviteFactory,
    GroupFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectInviteFactory,
    ProjectObjectiveFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ReportObservationLinkFactory,
    UserFactory,
)
from ghostwriter.home.navigation import (
    DEFAULT_PANEL_ORDER,
    DEFAULT_OPTIONAL_ORDER,
    DEFAULT_PINNED,
    DEFAULT_VISIBLE_PANELS,
    SIDEBAR_PREFERENCES_VERSION,
)
from ghostwriter.home.working_context import WORKSPACE_PREFERENCES_VERSION
from ghostwriter.home.templatetags import custom_tags
from ghostwriter.reporting.models import ReportTemplate

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


class EditorShortcutsDateTests(TestCase):
    """Tests for refreshing server-formatted editor shortcut dates."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("home:ajax_editor_shortcuts_date")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.get(self.uri)

        self.assertEqual(response.status_code, 302)

    @override_settings(DATE_FORMAT="Y/m/d")
    @patch("ghostwriter.home.editor_shortcuts._current_utc_time")
    def test_view_returns_date_and_next_utc_midnight(self, mock_current_utc_time):
        local_timezone = ZoneInfo("America/Los_Angeles")
        local_time = datetime(2026, 7, 21, 23, 59, 30, tzinfo=local_timezone)
        current_time = local_time.astimezone(datetime_timezone.utc)
        mock_current_utc_time.return_value = current_time

        with timezone.override(local_timezone):
            response = self.client_auth.get(self.uri)

        next_midnight = datetime(2026, 7, 23, tzinfo=datetime_timezone.utc)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response.json(),
            {
                "date": "2026/07/22",
                "expiresAt": round(next_midnight.timestamp() * 1000),
                "serverTime": round(current_time.timestamp() * 1000),
                "refreshUrl": self.uri,
            },
        )
        self.assertIn("no-store", response.headers["Cache-Control"])

    def test_view_rejects_post(self):
        response = self.client_auth.post(self.uri)

        self.assertEqual(response.status_code, 405)


# Tests related to custom management commands


class ManagementCommandsTestCase(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        pass

    def setUp(self):
        pass

    def call_command(self, *args, **kwargs):
        out = StringIO()
        call_command(
            "loaddata",
            *args,
            stdout=out,
            stderr=StringIO(),
            **kwargs,
        )
        return out.getvalue()

    def test_loaddata_command(self):
        out = self.call_command("ghostwriter/reporting/fixtures/initial.json")
        self.assertIn("Found 17 new records to insert into the database.", out)
        out = self.call_command("ghostwriter/reporting/fixtures/initial.json")
        self.assertIn("Found 3 new records to insert into the database.", out)
        out = self.call_command(
            "ghostwriter/reporting/fixtures/initial.json", "--force"
        )
        self.assertIn("Applying all fixtures.", out)
        self.assertIn("Found 17 new records to insert into the database.", out)

    def test_loaddata_required_only_skips_optional_records(self):
        out = self.call_command(
            "ghostwriter/reporting/fixtures/initial.json", "--required-only"
        )
        self.assertIn("Found 15 new records to insert into the database.", out)
        self.assertFalse(ReportTemplate.objects.exists())

    def test_loaddata_required_only_does_not_restore_deleted_optional_records(self):
        self.call_command("ghostwriter/reporting/fixtures/initial.json")
        self.assertEqual(ReportTemplate.objects.count(), 2)

        ReportTemplate.objects.all().delete()

        out = self.call_command(
            "ghostwriter/reporting/fixtures/initial.json", "--required-only"
        )
        self.assertIn("Found 3 new records to insert into the database.", out)
        self.assertFalse(ReportTemplate.objects.exists())

    def test_loaddata_force_and_required_only_are_rejected(self):
        with self.assertRaisesMessage(
            CommandError, "--force and --required-only cannot be used together."
        ):
            self.call_command(
                "ghostwriter/reporting/fixtures/initial.json",
                "--force",
                "--required-only",
            )


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.group_1 = GroupFactory(name="Group 1")
        cls.group_2 = GroupFactory(name="Group 2")
        cls.user = UserFactory(password=PASSWORD, groups=(cls.group_1,), role="user")
        cls.project = ProjectFactory(tags=["tag1", "tag2"])
        cls.report = ReportFactory(project=cls.project)
        cls.assignment = ProjectAssignmentFactory(
            project=cls.project, operator=cls.user
        )

        cls.Objective = ProjectObjectiveFactory._meta.model
        cls.objective = ProjectObjectiveFactory(project=cls.project, complete=False)
        cls.complete_objective = ProjectObjectiveFactory(
            project=cls.project, complete=True
        )
        cls.objectives = cls.Objective.objects.filter(project=cls.project)

        cls.num_of_findings = 3
        ReportFindingLinkFactory.create_batch(
            cls.num_of_findings, report=cls.report, assigned_to=cls.user
        )

        cls.uri = reverse("home:dashboard")

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_tags(self):
        result = custom_tags.has_group(self.user, "Group 1")
        self.assertTrue(result)
        result = custom_tags.has_group(self.user, "Group 2")
        self.assertFalse(result)

        result = custom_tags.get_groups(self.user)
        self.assertEqual(result, "Group 1")

        response = self.client_auth.get(self.uri)
        request = response.wsgi_request
        result = custom_tags.count_assignments(request)
        self.assertEqual(result, self.num_of_findings)

        projects, reports = custom_tags.get_assignment_data(request)
        self.assertEqual(len(projects), 1)
        self.assertEqual(projects[0], self.project)
        self.assertEqual(len(reports), 1)
        self.assertEqual(reports[0], self.report)
        self.assertEqual(reports[0].project, self.project)

    def test_get_assignment_data_prefetches_report_projects(self):
        response = self.client_auth.get(self.uri)
        request = response.wsgi_request

        with self.assertNumQueries(2):
            projects, reports = custom_tags.get_assignment_data(request)
            self.assertEqual(projects[0].codename, self.project.codename)
            self.assertEqual(reports[0].project.codename, self.project.codename)

        result = custom_tags.settings_value("DATE_FORMAT")
        self.assertEqual(result, settings.DATE_FORMAT)

        result = custom_tags.count_incomplete_objectives(self.objectives)
        self.assertEqual(result, 1)

        example_html = "<body><p>Example HTML</p><br /><br /><p></p></body>"
        result = custom_tags.strip_empty_tags(example_html)
        # The tag uses BS4's `prettify()` method to format the HTML, so there are newlines and indentations
        self.assertEqual(
            result,
            "<html>\n <body>\n  <p>\n   Example HTML\n  </p>\n </body>\n</html>\n",
        )

        result = custom_tags.divide(12700, 12700)
        self.assertEqual(result, 1.0)
        result = custom_tags.divide(12700, 0)
        self.assertEqual(result, None)

        result = custom_tags.has_access(self.project, self.user)
        self.assertTrue(result)

        self.assertFalse(custom_tags.can_create_finding(self.user))
        self.user.enable_finding_create = True
        self.user.save()
        self.assertTrue(custom_tags.can_create_finding(self.user))

        self.assertFalse(custom_tags.is_privileged(self.user))
        self.user.role = "manager"
        self.user.save()
        self.assertTrue(custom_tags.can_create_finding(self.user))

        self.user.role = "user"
        self.user.save()

        self.assertFalse(custom_tags.can_create_observation(self.user))
        self.user.enable_observation_create = True
        self.user.save()
        self.assertTrue(custom_tags.can_create_observation(self.user))

        self.assertFalse(custom_tags.is_privileged(self.user))
        self.user.role = "manager"
        self.user.save()
        self.assertTrue(custom_tags.can_create_observation(self.user))

        self.assertFalse(custom_tags.has_mfa(self.user))
        secret = generate_totp_secret()
        TOTP.activate(self.user, secret)
        self.assertTrue(custom_tags.has_mfa(self.user))

        test_string = "test,example,sample"
        result = custom_tags.split_and_join(test_string, ",")
        self.assertEqual(result, "test, example, sample")
        result = custom_tags.humanize_comma_list(test_string)
        self.assertEqual(result, "test, example, and sample")
        result = custom_tags.humanize_comma_list("report,evidence")
        self.assertEqual(result, "report and evidence")

        test_date = datetime(2024, 2, 20)
        result = custom_tags.add_days(test_date, 5)
        self.assertEqual(result, datetime(2024, 2, 27))
        result = custom_tags.add_days(test_date, -5)
        self.assertEqual(result, datetime(2024, 2, 13))

        tags = custom_tags.get_tags_list(self.project.tags.names())
        self.assertEqual(tags, "tag1, tag2")

        request = self.client_auth.get(self.uri).wsgi_request
        hide_quickstart = custom_tags.hide_quickstart(request)
        self.assertEqual(hide_quickstart, False)

        past_datetime = datetime.min
        future_datetime = datetime.max
        self.assertTrue(custom_tags.is_past(past_datetime))
        self.assertFalse(custom_tags.is_past(future_datetime))

        # Test custom_tags.multiply
        result = custom_tags.multiply(10, 5)
        self.assertEqual(result, 50)
        result = custom_tags.multiply(10, -2)
        self.assertEqual(result, -20)
        result = custom_tags.multiply("A", 5)
        self.assertEqual(result, None)

        # Test custom_tags.translate_domain_sid
        domains = [
            {"domain_sid": "S-1-5-21-1000", "name": "EXAMPLE_DOMAIN"},
            {"domain_sid": "S-1-5-21-2000", "name": "ANOTHER_DOMAIN"},
        ]
        result = custom_tags.translate_domain_sid("S-1-5-21-1000", domains)
        self.assertEqual(result, "EXAMPLE_DOMAIN")
        result = custom_tags.translate_domain_sid("S-1-5-21-3000", domains)
        self.assertEqual(result, "S-1-5-21-3000")

    def test_prepare_bhe_findings_groups_and_summarizes_records(self):
        domains = [{"domain_sid": "S-1-5-21-1000", "name": "EXAMPLE.LOCAL"}]
        findings = [
            {
                "id": 42,
                "severity": "Low",
                "environment_id": "S-1-5-21-1000",
                "finding_name": "LowFinding",
                "assets": {"title": "Low exposure", "type": "Privilege Zone"},
                "principals": [
                    {
                        "impact_percentage": 0.75,
                        "exposure_percentage": 0.25,
                    }
                ],
                "is_tier_zero": False,
            },
            {
                "id": 43,
                "severity": "Critical",
                "environment_id": "S-1-5-21-1000",
                "finding_name": "CriticalFinding",
                "assets": {"title": "Critical exposure", "type": "Kerberos"},
                "principals": [
                    {
                        "impact_percentage": 0.99,
                        "exposure_percentage": 0.5,
                    },
                    {
                        "impact_percentage": 0.8,
                        "exposure_percentage": 0.9,
                    },
                ],
                "is_tier_zero": True,
            },
        ]

        prepared = custom_tags.prepare_bhe_findings(findings, domains)

        self.assertEqual(prepared["total"], 2)
        self.assertEqual(prepared["critical"], 1)
        self.assertEqual(prepared["environment_count"], 1)
        self.assertEqual(prepared["principal_count"], 3)
        self.assertEqual(prepared["tier_zero_count"], 1)
        self.assertEqual(
            [group["key"] for group in prepared["groups"]],
            ["critical", "low"],
        )
        critical = prepared["groups"][0]["items"][0]
        self.assertEqual(critical["environment"], "EXAMPLE.LOCAL")
        self.assertEqual(critical["peak_impact"], 0.99)
        self.assertEqual(critical["peak_exposure"], 0.9)
        self.assertEqual(custom_tags.bhe_percent(0.98473), "98.5")
        self.assertEqual(custom_tags.bhe_percent(None), "--")


class DashboardTests(TestCase):
    """Collection of tests for :view:`home.dashboard`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.admin = UserFactory(password=PASSWORD, role="admin")
        cls.other_user = UserFactory(password=PASSWORD, name="Other Operator")

        cls.Project = ProjectFactory._meta.model
        cls.ProjectAssignment = ProjectAssignmentFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model
        cls.ReportObservationLink = ReportObservationLinkFactory._meta.model

        cls.current_project = ProjectFactory(
            codename="CURRENT",
            start_date=date.today() - timedelta(days=14),
            end_date=date.today(),
            complete=True,
        )
        cls.future_project = ProjectFactory(
            codename="FUTURE",
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
            complete=False,
        )
        cls.other_project = ProjectFactory(
            codename="OTHER",
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=21),
            complete=False,
        )
        cls.unassigned_project = ProjectFactory(
            codename="UNASSIGNED",
            start_date=date.today() + timedelta(days=21),
            end_date=date.today() + timedelta(days=35),
            complete=False,
        )
        cls.inaccessible_project = ProjectFactory(
            codename="INACCESSIBLE",
            start_date=date.today() + timedelta(days=28),
            end_date=date.today() + timedelta(days=42),
            complete=False,
        )
        ProjectAssignmentFactory(
            project=cls.current_project,
            operator=cls.user,
            start_date=date.today(),
            end_date=date.today() + timedelta(days=14),
        )
        ProjectAssignmentFactory(
            project=cls.future_project,
            operator=cls.user,
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
        )
        ProjectAssignmentFactory(
            project=cls.other_project,
            operator=cls.other_user,
            start_date=date.today() + timedelta(days=7),
            end_date=date.today() + timedelta(days=21),
        )
        ProjectAssignmentFactory.create_batch(
            3,
            project=cls.unassigned_project,
            operator=None,
            start_date=date.today() + timedelta(days=21),
            end_date=date.today() + timedelta(days=35),
        )
        ProjectInviteFactory(user=cls.user, project=cls.other_project)
        ProjectInviteFactory(user=cls.user, project=cls.future_project)
        ClientInviteFactory(user=cls.user, client=cls.unassigned_project.client)

        cls.report = ReportFactory(project=cls.current_project)
        ReportFindingLinkFactory.create_batch(
            3, report=cls.report, assigned_to=cls.user
        )
        ReportObservationLinkFactory.create_batch(
            3, report=cls.report, assigned_to=cls.user
        )

        cls.assigned_findings = (
            cls.ReportFindingLink.objects.select_related("report", "report__project")
            .filter(
                Q(assigned_to=cls.user) & Q(report__complete=False) & Q(complete=False)
            )
            .order_by("report__project__end_date")[:10]
        )
        cls.assigned_observations = (
            cls.ReportObservationLink.objects.select_related(
                "report", "report__project"
            )
            .filter(
                Q(assigned_to=cls.user) & Q(report__complete=False) & Q(complete=False)
            )
            .order_by("report__project__end_date")[:10]
        )
        cls.user_projects = cls.ProjectAssignment.objects.select_related(
            "project", "project__client", "role"
        ).filter(Q(operator=cls.user))
        cls.active_projects = cls.ProjectAssignment.objects.select_related(
            "project", "project__client", "role"
        ).filter(Q(operator=cls.user) & Q(project__complete=False))

        cls.uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_manager = Client()
        self.client_admin = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_manager.login(username=self.manager.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_admin.login(username=self.admin.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_application_shell_uses_bootstrap_five_and_accessible_sidebar_controls(
        self,
    ):
        response = self.client_auth.get(self.uri)

        self.assertContains(
            response, "/static/vendor/bootstrap/5.3.8/css/bootstrap.min.css"
        )
        self.assertContains(
            response, "/static/vendor/bootstrap/5.3.8/js/bootstrap.bundle.min.js"
        )
        self.assertContains(response, "/static/css/app_shell.css")
        self.assertContains(response, "/static/css/design_system.css")
        self.assertContains(response, 'class="sidebar-rail"')
        self.assertContains(response, 'class="sidebar-logo-mark"')
        self.assertContains(response, 'class="sidebar-product-meta"')
        self.assertContains(
            response, 'class="sidebar-toggle-control sidebar-desktop-toggle"'
        )
        self.assertContains(
            response, 'class="sidebar-toggle-control sidebar-mobile-toggle"'
        )
        self.assertContains(
            response, 'class="sidebar-toggle-control sidebar-expanded-toggle"'
        )
        self.assertContains(response, 'class="sidebar-rail-utilities"')
        self.assertContains(response, 'class="sidebar-actions"')
        self.assertContains(response, 'id="sidebarPreferencesModal"')
        self.assertContains(response, "data-sidebar-preferences-form")
        self.assertContains(response, 'id="workingContextModal"')
        self.assertContains(response, ">Working context<")
        self.assertContains(response, ">Pinned work<")
        self.assertContains(response, ">Pinned tools<")
        self.assertContains(response, ">More tools<")
        self.assertNotContains(response, 'class="active-report-shortcut')
        self.assertNotContains(response, ">Jump to Report")
        self.assertContains(response, 'id="theme-toggle-switch"')
        self.assertContains(response, 'id="theme-auto-checkbox"')
        self.assertContains(response, 'class="sun"')
        self.assertContains(response, 'class="moon"')
        self.assertContains(response, 'class="cloud"')
        self.assertContains(response, 'aria-controls="sidebar"')
        self.assertContains(response, 'aria-expanded="false"')
        self.assertContains(response, f"v{settings.VERSION}")
        self.assertContains(response, f"Build {settings.RELEASE_DATE}")
        self.assertNotContains(response, 'class="sidebar-footer"')
        self.assertNotContains(response, 'class="sidebar-header-tab"')
        self.assertNotContains(response, 'class="sidebar-navigation-eyebrow"')
        self.assertNotContains(response, "Ghostwriter workspace")
        self.assertNotContains(response, 'class="top-bar')
        self.assertNotContains(response, 'aria-label="breadcrumb"')
        self.assertContains(response, 'class="sidebar-account-row"')
        self.assertContains(response, 'class="sidebar-rail-profile"')
        self.assertContains(response, "data-working-context-tooltip")
        self.assertContains(
            response,
            "data-working-context-tooltip\n"
            '                  data-bs-toggle="modal"',
        )
        self.assertNotContains(response, "/static/css/bootstrap.min.css")
        self.assertNotContains(response, "/static/js/bootstrap.min.js")

    def test_application_shell_displays_viewable_active_engagement(self):
        session = self.client_auth.session
        session["active_report"] = {
            "id": self.report.id,
            "title": self.report.title,
        }
        session.save()

        response = self.client_auth.get(self.uri)

        self.assertEqual(response.context["active_engagement"]["report"], self.report)
        self.assertContains(
            response, 'class="engagement-context engagement-context-active"'
        )
        self.assertNotContains(response, "Open report")
        self.assertNotContains(response, "Open active report")
        self.assertContains(response, 'class="engagement-context-mobile-context"')
        self.assertContains(response, 'aria-label="Show client and project context"')
        self.assertContains(response, "Working on")
        self.assertContains(response, self.report.title)
        self.assertContains(response, self.current_project.client.name)
        self.assertContains(response, self.current_project.get_absolute_url())

    def test_application_shell_ignores_inaccessible_active_engagement(self):
        inaccessible_report = ReportFactory(project=self.inaccessible_project)
        session = self.client_auth.session
        session["active_report"] = {
            "id": inaccessible_report.id,
            "title": inaccessible_report.title,
        }
        session.save()

        response = self.client_auth.get(self.uri)

        self.assertIsNone(response.context["active_engagement"])
        self.assertContains(response, "No working report selected")
        self.assertNotContains(response, inaccessible_report.title)

    def test_application_shell_exposes_persisted_sidebar_state(self):
        session = self.client_auth.session
        session["sidebar"] = {"sticky": True}
        session.save()

        response = self.client_auth.get(self.uri)

        self.assertContains(response, '<nav id="sidebar" class="active">')
        self.assertContains(response, 'aria-expanded="true"')

    def test_view_handles_assignment_without_dates(self):
        ProjectAssignmentFactory(
            project=self.future_project,
            operator=self.user,
            start_date=None,
            end_date=None,
        )

        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")

    def test_dashboard_uses_operator_brief_layout(self):
        response = self.client_auth.get(self.uri)

        self.assertContains(response, 'class="operator-dashboard"')
        self.assertContains(response, ">Operator Brief<")
        self.assertContains(response, ">Your work<")
        self.assertContains(response, ">Engagement runway<")
        self.assertContains(response, "6 todo items")
        self.assertContains(response, ">6 todo</span>")
        self.assertContains(response, "All projects")
        self.assertContains(response, "fa-arrow-right ms-1")
        self.assertContains(response, ">Project calendar<")
        self.assertContains(response, 'id="dashboard-calendar-events"')
        self.assertNotContains(response, ">Ready to Work?<")
        self.assertNotContains(response, ">Assigned Findings<")
        self.assertNotContains(response, ">Assigned Observations<")
        self.assertNotContains(response, ">Recent Background Tasks<")
        self.assertNotContains(response, ">All Systems Go!<")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("user_projects", response.context)
        self.assertIn("active_projects", response.context)
        self.assertIn("dashboard_engagements", response.context)
        self.assertIn("failed_tasks", response.context)
        self.assertIn("assigned_findings", response.context)
        self.assertIn("assigned_observations", response.context)
        self.assertIn("work_items", response.context)
        self.assertEqual(len(response.context["user_projects"]), 2)
        self.assertEqual(response.context["user_projects"][0], self.user_projects[0])
        self.assertEqual(len(response.context["active_projects"]), 1)
        self.assertEqual(
            response.context["active_projects"][0], self.active_projects[0]
        )
        self.assertEqual(len(response.context["dashboard_engagements"]), 1)
        self.assertEqual(
            response.context["dashboard_engagements"][0]["status"], "upcoming"
        )
        self.assertEqual(len(response.context["assigned_findings"]), 3)
        self.assertEqual(len(response.context["assigned_observations"]), 3)
        self.assertEqual(response.context["work_item_count"], 6)
        self.assertEqual(len(response.context["work_items"]), 6)
        self.assertEqual(len(response.context["calendar_events"]), 3)
        self.assertEqual(
            {
                event["extendedProps"]["calendarKind"]
                for event in response.context["calendar_events"]
            },
            {"Project"},
        )
        self.assertEqual(
            {event["url"] for event in response.context["calendar_events"]},
            {
                self.future_project.get_absolute_url(),
                self.other_project.get_absolute_url(),
                self.unassigned_project.get_absolute_url(),
            },
        )
        future_project_event = next(
            event
            for event in response.context["calendar_events"]
            if event["url"] == self.future_project.get_absolute_url()
        )
        self.assertIn(self.future_project.codename, future_project_event["title"])
        self.assertIn(
            self.future_project.start_date.isoformat(), future_project_event["title"]
        )
        self.assertIn(
            self.future_project.end_date.isoformat(), future_project_event["title"]
        )

    def test_active_report_work_is_prioritized(self):
        future_report = ReportFactory(project=self.future_project)
        active_finding = ReportFindingLinkFactory(
            report=future_report,
            assigned_to=self.user,
            title="Active report task",
        )
        session = self.client_auth.session
        session["active_report"] = {
            "id": future_report.id,
            "title": future_report.title,
        }
        session.save()

        response = self.client_auth.get(self.uri)

        self.assertEqual(
            response.context["work_items"][0]["object"],
            active_finding,
        )
        self.assertTrue(response.context["work_items"][0]["is_active_report"])

    def test_assigned_finding_uses_configured_severity_color(self):
        finding = self.assigned_findings[0]
        finding.severity.color = "FF7E79"
        finding.severity.save(update_fields=["color"])

        response = self.client_auth.get(self.uri)

        finding_item = next(
            item
            for item in response.context["work_items"]
            if item["object"].pk == finding.pk and item["kind"] == "Finding"
        )
        self.assertEqual(finding_item["severity_color"], "#FF7E79")
        self.assertContains(response, 'style="--operator-severity-color: #FF7E79;"')

    def test_assigned_finding_uses_safe_fallback_for_invalid_severity_color(self):
        finding = self.assigned_findings[0]
        finding.severity.color = "ZZZZZZ"
        finding.severity.save(update_fields=["color"])

        response = self.client_auth.get(self.uri)

        finding_item = next(
            item
            for item in response.context["work_items"]
            if item["object"].pk == finding.pk and item["kind"] == "Finding"
        )
        self.assertEqual(finding_item["severity_color"], "#6C809A")
        self.assertContains(response, 'style="--operator-severity-color: #6C809A;"')
        self.assertNotContains(response, "--operator-severity-color: ZZZZZZ")

    @patch("ghostwriter.home.views.DjangoHealthChecks")
    def test_regular_operator_dashboard_skips_system_health_checks(self, healthcheck):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 200)
        healthcheck.assert_not_called()
        self.assertIsNone(response.context["system_health"])

    def assert_privileged_calendar_shows_ongoing_projects(self, client):
        response = client.get(self.uri)

        calendar_events = response.context["calendar_events"]

        self.assertEqual(len(calendar_events), 4)
        self.assertEqual(
            {event["extendedProps"]["calendarKind"] for event in calendar_events},
            {"Project"},
        )
        self.assertEqual(
            {event["url"] for event in calendar_events},
            {
                self.future_project.get_absolute_url(),
                self.other_project.get_absolute_url(),
                self.unassigned_project.get_absolute_url(),
                self.inaccessible_project.get_absolute_url(),
            },
        )
        other_project_event = next(
            event
            for event in calendar_events
            if event["url"] == self.other_project.get_absolute_url()
        )
        self.assertIn(self.other_project.codename, other_project_event["title"])
        self.assertIn(
            self.other_project.start_date.isoformat(), other_project_event["title"]
        )
        self.assertIn(
            self.other_project.end_date.isoformat(), other_project_event["title"]
        )
        self.assertEqual(
            len(other_project_event["extendedProps"]["assignedOperators"]), 1
        )
        self.assertIn(
            self.other_user.name,
            other_project_event["extendedProps"]["assignedOperators"][0],
        )
        unassigned_project_events = [
            event
            for event in calendar_events
            if event["url"] == self.unassigned_project.get_absolute_url()
        ]
        self.assertEqual(len(unassigned_project_events), 1)
        self.assertEqual(
            unassigned_project_events[0]["extendedProps"]["assignedOperators"],
            ["No assigned operators"],
        )

    def test_managers_see_all_ongoing_projects_on_calendar(self):
        self.assert_privileged_calendar_shows_ongoing_projects(self.client_manager)

    def test_admins_see_all_ongoing_projects_on_calendar(self):
        self.assert_privileged_calendar_shows_ongoing_projects(self.client_admin)


class ManagementTests(TestCase):
    """Collection of tests for :view:`home.Management`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:management")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/management.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("timezone", response.context)

    def test_view_uses_configuration_cards_and_contextual_tests(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="management-card"', count=7)
        self.assertContains(
            response, 'class="management-card management-card-wide"', count=1
        )
        self.assertContains(response, "System Configuration")
        self.assertContains(response, "Test connection", count=2)
        self.assertNotContains(response, 'class="table table-responsive-lg')


class UpdateSessionTests(TestCase):
    """Collection of tests for :view:`home.update_session`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("home:ajax_update_session")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_sticky_sidebar_value(self):
        self.client_auth.post(self.uri, {"session_data": "sidebar"})
        session = self.client_auth.session
        self.assertEqual(session["sidebar"]["sticky"], True)

        self.client_auth.post(self.uri, {"session_data": "sidebar"})
        session = self.client_auth.session
        self.assertEqual(session["sidebar"]["sticky"], False)

    def test_invalid_get_method(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 405)


class SidebarPreferencesTests(TestCase):
    """Tests for permission-aware, persistent sidebar shortcuts."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("home:sidebar_preferences")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

    def test_view_requires_login(self):
        response = self.client.post(self.uri)

        self.assertEqual(response.status_code, 302)

    def test_view_rejects_get(self):
        response = self.client_auth.get(self.uri)

        self.assertEqual(response.status_code, 405)

    def test_view_saves_valid_shortcuts_and_order(self):
        response = self.client_auth.post(
            self.uri,
            {
                "pinned": ["oplogs", "domains", "not-a-navigation-item"],
                "order": "domains,not-a-navigation-item,oplogs,findings",
                "panel_order": "pinned_work,not-a-panel,working_context",
                "visible_panels": ["pinned_work"],
                "next": reverse("home:dashboard"),
            },
        )

        self.assertRedirects(response, reverse("home:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.sidebar_preferences["version"],
            SIDEBAR_PREFERENCES_VERSION,
        )
        self.assertEqual(
            self.user.sidebar_preferences["pinned"],
            ["domains", "oplogs"],
        )
        self.assertNotIn(
            "not-a-navigation-item",
            self.user.sidebar_preferences["order"],
        )
        self.assertNotIn("management", self.user.sidebar_preferences["order"])
        self.assertNotIn("admin", self.user.sidebar_preferences["order"])
        self.assertEqual(
            self.user.sidebar_preferences["panel_order"],
            ["pinned_work", "working_context"],
        )
        self.assertEqual(
            self.user.sidebar_preferences["visible_panels"],
            ["pinned_work"],
        )

    def test_view_rejects_an_external_next_url(self):
        response = self.client_auth.post(
            self.uri,
            {
                "pinned": ["findings"],
                "order": "findings",
                "next": "https://example.com/leave-ghostwriter",
            },
        )

        self.assertRedirects(response, reverse("home:dashboard"))

    def test_view_resets_shortcuts_to_defaults(self):
        self.user.sidebar_preferences = {
            "version": SIDEBAR_PREFERENCES_VERSION,
            "pinned": ["oplogs"],
            "order": ["oplogs", "findings"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.post(
            self.uri,
            {
                "action": "reset",
                "next": reverse("home:dashboard"),
            },
        )

        self.assertRedirects(response, reverse("home:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.sidebar_preferences["pinned"],
            list(DEFAULT_PINNED),
        )
        self.assertEqual(self.user.sidebar_preferences["pinned"], [])
        self.assertEqual(
            self.user.sidebar_preferences["order"],
            [
                item_id
                for item_id in DEFAULT_OPTIONAL_ORDER
                if item_id not in {"management", "admin"}
            ],
        )
        self.assertEqual(
            self.user.sidebar_preferences["panel_order"],
            list(DEFAULT_PANEL_ORDER),
        )
        self.assertEqual(
            self.user.sidebar_preferences["visible_panels"],
            list(DEFAULT_VISIBLE_PANELS),
        )

        response = self.client_auth.get(reverse("home:dashboard"))
        self.assertEqual(response.context["sidebar_navigation"]["pinned"], [])

    def test_version_one_preferences_keep_shortcuts_and_gain_default_panels(self):
        self.user.sidebar_preferences = {
            "version": 1,
            "pinned": ["oplogs"],
            "order": ["oplogs", "findings", "templates"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.get(reverse("home:dashboard"))
        preferences = response.context["sidebar_navigation"]["preferences"]

        self.assertEqual(preferences["version"], SIDEBAR_PREFERENCES_VERSION)
        self.assertEqual(preferences["pinned"], ["oplogs"])
        self.assertEqual(preferences["panel_order"], list(DEFAULT_PANEL_ORDER))
        self.assertEqual(
            preferences["visible_panels"],
            list(DEFAULT_VISIBLE_PANELS),
        )

    def test_legacy_form_submission_preserves_panel_preferences(self):
        self.user.sidebar_preferences = {
            "version": SIDEBAR_PREFERENCES_VERSION,
            "pinned": ["findings"],
            "order": list(DEFAULT_OPTIONAL_ORDER),
            "panel_order": ["pinned_work", "working_context"],
            "visible_panels": ["pinned_work"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.post(
            self.uri,
            {
                "pinned": ["oplogs"],
                "order": "oplogs,findings",
                "next": reverse("home:dashboard"),
            },
        )

        self.assertRedirects(response, reverse("home:dashboard"))
        self.user.refresh_from_db()
        self.assertEqual(
            self.user.sidebar_preferences["panel_order"],
            ["pinned_work", "working_context"],
        )
        self.assertEqual(
            self.user.sidebar_preferences["visible_panels"],
            ["pinned_work"],
        )

    def test_dashboard_uses_panel_visibility_and_order(self):
        self.user.sidebar_preferences = {
            "version": SIDEBAR_PREFERENCES_VERSION,
            "pinned": ["findings", "templates"],
            "order": list(DEFAULT_OPTIONAL_ORDER),
            "panel_order": ["pinned_work", "working_context"],
            "visible_panels": ["pinned_work"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.get(reverse("home:dashboard"))

        panels = {
            panel["id"]: panel
            for panel in response.context["sidebar_navigation"]["panels"]
        }
        self.assertFalse(panels["working_context"]["visible"])
        self.assertTrue(panels["pinned_work"]["visible"])
        self.assertNotContains(response, "sidebar-working-context-action")
        self.assertContains(response, "sidebar-pinned-work-section")

    def test_dashboard_renders_visible_panels_in_saved_order(self):
        self.user.sidebar_preferences = {
            "version": SIDEBAR_PREFERENCES_VERSION,
            "pinned": ["findings", "templates"],
            "order": list(DEFAULT_OPTIONAL_ORDER),
            "panel_order": ["pinned_work", "working_context"],
            "visible_panels": ["pinned_work", "working_context"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.get(reverse("home:dashboard"))
        content = response.content.decode()

        self.assertLess(
            content.index('data-sidebar-panel-id="pinned_work"'),
            content.index('data-sidebar-panel-id="working_context"'),
        )

    def test_dashboard_uses_saved_shortcuts_and_keeps_unpinned_tools_available(self):
        self.user.sidebar_preferences = {
            "version": SIDEBAR_PREFERENCES_VERSION,
            "pinned": ["oplogs"],
            "order": ["oplogs", "findings", "templates"],
        }
        self.user.save(update_fields=["sidebar_preferences"])

        response = self.client_auth.get(reverse("home:dashboard"))

        navigation = response.context["sidebar_navigation"]
        self.assertEqual(
            [item["id"] for item in navigation["pinned"]],
            ["oplogs"],
        )
        self.assertIn(
            "findings",
            [item["id"] for item in navigation["more"]],
        )
        self.assertContains(response, reverse("reporting:findings"))


class WorkingContextTests(TestCase):
    """Tests for the working-report switcher and pinned work."""

    @classmethod
    def setUpTestData(cls):
        cls.report = ReportFactory()
        cls.other_report = ReportFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.catalog_uri = reverse("home:working_context_catalog")
        cls.pin_uri = reverse("home:toggle_workspace_pin")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(
                username=self.manager.username, password=PASSWORD
            )
        )

    def test_views_require_login(self):
        self.assertEqual(self.client.get(self.catalog_uri).status_code, 302)
        self.assertEqual(
            self.client.post(
                self.pin_uri, {"type": "report", "id": self.report.id}
            ).status_code,
            302,
        )

    def test_catalog_is_permission_filtered(self):
        response = self.client_auth.get(self.catalog_uri)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["groups"], [])

        ProjectAssignmentFactory(
            project=self.report.project, operator=self.user
        )
        response = self.client_auth.get(self.catalog_uri)
        report_ids = [
            report["id"]
            for group in response.json()["groups"]
            for report in group["reports"]
        ]

        self.assertIn(self.report.id, report_ids)
        self.assertNotIn(self.other_report.id, report_ids)

    def test_catalog_marks_the_working_report(self):
        session = self.client_mgr.session
        session["active_report"] = {
            "id": self.report.id,
            "title": self.report.title,
        }
        session.save()

        response = self.client_mgr.get(self.catalog_uri)
        reports = [
            report
            for group in response.json()["groups"]
            for report in group["reports"]
        ]
        working_report = next(
            report for report in reports if report["id"] == self.report.id
        )

        self.assertTrue(working_report["working"])
        self.assertEqual(
            response.json()["active_report_id"], self.report.id
        )

    def test_user_can_toggle_visible_pinned_work(self):
        response = self.client_mgr.post(
            self.pin_uri, {"type": "report", "id": self.report.id}
        )

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()["pinned"])
        self.manager.refresh_from_db()
        self.assertEqual(
            self.manager.workspace_preferences,
            {
                "version": WORKSPACE_PREFERENCES_VERSION,
                "pinned": [{"type": "report", "id": self.report.id}],
                "recent_reports": [],
            },
        )
        self.assertEqual(
            response.json()["pinned_items"][0]["label"],
            self.report.title,
        )

        response = self.client_mgr.post(
            self.pin_uri, {"type": "report", "id": self.report.id}
        )
        self.assertFalse(response.json()["pinned"])
        self.manager.refresh_from_db()
        self.assertEqual(self.manager.workspace_preferences["pinned"], [])

    def test_user_cannot_pin_inaccessible_work(self):
        response = self.client_auth.post(
            self.pin_uri, {"type": "report", "id": self.report.id}
        )

        self.assertEqual(response.status_code, 403)
        self.user.refresh_from_db()
        self.assertEqual(self.user.workspace_preferences, {})

    def test_shell_renders_visible_pinned_work(self):
        self.manager.workspace_preferences = {
            "version": WORKSPACE_PREFERENCES_VERSION,
            "pinned": [
                {"type": "client", "id": self.report.project.client.id},
                {"type": "project", "id": self.report.project.id},
                {"type": "report", "id": self.report.id},
            ],
            "recent_reports": [],
        }
        self.manager.save(update_fields=["workspace_preferences"])

        response = self.client_mgr.get(reverse("home:dashboard"))

        self.assertContains(response, ">Pinned work<")
        self.assertContains(response, self.report.title)
        self.assertContains(
            response,
            'data-pinned-work-type="report"',
        )
        self.assertContains(
            response,
            f'aria-label="Pinned report: {self.report.title}"',
        )


class TestAWSConnectionTests(TestCase):
    """Collection of tests for :view:`home.TestAWSConnection`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:ajax_test_aws")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)


class TestDOConnectionTests(TestCase):
    """Collection of tests for :view:`home.TestDOConnection`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:ajax_test_do")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)


class TestNamecheapConnectionTests(TestCase):
    """Collection of tests for :view:`home.TestNamecheapConnection`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:ajax_test_namecheap")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)


class TestSlackConnectionTests(TestCase):
    """Collection of tests for :view:`home.TestSlackConnection`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:ajax_test_slack")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)


class TestVirusTotalConnectionTests(TestCase):
    """Collection of tests for :view:`home.TestSlackConnection`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = reverse("home:ajax_test_virustotal")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        )

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
