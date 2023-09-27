# Standard Libraries
import csv
import logging
import os
from datetime import datetime

# Django Imports
from django.test import Client, TestCase
from django.urls import reverse
from django.utils.encoding import force_str

# Ghostwriter Libraries
from ghostwriter.factories import (
    OplogEntryFactory,
    OplogFactory,
    ProjectFactory,
    UserFactory,
    ProjectAssignmentFactory,
)

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


# Tests related to report modification actions


class OplogListViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogListView`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:index")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_list.html")

    def test_oplog_list_values(self):
        OplogFactory.create_batch(5)
        test_log = self.Oplog.objects.all()[0]

        response = self.client_mgr.get(self.uri)
        self.assertIn("oplog_list", response.context)
        self.assertEqual(response.context["oplog_list"][0], self.Oplog.objects.all()[0])
        self.assertEqual(len(response.context["oplog_list"]), self.Oplog.objects.count())

        ProjectAssignmentFactory(operator=self.user, project=test_log.project)
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.context["oplog_list"][0], test_log)
        self.assertEqual(len(response.context["oplog_list"]), 1)


class OplogListEntriesTests(TestCase):
    """Collection of tests for :view:`oplog.OplogListEntries`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.OplogEntry = OplogEntryFactory._meta.model

        cls.oplog = OplogFactory()
        OplogEntryFactory.create_batch(5, oplog_id=cls.oplog)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:oplog_entries", kwargs={"pk": cls.oplog.id})

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

        ProjectAssignmentFactory(operator=self.user, project=self.oplog.project)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_template(self):
        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_detail.html")


class OplogEntriesImportTests(TestCase):
    """Collection of tests for :view:`oplog.OplogEntriesImport`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.OplogEntry = OplogEntryFactory._meta.model

        cls.oplog = OplogFactory()
        cls.num_of_entries = 5
        for x in range(cls.num_of_entries):
            OplogEntryFactory(oplog_id=cls.oplog)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:oplog_import")
        cls.redirect_uri = reverse("oplog:oplog_entries", kwargs={"pk": cls.oplog.pk})
        cls.failure_redirect_uri = reverse("oplog:oplog_import")

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_import.html")

    def test_post_data_and_permissions(self):
        filename = "oplog_import_test.csv"
        fieldnames = [
            "start_date",
            "end_date",
            "source_ip",
            "dest_ip",
            "tool",
            "user_context",
            "command",
            "description",
            "output",
            "comments",
            "operator_name",
        ]
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONE)
            writer.writeheader()
            for entry in self.OplogEntry.objects.all():
                row = {}
                for field in fieldnames:
                    if field == "start_date":
                        row[field] = datetime.timestamp(entry.start_date)
                    elif field == "end_date":
                        row[field] = datetime.timestamp(entry.end_date)
                    else:
                        row[field] = getattr(entry, field)
                writer.writerow(row)

        with open(filename, "r") as csvfile:
            response = self.client_mgr.post(self.uri, {"csv_file": csvfile, "oplog_id": self.oplog.id})
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.redirect_uri)
            self.assertEqual(self.OplogEntry.objects.count(), self.num_of_entries * 2)

        with open(filename, "r") as csvfile:
            response = self.client_auth.post(self.uri, {"csv_file": csvfile, "oplog_id": self.oplog.id})
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.failure_redirect_uri)
            self.assertEqual(self.OplogEntry.objects.count(), self.num_of_entries * 2)

        ProjectAssignmentFactory(operator=self.user, project=self.oplog.project)
        with open(filename, "r") as csvfile:
            response = self.client_auth.post(self.uri, {"csv_file": csvfile, "oplog_id": self.oplog.id})
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.redirect_uri)
            self.assertEqual(self.OplogEntry.objects.count(), self.num_of_entries * 3)
        os.remove(filename)

    def test_oplog_id_override(self):
        """Test that the ``oplog_id`` field is overridden when importing."""
        filename = "oplog_import_test.csv"
        fieldnames = [
            "oplog_id",
            "start_date",
            "end_date",
            "source_ip",
            "dest_ip",
            "tool",
            "user_context",
            "command",
            "description",
            "output",
            "comments",
            "operator_name",
        ]
        with open(filename, "w") as csvfile:
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames, quoting=csv.QUOTE_NONE)
            writer.writeheader()
            for entry in self.OplogEntry.objects.all():
                row = {}
                for field in fieldnames:
                    if field == "oplog_id":
                        row[field] = 9000
                    elif field == "start_date":
                        row[field] = datetime.timestamp(entry.start_date)
                    elif field == "end_date":
                        row[field] = datetime.timestamp(entry.end_date)
                    else:
                        row[field] = getattr(entry, field)
                writer.writerow(row)

        with open(filename, "r") as csvfile:
            starting_entries = self.OplogEntry.objects.filter(oplog_id=self.oplog).count()
            response = self.client_mgr.post(self.uri, {"csv_file": csvfile, "oplog_id": self.oplog.id})
            self.assertEqual(response.status_code, 302)
            self.assertRedirects(response, self.redirect_uri)
            self.assertEqual(
                self.OplogEntry.objects.filter(oplog_id=self.oplog).count(), starting_entries + self.num_of_entries
            )
        os.remove(filename)


class OplogCreateViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogCreate`."""

    @classmethod
    def setUpTestData(cls):
        cls.project = ProjectFactory(complete=False)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:oplog_create_no_project")
        cls.project_uri = reverse("oplog:oplog_create", kwargs={"pk": cls.project.pk})
        ProjectAssignmentFactory(operator=cls.user, project=cls.project)
        ProjectFactory.create_batch(5, complete=False)
        ProjectFactory.create_batch(5, complete=True)

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)

    def test_view_uri_with_project_exists_at_desired_location(self):
        response = self.client_auth.get(self.project_uri)
        self.assertEqual(response.status_code, 200)

    def test_view_requires_login_and_permissions(self):
        response = self.client.get(self.uri)
        self.assertEqual(response.status_code, 302)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields["project"].queryset), 1)
        self.assertEqual(response.context["form"].fields["project"].queryset[0], self.project)

        response = self.client_mgr.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(len(response.context["form"].fields["project"].queryset), 6)

    def test_view_uses_correct_template(self):
        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/oplog_form.html")

    def test_custom_context_exists(self):
        response = self.client_mgr.get(self.uri)
        self.assertIn("cancel_link", response.context)
        self.assertIn("project", response.context)
        self.assertEqual(response.context["cancel_link"], reverse("oplog:index"))
        self.assertEqual(response.context["project"], "")

    def test_custom_context_exists_with_project(self):
        response = self.client_mgr.get(self.project_uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.project.pk}),
        )
        self.assertEqual(response.context["project"], self.project)

    def test_custom_context_changes_for_project(self):
        response = self.client_mgr.get(self.project_uri)
        self.assertIn("cancel_link", response.context)
        self.assertEqual(
            response.context["cancel_link"],
            reverse("rolodex:project_detail", kwargs={"pk": self.project.pk}),
        )

    def test_form_with_no_active_projects(self):
        self.project.complete = True
        self.project.save()

        response = self.client_auth.get(self.uri)
        self.assertInHTML(
            '<option value="" selected>-- No Active Projects --</option>',
            response.content.decode(),
        )

        self.project.complete = False
        self.project.save()


class OplogMuteToggleViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogMuteToggle`."""

    @classmethod
    def setUpTestData(cls):
        cls.log = OplogFactory()
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.admin_user = UserFactory(password=PASSWORD, role="admin")
        cls.uri = reverse("oplog:ajax_oplog_mute_toggle", kwargs={"pk": cls.log.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.client_admin = Client()
        self.client_auth.login(username=self.user.username, password=PASSWORD)
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.mgr_user.username, password=PASSWORD))
        self.client_admin.login(username=self.admin_user.username, password=PASSWORD)
        self.assertTrue(self.client_admin.login(username=self.admin_user.username, password=PASSWORD))

    def test_view_uri_exists_at_desired_location(self):
        data = {
            "result": "success",
            "message": "Log monitor notifications have been muted.",
            "toggle": 1,
        }
        self.log.mute_notifications = False
        self.log.save()

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertJSONEqual(force_str(response.content), data)

        self.log.refresh_from_db()
        self.assertEqual(self.log.mute_notifications, True)

        data = {
            "result": "success",
            "message": "Log monitor notifications have been unmuted.",
            "toggle": 0,
        }
        response = self.client_mgr.post(self.uri)
        self.assertJSONEqual(force_str(response.content), data)

        self.log.refresh_from_db()
        self.assertEqual(self.log.mute_notifications, False)

    def test_view_requires_login(self):
        response = self.client.post(self.uri)
        self.assertEqual(response.status_code, 302)

    def test_view_permissions(self):
        response = self.client_auth.post(self.uri)
        self.assertEqual(response.status_code, 403)
        data = {
            "result": "error",
            "message": "Only a manager or admin can mute notifications.",
        }
        self.assertJSONEqual(force_str(response.content), data)

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", force_str(response.content))

        response = self.client_admin.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", force_str(response.content))

        response = self.client_mgr.post(self.uri)
        self.assertEqual(response.status_code, 200)
        self.assertIn("success", force_str(response.content))


class OplogEntryUpdateViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogEntryUpdate`."""

    @classmethod
    def setUpTestData(cls):
        cls.log = OplogFactory()
        cls.entry = OplogEntryFactory(oplog_id=cls.log)
        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:oplog_entry_update", kwargs={"pk": cls.entry.pk})

    def setUp(self):
        self.client = Client()
        self.client_auth = Client()
        self.client_mgr = Client()
        self.assertTrue(self.client_auth.login(username=self.user.username, password=PASSWORD))
        self.assertTrue(self.client_mgr.login(username=self.mgr_user.username, password=PASSWORD))

    def test_permissions(self):
        response = self.client_auth.get(self.uri, **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 302)

        ProjectAssignmentFactory(operator=self.user, project=self.log.project)

        response = self.client_auth.get(self.uri, **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)

        response = self.client_mgr.get(self.uri, **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)

    def test_view_uses_correct_ajax_template(self):
        response = self.client_mgr.get(self.uri, **{"HTTP_X_REQUESTED_WITH": "XMLHttpRequest"})
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "oplog/snippets/oplogentry_form_inner.html")


class OplogExportViewTests(TestCase):
    """Collection of tests for :view:`oplog.OplogExport`."""

    @classmethod
    def setUpTestData(cls):
        cls.Oplog = OplogFactory._meta.model
        cls.OplogEntry = OplogEntryFactory._meta.model

        cls.oplog = OplogFactory()
        OplogEntryFactory.create_batch(5, oplog_id=cls.oplog)

        cls.user = UserFactory(password=PASSWORD)
        cls.mgr_user = UserFactory(password=PASSWORD, role="manager")
        cls.uri = reverse("oplog:oplog_export", kwargs={"pk": cls.oplog.id})

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

        ProjectAssignmentFactory(operator=self.user, project=self.oplog.project)

        response = self.client_auth.get(self.uri)
        self.assertEqual(response.status_code, 200)
