# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.factories import (
    AuxServerAddressFactory,
    ClientContactFactory,
    ClientFactory,
    ClientInviteFactory,
    ClientNoteFactory,
    ObjectiveStatusFactory,
    ProjectFactory,
    ProjectInviteFactory,
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
from ghostwriter.rolodex.templatetags import determine_primary

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


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

        self.assertEqual(response.get("Content-Disposition"), f"attachment; filename={self.scope.name}_scope.txt")


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
