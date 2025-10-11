# Standard Libraries
import logging
from datetime import date, datetime, timedelta
from io import StringIO

# Django Imports
from django.conf import settings
from django.core.management import call_command
from django.db.models import Q
from django.test import Client, TestCase
from django.test.utils import override_settings
from django.urls import reverse

# 3rd Party Libraries
from allauth.mfa.totp.internal.auth import generate_totp_secret, TOTP

# Ghostwriter Libraries
from ghostwriter.factories import (
    GroupFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    UserFactory,
)
from ghostwriter.home.templatetags import custom_tags

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


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
        out = self.call_command("ghostwriter/reporting/fixtures/initial.json", "--force")
        self.assertIn("Applying all fixtures.", out)
        self.assertIn("Found 17 new records to insert into the database.", out)


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
        cls.assignment = ProjectAssignmentFactory(project=cls.project, operator=cls.user)

        cls.Objective = ProjectObjectiveFactory._meta.model
        cls.objective = ProjectObjectiveFactory(project=cls.project, complete=False)
        cls.complete_objective = ProjectObjectiveFactory(project=cls.project, complete=True)
        cls.objectives = cls.Objective.objects.filter(project=cls.project)

        cls.num_of_findings = 3
        ReportFindingLinkFactory.create_batch(cls.num_of_findings, report=cls.report, assigned_to=cls.user)

        cls.uri = reverse("home:dashboard")

    def setUp(self):
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

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

        result = custom_tags.settings_value("DATE_FORMAT")
        self.assertEqual(result, settings.DATE_FORMAT)

        result = custom_tags.count_incomplete_objectives(self.objectives)
        self.assertEqual(result, 1)

        example_html = "<body><p>Example HTML</p><br /><br /><p></p></body>"
        result = custom_tags.strip_empty_tags(example_html)
        # The tag uses BS4's `prettify()` method to format the HTML, so there are newlines and indentations
        self.assertEqual(result, "<html>\n <body>\n  <p>\n   Example HTML\n  </p>\n </body>\n</html>\n")

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


class DashboardTests(TestCase):
    """Collection of tests for :view:`home.dashboard`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.Project = ProjectFactory._meta.model
        cls.ProjectAssignment = ProjectAssignmentFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model

        cls.current_project = ProjectFactory(
            start_date=date.today() - timedelta(days=14), end_date=date.today(), complete=True
        )
        cls.future_project = ProjectFactory(
            start_date=date.today() + timedelta(days=14), end_date=date.today() + timedelta(days=28), complete=False
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

        cls.report = ReportFactory(project=cls.current_project)
        ReportFindingLinkFactory.create_batch(3, report=cls.report, assigned_to=cls.user)

        cls.user_tasks = (
            cls.ReportFindingLink.objects.select_related("report", "report__project")
            .filter(Q(assigned_to=cls.user) & Q(report__complete=False) & Q(complete=False))
            .order_by("report__project__end_date")[:10]
        )
        cls.user_projects = cls.ProjectAssignment.objects.select_related("project", "project__client", "role").filter(
            Q(operator=cls.user)
        )
        cls.active_projects = cls.ProjectAssignment.objects.select_related("project", "project__client", "role").filter(
            Q(operator=cls.user) & Q(project__complete=False)
        )

        cls.uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "index.html")

    def test_custom_context_exists(self):
        response = self.client_auth.get(self.uri)
        self.assertIn("user_projects", response.context)
        self.assertIn("active_projects", response.context)
        self.assertIn("recent_tasks", response.context)
        self.assertIn("user_tasks", response.context)
        self.assertEqual(len(response.context["user_projects"]), 2)
        self.assertEqual(response.context["user_projects"][0], self.user_projects[0])
        self.assertEqual(len(response.context["active_projects"]), 1)
        self.assertEqual(response.context["active_projects"][0], self.active_projects[0])
        self.assertEqual(len(response.context["user_tasks"]), 3)


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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

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
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_post(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_staff(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ProtectedServeTest(TestCase):
    """Collection of tests for :view:`home.protected_serve`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.uri = "/media/templates"

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    @override_settings(DEBUG=True)
    def test_view_uri(self):
        assert settings.DEBUG
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 404)
        self.assertContains(response, "ghostwriter.home.views.protected_serve", status_code=404)

    def test_view_uri_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)
