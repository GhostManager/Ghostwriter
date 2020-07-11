"""This contains all of the forms used by the Rolodex application."""

from crispy_forms.helper import FormHelper
from django import forms
from django.core.exceptions import ValidationError
from django.forms import formset_factory
from django.forms.models import BaseInlineFormSet
from django.utils.translation import ugettext_lazy as _

from .models import (
    Client,
    ClientContact,
    ClientNote,
    Project,
    ProjectAssignment,
    ProjectNote,
    ProjectObjective,
)


class ClientCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.Client`.
    """

    class Meta:
        model = Client
        fields = "__all__"
        widgets = {
            "name": forms.TextInput(attrs={"size": 55}),
            "codename": forms.HiddenInput(),
            "short_name": forms.TextInput(attrs={"size": 55}),
            "note": forms.Textarea(attrs={"cols": 55}),
        }

    def __init__(self, *args, **kwargs):
        """Override the `init()` function to set some attributes."""
        super(ClientCreateForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["placeholder"] = "SpecterOps, Inc."
        self.fields["short_name"].widget.attrs["placeholder"] = "SpecterOps"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "SpecterOps was founded in 2017 and ..."
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"


class ProjectCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.Project`.
    """

    class Meta:
        model = Project
        exclude = ("operator", "codename")
        widgets = {
            "slack_channel": forms.TextInput(attrs={"size": 55}),
            "note": forms.Textarea(attrs={"cols": 55}),
        }

    def __init__(self, *args, **kwargs):
        super(ProjectCreateForm, self).__init__(*args, **kwargs)
        self.fields["start_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["slack_channel"].widget.attrs["placeholder"] = "#client-rt-2019"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "This project is intended to assess ..."
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]
        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(
                _(
                    "Invalid project date: The provided end date comes before the start date"
                )
            )
        return end_date


class ClientContactCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.ClientContact` for a pre-defined
    :model:`rolodex.Client`.
    """

    class Meta:
        model = ClientContact
        exclude = ("last_used_by", "burned_explanation")
        widgets = {
            "client": forms.HiddenInput(),
            "name": forms.TextInput(attrs={"size": 55}),
            "job_title": forms.TextInput(attrs={"size": 55}),
            "email": forms.TextInput(attrs={"size": 55}),
            "phone": forms.TextInput(attrs={"size": 55}),
            "note": forms.Textarea(attrs={"cols": 55}),
        }

    def __init__(self, *args, **kwargs):
        super(ClientContactCreateForm, self).__init__(*args, **kwargs)
        self.fields["name"].widget.attrs["placeholder"] = "Name to appear in reports"
        self.fields["email"].widget.attrs["placeholder"] = "info@specterops.io"
        self.fields["phone"].widget.attrs["placeholder"] = "(###) ###-####"
        self.fields["job_title"].widget.attrs[
            "placeholder"
        ] = "A role/title to appear in reports"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "Additional notes on the contact"
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"


class AssignmentCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.ProjectAssignment` for a pre-defined
    :model:`users.User`.
    """

    class Meta:
        model = ProjectAssignment
        fields = "__all__"
        widgets = {"project": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super(AssignmentCreateForm, self).__init__(*args, **kwargs)
        self.fields["operator"].queryset = self.fields["operator"].queryset.order_by(
            "name"
        )
        self.fields["operator"].label_from_instance = lambda obj: "%s (%s)" % (
            obj.name,
            obj.username,
        )
        self.fields["start_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "This assignment is only for 3 of the 4 weeks ..."
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"

    def clean(self):
        cleaned_data = self.cleaned_data
        project = cleaned_data["project"]
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]
        if project:
            # Check if assignment dates are within the project date range
            if start_date < project.start_date:
                raise ValidationError(
                    _(
                        "Invalid assignment: The provided start date comes before the start of this project, {}".format(
                            project.start_date
                        )
                    )
                )
            if end_date > project.end_date:
                raise ValidationError(
                    _(
                        "Invalid assignment: The provided end date comes after the end of this project, {}".format(
                            project.end_date
                        )
                    )
                )

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]
        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(
                _(
                    "Invalid assignment: The provided end date comes before the project's start date"
                )
            )
        return end_date


class ClientNoteCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.ClientNote` for a :model:`rolodex.Client`.
    """

    class Meta:
        model = ClientNote
        fields = "__all__"
        widgets = {
            "timestamp": forms.HiddenInput(),
            "operator": forms.HiddenInput(),
            "client": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(ClientNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
        self.helper.form_show_labels = False


class ProjectNoteCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.ProjectNote` for a :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectNote
        fields = "__all__"
        widgets = {
            "timestamp": forms.HiddenInput(),
            "operator": forms.HiddenInput(),
            "project": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(ProjectNoteCreateForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
        self.helper.form_show_labels = False


class ProjectObjectiveCreateForm(forms.ModelForm):
    """
    Create an individual :model:`rolodex.ProjectObjective` for a :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectObjective
        fields = "__all__"
        widgets = {"project": forms.HiddenInput()}

    def __init__(self, *args, **kwargs):
        super(ProjectObjectiveCreateForm, self).__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["deadline"].widget.attrs["autocomplete"] = "off"
        self.fields["deadline"].widget.input_type = "date"
        self.fields["objective"].widget.attrs[
            "placeholder"
        ] = "Obtain commit privileges to git"
        self.fields["objective"].error_messages = {
            "required": "You must provide an objective"
        }
        self.fields["deadline"].error_messages = {
            "required": "You must provide a deadline"
        }
        self.fields["objective"].error_messages = {
            "required": "You must provide an objective"
        }
        self.fields["status"].error_messages = {"required": "You must provide a status"}
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
        self.helper.form_show_labels = False


class BaseProjectObjectiveInlineFormSet(BaseInlineFormSet):
    """
    Inline FormSet template for :model:`rolodex.ProjectObjective` that adds validation
    to check that the same objective is not created twice and the objective forms are
    all complete or blank.
    """

    def clean(self):
        objectives = []
        duplicates = False
        super(BaseProjectObjectiveInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                objective = form.cleaned_data["objective"]
                deadline = form.cleaned_data["deadline"]

                # Check that no two objectives are the same
                if objective:
                    if objective in objectives:
                        duplicates = True
                    objectives.append(objective)

                if duplicates:
                    form.add_error(
                        "objective",
                        "Duplicate entry: Your project objectives should be unique",
                    )

                # Check that all objective have a deadline and status
                if deadline and not objective:
                    form.add_error(
                        "objective",
                        "Incomplete entry: You set a deadline without an objective",
                    )
                elif objective and not deadline:
                    form.add_error(
                        "deadline",
                        "Incomplete entry: Your objective still needs a deadline",
                    )


class BaseProjectAssignmentInlineFormSet(BaseInlineFormSet):
    """
    Inline FormSet template for :model:`rolodex.ProjectAssignment` that adds validation
    to check that the same operator is not assigned twice and the assignment forms are
    all complete or blank.
    """

    def clean(self):
        assignments = []
        duplicates = False
        super(BaseProjectAssignmentInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                operator = form.cleaned_data["operator"]
                start_date = form.cleaned_data["start_date"]
                end_date = form.cleaned_data["end_date"]
                role = form.cleaned_data["role"]
                note = form.cleaned_data["note"]

                # Check that one operator is not assigned twice
                if operator:
                    if operator in assignments:
                        duplicates = True
                    assignments.append(operator)

                if duplicates:
                    form.add_error(
                        "operator",
                        "Duplicate assignment: This operator is assigned more than once",
                    )

                # Check if assignment form is complete
                if operator and not all(
                    x is not None for x in [start_date, end_date, role]
                ):
                    if not start_date:
                        form.add_error(
                            "start_date",
                            "Incomplete assignment: Your assigned operator is missing a start date",
                        )
                    if not end_date:
                        form.add_error(
                            "end_date",
                            "Incomplete assignment: Your assigned operator is missing an end date",
                        )
                    if not role:
                        form.add_error(
                            "role",
                            "Incomplete assignment: Your assigned operator is missing a project role",
                        )
                elif (
                    all(x is not None for x in [start_date, end_date, role])
                    and not operator
                ):
                    form.add_error(
                        "operator",
                        "Incomplete assignment: Your assignment is incomplete, missing an operator",
                    )
                elif note and all(
                    x is None for x in [operator, start_date, end_date, role]
                ):
                    form.add_error(
                        "note",
                        "Incomplete assignment: This note is part of an incomplete assignment form",
                    )


class ProjectObjectiveCreateFormset(forms.ModelForm):
    """
    Create one or more :model:`rolodex.ProjectObjective`.
    """

    class Meta:
        model = ProjectObjective
        fields = ("deadline", "objective")

    def __init__(self, *args, **kwargs):
        super(ProjectObjectiveCreateFormset, self).__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["deadline"].widget.attrs["autocomplete"] = "off"
        self.fields["deadline"].widget.input_type = "date"
        self.fields["objective"].widget.attrs[
            "placeholder"
        ] = "Obtain commit privileges to git"
        self.fields["deadline"].error_messages = {"required": "deadline"}
        self.fields["objective"].error_messages = {"required": "objective"}
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"
        self.helper.form_show_labels = False


class AssignmentCreateFormset(forms.ModelForm):
    """
    Create one or more :model:`rolodex.ProjectAssignment`.
    """

    class Meta:
        model = ProjectAssignment
        fields = ("start_date", "end_date", "role", "operator", "note")

    def __init__(self, *args, **kwargs):
        super(AssignmentCreateFormset, self).__init__(*args, **kwargs)
        self.fields["operator"].queryset = self.fields["operator"].queryset.order_by(
            "name"
        )
        self.fields["operator"].label_from_instance = lambda obj: "%s (%s)" % (
            obj.name,
            obj.username,
        )
        self.fields["start_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "This assignment is only for 3 of the 4 weeks ..."
        self.fields["start_date"].error_messages = {"required": "start_date"}
        self.fields["end_date"].error_messages = {"required": "end_date"}
        self.fields["role"].error_messages = {"required": "role"}
        self.fields["operator"].error_messages = {"required": "operator"}
        self.fields["note"].error_messages = {"required": "note"}
        self.helper = FormHelper()
        self.helper.form_class = "form-inline"
        self.helper.form_method = "post"
        self.helper.field_class = "h-100 justify-content-center align-items-center"

