# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.db.models import Q
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import (
    GroupFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    UserFactory,
)
from ghostwriter.home.templatetags import custom_tags

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.group_1 = GroupFactory(name="Group 1")
        cls.group_2 = GroupFactory(name="Group 2")
        cls.user = UserFactory(password=PASSWORD, groups=(cls.group_1,))
        cls.project = ProjectFactory()
        cls.report = ReportFactory(project=cls.project)

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


class DashboardTests(TestCase):
    """Collection of tests for :view:`home.dashboard`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.Project = ProjectFactory._meta.model
        cls.ProjectAssignment = ProjectAssignmentFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model

        cls.current_project = ProjectFactory(
            start_date=date.today() - timedelta(days=14),
            end_date=date.today(),
            complete=True
        )
        cls.future_project = ProjectFactory(
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
            complete=False
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
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )

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
        self.assertEqual(
            response.context["active_projects"][0], self.active_projects[0]
        )
        self.assertEqual(len(response.context["user_tasks"]), 3)


class ManagementTests(TestCase):
    """Collection of tests for :view:`home.Management`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.staff_user = UserFactory(password=PASSWORD, is_staff=True)

        cls.uri = reverse("home:management")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_staff = Client()
        self.assertTrue(
            self.client_auth.login(username=self.user.username, password=PASSWORD)
        )
        self.assertTrue(
            self.client_staff.login(username=self.staff_user.username, password=PASSWORD)
        )

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_permissions(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_staff.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "home/management.html")

    def test_custom_context_exists(self):
        response = self.client_staff.get(self.uri)
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
