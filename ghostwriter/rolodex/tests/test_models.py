# Standard Libraries
import logging
from datetime import timedelta

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ClientContactFactory,
    ClientFactory,
    ClientNoteFactory,
    HistoryFactory,
    ObjectivePriorityFactory,
    ObjectiveStatusFactory,
    ProjectAssignmentFactory,
    ProjectFactory,
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
)

logging.disable(logging.INFO)


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
        self.assertQuerysetEqual(
            self.Client.objects.all(),
            ["<Client: SpecterOps, Inc.>"],
        )

        # Update
        client.name = "Kabletown"
        client.save()
        self.assertQuerysetEqual(
            self.Client.objects.all(),
            ["<Client: Kabletown>"],
        )

        # Delete
        client.delete()
        assert not self.Client.objects.all().exists()


class ClientContactModelTests(TestCase):
    """Collection of tests for :model:`rolodex.ClientContact`."""

    @classmethod
    def setUpTestData(cls):
        cls.ClientContact = ClientContactFactory._meta.model

    def test_crud_finding(self):
        # Create
        client = ClientContactFactory(name="David")

        # Read
        self.assertEqual(client.name, "David")
        self.assertEqual(client.pk, client.id)
        self.assertQuerysetEqual(
            self.ClientContact.objects.all(),
            [f"<ClientContact: {client.name} ({client.client})>"],
        )

        # Update
        client.name = "Kabletown"
        client.save()
        self.assertQuerysetEqual(
            self.ClientContact.objects.all(),
            [f"<ClientContact: {client.name} ({client.client})>"],
        )

        # Delete
        client.delete()
        assert not self.ClientContact.objects.all().exists()


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
        self.assertQuerysetEqual(
            self.ProjectType.objects.all(),
            ["<ProjectType: Red Team>"],
        )

        # Update
        project_type.project_type = "Penetration Test"
        project_type.save()
        self.assertQuerysetEqual(
            self.ProjectType.objects.all(),
            ["<ProjectType: Penetration Test>"],
        )

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
        self.assertQuerysetEqual(
            self.Project.objects.all(),
            [
                f"<Project: {project.start_date} {project.client} {project.project_type} (S3kr3t Codename)>"
            ],
        )

        # Update
        project.codename = "New Name"
        project.save()
        self.assertQuerysetEqual(
            self.Project.objects.all(),
            [
                f"<Project: {project.start_date} {project.client} {project.project_type} (New Name)>"
            ],
        )

        # Delete
        project.delete()
        assert not self.Project.objects.all().exists()

    def test_checkout_adjustment_signal(self):
        project = ProjectFactory()
        domain_checkout = HistoryFactory(
            start_date=project.start_date, end_date=project.end_date, project=project
        )
        server_checkout = ServerHistoryFactory(
            start_date=project.start_date, end_date=project.end_date, project=project
        )

        new_start = project.start_date - timedelta(days=14)
        new_end = project.end_date - timedelta(days=14)

        project.start_date = new_start
        project.end_date = new_end
        project.save()

        domain_checkout.refresh_from_db()
        server_checkout.refresh_from_db()

        self.assertEqual(domain_checkout.start_date, new_start)
        self.assertEqual(server_checkout.start_date, new_start)
        self.assertEqual(domain_checkout.end_date, new_end)
        self.assertEqual(server_checkout.end_date, new_end)

    def test_prop_count_findings(self):
        project = ProjectFactory()
        report = ReportFactory(project=project)
        for x in range(3):
            ReportFindingLinkFactory(report=report)
        self.assertEqual(project.count_findings(), 3)


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
        self.assertQuerysetEqual(
            self.ProjectRole.objects.all(),
            ["<ProjectRole: Lead>"],
        )

        # Update
        project_role.project_role = "Operator"
        project_role.save()
        self.assertQuerysetEqual(
            self.ProjectRole.objects.all(),
            ["<ProjectRole: Operator>"],
        )

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
        self.assertQuerysetEqual(
            self.ProjectAssignment.objects.all(),
            [
                f"<ProjectAssignment: {self.user} - {assignment.project} {assignment.end_date})>"
            ],
        )

        # Update
        assignment.operator = self.new_user
        assignment.save()
        self.assertQuerysetEqual(
            self.ProjectAssignment.objects.all(),
            [
                f"<ProjectAssignment: {self.new_user} - {assignment.project} {assignment.end_date})>"
            ],
        )

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
        self.assertQuerysetEqual(
            self.ObjectiveStatus.objects.all(),
            ["<ObjectiveStatus: In Progress>"],
        )

        # Update
        status.objective_status = "Done"
        status.save()
        self.assertQuerysetEqual(
            self.ObjectiveStatus.objects.all(),
            ["<ObjectiveStatus: Done>"],
        )

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
        self.assertQuerysetEqual(
            self.ObjectivePriority.objects.all(),
            ["<ObjectivePriority: Primary>"],
        )

        # Update
        priority.priority = "Secondary"
        priority.save()
        self.assertQuerysetEqual(
            self.ObjectivePriority.objects.all(),
            ["<ObjectivePriority: Secondary>"],
        )

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
        self.assertQuerysetEqual(
            self.ProjectObjective.objects.all(),
            [f"<ProjectObjective: {obj.project} - Get DA {obj.status})>"],
        )

        # Update
        obj.objective = "Access git"
        obj.save()
        self.assertQuerysetEqual(
            self.ProjectObjective.objects.all(),
            [f"<ProjectObjective: {obj.project} - Access git {obj.status})>"],
        )

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
            self.fail(
                "ProjectObjective model `calculate_status` method failed unexpectedly!"
            )


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
        self.assertQuerysetEqual(
            self.ProjectSubtask.objects.all(),
            [f"<ProjectSubTask: {task.parent.project} : Get an account ({task.status})>"],
        )

        # Update
        task.task = "Compromise an account"
        task.save()
        self.assertQuerysetEqual(
            self.ProjectSubtask.objects.all(),
            [
                f"<ProjectSubTask: {task.parent.project} : Compromise an account ({task.status})>"
            ],
        )

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
        self.assertQuerysetEqual(
            self.ClientNote.objects.all(),
            [f"<ClientNote: {note.client}: {note.timestamp} - Client note>"],
        )

        # Update
        note.note = "Updated note"
        note.save()
        self.assertQuerysetEqual(
            self.ClientNote.objects.all(),
            [f"<ClientNote: {note.client}: {note.timestamp} - Updated note>"],
        )

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
        self.assertQuerysetEqual(
            self.ProjectNote.objects.all(),
            [f"<ProjectNote: {note.project}: {note.timestamp} - Project note>"],
        )

        # Update
        note.note = "Updated note"
        note.save()
        self.assertQuerysetEqual(
            self.ProjectNote.objects.all(),
            [f"<ProjectNote: {note.project}: {note.timestamp} - Updated note>"],
        )

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
        self.assertQuerysetEqual(
            self.ProjectScope.objects.all(),
            [f"<ProjectScope: {scope.project}: CDE>"],
        )

        # Update
        scope.name = "Mainframes"
        scope.save()
        self.assertQuerysetEqual(
            self.ProjectScope.objects.all(),
            [f"<ProjectScope: {scope.project}: Mainframes>"],
        )

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
        self.assertQuerysetEqual(
            self.ProjectTarget.objects.all(),
            [f"<ProjectTarget: {target.hostname} (1.1.1.1)>"],
        )

        # Update
        target.ip_address = "1.1.1.2"
        target.save()
        self.assertQuerysetEqual(
            self.ProjectTarget.objects.all(),
            [f"<ProjectTarget: {target.hostname} (1.1.1.2)>"],
        )

        # Delete
        target.delete()
        assert not self.ProjectTarget.objects.all().exists()
