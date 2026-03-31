# Standard Libraries
import logging
from datetime import date, datetime, timedelta, timezone

# Django Imports
from django.core.exceptions import ValidationError
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ClientContactFactory,
    ClientFactory,
    ClientInviteFactory,
    ClientNoteFactory,
    DeconflictionFactory,
    DeconflictionStatusFactory,
    HistoryFactory,
    ObjectivePriorityFactory,
    ObjectiveStatusFactory,
    OplogEntryFactory,
    OplogFactory,
    ProjectAssignmentFactory,
    ProjectCollabNoteFactory,
    ProjectCollabNoteFieldFactory,
    ProjectCollabNoteFolderFactory,
    ProjectContactFactory,
    ProjectFactory,
    ProjectInviteFactory,
    ProjectNoteFactory,
    ProjectObjectiveFactory,
    ProjectRoleFactory,
    ProjectScopeFactory,
    ProjectSubtaskFactory,
    ProjectTargetFactory,
    ProjectTypeFactory,
    ReportFactory,
    ReportFindingLinkFactory,
    ServerHistoryFactory,
    UserFactory,
    WhiteCardFactory,
)
from ghostwriter.rolodex.models import Client, Project, ProjectCollabNote, ProjectCollabNoteField

logging.disable(logging.CRITICAL)


class ClientModelTests(TestCase):
    """Collection of tests for :model:`rolodex.Client`."""

    @classmethod
    def setUpTestData(cls):
        cls.Client = ClientFactory._meta.model

    def test_crud_finding(self):
        # Create
        client = ClientFactory(name="SpecterOps, Inc.")

        # Read
        self.assertEqual(client.name, "SpecterOps, Inc.")
        self.assertEqual(client.pk, client.id)

        # Update
        client.name = "Kabletown"
        client.save()

        # Delete
        client.delete()
        assert not self.Client.objects.all().exists()

    def test_get_absolute_url(self):
        client = ClientFactory(name="SpecterOps, Inc.")
        try:
            client.get_absolute_url()
        except:
            self.fail("Client.get_absolute_url() raised an exception")

    def test_access(self):
        client: Client = ClientFactory(name="SpecterOps, Inc.")
        user = UserFactory(password="SuperNaturalReporting!")

        self.assertFalse(Client.user_can_create(user))
        self.assertFalse(client.user_can_view(user))
        self.assertFalse(client.user_can_edit(user))
        self.assertFalse(client.user_can_delete(user))

        user.role = "manager"
        user.save()
        self.assertTrue(Client.user_can_create(user))
        self.assertTrue(client.user_can_view(user))
        self.assertTrue(client.user_can_edit(user))
        self.assertTrue(client.user_can_delete(user))

        user.role = "user"
        user.save()
        self.assertFalse(Client.user_can_create(user))
        self.assertFalse(client.user_can_view(user))
        self.assertFalse(client.user_can_edit(user))
        self.assertFalse(client.user_can_delete(user))

        client_invite = ClientInviteFactory(user=user, client=client)
        self.assertFalse(Client.user_can_create(user))
        self.assertTrue(client.user_can_view(user))
        self.assertTrue(client.user_can_edit(user))
        self.assertTrue(client.user_can_delete(user))

        client_invite.delete()
        self.assertFalse(Client.user_can_create(user))
        self.assertFalse(client.user_can_view(user))
        self.assertFalse(client.user_can_edit(user))
        self.assertFalse(client.user_can_delete(user))


class ClientContactModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ClientContact`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientContact = ClientContactFactory._meta.model

    def test_crud_finding(self):
        # Create
        contact = ClientContactFactory(name="David")

        # Read
        self.assertEqual(contact.name, "David")
        self.assertEqual(contact.pk, contact.id)

        # Update
        contact.name = "Jason"
        contact.save()

        # Delete
        contact.delete()
        assert not self.ClientContact.objects.all().exists()

    def test_primary_defaults_to_false(self):
        contact = ClientContactFactory()
        self.assertFalse(contact.primary)

    def test_primary_can_be_set(self):
        contact = ClientContactFactory(primary=True)
        self.assertTrue(contact.primary)


class ProjectTypeModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectType`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectType = ProjectTypeFactory._meta.model

    def test_crud_finding(self):
        # Create
        project_type = ProjectTypeFactory(project_type="Red Team")

        # Read
        self.assertEqual(project_type.project_type, "Red Team")
        self.assertEqual(project_type.pk, project_type.id)

        # Update
        project_type.project_type = "Penetration Test"
        project_type.save()

        # Delete
        project_type.delete()
        assert not self.ProjectType.objects.all().exists()


class ProjectModelTests(TestCase):
    """Collection of tests for :model:`rolodex.Project`."""

    @classmethod
    def setUpTestData(cls):
        cls.Project = ProjectFactory._meta.model

    def test_crud_finding(self):
        # Create
        project = ProjectFactory(codename="S3kr3t Codename")

        # Read
        self.assertEqual(project.codename, "S3kr3t Codename")
        self.assertEqual(project.pk, project.id)

        # Update
        project.codename = "New Name"
        project.save()

        # Delete
        project.delete()
        assert not self.Project.objects.all().exists()

    def test_get_absolute_url(self):
        project = ProjectFactory()
        try:
            project.get_absolute_url()
        except:
            self.fail("Project.get_absolute_url() raised an exception")

    def test_checkout_adjustment_signal(self):
        yesterday = date.today() - timedelta(days=1)

        project = ProjectFactory(
            start_date=date.today() - timedelta(days=14),
            end_date=date.today() + timedelta(days=14),
        )

        domain_checkout = HistoryFactory(start_date=project.start_date, end_date=project.end_date, project=project)
        exp_domain_checkout = HistoryFactory(start_date=project.start_date, end_date=yesterday, project=project)
        server_checkout = ServerHistoryFactory(
            start_date=project.start_date, end_date=project.end_date, project=project
        )
        exp_server_checkout = ServerHistoryFactory(start_date=project.start_date, end_date=yesterday, project=project)

        new_start = project.start_date - timedelta(days=7)
        new_end = project.end_date + timedelta(days=7)

        project.start_date = new_start
        project.end_date = new_end
        project.save()

        domain_checkout.refresh_from_db()
        exp_domain_checkout.refresh_from_db()
        server_checkout.refresh_from_db()
        exp_server_checkout.refresh_from_db()

        self.assertEqual(domain_checkout.start_date, new_start)
        self.assertEqual(server_checkout.start_date, new_start)
        self.assertEqual(domain_checkout.end_date, new_end)
        self.assertEqual(server_checkout.end_date, new_end)
        self.assertEqual(exp_domain_checkout.end_date, yesterday)
        self.assertEqual(exp_server_checkout.end_date, yesterday)

    def test_prop_count_findings(self):
        project = ProjectFactory()
        report = ReportFactory(project=project)
        for x in range(3):
            ReportFindingLinkFactory(report=report)
        self.assertEqual(project.count_findings(), 3)

    def test_update_project_signal(self):
        project = ProjectFactory(slack_channel="")
        project.end_date = project.end_date + timedelta(days=1)
        project.save()
        project.slack_channel = "#testing"
        project.save()
        project.slack_channel = ""
        project.save()

    def test_access(self):
        project: Project = ProjectFactory()
        user = UserFactory(password="SuperNaturalReporting!")

        self.assertFalse(Project.user_can_create(user))
        self.assertFalse(project.user_can_view(user))
        self.assertFalse(project.user_can_edit(user))
        self.assertFalse(project.user_can_delete(user))

        user.role = "manager"
        user.save()
        self.assertTrue(Project.user_can_create(user))
        self.assertTrue(project.user_can_view(user))
        self.assertTrue(project.user_can_edit(user))
        self.assertTrue(project.user_can_delete(user))

        user.role = "user"
        user.save()
        self.assertFalse(Project.user_can_create(user))
        self.assertFalse(project.user_can_view(user))
        self.assertFalse(project.user_can_edit(user))
        self.assertFalse(project.user_can_delete(user))

        assignment = ProjectAssignmentFactory(operator=user, project=project)
        self.assertFalse(Project.user_can_create(user))
        self.assertTrue(project.user_can_view(user))
        self.assertTrue(project.user_can_edit(user))
        self.assertTrue(project.user_can_delete(user))

        assignment.delete()
        self.assertFalse(Project.user_can_create(user))
        self.assertFalse(project.user_can_view(user))
        self.assertFalse(project.user_can_edit(user))
        self.assertFalse(project.user_can_delete(user))

        client_invite = ClientInviteFactory(user=user, client=project.client)
        self.assertFalse(Project.user_can_create(user))
        self.assertTrue(project.user_can_view(user))
        self.assertTrue(project.user_can_edit(user))
        self.assertTrue(project.user_can_delete(user))

        client_invite.delete()
        self.assertFalse(Project.user_can_create(user))
        self.assertFalse(project.user_can_view(user))
        self.assertFalse(project.user_can_edit(user))
        self.assertFalse(project.user_can_delete(user))


class ProjectRoleModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectRole`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectRole = ProjectRoleFactory._meta.model

    def test_crud_finding(self):
        # Create
        project_role = ProjectRoleFactory(project_role="Lead")

        # Read
        self.assertEqual(project_role.project_role, "Lead")
        self.assertEqual(project_role.pk, project_role.id)

        # Update
        project_role.project_role = "Operator"
        project_role.save()

        # Delete
        project_role.delete()
        assert not self.ProjectRole.objects.all().exists()


class ProjectAssignmentModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectAssignment`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectAssignment = ProjectAssignmentFactory._meta.model
        cls.user = UserFactory()
        cls.new_user = UserFactory()

    def test_crud_finding(self):
        # Create
        assignment = ProjectAssignmentFactory(operator=self.user)

        # Read
        self.assertEqual(assignment.operator, self.user)
        self.assertEqual(assignment.pk, assignment.id)

        # Update
        assignment.operator = self.new_user
        assignment.save()

        # Delete
        assignment.delete()
        assert not self.ProjectAssignment.objects.all().exists()


class ObjectiveStatusModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ObjectiveStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.ObjectiveStatus = ObjectiveStatusFactory._meta.model

    def test_crud_finding(self):
        # Create
        status = ObjectiveStatusFactory(objective_status="In Progress")

        # Read
        self.assertEqual(status.objective_status, "In Progress")
        self.assertEqual(status.pk, status.id)

        # Update
        status.objective_status = "Done"
        status.save()

        # Delete
        status.delete()
        assert not self.ObjectiveStatus.objects.all().exists()


class ObjectivePriorityModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ObjectivePriority`."""

    @classmethod
    def setUpTestData(cls):
        cls.ObjectivePriority = ObjectivePriorityFactory._meta.model

    def test_crud_finding(self):
        # Create
        priority = ObjectivePriorityFactory(priority="Primary")

        # Read
        self.assertEqual(priority.priority, "Primary")
        self.assertEqual(priority.pk, priority.id)

        # Update
        priority.priority = "Secondary"
        priority.save()

        # Delete
        priority.delete()
        assert not self.ObjectivePriority.objects.all().exists()


class ProjectObjectiveModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectObjective`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectObjective = ProjectObjectiveFactory._meta.model
        cls.status = ObjectiveStatusFactory(objective_status="Other")

    def test_crud_finding(self):
        # Create
        obj = ProjectObjectiveFactory(objective="Get DA")

        # Read
        self.assertEqual(obj.objective, "Get DA")
        self.assertEqual(obj.pk, obj.id)

        # Update
        obj.objective = "Access git"
        obj.save()

        # Delete
        obj.delete()
        assert not self.ProjectObjective.objects.all().exists()

    def test_method_calculate_status(self):
        obj = ProjectObjectiveFactory(complete=False)
        try:
            status = obj.calculate_status()
            self.assertEqual(0, status)

            ProjectSubtaskFactory(parent=obj, complete=False)
            ProjectSubtaskFactory(parent=obj, complete=True)
            status = obj.calculate_status()
            self.assertEqual(50.0, status)

            obj.complete = True
            obj.save()
            status = obj.calculate_status()
            self.assertEqual(100.0, status)
        except Exception:
            self.fail("ProjectObjective model `calculate_status` method failed unexpectedly!")


class ProjectSubTaskModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectSubTask`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectSubtask = ProjectSubtaskFactory._meta.model
        cls.status = ObjectiveStatusFactory(objective_status="Other")

    def test_crud_finding(self):
        # Create
        task = ProjectSubtaskFactory(task="Get an account")

        # Read
        self.assertEqual(task.task, "Get an account")
        self.assertEqual(task.pk, task.id)

        # Update
        task.task = "Compromise an account"
        task.save()

        # Delete
        task.delete()
        assert not self.ProjectSubtask.objects.all().exists()


class ClientNoteModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ClientNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientNote = ClientNoteFactory._meta.model

    def test_crud_finding(self):
        # Create
        note = ClientNoteFactory(note="Client note")

        # Read
        self.assertEqual(note.note, "Client note")
        self.assertEqual(note.pk, note.id)

        # Update
        note.note = "Updated note"
        note.save()

        # Delete
        note.delete()
        assert not self.ClientNote.objects.all().exists()


class ProjectNoteModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectNote = ProjectNoteFactory._meta.model

    def test_crud_finding(self):
        # Create
        note = ProjectNoteFactory(note="Project note")

        # Read
        self.assertEqual(note.note, "Project note")
        self.assertEqual(note.pk, note.id)

        # Update
        note.note = "Updated note"
        note.save()

        # Delete
        note.delete()
        assert not self.ProjectNote.objects.all().exists()


class ProjectScopeModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectScope`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectScope = ProjectScopeFactory._meta.model

    def test_crud_finding(self):
        # Create
        scope = ProjectScopeFactory(name="CDE")

        # Read
        self.assertEqual(scope.name, "CDE")
        self.assertEqual(scope.pk, scope.id)

        # Update
        scope.name = "Mainframes"
        scope.save()

        # Delete
        scope.delete()
        assert not self.ProjectScope.objects.all().exists()

    def test_method_count_lines(self):
        scope = ProjectScopeFactory(scope="1.1.1.1\n1.2.3.4\nhostname.local")
        try:
            lines = scope.count_lines()
            self.assertEqual(3, lines)
        except Exception:
            self.fail("ProjectScope model `count_lines` method failed unexpectedly!")

    def test_method_count_lines_str(self):
        scope = ProjectScopeFactory(scope="1.1.1.1\n1.2.3.4\nhostname.local")
        try:
            # Test with multiple lines
            lines = scope.count_lines_str()
            self.assertEqual("3 Lines", lines)

            # Test with single line
            scope.scope = "1.1.1.1"
            scope.save()
            lines = scope.count_lines_str()
            self.assertEqual("1 Line", lines)
        except Exception:
            self.fail("ProjectScope model `count_lines_str` method failed unexpectedly!")


class ProjectTargetModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectTarget`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectTarget = ProjectTargetFactory._meta.model

    def test_crud_finding(self):
        # Create
        target = ProjectTargetFactory(ip_address="1.1.1.1")

        # Read
        self.assertEqual(target.ip_address, "1.1.1.1")
        self.assertEqual(target.pk, target.id)

        # Update
        target.ip_address = "1.1.1.2"
        target.save()

        # Delete
        target.delete()
        assert not self.ProjectTarget.objects.all().exists()

    def test_invalid_ip(self):
        project = ProjectFactory()
        with self.assertRaises(ValidationError):
            obj = self.ProjectTarget.objects.create(ip_address="invalid", project_id=project.id)
            obj.full_clean()

        with self.assertRaises(ValidationError):
            obj = self.ProjectTarget.objects.create(ip_address="192.168.1.257", project_id=project.id)
            obj.full_clean()

        with self.assertRaises(ValidationError):
            obj = self.ProjectTarget.objects.create(ip_address="192.168.1.10/35", project_id=project.id)
            obj.full_clean()


class ClientInviteModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ClientInvite`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientInvite = ClientInviteFactory._meta.model

    def test_crud_finding(self):
        # Create
        invite = ClientInviteFactory(comment="Basic comment")

        # Read
        self.assertEqual(invite.comment, "Basic comment")
        self.assertEqual(invite.pk, invite.id)

        # Update
        invite.comment = "Updated comment"
        invite.save()
        invite.refresh_from_db()
        self.assertEqual(invite.comment, "Updated comment")

        # Delete
        invite.delete()
        assert not self.ClientInvite.objects.all().exists()


class ProjectInviteModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectInvite`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectInvite = ProjectInviteFactory._meta.model

    def test_crud_finding(self):
        # Create
        invite = ProjectInviteFactory(comment="Basic comment")

        # Read
        self.assertEqual(invite.comment, "Basic comment")
        self.assertEqual(invite.pk, invite.id)

        # Update
        invite.comment = "Updated comment"
        invite.save()
        invite.refresh_from_db()
        self.assertEqual(invite.comment, "Updated comment")

        # Delete
        invite.delete()
        assert not self.ProjectInvite.objects.all().exists()


class DeconflictionStatusModelTests(TestCase):
    """Collection of tests for :model:`rolodex.DeconflictionStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.DeconflictionStatus = DeconflictionStatusFactory._meta.model

    def test_crud_finding(self):
        # Create
        status = DeconflictionStatusFactory(status="Confirmed")

        # Read
        self.assertEqual(status.status, "Confirmed")
        self.assertEqual(status.pk, status.id)

        # Update
        status.status = "Undetermined"
        status.save()

        # Delete
        status.delete()
        assert not self.DeconflictionStatus.objects.all().exists()


class DeconflictionModelTests(TestCase):
    """Collection of tests for :model:`rolodex.Deconfliction`."""

    @classmethod
    def setUpTestData(cls):
        cls.Deconfliction = DeconflictionFactory._meta.model
        cls.project = ProjectFactory()

    def test_crud_finding(self):
        # Create
        status = DeconflictionFactory(title="Deconfliction Title", project=self.project)

        # Read
        self.assertEqual(status.title, "Deconfliction Title")
        self.assertEqual(status.pk, status.id)

        # Update
        status.title = "New Deconfliction Title"
        status.save()

        # Delete
        status.delete()
        assert not self.Deconfliction.objects.all().exists()

    def test_prop_log_entries(self):
        project = ProjectFactory()
        deconfliction = DeconflictionFactory(project=project, alert_timestamp=datetime.now(timezone.utc))
        oplog = OplogFactory(project=project)

        entry_too_old = OplogEntryFactory(oplog_id=oplog, start_date=datetime.now(timezone.utc) - timedelta(days=1))
        entry_hour_old = OplogEntryFactory(oplog_id=oplog, start_date=datetime.now(timezone.utc) - timedelta(hours=1))
        entry_within_hour = OplogEntryFactory(
            oplog_id=oplog, start_date=datetime.now(timezone.utc) - timedelta(minutes=30)
        )
        entry_recent = OplogEntryFactory(oplog_id=oplog, start_date=datetime.now(timezone.utc) + timedelta(minutes=5))

        self.assertEqual(len(deconfliction.log_entries), 2)
        self.assertTrue(entry_hour_old in deconfliction.log_entries)
        self.assertTrue(entry_within_hour in deconfliction.log_entries)
        self.assertFalse(entry_too_old in deconfliction.log_entries)
        self.assertFalse(entry_recent in deconfliction.log_entries)


class WhiteCardModelTests(TestCase):
    """Collection of tests for :model:`rolodex.WhiteCard`."""

    @classmethod
    def setUpTestData(cls):
        cls.WhiteCard = WhiteCardFactory._meta.model
        cls.project = ProjectFactory()

    def test_crud_finding(self):
        # Create
        card = WhiteCardFactory(title="White Card Title", project=self.project)

        # Read
        self.assertEqual(card.title, "White Card Title")
        self.assertEqual(card.pk, card.id)

        # Update
        card.title = "New White Card Title"
        card.save()

        # Delete
        card.delete()
        assert not self.WhiteCard.objects.all().exists()


class ProjectContactModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectContact`."""

    @classmethod
    def setUpTestData(cls):
        cls.ProjectContact = ProjectContactFactory._meta.model

    def test_crud_finding(self):
        # Create
        contact = ProjectContactFactory(name="David")

        # Read
        self.assertEqual(contact.name, "David")
        self.assertEqual(contact.pk, contact.id)

        # Update
        contact.name = "Kabletown"
        contact.save()

        # Delete
        contact.delete()
        assert not self.ProjectContact.objects.all().exists()


class ProjectCollabNoteModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectCollabNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory(password="test")
        cls.project = ProjectFactory()
        cls.assignment = ProjectAssignmentFactory(project=cls.project, operator=cls.user)

    def test_crud(self):
        note = ProjectCollabNoteFactory(project=self.project, title="Test Note")
        self.assertEqual(note.title, "Test Note")
        self.assertEqual(note.node_type, "note")

        note.title = "Updated"
        note.save()
        note.refresh_from_db()
        self.assertEqual(note.title, "Updated")

        note.delete()
        self.assertFalse(ProjectCollabNote.objects.filter(pk=note.pk).exists())

    def test_folder_creation(self):
        folder = ProjectCollabNoteFolderFactory(project=self.project, title="Folder")
        self.assertEqual(folder.node_type, "folder")
        self.assertEqual(folder.content, "")

    def test_hierarchical_structure(self):
        folder = ProjectCollabNoteFolderFactory(project=self.project)
        note = ProjectCollabNoteFactory(project=self.project, parent=folder)
        self.assertEqual(note.parent, folder)
        self.assertIn(note, folder.children.all())

    def test_cascade_delete(self):
        folder = ProjectCollabNoteFolderFactory(project=self.project)
        child = ProjectCollabNoteFactory(project=self.project, parent=folder)
        child_id = child.pk
        folder.delete()
        self.assertFalse(ProjectCollabNote.objects.filter(pk=child_id).exists())

    def test_user_can_edit_delegates_to_project(self):
        note = ProjectCollabNoteFactory(project=self.project)
        self.assertEqual(note.user_can_edit(self.user), self.project.user_can_edit(self.user))

    def test_str(self):
        note = ProjectCollabNoteFactory(title="My Note")
        self.assertEqual(str(note), "My Note (note)")


class ProjectCollabNoteFieldModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ProjectCollabNoteField`."""

    @classmethod
    def setUpTestData(cls):
        cls.note = ProjectCollabNoteFactory()

    def test_crud(self):
        field = ProjectCollabNoteFieldFactory(note=self.note, content="<p>Hello</p>")
        self.assertEqual(field.field_type, "rich_text")
        self.assertEqual(field.content, "<p>Hello</p>")

        field.content = "<p>Updated</p>"
        field.save()
        field.refresh_from_db()
        self.assertEqual(field.content, "<p>Updated</p>")

        field.delete()
        self.assertFalse(ProjectCollabNoteField.objects.filter(pk=field.pk).exists())

    def test_cascade_delete_with_note(self):
        note = ProjectCollabNoteFactory()
        field = ProjectCollabNoteFieldFactory(note=note)
        field_id = field.pk
        note.delete()
        self.assertFalse(ProjectCollabNoteField.objects.filter(pk=field_id).exists())

    def test_ordering(self):
        f1 = ProjectCollabNoteFieldFactory(note=self.note, position=2)
        f2 = ProjectCollabNoteFieldFactory(note=self.note, position=0)
        f3 = ProjectCollabNoteFieldFactory(note=self.note, position=1)
        fields = list(self.note.fields.all())
        self.assertEqual(fields, [f2, f3, f1])
