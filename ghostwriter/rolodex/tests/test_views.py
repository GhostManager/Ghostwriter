# Standard Libraries
import base64
import json
import logging
import shutil
import tempfile
from datetime import date, timedelta
from unittest import mock

# Django Imports
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ClientContactFactory,
    ClientFactory,
    ClientInviteFactory,
    ClientNoteFactory,
    MgrFactory,
    ObjectiveStatusFactory,
    ProjectFactory,
    ProjectInviteFactory,
    ProjectTypeFactory,
    ProjectNoteFactory,
    ProjectAssignmentFactory,
    ProjectObjectiveFactory,
    ProjectScopeFactory,
    StaticServerFactory,
    UserFactory,
)
from ghostwriter.rolodex.forms_project import (
    ProjectAssignmentFormSet,
    ProjectObjectiveFormSet,
    ProjectScopeFormSet,
    ProjectTargetFormSet,
    WhiteCardFormSet,
)
from ghostwriter.rolodex.data_parsers import (
    NEXPOSE_ARTIFACT_DEFINITIONS,
    DEFAULT_GENERAL_CAP_MAP,
    normalize_nexpose_artifact_payload,
    normalize_nexpose_artifacts_map,
)
from ghostwriter.rolodex.ip_artifacts import (
    IP_ARTIFACT_DEFINITIONS,
    IP_ARTIFACT_TYPE_EXTERNAL,
    IP_ARTIFACT_TYPE_INTERNAL,
)
from ghostwriter.rolodex.models import (
    ProjectDataFile,
    VulnerabilityMatrixEntry,
    WebIssueMatrixEntry,
)
from ghostwriter.rolodex.workbook_defaults import WORKBOOK_DEFAULTS
from ghostwriter.rolodex.templatetags import determine_primary

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


def assert_default_nexpose_artifacts(testcase, artifacts):
    """Assert that the provided ``artifacts`` contain empty Nexpose placeholders."""

    for definition in NEXPOSE_ARTIFACT_DEFINITIONS.values():
        artifact = artifacts.get(definition["artifact_key"])
        testcase.assertIsNotNone(
            artifact,
            msg=f"Missing Nexpose artifact for {definition['artifact_key']}",
        )
        normalized = normalize_nexpose_artifact_payload(artifact)
        testcase.assertEqual(normalized.get("label"), definition["label"])
        for severity_key in ("high", "med", "low"):
            group = normalized.get(severity_key)
            testcase.assertIsNotNone(group)
            testcase.assertEqual(group["total_unique"], 0)
            testcase.assertEqual(group["items"], [])


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
        for x in range(3):
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

        self.assertEqual(response.get("Content-Disposition"), f'attachment; filename="{self.scope.name}_scope.txt"')


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


class ClientDetailViewTest(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.client = ClientFactory(name="SpecterOps", short_name="SO", codename="BloodHound")
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.invited_user = UserFactory(password=PASSWORD)
        cls.project_assigned = ProjectFactory(client=cls.client)
        cls.project_unassigned = ProjectFactory(client=cls.client)
        ProjectAssignmentFactory(project=cls.project_assigned, operator=cls.user)
        ClientInviteFactory(client=cls.client, user=cls.invited_user)
        cls.uri = reverse("rolodex:client_detail", kwargs={"pk": cls.client.pk})

    def setUp(self):
        self.client = Client()
        self.client_mgr = Client()
        self.client_invited = Client()
        self.assertTrue(self.client.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))
        self.assertTrue(self.client_invited.login(username=self.invited_user.username, password=PASSWORD))

    # This test is valid, but we are currently passing all projects to the template
    # Projects the user cannot access are filtered in the template
    # def test_projects_assigned_only(self):
    #     response = self.client.get(self.uri)
    #     self.assertEqual(response.status_code, 200)
    #     self.assertEqual(set(response.context["projects"]), {self.project_assigned})

    def test_projects_staff_all(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["projects"]), {self.project_assigned, self.project_unassigned})

    def test_projects_invited_all(self):
        response = self.client_invited.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(set(response.context["projects"]), {self.project_assigned, self.project_unassigned})


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


class ProjectDetailViewTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectDetailView`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password=PASSWORD)
        cls.user_mgr = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
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

    def test_detail_view_shows_nexpose_missing_warning_and_button(self):
        self.project.workbook_data = {"external_nexpose": {"total": 1}}
        self.project.data_artifacts = {
            "external_nexpose_findings": {"findings": [], "software": []},
            "nexpose_matrix_gaps": {
                "missing_by_artifact": {
                    "external_nexpose_findings": {
                        "entries": [
                            {
                                "Vulnerability": "Missing Vuln",
                                "CVE": "http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2020-0001",
                            }
                        ]
                    }
                }
            },
        }
        self.project.save(update_fields=["workbook_data", "data_artifacts"])

        response = self.client_mgr.get(self.uri)
        self.assertContains(
            response,
            "Missing Nexpose issues identified! Update the matrix and re-upload",
        )
        self.assertContains(response, "Download Missing")
        self.assertContains(response, "?artifact=external_nexpose_findings")

    def test_detail_view_shows_web_issue_missing_warning_and_button(self):
        self.project.workbook_data = {"web": {"combined_unique": 1}}
        self.project.data_artifacts = {
            "web_issue_matrix_gaps": {
                "entries": [
                    {"issue": "Unhandled Issue", "impact": "", "fix": ""},
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_artifacts"])

        response = self.client_mgr.get(self.uri)
        self.assertContains(
            response, "Missing Web issues identified! Update the matrix and re-upload"
        )
        self.assertContains(response, "Download Missing")
        self.assertContains(
            response,
            reverse(
                "rolodex:project_web_issue_missing_download", kwargs={"pk": self.project.pk}
            ),
        )

    def test_processed_data_tab_shows_metrics_card(self):
        workbook_b64 = base64.b64encode(b"PK\x03\x04").decode("ascii")
        self.project.data_artifacts = {
            "external_nexpose_metrics": {
                "summary": {
                    "total": 4,
                    "total_high": 2,
                    "total_med": 1,
                    "total_low": 1,
                    "unique": 3,
                    "unique_high_med": 3,
                    "total_ood": 1,
                    "total_isc": 1,
                    "total_iwc": 1,
                },
                "xlsx_base64": workbook_b64,
            }
        }
        self.project.save(update_fields=["data_artifacts"])

        response = self.client_mgr.get(self.uri)
        self.assertContains(response, "Processed Data")
        self.assertContains(response, "Total Count")
        self.assertContains(response, "Download Nexpose Data file")
        self.assertContains(response, "?artifact=external_nexpose_metrics")

    def test_processed_data_tab_handles_firewall_summary_without_legacy_totals(self):
        self.project.data_artifacts = {
            "firewall_metrics": {
                "summary": {"unique": 3, "unique_high": 1, "config_count": 2}
            }
        }
        self.project.save(update_fields=["data_artifacts"])

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Firewall Findings")


class ProjectNexposeMissingMatrixDownloadTests(TestCase):
    """Tests for downloading missing Nexpose matrix entries."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.url = reverse(
            "rolodex:project_nexpose_missing_download", kwargs={"pk": cls.project.pk}
        )

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.manager.username, password=PASSWORD))

    def _set_missing_artifacts(self):
        self.project.data_artifacts = {
            "nexpose_matrix_gaps": {
                "missing_by_artifact": {
                    "external_nexpose_findings": {
                        "entries": [
                            {
                                "Vulnerability": "Missing Vuln",
                                "CVE": "http://web.nvd.nist.gov/view/vuln/detail?vulnId=CVE-2020-0001",
                            }
                        ]
                    }
                }
            }
        }
        self.project.save(update_fields=["data_artifacts"])

    def test_download_returns_csv(self):
        self._set_missing_artifacts()
        response = self.client_mgr.get(self.url + "?artifact=external_nexpose_findings")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("nexpose-missing.csv", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Missing Vuln", content)


class ProjectWebIssueMissingDownloadTests(TestCase):
    """Tests for downloading missing web issue matrix entries."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.url = reverse(
            "rolodex:project_web_issue_missing_download", kwargs={"pk": cls.project.pk}
        )

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.manager.username, password=PASSWORD))

    def _set_missing_artifacts(self):
        self.project.data_artifacts = {
            "web_issue_matrix_gaps": {"entries": [{"issue": "Missing Issue", "impact": "", "fix": ""}]}
        }
        self.project.save(update_fields=["data_artifacts"])

    def test_download_returns_csv(self):
        self._set_missing_artifacts()
        response = self.client_mgr.get(self.url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response["Content-Type"], "text/csv")
        self.assertIn("burp-missing.csv", response["Content-Disposition"])
        content = response.content.decode("utf-8")
        self.assertIn("Missing Issue", content)

    def test_download_redirects_when_missing_absent(self):
        self.project.data_artifacts = {}
        self.project.save(update_fields=["data_artifacts"])
        response = self.client_mgr.get(self.url + "?artifact=external_nexpose_findings")
        self.assertEqual(response.status_code, 302)


class ProjectNexposeDataDownloadTests(TestCase):
    """Tests for downloading processed Nexpose XLSX data."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.project = ProjectFactory()
        cls.url = reverse(
            "rolodex:project_nexpose_data_download", kwargs={"pk": cls.project.pk}
        )

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.manager.username, password=PASSWORD))

    def _set_metrics_artifacts(self):
        workbook_b64 = base64.b64encode(b"PK\x03\x04").decode("ascii")
        self.project.data_artifacts = {
            "external_nexpose_metrics": {
                "summary": {"total": 1},
                "xlsx_base64": workbook_b64,
                "xlsx_filename": "nexpose_data.xlsx",
            }
        }
        self.project.save(update_fields=["data_artifacts"])

    def test_download_returns_xlsx(self):
        self._set_metrics_artifacts()
        response = self.client_mgr.get(self.url + "?artifact=external_nexpose_metrics")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(
            response["Content-Type"],
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        self.assertTrue(response.content.startswith(b"PK"))

    def test_download_redirects_when_missing(self):
        self.project.data_artifacts = {}
        self.project.save(update_fields=["data_artifacts"])
        response = self.client_mgr.get(self.url + "?artifact=external_nexpose_metrics")
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


class ProjectWorkbookUploadViewTests(TestCase):
    """Tests for uploading CyberWriter workbook JSON files."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls._media_root = tempfile.mkdtemp()
        cls._override = override_settings(MEDIA_ROOT=cls._media_root)
        cls._override.enable()

    @classmethod
    def tearDownClass(cls):
        cls._override.disable()
        shutil.rmtree(cls._media_root, ignore_errors=True)
        super().tearDownClass()

    @classmethod
    def setUpTestData(cls):
        cls.user = MgrFactory(password=PASSWORD)

    def setUp(self):
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.project = ProjectFactory()
        self.upload_url = reverse("rolodex:project_workbook", kwargs={"pk": self.project.pk})
        self.detail_url = reverse("rolodex:project_detail", kwargs={"pk": self.project.pk})

    def test_upload_saves_file_and_parsed_data(self):
        workbook_payload = {
            "client": {"name": "Example Client"},
            "osint": {"total_squat": 1},
        }
        upload = SimpleUploadedFile(
            "workbook.json",
            json.dumps(workbook_payload).encode("utf-8"),
            content_type="application/json",
        )

        response = self.client_auth.post(self.upload_url, {"workbook_file": upload})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#workbook")

        self.project.refresh_from_db()
        self.addCleanup(lambda: self.project.workbook_file.delete(save=False))
        self.assertIn("client", self.project.workbook_data)
        self.assertEqual(self.project.workbook_data["client"]["name"], "Example Client")
        self.assertTrue(self.project.workbook_file.name.endswith("workbook.json"))
        self.assertIn("password", self.project.data_responses)
        password_responses = self.project.data_responses.get("password", {})
        self.assertEqual(password_responses.get("entries"), [])


class ProjectWorkbookDataUpdateViewTests(TestCase):
    """Tests for updating workbook data via the area cards."""

    @classmethod
    def setUpTestData(cls):
        cls.user = MgrFactory(password=PASSWORD)

    def setUp(self):
        self.client_auth = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.project = ProjectFactory()
        self.update_url = reverse(
            "rolodex:project_workbook_data_update", kwargs={"pk": self.project.pk}
        )

    def test_password_responses_and_cap_rebuilt_on_area_save(self):
        self.project.workbook_data = {
            "password": {
                "policies": [
                    {"domain_name": "corp.example.com", "password_min_length": 10},
                    {"domain_name": "old.example.com", "password_min_length": 8},
                ]
            }
        }
        self.project.data_responses = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com"},
                    {"domain": "old.example.com"},
                ]
            }
        }
        self.project.cap = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 10}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses", "cap"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {
                    "areas": {
                        "password": {
                            "policies": [
                                {
                                    "domain_name": "corp.example.com",
                                    "password_min_length": 14,
                                }
                            ]
                        }
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        password_response = self.project.data_responses.get("password")
        self.assertIsInstance(password_response, dict)
        password_entries = password_response.get("entries")
        self.assertIsInstance(password_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in password_entries], ["corp.example.com"]
        )

        password_cap = self.project.cap.get("password")
        self.assertIsInstance(password_cap, dict)
        cap_entries = password_cap.get("entries")
        self.assertIsInstance(cap_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in cap_entries], ["corp.example.com"]
        )

    def test_iam_save_does_not_persist_placeholder_password_policy(self):
        self.project.workbook_data = {}
        self.project.save(update_fields=["workbook_data"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {
                    "areas": {
                        "ad": {"domains": [{"domain": "corp.example"}]},
                        "password": {},
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        password_state = self.project.workbook_data.get("password")
        self.assertTrue(
            password_state is None
            or (
                isinstance(password_state, dict)
                and not password_state.get("policies")
                and not password_state.get("removed_ad_domains")
            )
        )

    def test_password_entries_removed_when_ad_domain_deleted(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com"}, {"domain": "old.example.com"}]},
            "password": {
                "policies": [
                    {"domain_name": "corp.example.com", "password_min_length": 14},
                    {"domain_name": "old.example.com", "password_min_length": 8},
                ]
            },
        }
        self.project.data_responses = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.cap = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses", "cap"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps({"remove_ad_domain": "old.example.com"}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        self.assertIsInstance(policies, list)
        self.assertListEqual(
            [policy.get("domain_name") for policy in policies if isinstance(policy, dict)],
            ["corp.example.com"],
        )

        password_response = self.project.data_responses.get("password")
        self.assertIsInstance(password_response, dict)
        password_entries = password_response.get("entries")
        self.assertIsInstance(password_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in password_entries], ["corp.example.com"]
        )

        password_cap = self.project.cap.get("password")
        self.assertIsInstance(password_cap, dict)
        cap_entries = password_cap.get("entries")
        self.assertIsInstance(cap_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in cap_entries], ["corp.example.com"]
        )

    def test_password_entries_removed_when_password_domain_deleted(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com"}, {"domain": "old.example.com"}]},
            "password": {
                "policies": [
                    {"domain_name": "corp.example.com", "password_min_length": 14},
                    {"domain_name": "old.example.com", "password_min_length": 8},
                ]
            },
        }
        self.project.data_responses = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.cap = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses", "cap"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {
                    "areas": {
                        "password": {
                            "policies": [
                                {
                                    "domain_name": "corp.example.com",
                                    "password_min_length": 14,
                                }
                            ]
                        }
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        self.assertIsInstance(policies, list)
        self.assertListEqual(
            [policy.get("domain_name") for policy in policies if isinstance(policy, dict)],
            ["corp.example.com"],
        )

        password_response = self.project.data_responses.get("password")
        self.assertIsInstance(password_response, dict)
        password_entries = password_response.get("entries")
        self.assertIsInstance(password_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in password_entries], ["corp.example.com"]
        )

        password_cap = self.project.cap.get("password")
        self.assertIsInstance(password_cap, dict)
        cap_entries = password_cap.get("entries")
        self.assertIsInstance(cap_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in cap_entries], ["corp.example.com"]
        )

    def test_password_entries_removed_when_domain_removed_without_payload_policies(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com"}, {"domain": "old.example.com"}]},
            "password": {
                "policies": [
                    {"domain_name": "corp.example.com", "password_min_length": 14},
                    {"domain_name": "old.example.com", "password_min_length": 8},
                ]
            },
        }
        self.project.data_responses = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.cap = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}},
                    {"domain": "old.example.com", "policy_cap_values": {"min_length": 8}},
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses", "cap"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {"areas": {"password": {"removed_ad_domains": ["old.example.com"]}}}
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        self.assertIsInstance(policies, list)
        self.assertListEqual(
            [policy.get("domain_name") for policy in policies if isinstance(policy, dict)],
            ["corp.example.com"],
        )
        self.assertListEqual(
            workbook_password.get("removed_ad_domains"), ["old.example.com"]
        )

        password_response = self.project.data_responses.get("password")
        self.assertIsInstance(password_response, dict)
        password_entries = password_response.get("entries")
        self.assertIsInstance(password_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in password_entries], ["corp.example.com"]
        )

        password_cap = self.project.cap.get("password")
        self.assertIsInstance(password_cap, dict)
        cap_entries = password_cap.get("entries")
        self.assertIsInstance(cap_entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in cap_entries], ["corp.example.com"]
        )

    def test_password_policy_not_created_until_metrics_saved(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com", "total_accounts": 10}]}
        }
        self.project.save(update_fields=["workbook_data"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {
                    "areas": {
                        "password": {
                            "policies": [
                                {
                                    "domain_name": "corp.example.com",
                                    "strong_passwords": 10,
                                }
                            ]
                        }
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = (
            workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        )
        self.assertIsInstance(policies, list)
        self.assertListEqual(policies, [])

        self.assertNotIn("password", self.project.cap or {})
        self.assertNotIn("password", self.project.data_responses or {})

    def test_password_policy_saved_after_metrics_added(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com", "total_accounts": 25}]}
        }
        self.project.save(update_fields=["workbook_data"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps(
                {
                    "areas": {
                        "password": {
                            "policies": [
                                {
                                    "domain_name": "corp.example.com",
                                    "passwords_cracked": 5,
                                }
                            ]
                        }
                    }
                }
            ),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = (
            workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        )
        self.assertIsInstance(policies, list)
        self.assertListEqual(
            [policy.get("domain_name") for policy in policies if isinstance(policy, dict)],
            ["corp.example.com"],
        )

        password_response = (self.project.data_responses or {}).get("password")
        self.assertIsInstance(password_response, dict)
        entries = password_response.get("entries")
        self.assertIsInstance(entries, list)
        self.assertListEqual(
            [entry.get("domain") for entry in entries if isinstance(entry, dict)],
            ["corp.example.com"],
        )

    def test_password_entries_removed_when_all_domains_deleted(self):
        self.project.workbook_data = {
            "ad": {"domains": [{"domain": "corp.example.com"}]},
            "password": {
                "policies": [
                    {"domain_name": "corp.example.com", "password_min_length": 14}
                ]
            },
        }
        self.project.data_responses = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}}
                ]
            }
        }
        self.project.cap = {
            "password": {
                "entries": [
                    {"domain": "corp.example.com", "policy_cap_values": {"min_length": 14}}
                ]
            }
        }
        self.project.save(update_fields=["workbook_data", "data_responses", "cap"])

        response = self.client_auth.post(
            self.update_url,
            data=json.dumps({"areas": {"password": {"policies": []}}}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        workbook_password = (
            self.project.workbook_data.get("password")
            if isinstance(self.project.workbook_data, dict)
            else {}
        )
        policies = workbook_password.get("policies") if isinstance(workbook_password, dict) else None
        self.assertIsInstance(policies, list)
        self.assertListEqual(policies, [])

        self.assertNotIn("password", self.project.data_responses)
        self.assertNotIn("password", self.project.cap)

    def test_upload_populates_project_risks(self):
        workbook_payload = {
            "external_internal_grades": {
                "external": {
                    "osint": {"risk": "high"},
                    "dns": {"risk": "medium"},
                    "nexpose": {"risk": "low"},
                    "web": {"risk": "medium"},
                },
                "internal": {
                    "cloud": {"risk": "medium"},
                    "configuration": {"risk": "low"},
                    "nexpose": {"risk": "high"},
                    "endpoint": {"risk": "medium"},
                    "snmp": {"risk": "low"},
                    "sql": {"risk": "medium"},
                    "iam": {"risk": "high"},
                    "password": {"risk": "low"},
                },
            },
            "report_card": {
                "overall": "B",
                "external": "C+",
                "internal": "D",
                "wireless": "A-",
                "firewall": "C-",
            },
        }

        upload = SimpleUploadedFile(
            "workbook.json",
            json.dumps(workbook_payload).encode("utf-8"),
            content_type="application/json",
        )

        response = self.client_auth.post(self.upload_url, {"workbook_file": upload})

        self.assertEqual(response.status_code, 302)

        self.project.refresh_from_db()
        expected_risks = {
            "osint": "High",
            "dns": "Medium",
            "external_nexpose": "Low",
            "web": "Medium",
            "cloud_config": "Medium",
            "system_config": "Low",
            "internal_nexpose": "High",
            "endpoint": "Medium",
            "snmp": "Low",
            "sql": "Medium",
            "iam": "High",
            "password": "Low",
            "cloud": "Medium",
            "configuration": "Low",
            "overall_risk": "Medium",
            "external": "Medium",
            "internal": "High",
            "wireless": "Low",
            "firewall": "High",
        }

        self.assertEqual(self.project.risks, expected_risks)

    def test_invalid_json_is_rejected(self):
        upload = SimpleUploadedFile(
            "workbook.json",
            b"{not: 'json' }",
            content_type="application/json",
        )

        response = self.client_auth.post(self.upload_url, {"workbook_file": upload})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#workbook")

        self.project.refresh_from_db()
        self.assertEqual(self.project.workbook_data, {})
        self.assertFalse(self.project.workbook_file)

    def test_clearing_workbook_removes_uploaded_artifacts(self):
        workbook_payload = {"dns": {"records": [{"domain": "example.com"}]}}
        workbook_file = SimpleUploadedFile("workbook.json", json.dumps(workbook_payload).encode("utf-8"))
        self.project.workbook_file = workbook_file
        self.project.workbook_data = workbook_payload
        self.project.data_responses = {"sample": "value"}
        self.project.save(update_fields=["workbook_file", "workbook_data", "data_responses"])

        dns_upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )

        self.project.rebuild_data_artifacts()
        self.project.refresh_from_db()
        self.assertTrue(self.project.data_files.exists())
        self.assertIn("dns_issues", self.project.data_artifacts)

        response = self.client_auth.post(self.upload_url, {"clear_workbook": "1"})

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#workbook")

        self.project.refresh_from_db()
        self.assertFalse(self.project.workbook_file)
        self.assertEqual(self.project.workbook_data, {})
        self.assertEqual(self.project.data_responses, {})
        self.assertEqual(self.project.risks, {})
        assert_default_nexpose_artifacts(self, self.project.data_artifacts)
        expected_keys = {
            definition["artifact_key"] for definition in NEXPOSE_ARTIFACT_DEFINITIONS.values()
        }
        self.assertEqual(set(self.project.data_artifacts.keys()), expected_keys)


class ProjectDataResponsesUpdateTests(TestCase):
    """Collection of tests for :view:`rolodex.ProjectDataResponsesUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.manager = UserFactory(password=PASSWORD, role="manager")
        cls.project_type = ProjectTypeFactory(project_type="CloudFirst")
        cls.project = ProjectFactory(project_type=cls.project_type)
        cls.url = reverse("rolodex:project_data_responses", kwargs={"pk": cls.project.pk})

    def setUp(self):
        self.client_mgr = Client()
        self.assertTrue(self.client_mgr.login(username=self.manager.username, password=PASSWORD))

    def test_scope_string_and_count_saved(self):
        payload = {
            "assessment_scope": ["external", "cloud"],
            "assessment_scope_cloud_on_prem": "yes",
        }

        response = self.client_mgr.post(self.url, payload)

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        data = self.project.data_responses
        general = data.get("general", {})
        self.assertEqual(general.get("assessment_scope"), ["external", "cloud"])
        self.assertEqual(general.get("scope_count"), 2)
        self.assertEqual(general.get("assessment_scope_cloud_on_prem"), "yes")
        self.assertEqual(
            general.get("scope_string"),
            "External network and systems, Cloud/On-Prem network and systems and Cloud management configuration",
        )

    def test_followup_removed_when_cloud_unselected(self):
        self.project.data_responses = {
            "general": {
                "assessment_scope": ["external", "cloud"],
                "assessment_scope_cloud_on_prem": "yes",
                "scope_string": "Existing",
                "scope_count": 2,
            }
        }
        self.project.save(update_fields=["data_responses"])

        payload = {"assessment_scope": ["external"]}
        response = self.client_mgr.post(self.url, payload)

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        data = self.project.data_responses
        general = data.get("general", {})
        self.assertEqual(general.get("assessment_scope"), ["external"])
        self.assertEqual(general.get("scope_count"), 1)
        self.assertEqual(general.get("scope_string"), "External network and systems")
        self.assertNotIn("assessment_scope_cloud_on_prem", general)

    def test_password_domain_responses_preserved_after_rebuild(self):
        workbook_password_response = {"hashes_obtained": "yes"}
        workbook_domain_values = {
            "corp.example.com": {"policy_cap_values": {"Password Maturity": "medium"}}
        }

        questions = [
            {
                "key": "password_corp-example-com_risk",
                "section_key": "password",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "choices": [("high", "High"), ("medium", "Medium"), ("low", "Low")],
                    "required": False,
                },
                "subheading": "corp.example.com",
                "entry_slug": "password_corp-example-com",
                "entry_field_key": "risk",
            }
        ]

        payload = {"password_corp-example-com_risk": "high"}

        general_cap_map = {
            issue: {"recommendation": recommendation, "score": score}
            for issue, (recommendation, score) in DEFAULT_GENERAL_CAP_MAP.items()
        }

        with mock.patch(
            "ghostwriter.rolodex.views.build_data_configuration",
            return_value=(questions, {}),
        ):
            with mock.patch("ghostwriter.rolodex.models.build_project_artifacts", return_value={}):
                with mock.patch(
                    "ghostwriter.rolodex.models.build_workbook_ad_response", return_value={}
                ):
                    with mock.patch(
                        "ghostwriter.rolodex.models.build_workbook_dns_response", return_value={}
                    ):
                        with mock.patch(
                            "ghostwriter.rolodex.models.build_workbook_firewall_response",
                            return_value={},
                        ):
                            with mock.patch(
                                "ghostwriter.rolodex.models.build_workbook_password_response",
                                return_value=(
                                    workbook_password_response,
                                    workbook_domain_values,
                                    ["corp.example.com"],
                                ),
                            ):
                                with mock.patch(
                                    "ghostwriter.rolodex.models.load_general_cap_map",
                                    return_value=general_cap_map,
                                ):
                                    response = self.client_mgr.post(self.url, payload)

        self.assertEqual(response.status_code, 302)

        self.project.refresh_from_db()
        password_responses = self.project.data_responses.get("password", {})
        entries = password_responses.get("entries") if isinstance(password_responses, dict) else None
        self.assertIsInstance(entries, list)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].get("domain"), "corp.example.com")
        self.assertEqual(entries[0].get("risk"), "high")

    def test_password_cap_updates_when_questionnaire_changes(self):
        workbook_password_response = {}
        workbook_domain_values = {
            "corp.example.com": {
                "passwords_cracked": 1,
                "lanman": False,
                "no_fgpp": False,
            }
        }

        general_cap_map = {
            "Weak passwords in use": {"recommendation": "", "score": 1},
            "LANMAN password hashing enabled": {"recommendation": "", "score": 1},
            "Fine-grained Password Policies not defined": {"recommendation": "", "score": 1},
            "Additional password controls not implemented": {"recommendation": "", "score": 1},
            "MFA not enforced for all accounts": {"recommendation": "", "score": 1},
        }

        self.project.data_responses = {
            "password": {
                "password_enforce_mfa_all_accounts": "no",
                "password_additional_controls": "no",
            }
        }
        self.project.save(update_fields=["data_responses"])

        with mock.patch("ghostwriter.rolodex.models.build_project_artifacts", return_value={}):
            with mock.patch("ghostwriter.rolodex.models.build_workbook_ad_response", return_value={}):
                with mock.patch(
                    "ghostwriter.rolodex.models.build_workbook_dns_response",
                    return_value={},
                ):
                    with mock.patch(
                        "ghostwriter.rolodex.models.build_workbook_firewall_response",
                        return_value={},
                    ):
                        with mock.patch(
                            "ghostwriter.rolodex.models.build_workbook_password_response",
                            return_value=(
                                workbook_password_response,
                                workbook_domain_values,
                                ["corp.example.com"],
                            ),
                        ):
                            with mock.patch(
                                "ghostwriter.rolodex.models.load_general_cap_map",
                                return_value=general_cap_map,
                            ):
                                self.project.rebuild_data_artifacts()

        self.project.refresh_from_db()
        password_cap = self.project.cap.get("password", {})
        badpass_map = password_cap.get("badpass_cap_map", {})
        self.assertIn("global", badpass_map)

        questions = [
            {
                "key": "password_enforce_mfa_all_accounts",
                "section_key": "password",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "choices": [("yes", "Yes"), ("no", "No")],
                    "required": False,
                },
            },
            {
                "key": "password_additional_controls",
                "section_key": "password",
                "field_class": forms.ChoiceField,
                "field_kwargs": {
                    "choices": [("yes", "Yes"), ("no", "No")],
                    "required": False,
                },
            },
        ]

        payload = {
            "password_enforce_mfa_all_accounts": "yes",
            "password_additional_controls": "yes",
        }

        with mock.patch(
            "ghostwriter.rolodex.views.build_data_configuration",
            return_value=(questions, {}),
        ):
            with mock.patch("ghostwriter.rolodex.models.build_project_artifacts", return_value={}):
                with mock.patch(
                    "ghostwriter.rolodex.models.build_workbook_ad_response", return_value={}
                ):
                    with mock.patch(
                        "ghostwriter.rolodex.models.build_workbook_dns_response",
                        return_value={},
                    ):
                        with mock.patch(
                            "ghostwriter.rolodex.models.build_workbook_firewall_response",
                            return_value={},
                        ):
                            with mock.patch(
                                "ghostwriter.rolodex.models.build_workbook_password_response",
                                return_value=(
                                    workbook_password_response,
                                    workbook_domain_values,
                                    ["corp.example.com"],
                                ),
                            ):
                                with mock.patch(
                                    "ghostwriter.rolodex.models.load_general_cap_map",
                                    return_value=general_cap_map,
                                ):
                                    response = self.client_mgr.post(self.url, payload)

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()

        password_cap = self.project.cap.get("password", {})
        badpass_map = password_cap.get("badpass_cap_map", {})
        self.assertNotIn("global", badpass_map)

    def test_detail_view_displays_uploaded_workbook_sections(self):
        workbook_payload = {
            "client": {"name": "Example Client"},
            "osint": {"total_squat": 1},
        }
        upload = SimpleUploadedFile(
            "workbook.json",
            json.dumps(workbook_payload).encode("utf-8"),
            content_type="application/json",
        )

        self.client_auth.post(self.upload_url, {"workbook_file": upload})

        self.project.refresh_from_db()
        self.addCleanup(lambda: self.project.workbook_file.delete(save=False))

        response = self.client_auth.get(self.detail_url)

        sections = response.context["workbook_sections"]
        self.assertTrue(any(section["key"] == "client" for section in sections))
        client_section = next(section for section in sections if section["key"] == "client")
        self.assertIn("tree", client_section)
        self.assertEqual(client_section["tree"]["type"], "dict")

    def test_required_file_entries_include_existing_uploads(self):
        workbook_payload = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data"])

        uploaded = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile("dns_report.csv", b"domain,value\nexample.com,1\n", content_type="text/csv"),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.addCleanup(lambda: uploaded.delete())

        response = self.client_auth.get(self.detail_url)

        requirements = response.context["required_data_files"]
        matching = next(item for item in requirements if item["slug"] == uploaded.requirement_slug)
        self.assertEqual(matching.get("existing"), uploaded)

    def test_burp_requirement_follows_dns_entries(self):
        workbook_payload = {
            "dns": {"records": [{"domain": "example.com"}, {"domain": "test.example.com"}]},
            "web": {"combined_unique": 5},
            "external_nexpose": {"total": 10},
            "internal_nexpose": {"total": 1},
            "iot_iomt_nexpose": {"total": 1},
        }
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data"])

        response = self.client_auth.get(self.detail_url)

        requirements = response.context["required_data_files"]
        labels = [requirement.get("label") for requirement in requirements]

        self.assertIn("burp_xml.xml", labels)
        for absent in ("burp_cap.csv", "burp-cap.csv", "burp_csv.csv"):
            self.assertNotIn(absent, labels)
        dns_indexes = [index for index, label in enumerate(labels) if label == "dns_report.csv"]
        self.assertTrue(dns_indexes)
        burp_index = labels.index("burp_xml.xml")
        self.assertEqual(burp_index, max(dns_indexes) + 1)
        self.assertEqual(
            labels[burp_index + 1 : burp_index + 4],
            [
                "external_nexpose_xml.xml",
                "internal_nexpose_xml.xml",
                "iot_nexpose_xml.xml",
            ],
        )

    def test_ip_cards_follow_nexpose_cards_after_burp_in_supplementals(self):
        workbook_payload = {
            "web": {"combined_unique": 2},
            "external_nexpose": {"total": 4},
            "internal_nexpose": {"total": 2},
            "iot_iomt_nexpose": {"total": 1},
        }
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data"])

        response = self.client_auth.get(self.detail_url)

        supplemental_cards = response.context["supplemental_cards"]
        labels = [card["data"]["label"] for card in supplemental_cards]

        self.assertIn("burp_xml.xml", labels)
        for absent in ("burp_cap.csv", "burp-cap.csv", "burp_csv.csv"):
            self.assertNotIn(absent, labels)

        nexpose_labels = [
            "external_nexpose_xml.xml",
            "internal_nexpose_xml.xml",
            "iot_nexpose_xml.xml",
        ]
        nexpose_indices = [labels.index(label) for label in nexpose_labels]
        ip_labels = [
            IP_ARTIFACT_DEFINITIONS[IP_ARTIFACT_TYPE_EXTERNAL].label,
            IP_ARTIFACT_DEFINITIONS[IP_ARTIFACT_TYPE_INTERNAL].label,
        ]
        ip_indices = [labels.index(label) for label in ip_labels]

        self.assertGreater(min(ip_indices), max(nexpose_indices))

    def test_dns_required_entry_includes_fail_count(self):
        workbook_payload = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.workbook_data = workbook_payload
        self.project.save(update_fields=["workbook_data"])

        upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\nFAIL,The domain does not have an SPF record\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.addCleanup(lambda: upload.delete())

        self.project.rebuild_data_artifacts()

        response = self.client_auth.get(self.detail_url)

        requirements = response.context["required_data_files"]
        matching = next(item for item in requirements if item["slug"] == upload.requirement_slug)
        self.assertEqual(matching.get("parsed_fail_count"), 2)
        self.assertEqual(getattr(matching.get("existing"), "parsed_fail_count", None), 2)

    def test_dns_report_upload_updates_project_artifacts(self):
        self.project.workbook_data = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.save(update_fields=["workbook_data"])

        upload_url = reverse("rolodex:project_data_file_upload", kwargs={"pk": self.project.pk})
        csv_content = "Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\nFAIL,The domain does not have an SPF record\n"
        upload = SimpleUploadedFile(
            "dns_report.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client_auth.post(
            upload_url,
            {
                "file": upload,
                "requirement_slug": "required_dns-report-csv_example-com",
                "requirement_label": "dns_report.csv",
                "requirement_context": "example.com",
                "description": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        self.addCleanup(
            lambda: [
                (data_file.file.delete(save=False), data_file.delete())
                for data_file in list(self.project.data_files.all())
            ]
        )
        artifacts = self.project.data_artifacts
        self.assertIn("dns_issues", artifacts)
        issues = artifacts["dns_issues"]
        self.assertEqual(len(issues), 1)
        entry = issues[0]
        self.assertEqual(entry["domain"], "example.com")
        self.assertEqual(len(entry["issues"]), 2)
        first_issue = entry["issues"][0]
        self.assertEqual(
            first_issue,
            {
                "issue": "One or more SOA fields are outside recommended ranges",
                "finding": "configuring DNS records according to best practice",
                "recommendation": "update SOA fields to follow best practice",
                "cap": "Get-SOA $domname",
                "impact": "Incorrect SOA settings can disrupt DNS propagation, caching, and zone transfers, leading to stale or inconsistent domain data.",
            },
        )

    def test_burp_upload_updates_project_artifacts(self):
        self.project.workbook_data = {"web": {"combined_unique": 1}}
        self.project.save(update_fields=["workbook_data"])

        upload_url = reverse("rolodex:project_data_file_upload", kwargs={"pk": self.project.pk})
        csv_content = "\n".join(
            [
                "Host,Risk,Issue,Impact",
                "portal.example.com,High,SQL Injection,This may lead to full database compromise.",
                "portal.example.com,Medium,Cross-Site Scripting,This can result in credential theft.",
                "portal.example.com,Medium,Cross-Site Scripting,This can result in credential theft.",
                "portal.example.com,Medium,Session Fixation,This can lead to account takeover.",
                "portal.example.com,Medium,Session Fixation,This can lead to account takeover.",
                "portal.example.com,Medium,Session Fixation,This can lead to account takeover.",
                "intranet.example.com,Medium,Authentication Bypass,This may expose sensitive data.",
                "intranet.example.com,Medium,Authentication Bypass,This may expose sensitive data.",
                "intranet.example.com,Low,Directory Listing,This may expose directory structure.",
                "intranet.example.com,Low,Directory Listing,This may expose directory structure.",
                "portal.example.com,Low,Missing X-Frame-Options header,This may allow clickjacking.",
                "portal.example.com,Low,Missing X-Frame-Options header,This may allow clickjacking.",
                "portal.example.com,Low,Missing X-Frame-Options header,This may allow clickjacking.",
                "extranet.example.com,Informational,Banner Disclosure,This can reveal version information.",
                "extranet.example.com,Informational,Banner Disclosure,This can reveal version information.",
            ]
        )
        upload = SimpleUploadedFile(
            "burp_csv.csv",
            csv_content.encode("utf-8"),
            content_type="text/csv",
        )

        response = self.client_auth.post(
            upload_url,
            {
                "file": upload,
                "requirement_slug": "required_burp-csv-csv",
                "requirement_label": "burp_csv.csv",
                "requirement_context": "",
                "description": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        self.addCleanup(
            lambda: [
                (data_file.file.delete(save=False), data_file.delete())
                for data_file in list(self.project.data_files.all())
            ]
        )

        artifacts = normalize_nexpose_artifacts_map(self.project.data_artifacts)
        self.assertIn("web_issues", artifacts)
        web_artifacts = artifacts["web_issues"]
        self.assertIsInstance(web_artifacts, dict)
        self.assertIn("ai_response", web_artifacts)
        self.assertIsNone(web_artifacts["ai_response"])
        self.assertEqual(
            web_artifacts["low_sample_string"],
            "'Missing X-Frame-Options header', 'Banner Disclosure' and 'Directory Listing'",
        )
        self.assertEqual(
            web_artifacts["med_sample_string"],
            "'lead to account takeover.', 'expose sensitive data.' and 'result in credential theft.'",
        )
        high_summary = web_artifacts["high"]
        self.assertEqual(high_summary["total_unique"], 1)
        self.assertEqual(
            high_summary["items"],
            [
                {
                    "issue": "SQL Injection",
                    "impact": "This may lead to full database compromise.",
                    "fix": "",
                    "count": 1,
                }
            ],
        )

        med_summary = web_artifacts["med"]
        self.assertEqual(med_summary["total_unique"], 3)
        self.assertEqual(len(med_summary["items"]), 3)
        self.assertEqual(med_summary["items"][0]["issue"], "Session Fixation")
        self.assertEqual(med_summary["items"][0]["count"], 3)

        low_summary = web_artifacts["low"]
        self.assertEqual(low_summary["total_unique"], 3)
        self.assertEqual(len(low_summary["items"]), 3)
        self.assertEqual(low_summary["items"][0]["issue"], "Missing X-Frame-Options header")

    def test_firewall_upload_updates_project_artifacts(self):
        self.project.workbook_data = {"firewall": {"unique": 1}}
        self.project.save(update_fields=["workbook_data"])

        upload_url = reverse("rolodex:project_data_file_upload", kwargs={"pk": self.project.pk})
        xml_content = b"""
<root>
  <document>
    <information>
      <devices><device><name>FW-1</name></device></devices>
    </information>
  </document>
  <section ref=\"SECURITYAUDIT\">
    <section ref=\"FILTER.TEST\" title=\"Blocked traffic review\">
      <issuedetails>
        <devices><device><name>FW-1</name></device></devices>
        <ratings><rating>High</rating><cvssv2-temporal score=\"8.5\" /></ratings>
      </issuedetails>
      <section ref=\"IMPACT\"><text>Service disruption</text></section>
      <section ref=\"RECOMMENDATION\"><text>Adjust rule set</text></section>
      <section ref=\"FINDING\"><text>Traffic dropped</text></section>
    </section>
  </section>
</root>
"""
        upload = SimpleUploadedFile(
            "firewall_xml.xml",
            xml_content,
            content_type="application/xml",
        )

        response = self.client_auth.post(
            upload_url,
            {
                "file": upload,
                "requirement_slug": "required_firewall-xml-xml",
                "requirement_label": "firewall_xml.xml",
                "requirement_context": "",
                "description": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        self.addCleanup(
            lambda: [
                (data_file.file.delete(save=False), data_file.delete())
                for data_file in list(self.project.data_files.all())
            ]
        )

        artifacts = self.project.data_artifacts
        self.assertIn("firewall_findings", artifacts)
        self.assertIn("firewall_metrics", artifacts)
        metrics = artifacts["firewall_metrics"]
        self.assertEqual(metrics.get("summary", {}).get("unique_high"), 1)

        firewall_cap = self.project.cap.get("firewall")
        self.assertIsInstance(firewall_cap, dict)
        cap_entries = firewall_cap.get("firewall_cap_map")
        self.assertEqual(len(cap_entries), 1)
        cap_entry = cap_entries[0]
        expected_recommendation, expected_score = DEFAULT_GENERAL_CAP_MAP[
            "Business justification for firewall rules"
        ]
        self.assertEqual(
            cap_entry,
            {
                "recommendation": expected_recommendation,
                "score": expected_score,
                "issue": "Blocked traffic review",
                "devices": "FW-1;FW-2",
                "solution": "Adjust rule set",
                "impact": "Service disruption",
                "details": "Traffic dropped",
                "reference": "http://example.com",
                "accepted": "No",
                "type": "External",
                "risk": "High",
                "finding_score": 8.5,
            },
        )
        self.assertEqual(vulnerabilities["med"], {"total_unique": 0, "items": []})
        self.assertEqual(vulnerabilities["low"], {"total_unique": 0, "items": []})

    def test_remove_firewall_data_clears_artifacts_and_workbook(self):
        self.project.workbook_data = {"firewall": {"unique": 1}}
        self.project.save(update_fields=["workbook_data"])

        upload_url = reverse("rolodex:project_data_file_upload", kwargs={"pk": self.project.pk})
        xml_content = b"""
<root>
  <document>
    <information>
      <devices><device><name>FW-1</name></device></devices>
    </information>
  </document>
  <section ref=\"SECURITYAUDIT\">
    <section ref=\"FILTER.TEST\" title=\"Blocked traffic review\">
      <issuedetails>
        <devices><device><name>FW-1</name></device></devices>
        <ratings><rating>High</rating><cvssv2-temporal score=\"8.5\" /></ratings>
      </issuedetails>
      <section ref=\"IMPACT\"><text>Service disruption</text></section>
      <section ref=\"RECOMMENDATION\"><text>Adjust rule set</text></section>
      <section ref=\"FINDING\"><text>Traffic dropped</text></section>
    </section>
  </section>
</root>
"""
        upload = SimpleUploadedFile(
            "firewall_xml.xml",
            xml_content,
            content_type="application/xml",
        )

        response = self.client_auth.post(
            upload_url,
            {
                "file": upload,
                "requirement_slug": "required_firewall-xml-xml",
                "requirement_label": "firewall_xml.xml",
                "requirement_context": "",
                "description": "",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        self.addCleanup(
            lambda: [
                (data_file.file.delete(save=False), data_file.delete())
                for data_file in list(self.project.data_files.all())
            ]
        )

        self.assertIn("firewall_metrics", self.project.data_artifacts)

        update_url = reverse(
            "rolodex:project_workbook_data_update", kwargs={"pk": self.project.pk}
        )
        response = self.client_auth.post(
            update_url,
            data=json.dumps({"remove_firewall": True}),
            content_type="application/json",
        )

        self.assertEqual(response.status_code, 200)
        self.project.refresh_from_db()

        self.assertFalse(
            self.project.data_files.filter(requirement_label="firewall_xml.xml").exists()
        )

        artifacts = self.project.data_artifacts or {}
        self.assertNotIn("firewall_findings", artifacts)
        self.assertNotIn("firewall_metrics", artifacts)
        self.assertNotIn("firewall_vulnerabilities", artifacts)

        self.assertEqual(
            self.project.workbook_data.get("firewall"),
            WORKBOOK_DEFAULTS.get("firewall"),
        )

    def test_nexpose_distilled_toggle_updates_cap(self):
        toggle_url = reverse(
            "rolodex:project_nexpose_distilled_update", kwargs={"pk": self.project.pk}
        )

        response = self.client_auth.post(toggle_url, {"nexpose_distilled": "1"})
        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#processed-data")

        self.project.refresh_from_db()
        nexpose_section = self.project.cap.get("nexpose")
        self.assertIsInstance(nexpose_section, dict)
        self.assertTrue(nexpose_section.get("distilled"))

        response = self.client_auth.post(toggle_url, {})
        self.assertEqual(response.status_code, 302)
        self.project.refresh_from_db()
        nexpose_section = self.project.cap.get("nexpose")
        self.assertFalse(nexpose_section.get("distilled"))

    def test_external_ip_submission_creates_artifact(self):
        upload_url = reverse("rolodex:project_ip_artifact_upload", kwargs={"pk": self.project.pk})
        response = self.client_auth.post(
            upload_url,
            {
                "ip_type": IP_ARTIFACT_TYPE_EXTERNAL,
                "ip_text": "192.0.2.1\n198.51.100.2\n192.0.2.1",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        definition = IP_ARTIFACT_DEFINITIONS[IP_ARTIFACT_TYPE_EXTERNAL]
        data_file = self.project.data_files.get(requirement_slug=definition.slug)
        self.addCleanup(lambda: (data_file.file.delete(save=False), data_file.delete()))

        artifacts = self.project.data_artifacts
        self.assertIn(definition.artifact_key, artifacts)
        self.assertEqual(artifacts[definition.artifact_key], ["192.0.2.1", "198.51.100.2"])

    def test_internal_ip_submission_accepts_file_upload(self):
        upload_url = reverse("rolodex:project_ip_artifact_upload", kwargs={"pk": self.project.pk})
        ip_file = SimpleUploadedFile(
            "internal_ips.txt",
            b"203.0.113.10\n198.51.100.25\n",
            content_type="text/plain",
        )

        response = self.client_auth.post(
            upload_url,
            {
                "ip_type": IP_ARTIFACT_TYPE_INTERNAL,
                "ip_file": ip_file,
                "ip_text": "198.51.100.25\n",
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        definition = IP_ARTIFACT_DEFINITIONS[IP_ARTIFACT_TYPE_INTERNAL]
        data_file = self.project.data_files.get(requirement_slug=definition.slug)
        self.addCleanup(lambda: (data_file.file.delete(save=False), data_file.delete()))

        artifacts = self.project.data_artifacts
        self.assertIn(definition.artifact_key, artifacts)
        self.assertEqual(
            artifacts[definition.artifact_key],
            ["203.0.113.10", "198.51.100.25"],
        )

    def test_data_file_deletion_refreshes_project_artifacts(self):
        self.project.workbook_data = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.save(update_fields=["workbook_data"])

        upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.project.rebuild_data_artifacts()

        delete_url = reverse("rolodex:project_data_file_delete", kwargs={"pk": upload.pk})
        response = self.client_auth.post(delete_url)

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")

        self.project.refresh_from_db()
        assert_default_nexpose_artifacts(self, self.project.data_artifacts)
        expected_keys = {
            definition["artifact_key"] for definition in NEXPOSE_ARTIFACT_DEFINITIONS.values()
        }
        self.assertEqual(set(self.project.data_artifacts.keys()), expected_keys)

    def test_data_file_deletion_returns_json_for_ajax_request(self):
        self.project.workbook_data = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.save(update_fields=["workbook_data"])

        upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.project.rebuild_data_artifacts()

        delete_url = reverse("rolodex:project_data_file_delete", kwargs={"pk": upload.pk})
        response = self.client_auth.post(
            delete_url,
            HTTP_X_REQUESTED_WITH="XMLHttpRequest",
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertTrue(payload.get("success"))
        self.assertEqual(payload.get("redirect_url"), f"{self.detail_url}#supplementals")
        self.assertFalse(self.project.data_files.filter(pk=upload.pk).exists())

    def test_data_file_deletion_falls_back_to_requirement_slug(self):
        self.project.workbook_data = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.save(update_fields=["workbook_data"])

        upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.project.rebuild_data_artifacts()

        delete_url = reverse(
            "rolodex:project_data_file_delete",
            kwargs={"pk": upload.pk + 999},
        )
        response = self.client_auth.post(
            delete_url,
            {
                "project_id": str(self.project.pk),
                "requirement_slug": upload.requirement_slug,
            },
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(response.url, f"{self.detail_url}#supplementals")
        self.assertFalse(self.project.data_files.filter(pk=upload.pk).exists())
        self.project.refresh_from_db()
        assert_default_nexpose_artifacts(self, self.project.data_artifacts)

    def test_required_artifact_delete_forms_include_success_anchor(self):
        self.project.workbook_data = {"dns": {"records": [{"domain": "example.com"}]}}
        self.project.save(update_fields=["workbook_data"])

        upload = ProjectDataFile.objects.create(
            project=self.project,
            file=SimpleUploadedFile(
                "dns_report.csv",
                b"Status,Info\nFAIL,One or more SOA fields are outside recommended ranges\n",
                content_type="text/csv",
            ),
            requirement_slug="required_dns-report-csv_example-com",
            requirement_label="dns_report.csv",
            requirement_context="example.com",
        )
        self.addCleanup(lambda: upload.delete())

        self.project.rebuild_data_artifacts()
        response = self.client_auth.get(self.detail_url)

        self.assertContains(response, "project-data-file-delete-form")
        self.assertIn(
            f'data-success-url="{self.detail_url}#supplementals"',
            response.content.decode("utf-8"),
        )


class MatrixViewTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.manager = UserFactory(username="matrix_manager", role="manager")
        cls.manager.set_password(PASSWORD)
        cls.manager.save()
        cls.user = UserFactory(username="matrix_user", role="user")
        cls.user.set_password(PASSWORD)
        cls.user.save()

    def test_manager_can_view_vulnerability_matrix(self):
        VulnerabilityMatrixEntry.objects.create(
            vulnerability="SQL Injection",
            action_required="Update all input validation.",
            remediation_impact="High",
            vulnerability_threat="Data exfiltration",
            category="Injection",
        )
        self.client.login(username=self.manager.username, password=PASSWORD)
        response = self.client.get(reverse("rolodex:vulnerability_matrix"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "SQL Injection")

    def test_non_privileged_user_redirected(self):
        self.client.login(username=self.user.username, password=PASSWORD)
        response = self.client.get(reverse("rolodex:web_issue_matrix"))
        self.assertRedirects(response, reverse("home:dashboard"))

    def test_manager_can_create_vulnerability_entry(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_add"),
            {
                "vulnerability": "Cross-Site Scripting",
                "action_required": "Sanitize all user-supplied output.",
                "remediation_impact": "Medium",
                "vulnerability_threat": "Account takeover",
                "category": "Injection",
            },
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertTrue(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Cross-Site Scripting").exists()
        )

    def test_manager_can_import_vulnerability_matrix_csv(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category\n"
            "Old Vuln,Apply patch,Low,Info leak <EC>,OOD\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertTrue(VulnerabilityMatrixEntry.objects.filter(vulnerability="Old Vuln").exists())

    def test_import_rejects_missing_required_fields(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category\n"
            "Missing Data,,Low,Info leak <EC>,OOD\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertFalse(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Missing Data").exists()
        )

    def test_import_rejects_invalid_category(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category\n"
            "Bad Category,Apply patch,Low,Info leak <EC>,Other\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertFalse(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Bad Category").exists()
        )

    def test_import_rejects_missing_ec_marker(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category\n"
            "No Marker,Apply patch,Low,Info leak,OOD\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertFalse(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="No Marker").exists()
        )

    def test_import_rejects_placeholder_values(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category\n"
            "Update Needed,UPDATE ME,Low,Info leak <EC>,OOD\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertFalse(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Update Needed").exists()
        )

    def test_import_rejects_placeholder_values_in_extra_columns(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category,notes\n"
            "Extra Placeholder,Apply patch,Low,Info leak <EC>,ISC,UPDATE ME soon\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertFalse(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Extra Placeholder").exists()
        )

    def test_import_ignores_additional_columns(self):
        self.client.login(username=self.manager.username, password=PASSWORD)
        csv_content = (
            "vulnerability,action_required,remediation_impact,vulnerability_threat,category,extra\n"
            "Extra Column,Apply patch,Low,Info leak <EC>,ISC,Ignore me\n"
        )
        upload = SimpleUploadedFile("matrix.csv", csv_content.encode("utf-8"), content_type="text/csv")
        response = self.client.post(
            reverse("rolodex:vulnerability_matrix_import"),
            {"csv_file": upload},
        )
        self.assertRedirects(response, reverse("rolodex:vulnerability_matrix"))
        self.assertTrue(
            VulnerabilityMatrixEntry.objects.filter(vulnerability="Extra Column").exists()
        )

    def test_manager_can_export_web_issue_matrix(self):
        WebIssueMatrixEntry.objects.create(title="Missing CSP", impact="Medium", fix="Add policy")
        self.client.login(username=self.manager.username, password=PASSWORD)
        response = self.client.get(reverse("rolodex:web_issue_matrix_export"))
        self.assertEqual(response.status_code, 200)
        self.assertIn("text/csv", response["Content-Type"])
        self.assertIn("Missing CSP", response.content.decode("utf-8"))
