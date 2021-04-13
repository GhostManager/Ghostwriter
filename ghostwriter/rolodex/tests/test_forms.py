# Django Imports
from django.contrib.auth import get_user_model
from django.forms.models import inlineformset_factory
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.rolodex.forms_client import (
    BaseClientContactInlineFormSet,
    ClientContactForm,
    ClientForm,
    ClientNoteForm,
)
from ghostwriter.rolodex.forms_project import (
    BaseProjectAssignmentInlineFormSet,
    BaseProjectObjectiveInlineFormSet,
    ProjectAssignmentForm,
    ProjectForm,
    ProjectNoteForm,
    ProjectObjectiveForm,
)
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectObjective,
    ProjectRole,
    ProjectType,
)

User = get_user_model()


class ProjectFormTest(TestCase):
    """
    Test :form:`forms_project.ProjectForm`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )
        self.project_role = ProjectRole.objects.create(project_role="Assessment Lead")
        self.project_type = ProjectType.objects.create(project_type="Red Team")

        # Setup users
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.reg_user = User.objects.create_user(
            "spenny", "spenny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.reg_user.is_active = True
        self.reg_user.save()

    def form_data(self, start_date, end_date, note, slack_channel, project_type, client):
        # Create `ProjectForm` form data
        return ProjectForm(
            data={
                "start_date": start_date,
                "end_date": end_date,
                "note": note,
                "slack_channel": slack_channel,
                "project_type": project_type,
                "client": client,
            },
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        # Send all valid form data
        form = self.form_data(
            start_date="2020-06-22",
            end_date="2020-06-27",
            note="Some note content from test",
            slack_channel="#slack",
            project_type=self.project_type.pk,
            client=self.client.pk,
        )
        self.assertTrue(form.is_valid())

    def test_invalid_dates(self):
        """
        Attempt to validate form data with invalid dates.
        """
        # Provide an ``end_date`` value that is before ``start_date``
        form = self.form_data(
            start_date="2020-06-27",
            end_date="2020-06-22",
            note="Some note content from test",
            slack_channel="#slack",
            project_type=self.project_type.pk,
            client=self.client.pk,
        )
        errors = form["end_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_date")

    def test_missing_date(self):
        """
        Attempt to validate form data that is missing a date.
        """
        # Do not provide an ``end_date`` value
        form = self.form_data(
            start_date="2020-06-27",
            end_date="",
            note="Some note content from test",
            slack_channel="#slack",
            project_type=self.project_type.pk,
            client=self.client.pk,
        )
        errors = form["end_date"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_invalid_slack(self):
        """
        Attempt to validate form data that has a Slack channel without a ``#``.
        """
        # Provide a Slack channel without ``#``
        form = self.form_data(
            start_date="2020-06-22",
            end_date="2020-06-27",
            note="Some note content from test",
            slack_channel="slack",
            project_type=self.project_type.pk,
            client=self.client.pk,
        )
        errors = form["slack_channel"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid_channel")


class ProjectObjectiveFormsetTest(TestCase):
    """
    Test :formset:`forms_project.ProjectObjectiveFormSet`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )
        self.project_role = ProjectRole.objects.create(project_role="Assessment Lead")
        self.project_type = ProjectType.objects.create(project_type="Red Team")
        self.objective_status = ObjectiveStatus.objects.create(objective_status="Active")

        # Setup an administrative user
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Setup a regular user
        self.reg_user = User.objects.create_user(
            "spenny", "spenny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.reg_user.is_active = True
        self.reg_user.save()

        # Create the same sort of `ProjectObjectiveFormSet` formset used with `ProjectForm`
        self.ProjectObjectiveFormSet = inlineformset_factory(
            Project,
            ProjectObjective,
            form=ProjectObjectiveForm,
            formset=BaseProjectObjectiveInlineFormSet,
        )

    def form_data(self, deadline_1="", objective_1="", deadline_2="", objective_2=""):
        # Create `ProjectObjectiveFormSet` formset data
        return self.ProjectObjectiveFormSet(
            data={
                "start_date": "2020-06-22",
                "end_date": "2020-06-27",
                "note": "Some note content from test",
                "slack_channel": "#slack",
                "project_type": self.project_type.pk,
                "client": self.client.pk,
                "obj-TOTAL_FORMS": 2,
                "obj-INITIAL_FORMS": 0,
                "obj-0-objective": objective_1,
                "obj-0-deadline": deadline_1,
                "obj-1-objective": objective_2,
                "obj-1-deadline": deadline_2,
            },
            prefix="obj",
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        form = self.form_data(deadline_1="2020-06-22", objective_1="Objective 1")
        self.assertTrue(form.is_valid())

    def test_empty_fields(self):
        """
        Attempt to validate an empty form.
        """
        # An empty formset should always be ignored and validate true
        form = self.form_data("", "")
        self.assertTrue(form.is_valid())

    def test_duplicate_objectives(self):
        """
        Attempt to validate form data with duplicate entries.
        """
        # Validate a form with duplicate ``objective`` values
        form = self.form_data(
            deadline_1="2020-06-22",
            objective_1="Objective 1",
            deadline_2="2020-06-22",
            objective_2="Objective 1",
        )
        errors = form.errors[1]["objective"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_missing_date(self):
        """
        Attempt to validate form data that is missing a date.
        """
        # Validate a form with a missing ``deadline`` value
        form = self.form_data(
            deadline_1="",
            objective_1="Objective 1",
        )
        errors = form.errors[0]["deadline"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_missing_objective(self):
        """
        Attempt to validate form data that is missing an objective.
        """
        # Validate a form with a missing ``objective`` value
        form = self.form_data(
            deadline_1="2020-06-22",
            objective_1="",
        )
        errors = form.errors[0]["objective"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")


class ProjectAssignmentFormsetTest(TestCase):
    """
    Test :formset:`forms_project.ProjectAssignmentFormSet`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )
        self.project_role = ProjectRole.objects.create(project_role="Assessment Lead")
        self.project_type = ProjectType.objects.create(project_type="Red Team")
        self.objective_status = ObjectiveStatus.objects.create(objective_status="Active")

        # Setup an administrative user
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Setup a regular user
        self.reg_user = User.objects.create_user(
            "spenny", "spenny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.reg_user.is_active = True
        self.reg_user.save()

        # Create the same sort of `ProjectAssignmentFormSet` formset used with `ProjectForm`
        self.ProjectAssignmentFormSet = inlineformset_factory(
            Project,
            ProjectAssignment,
            form=ProjectAssignmentForm,
            formset=BaseProjectAssignmentInlineFormSet,
        )

    def form_data(
        self,
        operator_1,
        role_1,
        start_date_1,
        end_date_1,
        note_1="",
        operator_2="",
        role_2="",
        start_date_2="",
        end_date_2="",
        note_2="",
    ):
        # Create `ProjectAssignmentForm` form data
        return self.ProjectAssignmentFormSet(
            data={
                "start_date": "2020-06-22",
                "end_date": "2020-06-27",
                "note": "Some note content from test",
                "slack_channel": "#slack",
                "project_type": self.project_type.pk,
                "client": self.client.pk,
                "assign-TOTAL_FORMS": 2,
                "assign-INITIAL_FORMS": 0,
                "assign-0-operator": operator_1,
                "assign-0-role": role_1,
                "assign-0-start_date": start_date_1,
                "assign-0-end_date": end_date_1,
                "assign-0-note": note_1,
                "assign-1-operator": operator_2,
                "assign-1-role": role_2,
                "assign-1-start_date": start_date_2,
                "assign-1-end_date": end_date_2,
                "assign-1-note": note_2,
            },
            prefix="assign",
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="2020-06-27",
            note_1="",
        )
        self.assertTrue(form.is_valid())

    def test_empty_fields(self):
        """
        Attempt to validate an empty form.
        """
        # An empty formset should always be ignored and validate true
        form = self.form_data("", "", "", "")
        self.assertTrue(form.is_valid())

    def test_duplicate_assignments(self):
        """
        Attempt to validate form data with a duplicate entry.
        """
        # Validate a form with duplicate entries
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="2020-06-27",
            note_1="",
            operator_2=self.staff_user.pk,
            role_2=self.project_role.pk,
            start_date_2="2020-06-22",
            end_date_2="2020-06-27",
            note_2="",
        )
        errors = form.errors[1]["operator"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_missing_start_date(self):
        """
        Attempt to validate form data that is missing a start date.
        """
        # Validate a form with a missing ``start_date`` value
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="2020-06-27",
            note_1="",
            operator_2=self.staff_user.pk,
            role_2=self.project_role.pk,
            start_date_2="",
            end_date_2="2020-06-27",
            note_2="",
        )
        errors = form.errors[1]["start_date"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_missing_end_date(self):
        """
        Attempt to validate form data that is missing an end date.
        """
        # Validate a form with a missing ``end_date`` value
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="",
            note_1="",
            operator_2=self.staff_user.pk,
            role_2=self.project_role.pk,
            start_date_2="2020-06-22",
            end_date_2="",
            note_2="",
        )
        errors = form.errors[1]["end_date"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_missing_operator(self):
        """
        Attempt to validate form data that is missing a person.
        """
        # Validate a form with a missing ``operator`` selection
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="2020-06-27",
            note_1="",
            operator_2="",
            role_2=self.project_role.pk,
            start_date_2="2020-06-22",
            end_date_2="2020-06-27",
            note_2="",
        )
        errors = form.errors[1]["operator"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_blank_with_note(self):
        """
        Attempt to validate form data that is missing all but a note.
        """
        # Validate a form with just a value for the ``note`` field
        form = self.form_data(
            operator_1=self.staff_user.pk,
            role_1=self.project_role.pk,
            start_date_1="2020-06-22",
            end_date_1="2020-06-27",
            note_1="",
            operator_2="",
            role_2="",
            start_date_2="",
            end_date_2="",
            note_2="Assignment note",
        )
        errors = form.errors[1]["note"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")


class ClientFormTest(TestCase):
    """
    Test :form:`forms_client.ClientForm`.
    """

    def setUp(self):
        # Setup users
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()
        self.reg_user = User.objects.create_user(
            "spenny", "spenny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.reg_user.is_active = True
        self.reg_user.save()

    def form_data(self, name, short_name, note):
        # Create `ClientForm` form data
        return ClientForm(
            data={"name": name, "short_name": short_name, "note": note},
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        # Send all valid project data
        form = self.form_data(
            name="Kabeltown",
            short_name="K-Town",
            note="This is a test note",
        )
        self.assertTrue(form.is_valid())


class ClientContactFormSetTest(TestCase):
    """
    Test :formset:`forms_client.ClientContactFormSet`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )

        # Setup an administrative user
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()

        # Setup a regular user
        self.reg_user = User.objects.create_user(
            "spenny", "spenny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.reg_user.is_active = True
        self.reg_user.save()

        # Create the same sort of `ClientContactForm` formset used with `ClientForm`
        self.ClientContactFormSet = inlineformset_factory(
            Client,
            ClientContact,
            form=ClientContactForm,
            formset=BaseClientContactInlineFormSet,
            extra=1,
            can_delete=True,
        )

    def form_data(
        self,
        name_0="",
        email_0="",
        phone_0="",
        job_title_0="",
        note_0="",
        name_1="",
        email_1="",
        phone_1="",
        job_title_1="",
        note_1="",
    ):
        # Create `ClientContactFormSet` form data
        return self.ClientContactFormSet(
            data={
                "poc-TOTAL_FORMS": 2,
                "poc-INITIAL_FORMS": 0,
                "poc-0-name": name_0,
                "poc-0-email": email_0,
                "poc-0-phone": phone_0,
                "poc-0-job_title": job_title_0,
                "poc-0-note": note_0,
                "poc-1-name": name_1,
                "poc-1-email": email_1,
                "poc-1-phone": phone_1,
                "poc-1-job_title": job_title_1,
                "poc-1-note": note_1,
            },
            prefix="poc",
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        form = self.form_data(
            name_0="David McQuire",
            email_0="info@specterops.io",
            phone_0="(555) 555-5555",
            job_title_0="CEO",
            note_0="A note about this contact",
        )
        self.assertTrue(form.is_valid())

    def test_empty_fields(self):
        """
        Attempt to validate an empty form.
        """
        # An empty formset should always be ignored and validate true
        form = self.form_data()
        self.assertTrue(form.is_valid())

    def test_duplicate_contacts(self):
        """
        Attempt to validate form data with duplicate entries.
        """
        # Validate a form with duplicate ``name`` values
        form = self.form_data(
            name_0="David McQuire",
            email_0="info@specterops.io",
            phone_0="(555) 555-5555",
            job_title_0="CEO",
            note_0="A note about this contact",
            name_1="David McQuire",
            email_1="info@specterops.io",
            phone_1="(555) 555-5555",
            job_title_1="CEO",
            note_1="A note about this contact",
        )
        errors = form.errors[1]["name"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "duplicate")

    def test_missing_name(self):
        """
        Attempt to validate form data with a missing name.
        """
        # Validate a form with a missing contact ``name``
        form = self.form_data(
            name_0="David McQuire",
            email_0="info@specterops.io",
            phone_0="(555) 555-5555",
            job_title_0="CEO",
            note_0="A note about this contact",
            name_1="",
            email_1="info@specterops.io",
            phone_1="(555) 555-5555",
            job_title_1="CEO",
            note_1="A note about this contact",
        )
        errors = form.errors[1]["name"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")

    def test_missing_details(self):
        """
        Attempt to validate form data with a missing required field.
        """
        # Validate a form with a blank required field, ``job_title``
        form = self.form_data(
            name_0="David McQuire",
            email_0="info@specterops.io",
            phone_0="(555) 555-5555",
            job_title_0="CEO",
            note_0="A note about this contact",
            name_1="Jeff Dimmock",
            email_1="info@specterops.io",
            phone_1="(555) 555-5555",
            job_title_1="",
            note_1="A note about this contact",
        )
        errors = form.errors[1]["job_title"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "incomplete")

    def test_invalid_email(self):
        """
        Attempt to validate form data with an invalid email address.
        """
        # Validate a form with an invalid ``email`` value
        form = self.form_data(
            name_0="David McQuire",
            email_0="info at specterops.io",
            phone_0="(555) 555-5555",
            job_title_0="CEO",
            note_0="A note about this contact",
        )
        errors = form.errors[0]["email"].as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "invalid")


class ProjectNoteTest(TestCase):
    """
    Test :form:`forms_project.ProjectNote`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )
        self.project_type = ProjectType.objects.create(project_type="Red Team")
        self.project = Project.objects.create(
            start_date="2020-06-22",
            end_date="2020-06-27",
            project_type=self.project_type,
            client=self.client,
        )
        # Setup an administrative user
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()

    def form_data(self, note, project, operator):
        # Create `PojectNoteForm` form data
        return ProjectNoteForm(
            data={"note": note, "project": project, "operator": operator}
        )

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        # Send all valid form data
        form = self.form_data(
            note="This is a test note",
            project=self.project.pk,
            operator=self.staff_user.pk,
        )
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        """
        Attempt to validate form data with invalid dates.
        """
        # Provide a blank note
        form = self.form_data(
            note="", project=self.project.pk, operator=self.staff_user.pk
        )
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")


class ClientNoteTest(TestCase):
    """
    Test :form:`forms_clientClientNote`.
    """

    def setUp(self):
        # Setup foreign key entries
        self.client = Client.objects.create(
            name="Kabletown", short_name="K-Town", note="Client note for the test"
        )
        # Setup an administrative user
        self.staff_user = User.objects.create_user(
            "benny", "benny@getghostwriter.io", "SupernaturalReporting_1337!"
        )
        self.staff_user.is_active = True
        self.staff_user.is_staff = True
        self.staff_user.save()

    def form_data(self, note, client, operator):
        # Create `ClientNoteForm` form data
        return ClientNoteForm(data={"note": note, "client": client, "operator": operator})

    def test_valid_data(self):
        """
        Attempt to validate form data that should always validate.
        """
        # Send all valid form data
        form = self.form_data(
            note="This is a test note",
            client=self.client.pk,
            operator=self.staff_user.pk,
        )
        self.assertTrue(form.is_valid())

    def test_blank_note(self):
        """
        Attempt to validate form data with invalid dates.
        """
        # Provide a blank note
        form = self.form_data(note="", client=self.client.pk, operator=self.staff_user.pk)
        errors = form["note"].errors.as_data()
        self.assertEqual(len(errors), 1)
        self.assertEqual(errors[0].code, "required")
