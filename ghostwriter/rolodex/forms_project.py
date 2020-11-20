"""This contains all project-related forms used by the Rolodex application."""

# Django & Other 3rd Party Libraries
from crispy_forms.bootstrap import Alert, FieldWithButtons, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
    Button,
    ButtonHolder,
    Column,
    Div,
    Field,
    Layout,
    Row,
    Submit,
)
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.modules.custom_layout_object import CustomTab, Formset

from .models import Project, ProjectAssignment, ProjectNote, ProjectObjective


class BaseProjectObjectiveInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectObjective` that adds validation
    for this model.
    """

    def clean(self):
        objectives = []
        duplicates = False
        super(BaseProjectObjectiveInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
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
                            ValidationError(
                                _("Your project objectives must be unique"),
                                code="duplicate",
                            ),
                        )
                    # Check that all objective have a deadline and status
                    if deadline and not objective:
                        form.add_error(
                            "objective",
                            ValidationError(
                                _("You set a deadline without an objective"),
                                code="incomplete",
                            ),
                        )
                    elif objective and not deadline:
                        form.add_error(
                            "deadline",
                            ValidationError(
                                _("Your objective still needs a deadline"),
                                code="incomplete",
                            ),
                        )


class BaseProjectAssignmentInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectAssignment` that adds validation
    for this model.
    """

    def clean(self):
        assignments = []
        duplicates = False
        super(BaseProjectAssignmentInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
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
                            ValidationError(
                                _("This operator is assigned more than once"),
                                code="duplicate",
                            ),
                        )
                    # Raise an error if an operator is selected provided without any required details
                    if operator and any(
                        x is None for x in [start_date, end_date, role]
                    ):
                        if not start_date:
                            form.add_error(
                                "start_date",
                                ValidationError(
                                    _("Your assigned operator is missing a start date"),
                                    code="incomplete",
                                ),
                            )
                        if not end_date:
                            form.add_error(
                                "end_date",
                                ValidationError(
                                    _("Your assigned operator is missing an end date"),
                                    code="incomplete",
                                ),
                            )
                        if not role:
                            form.add_error(
                                "role",
                                ValidationError(
                                    _(
                                        "Your assigned operator is missing a project role"
                                    ),
                                    code="incomplete",
                                ),
                            )
                    # Raise an error if details are present without a selected operator
                    elif operator is None and any(
                        x is not None for x in [start_date, end_date, role]
                    ):
                        form.add_error(
                            "operator",
                            ValidationError(
                                _("Your assignment is missing an operator"),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if a form only has a value for the note
                    elif note and any(
                        x is None for x in [operator, start_date, end_date, role]
                    ):
                        form.add_error(
                            "note",
                            ValidationError(
                                _("This note is part of an incomplete assignment form"),
                                code="incomplete",
                            ),
                        )


class ProjectAssignmentForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectAssignment` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectAssignment
        exclude = ()

    def __init__(self, *args, **kwargs):
        super(ProjectAssignmentForm, self).__init__(*args, **kwargs)
        self.fields["operator"].queryset = self.fields["operator"].queryset.order_by(
            "username", "name"
        )
        self.fields["operator"].label_from_instance = lambda obj: obj.get_display_name
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
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Hide the field labels from the model
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            # Wrap form in a div so Django renders form instances in their own element
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Assignment Deleted!</strong>
                        Deletion will be permanent once the form is submitted. Click this alert to undo.
                        """
                    ),
                    css_class="alert alert-danger show formset-undo-button",
                    style="display:none; cursor:pointer;",
                    template="alert.html",
                    block=False,
                    dismiss=False,
                ),
                Div(
                    HTML(
                        """
                        <p><strong>Assignment #<span class="counter">{{ forloop.counter }}</span></strong></p>
                        <hr>
                        """
                    ),
                    Row(
                        Column("operator", css_class="form-group col-md-6 mb-0"),
                        Column("role", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column(
                            FieldWithButtons(
                                "start_date",
                                HTML(
                                    """
                                    <button
                                        class="btn btn-secondary"
                                        type="button"
                                        onclick="copyStartDate($(this).closest('div').find('input'))"
                                    >
                                    Copy
                                    </button>
                                    """
                                ),
                            ),
                            css_class="form-group col-md-6 mb-0",
                        ),
                        Column(
                            FieldWithButtons(
                                "end_date",
                                HTML(
                                    """
                                <button
                                    class="btn btn-secondary"
                                    type="button"
                                    onclick="copyEndDate($(this).closest('div').find('input'))"
                                >
                                Copy
                                </button>
                                """
                                ),
                            ),
                            css_class="form-group col-md-6 mb-0",
                        ),
                    ),
                    "note",
                    Row(
                        Column(
                            Field("DELETE", style="display: none;"),
                            Button(
                                "formset-del-button",
                                "Delete Assignment",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-12 text-center",
                        ),
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            ),
        )


class ProjectObjectiveForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectObjective` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectObjective
        fields = ("deadline", "objective")

    def __init__(self, *args, **kwargs):
        super(ProjectObjectiveForm, self).__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["deadline"].widget.attrs["autocomplete"] = "off"
        self.fields["deadline"].widget.input_type = "date"
        self.fields["objective"].widget.attrs[
            "placeholder"
        ] = "Obtain commit privileges to git"
        self.helper = FormHelper()
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Hide the field labels from the model
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            # Wrap form in a div so Django renders form instances in their own element
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Objective Deleted!</strong>
                        Deletion will be permanent once the form is submitted. Click this alert to undo.
                        """
                    ),
                    css_class="alert alert-danger show formset-undo-button",
                    style="display:none; cursor:pointer;",
                    template="alert.html",
                    block=False,
                    dismiss=False,
                ),
                Div(
                    HTML(
                        """
                        <p><strong>Objective #<span class="counter">{{ forloop.counter }}</span></strong></p>
                        <hr>
                        """
                    ),
                    Row(
                        Column(
                            FieldWithButtons(
                                "deadline",
                                HTML(
                                    """
                                    <button
                                        class="btn btn-secondary"
                                        type="button"
                                        onclick="copyEndDate($(this).closest('div').find('input'))"
                                    >
                                    Copy
                                    </button>
                                    """
                                ),
                            ),
                            css_class="form-group col-md-6 mb-0",
                        ),
                        css_class="form-row",
                    ),
                    "objective",
                    Row(
                        Column(
                            Field("DELETE", style="display: none;"),
                            Button(
                                "formset-del-button",
                                "Delete Objective",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-12 text-center",
                        ),
                        css_class="form-row",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


# Create the `inlineformset_factory()` objects for `ProjectForm()`

ProjectAssignmentFormSet = inlineformset_factory(
    Project,
    ProjectAssignment,
    form=ProjectAssignmentForm,
    formset=BaseProjectAssignmentInlineFormSet,
    extra=1,
    can_delete=True,
)

ProjectObjectiveFormSet = inlineformset_factory(
    Project,
    ProjectObjective,
    form=ProjectObjectiveForm,
    formset=BaseProjectObjectiveInlineFormSet,
    extra=1,
    can_delete=True,
)


class ProjectForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.Project` with instances of
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective` associated
    with an individual :model:`rolodex.Client`.
    """

    update_checkouts = forms.BooleanField(
        label="Update Domain & Server Checkouts",
        help_text="Update domain and server checkout if the project dates change",
        required=False,
        initial=True,
    )

    class Meta:
        model = Project
        exclude = ("operator", "complete")

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields["start_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["placeholder"] = "mm/dd/yyyy"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["slack_channel"].widget.attrs["placeholder"] = "#client-rt-2020"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "This project is intended to assess ..."
        # Hide labels for specific fields because ``form_show_labels`` takes priority
        self.fields["start_date"].label = False
        self.fields["end_date"].label = False
        self.fields["note"].label = False
        self.fields["slack_channel"].label = False
        self.fields["project_type"].label = False
        self.fields["client"].label = False
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_class = "form-inline justify-content-center"
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Project Information",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    "client",
                    "codename",
                    Row(
                        Column("start_date", css_class="form-group col-md-6 mb-0"),
                        Column("end_date", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("project_type", css_class="form-group col-md-6 mb-0"),
                        Column("slack_channel", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    "update_checkouts",
                    "note",
                    link_css_class="project-icon",
                    css_id="project",
                ),
                CustomTab(
                    "Assignments",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("assignments", object_context_name="Assignment"),
                    Button(
                        "add-assignment",
                        "Add Assignment",
                        css_class="btn-block btn-secondary formset-add-assign",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="assignment-icon",
                    css_id="assignments",
                ),
                CustomTab(
                    "Objectives",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("objectives", object_context_name="Objective"),
                    Button(
                        "add-objective",
                        "Add Objective",
                        css_class="btn-block btn-secondary formset-add-obj",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="objective-icon",
                    css_id="objectives",
                ),
                template="tab.html",
                css_class="nav-justified",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]
        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(
                _("The provided end date comes before the start date"),
                code="invalid_date",
            )
        return end_date

    def clean_slack_channel(self):
        slack_channel = self.cleaned_data["slack_channel"]
        if slack_channel:
            if not slack_channel.startswith("#"):
                slack_channel = "#" + slack_channel
                raise ValidationError(
                    _("Slack channels should start with # – check this channel name"),
                    code="invalid_channel",
                )
        return slack_channel


class ProjectNoteForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectNote` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super(ProjectNoteForm, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div("note"),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_note(self):
        note = self.cleaned_data["note"]
        # Check if note is empty
        if not note:
            raise ValidationError(
                _("You must provide some content for the note"),
                code="required",
            )
        return note
