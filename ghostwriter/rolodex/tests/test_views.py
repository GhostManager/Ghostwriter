# Standard Libraries
import logging
import os
from datetime import date, timedelta

# 3rd Party Libraries
import factory
from bs4 import BeautifulSoup

# Django Imports
from django.conf import settings
from django.contrib.auth.models import Permission
from django.template.loader import render_to_string
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.commandcenter.models import BloodHoundConfiguration
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ClientContactFactory,
    ClientFactory,
    ClientInviteFactory,
    ClientNoteFactory,
    DeconflictionFactory,
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
    HistoryFactory,
    ObjectivePriorityFactory,
    ObjectiveStatusFactory,
    ProjectContactFactory,
    ProjectRoleFactory,
    ProjectFactory,
    ProjectInviteFactory,
    ProjectNoteFactory,
    ProjectAssignmentFactory,
    ProjectObjectiveFactory,
    ProjectSubtaskFactory,
    ProjectScopeFactory,
    ProjectTargetFactory,
    ProjectSubtaskFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ServerHistoryFactory,
    SeverityFactory,
    StaticServerFactory,
    TransientServerFactory,
    UserFactory,
    WhiteCardFactory,
)
from ghostwriter.rolodex.forms_project import (
    ProjectAssignmentFormSet,
    ProjectObjectiveFormSet,
    ProjectScopeFormSet,
    ProjectTargetFormSet,
    WhiteCardFormSet,
)
from ghostwriter.rolodex.templatetags import determine_primary

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


def assert_active_tab(test_case, response, tab_id):
    soup = BeautifulSoup(response.content, "html.parser")
    tab_link = soup.select_one(f'a[data-bs-toggle="tab"][data-tab-hash="#{tab_id}"]')
    tab_pane = soup.select_one(f"#tab-pane-{tab_id}.tab-pane")
    legacy_anchor = soup.select_one(f"#{tab_id}.tab-pane")

    test_case.assertIsNotNone(tab_link)
    test_case.assertIsNotNone(tab_pane)
    test_case.assertIsNone(legacy_anchor)
    test_case.assertEqual(tab_link.get("href"), f"#{tab_id}")
    test_case.assertEqual(tab_link.get("data-bs-target"), f"#tab-pane-{tab_id}")
    test_case.assertIn("active", tab_link.get("class", []))
    test_case.assertIn("active", tab_pane.get("class", []))


class IndexViewTests(TestCase):
    """Collection of tests for :view:`rolodex.index`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("rolodex:index")
        cls.redirect_uri = reverse("home:dashboard")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.post(self.uri)
        self.assertRedirects(response, self.redirect_uri)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectObjective = ProjectObjectiveFactory._meta.model
        cls.project = ProjectFactory()
        for _ in range(3):
            ProjectObjectiveFactory(project=cls.project)

        cls.server = StaticServerFactory()
        cls.aux_address_1 = AuxServerAddressFactory(static_server=cls.server, ip_address="1.1.1.1", primary=True)
        cls.aux_address_2 = AuxServerAddressFactory(static_server=cls.server, ip_address="1.1.1.2", primary=False)

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
            self.assertEqual(determine_primary.get_item(obj_dict, group), obj_dict.get(group))

        future_date = date.today() + timedelta(days=10)
        self.assertEqual(determine_primary.plus_days(date.today(), 10), future_date)
        self.assertEqual(determine_primary.days_left(future_date), 10)

        self.assertEqual(determine_primary.get_primary_address(self.server), "1.1.1.1")

        self.assertEqual(
            determine_primary.get_scope_preview(self.scope.scope, 5),
            "1.1.1.1\n1.1.1.2\n1.1.1.3\n1.1.1.4\n1.1.1.5",
        )
        self.assertEqual(determine_primary.get_scope_preview(self.scope.scope, 2), "1.1.1.1\n1.1.1.2")


# Tests related to misc views


class RollCodenameViewTests(TestCase):
    """Collection of tests for :view:`rolodex.roll_codename`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.uri = reverse("rolodex:ajax_roll_codename")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


# Tests related to :model:`rolodex.ProjectObjective`


class ProjectObjectiveStatusUpdateViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectObjectiveStatusUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.active = ObjectiveStatusFactory(objective_status="Active")
        cls.in_progress = ObjectiveStatusFactory(objective_status="In Progress")
        cls.missed = ObjectiveStatusFactory(objective_status="Missed")
        cls.objective = ProjectObjectiveFactory(status=cls.active)
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:ajax_set_objective_status", kwargs={"pk": cls.objective.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD)
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "result": "success",
                "status": f"{self.in_progress}",
            },
        )

        self.objective.refresh_from_db()
        self.assertEqual(self.objective.status, self.in_progress)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "result": "success",
                "status": f"{self.missed}",
            },
        )

        self.objective.refresh_from_db()
        self.assertEqual(self.objective.status, self.missed)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(
            force_str(response.content),
            {
                "result": "success",
                "status": f"{self.active}",
            },
        )

        self.objective.refresh_from_db()
        self.assertEqual(self.objective.status, self.active)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)


class ProjectObjectiveToggleViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectStatusToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.objective = ProjectObjectiveFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:ajax_toggle_project_objective", kwargs={"pk": cls.objective.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD)
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "message": "Objective successfully marked as complete.",
            "toggle": 1,
        }
        self.objective.complete = False
        self.objective.save()

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        self.objective.refresh_from_db()
        self.assertEqual(self.objective.complete, True)

        data = {
            "result": "success",
            "message": "Objective successfully marked as incomplete.",
            "toggle": 0,
        }
        response = self.client_mgr.post(self.uri)
        self.assertJSONEqual(force_str(response.content), data)

        self.objective.refresh_from_db()
        self.assertEqual(self.objective.complete, False)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)


# Tests related to :model:`rolodex.Project`


class ProjectStatusToggleViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectStatusToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:ajax_toggle_project", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD)
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "message": "Project successfully marked as complete.",
            "status": "Complete",
            "toggle": 1,
        }
        self.project.complete = False
        self.project.save()

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        self.project.refresh_from_db()
        self.assertEqual(self.project.complete, True)

        data = {
            "result": "success",
            "message": "Project successfully marked as incomplete.",
            "status": "In Progress",
            "toggle": 0,
        }
        response = self.client_mgr.post(self.uri)
        self.assertJSONEqual(force_str(response.content), data)

        self.project.refresh_from_db()
        self.assertEqual(self.project.complete, False)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)


# Tests related to :model:`rolodex.ProjectScope`


class ProjectScopeExportViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectScopeExport`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.scope = ProjectScopeFactory(name="TestScope")
        cls.uri = reverse("rolodex:ajax_export_project_scope", kwargs={"pk": cls.scope.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD)
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 403)

    def test_download_success(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        self.assertEqual(
            response.get("Content-Disposition"),
            f'attachment; filename="{self.scope.name}_scope.txt"',
        )


class ClientNoteUpdateTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientNote = ClientNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = ClientNoteFactory(operator=cls.user)
        cls.uri = reverse("rolodex:client_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = ClientNoteFactory()
        cls.other_user_uri = reverse("rolodex:client_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ClientNoteDeleteTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientNote = ClientNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.ClientNote.objects.all().delete()
        note = ClientNoteFactory(operator=self.user)
        uri = reverse("rolodex:ajax_delete_client_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.ClientNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.ClientNote.objects.all()), 0)

    def test_view_permissions(self):
        note = ClientNoteFactory()
        uri = reverse("rolodex:ajax_delete_client_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = ClientNoteFactory()
        uri = reverse("rolodex:ajax_delete_client_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class ProjectNoteUpdateTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectNoteUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectNote = ProjectNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.note = ProjectNoteFactory(operator=cls.user)
        cls.uri = reverse("rolodex:project_note_edit", kwargs={"pk": cls.note.pk})
        cls.other_user_note = ProjectNoteFactory()
        cls.other_user_uri = reverse("rolodex:project_note_edit", kwargs={"pk": cls.other_user_note.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_permissions(self):
        response = self.client_auth.get(self.other_user_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)


class ProjectNoteDeleteTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectNoteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectNote = ProjectNoteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        self.ProjectNote.objects.all().delete()
        note = ProjectNoteFactory(operator=self.user)
        uri = reverse("rolodex:ajax_delete_project_note", kwargs={"pk": note.pk})

        self.assertEqual(len(self.ProjectNote.objects.all()), 1)

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Note successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.ProjectNote.objects.all()), 0)

    def test_view_permissions(self):
        note = ProjectNoteFactory()
        uri = reverse("rolodex:ajax_delete_project_note", kwargs={"pk": note.pk})

        response = self.client_auth.post(uri)
        self.assertEqual(response.status_code, 302)

    def test_view_requires_login(self):
        note = ProjectNoteFactory()
        uri = reverse("rolodex:ajax_delete_project_note", kwargs={"pk": note.pk})

        response = self.client.post(uri)
        self.assertEqual(response.status_code, 302)


class ProjectCreateTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.Project = ProjectFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.project_client = ClientFactory()
        cls.uri = reverse("rolodex:project_create", kwargs={"pk": cls.project_client.pk})
        cls.no_client_uri = reverse("rolodex:project_create_no_client")
        cls.client_cancel_uri = reverse("rolodex:client_detail", kwargs={"pk": cls.project_client.pk})
        cls.no_client_cancel_uri = reverse("rolodex:projects")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        response = self.client_mgr.get(self.no_client_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client.get(self.no_client_uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        response = self.client_auth.get(self.no_client_uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/project_form.html")

    def test_view_selects_initial_tab(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        assert_active_tab(self, response, "project")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        self.assertIn("assignments", response.context)
        self.assertIn("cancel_link", response.context)

        self.assertTrue(isinstance(response.context["assignments"], ProjectAssignmentFormSet))
        self.assertTrue(isinstance(response.context["assignments"], ProjectAssignmentFormSet))
        self.assertEqual(response.context["cancel_link"], self.client_cancel_uri)

        response = self.client_mgr.get(self.no_client_uri)
        self.assertEqual(response.context["cancel_link"], self.no_client_cancel_uri)

    def test_initial_form_values(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn("client", response.context["form"].initial)
        self.assertIn("codename", response.context["form"].initial)
        self.assertEqual(response.context["client"], self.project_client)

        response = self.client_mgr.get(self.no_client_uri)
        self.assertIn("client", response.context["form"].initial)
        self.assertEqual(response.context["client"], "")


class ProjectUpdateTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.uri = reverse("rolodex:project_update", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/project_form.html")

    def test_view_uses_modern_project_form_layout(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'id="tab-bar"')
        self.assertContains(response, 'class="project-form-shell"')
        self.assertContains(response, 'data-tiptap-min-height="240"')
        self.assertContains(response, "formset-add-assign formset-action-button")
        self.assertContains(response, "formset-add-invite formset-action-button")
        self.assertContains(response, "formset-del-button formset-action-button")
        self.assertContains(response, "projectCollectionConfigs")
        self.assertContains(response, "isNewProjectCollectionForm")
        self.assertContains(response, "gwInitTiptapStableContainer")

    def test_view_selects_initial_tab(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        assert_active_tab(self, response, "project")


class ProjectComponentsUpdateTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectComponentsUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.Project = ProjectFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.uri = reverse("rolodex:project_component_update", kwargs={"pk": cls.project.pk})
        cls.cancel_uri = reverse("rolodex:project_detail", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/project_form.html")

    def test_view_uses_modern_component_form_layout(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'id="tab-bar"')
        self.assertContains(response, 'class="project-form-shell"')
        self.assertContains(response, 'data-tiptap-min-height="240"')
        self.assertContains(response, "formset-add-contact formset-action-button")
        self.assertContains(response, "formset-add-card formset-action-button")
        self.assertContains(response, "formset-add-scope formset-action-button")
        self.assertContains(response, "formset-add-obj formset-action-button")
        self.assertContains(response, "formset-add-target formset-action-button")
        self.assertContains(response, "formset-del-button formset-action-button")
        self.assertContains(response, "projectCollectionConfigs")
        self.assertContains(response, "isNewProjectCollectionForm")
        self.assertContains(response, "gwInitTiptapStableContainer")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        self.assertIn("objectives", response.context)
        self.assertIn("scopes", response.context)
        self.assertIn("targets", response.context)
        self.assertIn("whitecards", response.context)
        self.assertIn("cancel_link", response.context)

        self.assertTrue(isinstance(response.context["objectives"], ProjectObjectiveFormSet))
        self.assertTrue(isinstance(response.context["scopes"], ProjectScopeFormSet))
        self.assertTrue(isinstance(response.context["targets"], ProjectTargetFormSet))
        self.assertTrue(isinstance(response.context["whitecards"], WhiteCardFormSet))
        self.assertEqual(response.context["cancel_link"], self.cancel_uri)


class ClientListViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientListView`."""

    @classmethod
    def setUpTestData(cls):
        client_1 = ClientFactory(name="SpecterOps", short_name="SO", codename="BloodHound")
        client_2 = ClientFactory(name="SpecterPops", short_name="SP", codename="Ghost")
        ClientFactory(name="Test", short_name="TST", codename="Popsicle")
        cls.user = UserFactory(password=PASSWORD)
        cls.assign_user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:clients")
        ClientInviteFactory(user=cls.user, client=client_1)
        p = ProjectFactory(client=client_2)
        ProjectAssignmentFactory(project=p, operator=cls.assign_user)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_assign = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))
        self.assertTrue(self.client_assign.login(username=self.assign_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/client_list.html")

    def test_client_library_uses_modern_header_filters_and_results_card(self):
        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        name_filter = soup.select_one("#id_name")

        self.assertContains(response, 'class="library-page client-library-page d-grid gap-4"')
        self.assertContains(response, '<h2>Client Library</h2>')
        self.assertNotContains(response, '<span class="detail-eyebrow">Rolodex</span>')
        self.assertContains(response, 'class="filter-form library-filters client-library-filters"')
        self.assertContains(response, 'class="library-results client-library-results"')
        self.assertContains(response, 'class="tablesorter table table-hover library-table client-library-table"')
        self.assertContains(response, 'library-primary-link client-library-name-link', count=3)
        self.assertContains(response, 'id="resetSortBtn"')
        self.assertNotContains(response, 'btn btn-info col-2')
        self.assertEqual(name_filter.get("data-1p-ignore"), "true")

    def test_client_filtering(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 3)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)
        self.assertEqual(response.context["filter"].qs[0].name, "SpecterOps")

        response = self.client_assign.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)
        self.assertEqual(response.context["filter"].qs[0].name, "SpecterPops")

        response = self.client_mgr.get(f"{self.uri}?name=SpecterOps")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)

        response = self.client_mgr.get(f"{self.uri}?name=pops")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 2)

    def test_tags_are_scoped_to_visible_clients(self):
        visible_client = ClientFactory(name="Visible Client")
        hidden_client = ClientFactory(name="Hidden Client")
        ClientInviteFactory(user=self.user, client=visible_client)
        visible_client.tags.add("visible-tag")
        hidden_client.tags.add("hidden-tag")

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-tag", tag_names)
        self.assertNotIn("hidden-tag", tag_names)
        self.assertIn("visible-tag", response.context["autocomplete_data"]["tags"])
        self.assertNotIn("hidden-tag", response.context["autocomplete_data"]["tags"])


class ClientCreateViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.extra_field_model = ExtraFieldModelFactory(
            model_internal_name="rolodex.Client",
            model_display_name="Clients",
        )
        cls.extra_field = ExtraFieldSpecFactory(
            internal_name="analyst_notes",
            display_name="Analyst Notes",
            description="Internal context for this client.",
            type="rich_text",
            target_model=cls.extra_field_model,
        )
        cls.uri = reverse("rolodex:client_create")

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_selects_initial_tab(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        assert_active_tab(self, response, "client")

    def test_view_uses_modern_tabs_and_native_logo_input(self):
        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")

        tab_bar = soup.select_one("ul#tab-bar.nav.nav-tabs")
        logo_input = soup.select_one('input#id_logo[type="file"].form-control')

        self.assertIsNotNone(tab_bar)
        self.assertIsNotNone(logo_input)
        self.assertContains(response, "formset-actions")
        self.assertContains(response, "formset-action-button")
        self.assertContains(response, "gwInitTiptapStableContainer")
        self.assertNotContains(response, "formset-del-button col-8")
        self.assertNotContains(response, "formset-add-poc mb-2 offset-4 col-4")

    def test_extra_fields_use_a_dedicated_card_tab(self):
        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")

        client_pane = soup.select_one("#tab-pane-client")
        extra_fields_pane = soup.select_one("#tab-pane-extra-fields")
        extra_fields_link = soup.select_one(
            'a[data-bs-toggle="tab"][data-tab-hash="#extra-fields"]'
        )

        self.assertIsNotNone(extra_fields_link)
        self.assertIsNotNone(extra_fields_pane)
        self.assertIsNone(client_pane.select_one("#div_id_extra_fields"))
        self.assertIsNotNone(extra_fields_pane.select_one("#div_id_extra_fields"))
        self.assertIsNotNone(extra_fields_pane.select_one(".extra-fields-form-grid"))
        self.assertEqual(
            len(extra_fields_pane.select(".extra-field-form-card")),
            1,
        )
        self.assertContains(
            response,
            'class="client-form-shell tabbed-form-shell"',
        )
        self.assertNotContains(response, 'data-tiptap-min-height="240"')

    def test_create_view_uses_task_oriented_client_workspace(self):
        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertIsNotNone(soup.select_one(".resource-form-page-heading"))
        self.assertEqual(
            soup.select_one(".resource-form-page-heading h1").get_text(strip=True),
            "Create client",
        )
        self.assertEqual(
            soup.select_one('a[data-tab-hash="#invites"]').get_text(" ", strip=True),
            "Access",
        )
        self.assertIsNotNone(soup.select_one('[data-collection-empty="contact"]'))
        self.assertIsNotNone(soup.select_one('[data-collection-empty="access"]'))
        self.assertEqual(len(soup.select("#formset-poc .formset-container")), 0)
        self.assertEqual(len(soup.select("#formset-invite .formset-container")), 0)
        self.assertIsNotNone(soup.select_one(".client-form-actions"))
        self.assertEqual(
            soup.select_one("#submit-id-submit-button").get("value"),
            "Create Client",
        )

    def test_incomplete_contact_formset_rerenders_errors(self):
        response = self.client_mgr.post(
            self.uri,
            {
                "name": "New Client",
                "short_name": "New",
                "codename": "New Client Codename",
                "timezone": "America/Los_Angeles",
                "poc-TOTAL_FORMS": "1",
                "poc-INITIAL_FORMS": "0",
                "poc-0-name": "Janine Melnitz",
                "poc-0-job_title": "",
                "poc-0-email": "",
                "poc-0-phone": "",
                "poc-0-timezone": "America/Los_Angeles",
                "poc-0-description": "",
                "invite-TOTAL_FORMS": "0",
                "invite-INITIAL_FORMS": "0",
            },
        )

        self.assertEqual(response.status_code, 200)
        contact_form = response.context["contacts"].forms[0]
        self.assertEqual(contact_form.errors["job_title"].as_data()[0].code, "required")
        self.assertEqual(contact_form.errors["email"].as_data()[0].code, "required")
        self.assertFalse(ClientFactory._meta.model.objects.filter(name="New Client").exists())

    def test_create_client_without_optional_collection_entries(self):
        response = self.client_mgr.post(
            self.uri,
            {
                "name": "Client Without Initial Contacts",
                "short_name": "CWIC",
                "codename": "EMPTY-COLLECTIONS",
                "timezone": "America/Los_Angeles",
                "poc-TOTAL_FORMS": "0",
                "poc-INITIAL_FORMS": "0",
                "invite-TOTAL_FORMS": "0",
                "invite-INITIAL_FORMS": "0",
            },
        )

        self.assertEqual(response.status_code, 302)
        client_obj = ClientFactory._meta.model.objects.get(
            name="Client Without Initial Contacts"
        )
        self.assertFalse(client_obj.clientcontact_set.exists())
        self.assertFalse(client_obj.clientinvite_set.exists())


class ClientUpdateViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.client_obj = ClientFactory()
        cls.uri = reverse("rolodex:client_update", kwargs={"pk": cls.client_obj.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/client_form.html")
        self.assertContains(response, "assets/standalone_tiptap_loader.js?v=")

    def test_view_selects_initial_tab(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        assert_active_tab(self, response, "client")

    def test_existing_collections_render_as_collapsed_summary_cards(self):
        contact = ClientContactFactory(
            client=self.client_obj,
            name="Janine Melnitz",
            job_title="Operations Coordinator",
            primary=True,
        )
        invite = ClientInviteFactory(client=self.client_obj)

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        contact_card = soup.select_one(
            f'details.collection-form-card[data-collection-item="contact"]'
        )
        access_card = soup.select_one(
            f'details.collection-form-card[data-collection-item="access"]'
        )

        self.assertIsNotNone(contact_card)
        self.assertIsNotNone(access_card)
        self.assertNotIn("open", contact_card.attrs)
        self.assertNotIn("open", access_card.attrs)
        self.assertEqual(
            contact_card.select_one('input[id$="-name"]').get("value"),
            contact.name,
        )
        self.assertContains(response, invite.user.get_display_name())
        self.assertContains(response, "gw-tiptap-compact")
        self.assertContains(response, "gw-tiptap-narrative")
        self.assertEqual(
            soup.select_one("#submit-id-submit-button").get("value"),
            "Save Changes",
        )


class ClientDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = ClientFactory(name="SpecterOps", short_name="SO", codename="BloodHound")
        cls.extra_field_model = ExtraFieldModelFactory(
            model_internal_name="rolodex.Client",
            model_display_name="Clients",
        )
        cls.extra_field = ExtraFieldSpecFactory(
            internal_name="tracking_reference",
            display_name="Tracking Reference",
            type="single_line_text",
            target_model=cls.extra_field_model,
        )
        cls.richtext_extra_field = ExtraFieldSpecFactory(
            internal_name="analyst_notes",
            display_name="Analyst Notes",
            type="rich_text",
            target_model=cls.extra_field_model,
        )
        cls.client.extra_fields = {
            "tracking_reference": "CLIENT-001",
            "analyst_notes": "<p>Extra field notes</p>",
        }
        cls.client.save(update_fields=["extra_fields"])
        cls.client.tags.add("Priority")
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.invited_user = UserFactory(password=PASSWORD)
        cls.project_assigned = ProjectFactory(client=cls.client, codename="ASSIGNED_PROJECT")
        cls.project_unassigned = ProjectFactory(client=cls.client, codename="SUPER_SECRET_PROJECT_NO_REGULAR_USERS")
        ProjectAssignmentFactory(project=cls.project_assigned, operator=cls.user)
        ClientInviteFactory(
            client=cls.client,
            user=cls.invited_user,
            comment="Invitation comment",
        )
        cls.client_contact = ClientContactFactory(
            client=cls.client,
            name="Contact With Details",
            description="Contact comment",
        )
        cls.domain_assigned = HistoryFactory(client=cls.client, project=cls.project_assigned)
        cls.domain_unassigned = HistoryFactory(client=cls.client, project=cls.project_unassigned)
        cls.server_assigend = ServerHistoryFactory(client=cls.client, project=cls.project_assigned)
        cls.server_unassigend = ServerHistoryFactory(client=cls.client, project=cls.project_unassigned)
        cls.vps_assigned = TransientServerFactory(project=cls.project_assigned)
        cls.vps_unassigned = TransientServerFactory(project=cls.project_unassigned)
        cls.client_note = ClientNoteFactory(client=cls.client, operator=cls.mgr_user, note="A readable client note")
        cls.uri = reverse("rolodex:client_detail", kwargs={"pk": cls.client.pk})

    def setUp(self):
        self.client = Client()
        self.client_mgr = Client()
        self.client_invited = Client()
        self.assertTrue(self.client.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))
        self.assertTrue(self.client_invited.login(username=self.invited_user.username, password=PASSWORD))

    def test_projects_assigned_only(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, self.project_assigned.codename)
        self.assertNotContains(response, self.project_unassigned.codename)

    def test_projects_staff_all(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["projects"]),
            {self.project_assigned, self.project_unassigned},
        )
        self.assertContains(response, self.project_assigned.codename)
        self.assertContains(response, self.project_unassigned.codename)

    def test_projects_invited_all(self):
        response = self.client_invited.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            set(response.context["projects"]),
            {self.project_assigned, self.project_unassigned},
        )
        self.assertContains(response, self.project_assigned.codename)
        self.assertContains(response, self.project_unassigned.codename)

    def test_general_tab_uses_responsive_detail_cards(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="detail-layout client-overview-layout"')
        self.assertContains(response, 'class="detail-grid"')
        self.assertContains(response, 'role="tablist"')
        self.assertNotContains(response, "project-details-table offset-2 col-8")
        self.assertNotContains(response, "clientDescriptionDropdown")
        self.assertNotContains(response, 'class="description-block detail-prose"')

    def test_client_heading_uses_explicit_actions_menu(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="detail-page-heading client-detail-heading"')
        self.assertContains(response, 'class="detail-page-heading-main client-detail-heading-main"')
        self.assertContains(response, 'class="client-detail-identity"')
        self.assertContains(response, '<span class="detail-eyebrow">Client</span>', html=True)
        self.assertContains(response, 'class="detail-tag-list" aria-label="Client tags"')
        self.assertContains(response, "Priority")
        self.assertContains(response, 'id="client-actions-button"')
        self.assertContains(response, "Actions")
        self.assertContains(response, "Edit client")
        self.assertContains(response, "Delete client")
        self.assertNotContains(response, 'onclick="hamburger(this)"')
        self.assertNotContains(response, 'class="bar1"')

        response = self.client.get(self.uri)
        self.assertContains(response, 'id="client-actions-button"')
        self.assertContains(response, "Pin to sidebar")
        self.assertNotContains(response, "Edit client")
        self.assertNotContains(response, "Delete client")

    def test_client_tabs_use_section_headers_and_complete_table_rows(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="content-section-header"', count=7)
        self.assertContains(response, 'class="missing-value">Not applicable</span>', count=2)
        self.assertNotContains(response, 'class="text-center offset-2 col-8"')
        self.assertNotContains(response, 'class="icon add-icon btn btn-primary mb-3 col-3"')

    def test_client_notes_use_theme_aware_cards(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="note-card-list"')
        self.assertContains(response, 'class="note-card"')
        self.assertContains(response, 'class="note-card-body"')
        self.assertContains(response, 'class="note-card-footer"')
        self.assertContains(response, 'class="note-card-meta"')
        self.assertContains(response, "A readable client note")
        self.assertContains(response, 'id="note-delete-button-')
        self.assertContains(response, 'class="btn btn-outline-danger btn-sm js-confirm-delete"')
        self.assertNotContains(response, 'id="note-actions-')
        self.assertNotContains(response, "note-container darker")
        self.assertContains(response, "const $relatedTarget = $(event.relatedTarget);")

    def test_client_tables_use_modern_actions_and_render_contact_details(self):
        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertContains(response, 'class="table-row-actions"', count=4)
        self.assertContains(response, 'class="table-row-action"', count=7)
        self.assertContains(response, 'class="table-row-action table-row-action-danger"', count=2)
        self.assertNotContains(response, 'class="d-flex justify-content-center"')
        self.assertContains(response, 'class="align-middle sorter-false text-end">Options</th>')
        self.assertContains(response, 'class="sorter-false text-end">Options</th>', count=2)
        self.assertContains(response, 'class="align-middle text-start">\n                    Invitation comment')
        self.assertTrue(all(action.get("title") for action in soup.select(".table-row-action")))
        self.assertContains(response, ".table-row-action[title]")
        self.assertContains(response, "fallbackPlacements = ['bottom']")
        self.assertContains(response, "Contact comment")
        self.assertNotContains(response, "No additional information available.")

    def test_client_extra_fields_use_shared_card_hierarchy(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, "client-extra-fields-grid")
        self.assertContains(response, 'class="extra-field-card-header"', count=2)
        self.assertContains(response, 'class="extra-field-type-badge"', count=2)
        self.assertContains(response, 'class="extra-field-reference"', count=2)
        self.assertContains(response, 'class="extra-field-value-label"', count=2)
        self.assertContains(response, "Edit Extra Fields", count=1)
        self.assertContains(response, "client.extra_fields.tracking_reference")
        self.assertContains(response, 'class="btn-close flex-shrink-0 align-self-start"', count=1)
        self.assertNotContains(response, 'title="Edit Tracking Reference"')

    def test_client_tabs_distinguish_empty_collections(self):
        empty_client = ClientFactory(name="Client Without History")
        uri = reverse("rolodex:client_detail", kwargs={"pk": empty_client.pk})

        response = self.client_mgr.get(uri)

        self.assertContains(response, "No invitations yet")
        self.assertContains(response, "No contacts yet")
        self.assertContains(response, "No projects yet")
        self.assertContains(response, "No infrastructure used")
        self.assertContains(response, "No notes yet")
        self.assertNotContains(response, "There is nothing to see here yet")


class ProjectListViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectListView`."""

    @classmethod
    def setUpTestData(cls):
        client_1 = ClientFactory(name="SpecterOps", short_name="SO", codename="BloodHound")
        client_2 = ClientFactory(name="SpecterPops", short_name="SP", codename="Ghost")
        client_3 = ClientFactory(name="Test", short_name="TST", codename="Popsicle")
        project_1 = ProjectFactory(codename="P1", client=client_1)
        project_2 = ProjectFactory(codename="P2", client=client_2)
        ProjectFactory(codename="P2", client=client_3)
        cls.user = UserFactory(password=PASSWORD)
        cls.assign_user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:projects")
        ClientInviteFactory(user=cls.user, client=client_1)
        ProjectInviteFactory(user=cls.user, project=project_2)
        ProjectAssignmentFactory(project=project_1, operator=cls.assign_user)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_assign = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))
        self.assertTrue(self.client_assign.login(username=self.assign_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "rolodex/project_list.html")

    def test_project_library_uses_shared_library_layout(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="library-page project-library-page d-grid gap-4"')
        self.assertContains(response, '<h2>Project Library</h2>')
        self.assertContains(response, 'class="filter-form library-filters project-library-filters"')
        self.assertContains(response, 'class="library-results project-library-results"')
        self.assertContains(response, "library-table library-table-wide")
        self.assertContains(response, 'class="fas fa-project-diagram"')
        self.assertContains(response, 'data-1p-ignore="true"', count=3)
        self.assertNotContains(response, "btn btn-info col-2")
        self.assertNotContains(response, 'id="project-library-results-title"')

    def test_client_filtering(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 3)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 2)

        response = self.client_assign.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)
        self.assertEqual(response.context["filter"].qs[0].codename, "P1")

        response = self.client_mgr.get(f"{self.uri}?client=SpecterOps")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)

    def test_tags_are_scoped_to_visible_projects(self):
        visible_project = ProjectFactory(codename="VISIBLE")
        hidden_project = ProjectFactory(codename="HIDDEN")
        ProjectInviteFactory(user=self.user, project=visible_project)
        visible_project.tags.add("visible-project-tag")
        hidden_project.tags.add("hidden-project-tag")

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        tag_names = list(response.context["tags"].values_list("name", flat=True))
        self.assertIn("visible-project-tag", tag_names)
        self.assertNotIn("hidden-project-tag", tag_names)
        self.assertIn(
            "visible-project-tag", response.context["autocomplete_data"]["tags"]
        )
        self.assertNotIn(
            "hidden-project-tag", response.context["autocomplete_data"]["tags"]
        )

        response = self.client_mgr.get(f"{self.uri}?client=pops")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 2)

    def test_codename_filtering(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 3)

        response = self.client_mgr.get(f"{self.uri}?codename=p")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 3)

        response = self.client_mgr.get(f"{self.uri}?codename=p1")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["filter"].qs), 1)

    def test_date_sort_attribute_in_template(self):
        """Test that execution window cells have data-text attribute for locale-independent sorting."""
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Check that the response contains data-text attribute with ISO date format
        content = response.content.decode("utf-8")
        self.assertIn(
            'data-text="',
            content,
            "data-text attribute should be present in the template",
        )

        # Verify each project in the queryset has its start_date in the data-text attribute
        for project in response.context["filter"].qs:
            expected_sort_value = project.start_date.strftime("%Y-%m-%d")
            self.assertIn(
                f'data-text="{expected_sort_value}"',
                content,
                f"Project {project.codename} should have data-text attribute with ISO date {expected_sort_value}",
            )


class AssignProjectContactViewTests(TestCase):
    """Collection of tests for :view:`rolodex.AssignProjectContact`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory()
        cls.contact = ClientContactFactory(client=cls.project.client)
        cls.other_contact = ClientContactFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("rolodex:ajax_assign_project_contact", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD)
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "message": f"{self.contact.name} successfully added to your project.",
        }
        response = self.client_mgr.post(self.uri, {"contact": self.contact.pk})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_view_requires_login_and_permissions(self):
        response = self.client.post(self.uri, {"contact": self.contact.pk})
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(self.uri, {"contact": self.contact.pk})
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.project, operator=self.user)
        response = self.client_auth.post(self.uri, {"contact": self.other_contact.pk})
        self.assertEqual(response.status_code, 403)
        response = self.client_auth.post(self.uri, {"contact": self.contact.pk})
        self.assertEqual(response.status_code, 200)

    def test_invalid_contact_id(self):
        data = {
            "result": "error",
            "message": "Submitted contact ID was not an integer.",
        }
        response = self.client_mgr.post(self.uri, {"contact": "foo"})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        data = {
            "result": "error",
            "message": "You must choose a contact.",
        }
        response = self.client_mgr.post(self.uri, {"contact": -1})
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

    def test_primary_contact_inherits_when_no_project_primary(self):
        primary_contact = ClientContactFactory(client=self.project.client, primary=True)
        uri = reverse("rolodex:ajax_assign_project_contact", kwargs={"pk": self.project.pk})
        response = self.client_mgr.post(uri, {"contact": primary_contact.pk})
        self.assertEqual(response.status_code, 200)
        from ghostwriter.rolodex.models import ProjectContact

        project_contact = ProjectContact.objects.get(project=self.project, name=primary_contact.name)
        self.assertTrue(project_contact.primary)
        project_contact.delete()

    def test_primary_contact_does_not_inherit_when_project_primary_exists(self):
        primary_contact = ClientContactFactory(client=self.project.client, primary=True)
        existing_primary = ProjectContactFactory(project=self.project, primary=True)
        uri = reverse("rolodex:ajax_assign_project_contact", kwargs={"pk": self.project.pk})
        response = self.client_mgr.post(uri, {"contact": primary_contact.pk})
        self.assertEqual(response.status_code, 200)
        from ghostwriter.rolodex.models import ProjectContact

        project_contact = ProjectContact.objects.get(project=self.project, name=primary_contact.name)
        self.assertFalse(project_contact.primary)
        project_contact.delete()
        existing_primary.delete()

    def test_non_primary_client_contact_does_not_set_project_primary(self):
        non_primary_contact = ClientContactFactory(client=self.project.client, primary=False)
        uri = reverse("rolodex:ajax_assign_project_contact", kwargs={"pk": self.project.pk})
        response = self.client_mgr.post(uri, {"contact": non_primary_contact.pk})
        self.assertEqual(response.status_code, 200)
        from ghostwriter.rolodex.models import ProjectContact

        project_contact = ProjectContact.objects.get(project=self.project, name=non_primary_contact.name)
        self.assertFalse(project_contact.primary)
        project_contact.delete()


class ProjectDetailViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.extra_field_model = ExtraFieldModelFactory(
            model_internal_name="rolodex.Project",
            model_display_name="Projects",
        )
        cls.extra_field = ExtraFieldSpecFactory(
            internal_name="summary",
            display_name="Summary",
            type="single_line_text",
            target_model=cls.extra_field_model,
        )
        cls.json_extra_field = ExtraFieldSpecFactory(
            internal_name="testJSON",
            display_name="Test JSON",
            type="json",
            target_model=cls.extra_field_model,
        )
        cls.richtext_extra_field = ExtraFieldSpecFactory(
            internal_name="notes",
            display_name="Notes",
            type="rich_text",
            target_model=cls.extra_field_model,
        )
        cls.project.extra_fields = {
            "summary": "Project summary",
            "testJSON": {"large": ["value", {"nested": "content"}]},
            "notes": "<p>Test notes</p>",
        }
        cls.project.save(update_fields=["extra_fields"])
        cls.uri = reverse("rolodex:project_detail", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_report_activation_treats_report_title_as_text(self):
        response = self.client_mgr.get(self.uri)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "/static/js/active-report.js?v=")

        active_report_path = os.path.join(
            settings.APPS_DIR,
            "static",
            "js",
            "active-report.js",
        )
        with open(active_report_path) as active_report_file:
            active_report_script = active_report_file.read()

        self.assertIn(".text(reportTitle || 'Working report')", active_report_script)
        self.assertIn("title.textContent = reportTitle", active_report_script)
        self.assertNotIn(".html(reportTitle", active_report_script)

    def test_calendar_escapes_user_controlled_titles_for_javascript(self):
        payload = "'+(function(){window.calendarXss=true})()+'</script>"
        self.user.name = payload
        self.user.save()
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        objective = ProjectObjectiveFactory(
            project=self.project,
            objective=payload,
            deadline=date.today(),
        )
        ProjectSubtaskFactory(parent=objective, task=payload, deadline=date.today())

        response = self.client_mgr.get(self.uri)
        content = force_str(response.content)

        self.assertEqual(response.status_code, 200)
        self.assertNotIn(f"title: '{payload}'", content)
        self.assertIn(r"\u0027", content)
        self.assertIn(r"\u003C/script\u003E", content)

    def test_context_data_scopes_collab_jwt_to_project(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        payload = utils.get_jwt_payload(response.context["collab_jwt"])

        self.assertEqual(payload[utils.COLLAB_MODEL_CLAIM], "project")
        self.assertEqual(payload[utils.COLLAB_OBJECT_ID_CLAIM], self.project.id)
        self.assertEqual(payload[utils.COLLAB_REPORT_ID_CLAIM], utils.COLLAB_NO_ID)
        self.assertEqual(payload[utils.COLLAB_FINDING_ID_CLAIM], utils.COLLAB_NO_ID)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_project_heading_uses_compact_context_badges_and_actions(self):
        long_client_name = "A Very Long Client Name " + ("With Additional Context " * 8)
        self.project.client.name = long_client_name
        self.project.client.save(update_fields=["name"])

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        client_badge = soup.select_one(".project-context-badge-client")

        self.assertContains(response, 'class="detail-page-heading project-detail-heading"')
        self.assertContains(response, 'id="project-actions-button"')
        self.assertContains(response, "Edit project")
        self.assertContains(response, "Delete project")
        self.assertEqual(client_badge["title"], long_client_name)
        self.assertEqual(client_badge.find("span").get_text(strip=True), long_client_name.strip())
        self.assertNotContains(response, 'onclick="hamburger(this)"')
        self.assertNotContains(response, 'class="bar1"')

    def test_project_planning_uses_responsive_detail_cards(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="detail-layout project-overview-layout"')
        self.assertContains(response, 'class="detail-grid detail-grid-three"')
        self.assertContains(response, 'class="detail-panel project-calendar-panel"')
        self.assertNotContains(response, "project-details-table offset-2 col-8")
        self.assertNotContains(response, "projectDescriptionDropdown")

    def test_project_sections_use_inline_actions_and_shared_empty_states(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, "Add & Edit Assignments")
        self.assertContains(response, "Add & Edit Contacts")
        self.assertContains(response, "Add & Edit Invitations")
        self.assertContains(response, 'class="content-section-actions"')
        self.assertContains(response, "No invitations yet")
        self.assertNotContains(response, 'class="icon edit-icon btn btn-primary mb-1 col-3"')
        self.assertNotContains(response, "There is nothing to see here yet")

    def test_whitecards_and_deconflictions_use_distinct_record_patterns(self):
        WhiteCardFactory(
            project=self.project,
            title="Client-provided domain account",
            description="<p>Use this account for ceded access.</p>",
        )
        DeconflictionFactory(
            project=self.project,
            title="Suspicious PowerShell activity",
            alert_source="EDR",
            response_timestamp=None,
            description="<p>Attribution is still in progress.</p>",
        )

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")

        self.assertIsNotNone(soup.select_one(".whitecard-ledger .whitecard-entry"))
        self.assertIsNotNone(soup.select_one(".whitecard-entry-marker .fa-handshake"))
        self.assertContains(response, "Assessment enablement")
        self.assertContains(response, "Client-provided access, accounts, and actions")
        self.assertContains(response, "Manage White Cards")
        self.assertNotContains(response, 'class="card card-project text-center mb-3"')

        deconfliction = soup.select_one(".deconfliction-record.is-awaiting-response")
        self.assertIsNotNone(deconfliction)
        self.assertEqual(len(deconfliction.select(".deconfliction-phase")), 3)
        self.assertEqual(len(deconfliction.select(".deconfliction-phase.is-complete")), 2)
        self.assertEqual(len(deconfliction.select(".deconfliction-phase.is-current")), 1)
        self.assertContains(response, "Investigation &amp; client closeout", html=True)
        self.assertContains(response, "Attribution is still in progress.")
        self.assertContains(response, "No related activity")
        self.assertContains(response, "Update record")

    def test_project_tables_use_modern_right_aligned_actions(self):
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        ProjectInviteFactory(project=self.project, user=self.user)
        ProjectContactFactory(project=self.project, name="Project contact")
        ProjectScopeFactory(project=self.project, name="Approved scope")
        ProjectTargetFactory(project=self.project)

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        option_headers = [
            header
            for header in soup.find_all("th")
            if header.get_text(strip=True) == "Options"
        ]

        self.assertGreaterEqual(len(option_headers), 4)
        self.assertTrue(all("text-end" in header.get("class", []) for header in option_headers))
        self.assertEqual(len(soup.select(".table-row-actions")), 4)
        self.assertEqual(len(soup.select(".table-row-action")), 12)
        self.assertEqual(len(soup.select(".table-row-action-danger")), 4)
        self.assertIsNotNone(soup.select_one("#contactTable .table-row-action .fa-eye"))
        self.assertIsNone(soup.select_one("#contactTable .expandme"))
        self.assertIsNotNone(soup.select_one("#targetTable .table-row-action-fire.js-compromise-target"))
        self.assertTrue(
            all(
                "text-start" in cell.get("class", [])
                for cell in soup.select("#targetTable td[id^='target-status-']")
            )
        )
        self.assertTrue(all(action.get("title") for action in soup.select(".table-row-action")))
        self.assertContains(response, ".table-row-action[title]")
        self.assertContains(response, "fallbackPlacements = ['bottom']")
        self.assertNotContains(response, 'class="d-flex justify-content-center"')
        self.assertNotContains(response, 'class="icon trash-icon"')

    def test_project_people_details_use_description_fields_and_contact_modal(self):
        assignment = ProjectAssignmentFactory(
            project=self.project,
            operator=self.user,
            description="<p>Lead the external testing workstream.</p>",
        )
        contact = ProjectContactFactory(
            project=self.project,
            name="Dana Barrett",
            description="<p>Call before testing the production tenant.</p>",
        )

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        assignment_row = soup.select_one(
            f"#delete-target-content-assignment-{assignment.id}"
        ).parent
        details_button = soup.select_one(
            f'#contactTable button[data-bs-target="#client_contact_detail_{contact.id}"]'
        )
        details_modal = soup.select_one(f"#client_contact_detail_{contact.id}")

        self.assertIn(
            "Lead the external testing workstream.",
            assignment_row.get_text(" ", strip=True),
        )
        self.assertIsNotNone(details_button)
        self.assertEqual(details_button.get("data-bs-toggle"), "modal")
        self.assertIsNone(details_button.get("onclick"))
        self.assertIsNotNone(details_modal)
        self.assertIn(
            "Call before testing the production tenant.",
            details_modal.get_text(" ", strip=True),
        )
        self.assertIsNone(soup.select_one("#contactTable tr.hidden-row"))
        self.assertNotContains(response, "showHideRow($(this)")
        self.assertNotContains(response, "There are no notes for this contact.")

    def test_project_reporting_uses_report_style_severity_finding_groups(self):
        report = ReportFactory(project=self.project, title="Engagement report")
        critical = SeverityFactory(severity="Critical", weight=1)
        moderate = SeverityFactory(severity="Moderate", weight=3)
        ReportFindingLinkFactory(
            report=report,
            title="Domain admin path",
            severity=critical,
            assigned_to=self.user_mgr,
            cvss_score=9.8,
            cvss_vector="CVSS:3.1/AV:N/AC:L",
        )
        ReportFindingLinkFactory(
            report=report,
            title="Legacy TLS configuration",
            severity=moderate,
            assigned_to=None,
            complete=True,
            cvss_score=None,
        )

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        finding_table = soup.select_one(".project-report-findings-table")

        self.assertIsNotNone(finding_table)
        self.assertEqual(
            [header.get_text(" ", strip=True) for header in finding_table.select("thead th")],
            ["Finding", "CVSS", "Owner", "Status"],
        )
        self.assertEqual(
            [label.get_text(" ", strip=True) for label in finding_table.select(".report-severity-label")],
            ["Critical 1", "Moderate 1"],
        )
        self.assertIsNotNone(
            finding_table.select_one(".report-severity-header.severity_1 .report-severity-dot")
        )
        self.assertIsNotNone(
            finding_table.select_one(".report-score-badge.cvss-critical")
        )
        self.assertIsNotNone(finding_table.select_one(".report-owner-badge.is-unassigned"))
        self.assertIsNotNone(finding_table.select_one(".report-status-badge.is-ready"))
        self.assertIsNotNone(finding_table.select_one(".missing-value"))
        self.assertContains(response, "Open report")

    def test_objectives_use_aligned_cards_and_inline_subtask_workspaces(self):
        primary = ObjectivePriorityFactory(priority="Primary", weight=1)
        secondary = ObjectivePriorityFactory(priority="Secondary", weight=2)
        primary_objective = ProjectObjectiveFactory(
            project=self.project,
            priority=primary,
            objective="Access the PCI environment",
            description="Identify and validate an access path.",
        )
        ProjectSubtaskFactory(
            parent=primary_objective,
            task="Identify the PCI network boundary",
            deadline=primary_objective.deadline,
            complete=False,
        )
        ProjectObjectiveFactory(project=self.project, priority=secondary, objective="Collect evidence")
        ProjectObjectiveFactory(project=self.project, priority=secondary, objective="Validate controls")

        response = self.client_mgr.get(self.uri)
        soup = BeautifulSoup(response.content, "html.parser")
        objective_rows = soup.select("#objectives-table .objective-row")
        secondary_rows = soup.select("#secondary_priority > .objective-row")

        self.assertEqual(len(objective_rows), 3)
        self.assertEqual(len(secondary_rows), 2)
        self.assertEqual(len(soup.select(".objective-priority-heading")), 2)
        self.assertEqual(len(soup.select(".objective-expand-button .objective-expand-icon")), 3)
        self.assertEqual(len(soup.select(".objective-add-task-button")), 3)
        self.assertEqual(len(soup.select(".objective-quick-add-form")), 3)
        self.assertEqual(len(soup.select(".objective-task-workspace")), 3)
        self.assertEqual(len(soup.select("textarea.edit-todo-input.no-auto-rich-text")), 1)
        self.assertContains(response, "What needs to happen?")
        self.assertContains(response, "No subtasks yet", count=2)
        self.assertContains(response, "ele.addClass('is-updating').attr('aria-busy', 'true')")
        self.assertContains(response, "taskList.attr('aria-busy', 'true')")
        self.assertNotContains(response, "taskList.html('').load(url")
        self.assertNotContains(response, 'class="alert alert-secondary col-md-12"')

    def test_project_extra_fields_use_client_card_hierarchy(self):
        response = self.client_mgr.get(self.uri)

        self.assertContains(response, "project-extra-fields-grid")
        self.assertContains(response, 'class="extra-field-card-header"', count=3)
        self.assertContains(response, 'class="extra-field-type-badge"', count=3)
        self.assertContains(response, 'class="extra-field-reference"', count=3)
        self.assertContains(response, 'class="extra-field-value-label"', count=3)
        self.assertContains(response, "Edit Extra Fields", count=1)
        self.assertContains(response, "project.extra_fields.summary")
        self.assertNotContains(response, 'title="Edit Summary"')

    def test_project_legacy_comments_use_theme_aware_cards(self):
        ProjectNoteFactory(
            project=self.project,
            operator=self.user_mgr,
            note="A readable project comment",
        )

        response = self.client_mgr.get(self.uri)

        self.assertContains(response, 'class="note-card-list"')
        self.assertContains(response, 'class="note-card"')
        self.assertContains(response, 'class="note-card-body"')
        self.assertContains(response, 'class="note-card-footer"')
        self.assertContains(response, 'class="note-card-meta"')
        self.assertContains(response, "A readable project comment")
        self.assertNotContains(response, "note-container darker")

    def test_json_extra_field_modal_is_lazy_loaded(self):
        lazy_json_url = reverse(
            "rolodex:project_extra_field_json",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )
        rendered = render_to_string(
            "user_extra_fields/extra_field_modal.html",
            {
                "extra_fields": self.project.extra_fields,
                "field_spec": self.json_extra_field,
                "lazy_json_url": lazy_json_url,
            },
        )

        self.assertIn(lazy_json_url, rendered)
        self.assertIn("JSON content will load when this preview opens.", rendered)
        self.assertNotIn("jsonView", rendered)
        self.assertNotIn("nested", rendered)

    def test_project_detail_json_lazy_loader_has_cleanup_handlers(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "fa-spinner fa-spin")
        self.assertContains(response, "Loading JSON content...")
        self.assertContains(response, "shown.bs.modal")
        self.assertContains(response, "minimumJsonLoadingMs")
        self.assertContains(response, "hide.bs.modal")
        self.assertContains(response, "jsonPreviewPlaceholder")
        self.assertContains(response, "jsonAbortController")
        self.assertNotContains(response, "nested")

    def test_json_extra_field_endpoint_requires_login_and_permissions(self):
        uri = reverse(
            "rolodex:project_extra_field_json",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["field"], "Test JSON")
        self.assertEqual(
            response.json()["value"],
            {"large": ["value", {"nested": "content"}]},
        )

    def test_json_extra_field_endpoint_rejects_non_json_fields(self):
        uri = reverse(
            "rolodex:project_extra_field_json",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_richtext_preview_endpoint_requires_login_and_permissions(self):
        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.richtext_extra_field.internal_name,
            },
        )

        response = self.client.get(uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)

    def test_richtext_preview_endpoint_rejects_non_richtext_fields(self):
        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.json_extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 404)

    def test_richtext_preview_grants_access_to_assigned_user(self):
        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.richtext_extra_field.internal_name,
            },
        )

        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 403)

        ProjectAssignmentFactory(project=self.project, operator=self.user)
        response = self.client_auth.get(uri)
        self.assertEqual(response.status_code, 200)

    def test_richtext_preview_ignores_unrelated_broken_richtext_field(self):
        broken_field = ExtraFieldSpecFactory(
            internal_name="broken_notes",
            display_name="Broken Notes",
            type="rich_text",
            target_model=self.extra_field_model,
        )
        self.project.extra_fields.update(
            {
                self.richtext_extra_field.internal_name: "<p>Requested preview content</p>",
                broken_field.internal_name: "<p>{% for item in %}broken{% endfor %}</p>",
            }
        )
        self.project.save(update_fields=["extra_fields"])
        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.richtext_extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Requested preview content", content)
        self.assertNotIn("Template Error", content)
        self.assertNotIn("broken_notes", content)

    def test_richtext_preview_unexpected_export_error_returns_generic_error(self):
        ProjectAssignmentFactory(
            project=self.project,
            operator=UserFactory(),
            start_date=None,
            end_date=None,
        )
        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.richtext_extra_field.internal_name,
            },
        )

        response = self.client_mgr.get(uri)

        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertIn("Preview Error", content)
        self.assertIn("An unexpected error occurred while rendering this preview.", content)
        self.assertNotIn("NoneType", content)
        self.assertNotIn("object has no attribute", content)

    def test_richtext_preview_renders_client_logo_without_report_context(self):
        """CLIENT_LOGO should render as an <img> even when report is None."""
        self.project.extra_fields["notes"] = '<div data-gw-image="CLIENT_LOGO"></div>'
        self.project.save(update_fields=["extra_fields"])

        uri = reverse(
            "rolodex:project_extra_field_richtext",
            kwargs={
                "pk": self.project.pk,
                "extra_field_name": self.richtext_extra_field.internal_name,
            },
        )
        response = self.client_mgr.get(uri)
        self.assertEqual(response.status_code, 200)
        content = response.content.decode()
        self.assertNotIn("__GW_IMAGE_PREVIEW_", content)
        if self.project.client.logo:
            self.assertIn("<img", content)
            self.assertIn("client_logo_download", content)

    def test_project_assignments_render_in_role_order(self):
        lead_role = ProjectRoleFactory(project_role="Lead", position=1)
        operator_role = ProjectRoleFactory(project_role="Operator", position=2)

        ProjectAssignmentFactory(
            project=self.project,
            role=operator_role,
            operator=UserFactory(name="Zed Zebra"),
        )
        ProjectAssignmentFactory(
            project=self.project,
            role=lead_role,
            operator=UserFactory(name="Beth Baker"),
        )
        ProjectAssignmentFactory(
            project=self.project,
            role=lead_role,
            operator=UserFactory(name="Amy Adams"),
        )

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)

        content = force_str(response.content)

        self.assertLess(content.index("Amy Adams"), content.index("Beth Baker"))
        self.assertLess(content.index("Beth Baker"), content.index("Zed Zebra"))

    def test_shared_global_bloodhound_copy_renders_for_project_viewers(self):
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        bloodhound_config = BloodHoundConfiguration.get_solo()
        bloodhound_config.allow_project_fallback = True
        bloodhound_config.bloodhound_api_root_url = "https://bloodhound.example"
        bloodhound_config.bloodhound_api_key_id = "id"
        bloodhound_config.bloodhound_api_key_token = "token"
        bloodhound_config.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'class="bh-connection-panel is-shared"')
        self.assertContains(response, "Shared data source")
        self.assertContains(response, "Global BloodHound connection")
        self.assertContains(
            response,
            "refreshes the shared cache for every project using this fallback",
        )
        self.assertContains(response, "Test connection")
        self.assertContains(response, "Fetch latest data")
        self.assertNotContains(response, 'class="alert alert-info')

    def test_bloodhound_domain_summary_is_primary_ce_interface(self):
        result = {
            "domains": [
                {
                    "name": "EXAMPLE.LOCAL",
                    "functional_level": "2016",
                    "distinguished_name": "DC=EXAMPLE,DC=LOCAL",
                    "domain_sid": "S-1-5-21-1",
                    "users": {"count": 125, "with_old_pw": 12},
                    "computers": {"count": 48, "operating_systems": {}},
                    "data_quality": {
                        "groups": 32,
                        "sessions": 8,
                        "gpos": 5,
                        "acls": 9,
                        "relationships": 150,
                        "session_completeness": 85,
                        "local_group_completeness": 70,
                    },
                    "inbound_trusts": [],
                    "outbound_trusts": [],
                }
            ],
            "findings": [],
            "finding_assets": {},
        }

        rendered = render_to_string("snippets/bloodhound_info.html", {"res": result})
        soup = BeautifulSoup(rendered, "html.parser")
        summary = soup.select_one("button.bh-domain-summary")

        self.assertIsNotNone(summary)
        self.assertEqual(summary["aria-controls"], "bh_domain_1")
        self.assertEqual(
            [label.get_text(strip=True) for label in soup.select(".stat-label")],
            ["Users", "Computers", "Groups"],
        )
        self.assertEqual(
            [value.get_text(strip=True) for value in soup.select(".stat-value")],
            ["125", "48", "32"],
        )
        self.assertIsNotNone(soup.select_one(".bh-collapse-indicator"))
        self.assertEqual(
            [
                metric.get_text(" ", strip=True)
                for metric in soup.select(".bh-coverage-metric")
            ],
            ["Session completeness 85%", "Local group completeness 70%"],
        )
        self.assertIsNone(soup.select_one("#bheFindingsWorkspace"))
        self.assertNotIn("Enterprise findings", rendered)
        ce_summary = str(summary)

        result["findings"] = [
            {
                "id": 27,
                "severity": "Critical",
                "environment_id": "S-1-5-21-1",
                "finding_name": "Example finding",
                "assets": {
                    "title": "Tier Zero objects lack delegation protection",
                    "type": "Kerberos Attack Paths",
                    "short_description": "<p>Delegation protection is missing.</p><script>alert('xss')</script>",
                    "short_remediation": "<p>Protect the affected accounts.</p>",
                    "long_description": "<p>Technical background.</p>",
                    "long_remediation": "<p>Detailed remediation.</p>",
                    "references": '<p><a href="https://example.com/reference">Reference</a></p>',
                },
                "principals": [
                    {
                        "source_id": "S-1-5-21-1-1000",
                        "source_kind": "Group",
                        "source_properties": {"name": "DOMAIN USERS@EXAMPLE.LOCAL"},
                        "target_id": "S-1-5-21-1-500",
                        "target_kind": "User",
                        "target_properties": {"name": "ADMINISTRATOR@EXAMPLE.LOCAL"},
                        "impact_percentage": 0.99,
                        "exposure_percentage": 0.75,
                    }
                ],
                "is_tier_zero": True,
            }
        ]
        rendered = render_to_string("snippets/bloodhound_info.html", {"res": result})
        soup = BeautifulSoup(rendered, "html.parser")

        self.assertEqual(str(soup.select_one("button.bh-domain-summary")), ce_summary)
        self.assertIsNotNone(
            soup.select_one("#bheFindingsWorkspace.bhe-findings-workspace")
        )
        self.assertIsNotNone(soup.select_one(".bhe-severity-group.severity-critical"))
        self.assertIsNotNone(
            soup.select_one(".bhe-finding-row[data-bhe-tier-zero='true']")
        )
        self.assertIsNotNone(
            soup.select_one(".bhe-preview-button[data-bs-toggle='modal']")
        )
        clear_filters = soup.select_one("#bheClearFilters")
        self.assertIsNotNone(clear_filters)
        self.assertTrue(clear_filters.has_attr("disabled"))
        self.assertNotIn("d-none", clear_filters.get("class", []))
        self.assertIsNotNone(soup.select_one(".bhe-finding-modal .bhe-principal-row"))
        self.assertIn("Peak impact", rendered)
        self.assertIn("99%", rendered)
        self.assertIn("75%", rendered)
        self.assertIn("Delegation protection is missing.", rendered)
        self.assertIn("Protect the affected accounts.", rendered)
        self.assertNotIn("<script>alert", rendered)
        self.assertIsNone(soup.select_one("#bheFindingsTable"))
        self.assertIsNone(soup.select_one("#resetSortBtn"))

        rendered = render_to_string("snippets/bloodhound_info.html", {"res": {}})
        soup = BeautifulSoup(rendered, "html.parser")
        self.assertIsNotNone(soup.select_one(".empty-state.bh-data-empty-state"))
        self.assertIn("No BloodHound data yet", rendered)
        self.assertIn("Fetch latest data", rendered)
        self.assertIsNone(soup.select_one(".alert"))

        rendered = render_to_string(
            "snippets/bloodhound_info.html",
            {"res": {"empty": True}},
        )
        soup = BeautifulSoup(rendered, "html.parser")
        self.assertIsNotNone(soup.select_one(".empty-state.bh-data-empty-state"))
        self.assertIn("No domains available yet", rendered)
        self.assertNotIn("No BloodHound data yet", rendered)
        self.assertIsNone(soup.select_one(".alert"))

    def test_shared_global_bloodhound_tab_hidden_when_fallback_disabled(self):
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        bloodhound_config = BloodHoundConfiguration.get_solo()
        bloodhound_config.bloodhound_api_root_url = "https://bloodhound.example"
        bloodhound_config.bloodhound_api_key_id = "id"
        bloodhound_config.bloodhound_api_key_token = "token"
        bloodhound_config.allow_project_fallback = False
        bloodhound_config.save()

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Shared data source")
        self.assertNotContains(response, "Global BloodHound connection")


class BloodhoundApiAccessTests(TestCase):
    """Collection of tests for BloodHound API access boundaries."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.fetch_uri = reverse("rolodex:ajax_bloodhound_fetch")
        cls.test_uri = reverse("rolodex:ajax_bloodhound_test")
        cls.admin_permission = Permission.objects.get(codename="change_bloodhoundconfiguration")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.project = ProjectFactory()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.user_mgr.username, password=PASSWORD))
        self.user_mgr.user_permissions.add(self.admin_permission)

    def test_global_fetch_requires_privileged_user(self):
        response = self.client_auth.post(self.fetch_uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.fetch_uri)
        self.assertEqual(response.status_code, 302)

    def test_global_connectivity_test_requires_privileged_user(self):
        response = self.client_auth.post(self.test_uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.test_uri)
        self.assertEqual(response.status_code, 302)

    def test_project_viewer_cannot_use_global_fallback_when_not_enabled(self):
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        bloodhound_config = BloodHoundConfiguration.get_solo()
        bloodhound_config.bloodhound_api_root_url = "https://bloodhound.example"
        bloodhound_config.bloodhound_api_key_id = "id"
        bloodhound_config.bloodhound_api_key_token = "token"
        bloodhound_config.allow_project_fallback = False
        bloodhound_config.save()

        response = self.client_auth.post(f"{self.fetch_uri}?project={self.project.pk}")
        self.assertEqual(response.status_code, 403)

        response = self.client_auth.post(f"{self.test_uri}?project={self.project.pk}")
        self.assertEqual(response.status_code, 403)

    def test_project_viewer_can_use_global_fallback_when_explicitly_enabled(self):
        ProjectAssignmentFactory(project=self.project, operator=self.user)
        bloodhound_config = BloodHoundConfiguration.get_solo()
        bloodhound_config.bloodhound_api_root_url = "https://bloodhound.example"
        bloodhound_config.bloodhound_api_key_id = "id"
        bloodhound_config.bloodhound_api_key_token = "token"
        bloodhound_config.allow_project_fallback = True
        bloodhound_config.save()

        response = self.client_auth.post(f"{self.fetch_uri}?project={self.project.pk}")
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.post(f"{self.test_uri}?project={self.project.pk}")
        self.assertEqual(response.status_code, 302)


class ProjectInviteDeleteTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectInviteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectInvite = ProjectInviteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.invite = ProjectInviteFactory()
        cls.uri = reverse("rolodex:ajax_delete_project_invite", kwargs={"pk": cls.invite.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_permissions(self):
        self.assertEqual(len(self.ProjectInvite.objects.all()), 1)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Invite successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.ProjectInvite.objects.all()), 0)


class ClientInviteDeleteTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientInviteDelete`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientInvite = ClientInviteFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")

        cls.invite = ClientInviteFactory()
        cls.uri = reverse("rolodex:ajax_delete_client_invite", kwargs={"pk": cls.invite.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_permissions(self):
        self.assertEqual(len(self.ClientInvite.objects.all()), 1)

        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)

        data = {"result": "success", "message": "Invite successfully deleted!"}
        self.assertJSONEqual(force_str(response.content), data)

        self.assertEqual(len(self.ClientInvite.objects.all()), 0)


class ClientLogoDownloadTests(TestCase):
    """Collection of tests for :view:`rolodex.ClientLogoDownload`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        # Create a client with a logo
        cls.client_with_logo = ClientFactory(logo=factory.django.ImageField(filename="test_logo.png", width=100, height=100))
        # Create another client with a logo that we'll delete for testing
        cls.client_deleted_logo = ClientFactory(logo=factory.django.ImageField(filename="deleted_logo.png", width=100, height=100))
        # Create a client with no logo to test ValueError handling
        cls.client_no_logo = ClientFactory()
        cls.uri = reverse("rolodex:client_logo_download", kwargs={"pk": cls.client_with_logo.pk})
        cls.deleted_uri = reverse("rolodex:client_logo_download", kwargs={"pk": cls.client_deleted_logo.pk})
        cls.no_logo_uri = reverse("rolodex:client_logo_download", kwargs={"pk": cls.client_no_logo.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEquals(
            response.get("Content-Disposition"),
            f'attachment; filename="{os.path.basename(self.client_with_logo.logo.path)}"',
        )

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 302)

        # Grant the user access to the client
        ClientInviteFactory(client=self.client_with_logo, user=self.user)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

        # Manager should have access
        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 200)

        # Delete the logo file and test 404
        if os.path.exists(self.client_deleted_logo.logo.path):
            os.remove(self.client_deleted_logo.logo.path)

        response = self.client_mgr.get(self.deleted_uri)
        self.assertEqual(response.status_code, 404)

    def test_no_logo_returns_404(self):
        """A client with no logo set should return 404, not 500."""
        response = self.client_mgr.get(self.no_logo_uri)
        self.assertEqual(response.status_code, 404)

    def test_inline_view_parameter(self):
        """?view=true serves inline, sets security headers, and does not force download."""
        response = self.client_mgr.get(self.uri + "?view=true")
        self.assertEqual(response.status_code, 200)

        # Content-Disposition must not trigger a download (no 'attachment')
        content_disposition = response.get("Content-Disposition", "")
        self.assertNotIn("attachment", content_disposition)

        # Nosniff must always be present
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")

        # CSP must be present and restrict to safe sources for inline image rendering
        csp = response.get("Content-Security-Policy", "")
        self.assertIn("img-src", csp)
        self.assertIn("default-src 'none'", csp)
        self.assertNotIn("unsafe-inline", csp)

    def test_default_download_has_nosniff_but_no_csp(self):
        """Default (no view param) forces download, sets nosniff, and omits the inline CSP."""
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn("attachment", response.get("Content-Disposition", ""))
        self.assertEqual(response.get("X-Content-Type-Options"), "nosniff")
        # CSP is only added for inline responses
        self.assertIsNone(response.get("Content-Security-Policy"))
