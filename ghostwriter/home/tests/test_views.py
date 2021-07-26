# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.db.models import Q
from django.test import Client, TestCase
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
    ProjectObjectiveFactory,
    ProjectScopeFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    StaticServerFactory,
    UserFactory,
)
from ghostwriter.rolodex.templatetags import determine_primary

logging.disable(logging.INFO)

PASSWORD = "SuperNaturalReporting!"


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectObjective = ProjectObjectiveFactory._meta.model
        cls.project = ProjectFactory()
        for x in range(3):
            ProjectObjectiveFactory(project=cls.project)

        cls.server = StaticServerFactory()
        cls.aux_address_1 = AuxServerAddressFactory(
            static_server=cls.server, ip_address="1.1.1.1", primary=True
        )
        cls.aux_address_2 = AuxServerAddressFactory(
            static_server=cls.server, ip_address="1.1.1.2", primary=False
        )

        cls.scope = ProjectScopeFactory(
            project=cls.project,
            scope="1.1.1.1\r\n1.1.1.2\r\n1.1.1.3\r\n1.1.1.4\r\n1.1.1.5",
        )

    def setUp(self):
        pass

    def test_tags(self):
        queryset = self.ProjectObjective.objects.all()

        obj_dict = determine_primary.group_by_priority(queryset)
        self.assertEqual(len(obj_dict), 3)

        for group in obj_dict:
            self.assertEqual(
                determine_primary.get_item(obj_dict, group), obj_dict.get(group)
            )

        future_date = date.today() + timedelta(days=10)
        self.assertEqual(determine_primary.plus_days(date.today(), 10), future_date)
        self.assertEqual(determine_primary.days_left(future_date), 10)

        self.assertEqual(determine_primary.get_primary_address(self.server), "1.1.1.1")

        self.assertEqual(
            determine_primary.get_scope_preview(self.scope.scope, 5),
            "1.1.1.1\n1.1.1.2\n1.1.1.3\n1.1.1.4\n1.1.1.5",
        )
        self.assertEqual(
            determine_primary.get_scope_preview(self.scope.scope, 2), "1.1.1.1\n1.1.1.2"
        )


class DashboardTests(TestCase):
    """Collection of tests for :view:`home.dashboard`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.Project = ProjectFactory._meta.model
        cls.ProjectAssignment = ProjectAssignmentFactory._meta.model
        cls.ReportFindingLink = ReportFindingLinkFactory._meta.model

        cls.current_project = ProjectFactory(
            start_date=date.today(), end_date=date.today() + timedelta(days=14)
        )
        cls.future_project = ProjectFactory(
            start_date=date.today() + timedelta(days=14),
            end_date=date.today() + timedelta(days=28),
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
        ).filter(
            Q(operator=cls.user)
            & Q(start_date__lte=date.today())
            & Q(end_date__gte=date.today())
        )
        cls.upcoming_project = cls.ProjectAssignment.objects.select_related(
            "project", "project__client", "role"
        ).filter(Q(operator=cls.user) & Q(start_date__gt=date.today()))

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
        self.assertIn("upcoming_project", response.context)
        self.assertIn("recent_tasks", response.context)
        self.assertIn("user_tasks", response.context)
        self.assertEqual(len(response.context["user_projects"]), 1)
        self.assertEqual(response.context["user_projects"][0], self.user_projects[0])
        self.assertEqual(len(response.context["upcoming_project"]), 1)
        self.assertEqual(
            response.context["upcoming_project"][0], self.upcoming_project[0]
        )
        self.assertEqual(len(response.context["user_tasks"]), 3)


class UserProfileTests(TestCase):
    """Collection of tests for :view:`home.profile`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)

        cls.uri = reverse("home:upload_avatar")

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
        self.assertTemplateUsed(response, "home/upload_avatar.html")


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
