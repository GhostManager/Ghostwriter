"""This contains all project-related forms used by the Rolodex application."""

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
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

# Ghostwriter Libraries
from ghostwriter.modules.custom_layout_object import CustomTab, Formset, SwitchToggle

from .models import (
    Project,
    ProjectAssignment,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectTarget,
)

# Number of "extra" formsets created by default
# Higher numbers can increase page load times with WYSIWYG editors
EXTRAS = 0


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
                    description = form.cleaned_data["description"]

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
                    # Check if a description has been filled-out for an empty objective
                    if description and not objective:
                        form.add_error(
                            "description",
                            ValidationError(
                                _("Your description is missing an objective"),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if dates are out of bounds
                    if self.instance.start_date:
                        if deadline < self.instance.start_date:
                            form.add_error(
                                "deadline",
                                ValidationError(
                                    _(
                                        "Your selected date is before the project start date"
                                    ),
                                    code="invalid_date",
                                ),
                            )
                        if deadline > self.instance.end_date:
                            form.add_error(
                                "deadline",
                                ValidationError(
                                    _("Your selected date is after the project end date"),
                                    code="invalid_date",
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
                    if operator and any(x is None for x in [start_date, end_date, role]):
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
                                    _("Your assigned operator is missing a project role"),
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
                    # Raise an error if dates are out of bounds
                    if self.instance.start_date:
                        if start_date < self.instance.start_date:
                            form.add_error(
                                "start_date",
                                ValidationError(
                                    _(
                                        "Your selected date is before the project start date"
                                    ),
                                    code="invalid_date",
                                ),
                            )
                        if end_date > self.instance.end_date:
                            form.add_error(
                                "end_date",
                                ValidationError(
                                    _("Your selected date is after the project end date"),
                                    code="invalid_date",
                                ),
                            )


class BaseProjectScopeInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectScope` that adds validation
    for this model.
    """

    def clean(self):
        names = []
        duplicates = False
        super(BaseProjectScopeInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
                    name = form.cleaned_data["name"]
                    scope = form.cleaned_data["scope"]
                    description = form.cleaned_data["description"]

                    # Check that no two names are the same
                    if name:
                        if name.lower() in names:
                            duplicates = True
                        names.append(name.lower())
                    if duplicates:
                        form.add_error(
                            "name",
                            ValidationError(
                                _("Your names must be unique"),
                                code="duplicate",
                            ),
                        )
                    if name or description:
                        if not scope:
                            form.add_error(
                                "scope",
                                ValidationError(
                                    _("You scope list is missing"),
                                    code="incomplete",
                                ),
                            )
                    if scope and not name:
                        form.add_error(
                            "name",
                            ValidationError(
                                _("Your scope list is missing a name"),
                                code="incomplete",
                            ),
                        )


class BaseProjectTargetInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectTarget` that adds validation
    for this model.
    """

    def clean(self):
        hostnames = []
        ip_addresses = []
        duplicate_fqdn = False
        duplicate_addy = False
        super(BaseProjectTargetInlineFormSet, self).clean()
        if any(self.errors):
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
                    hostname = form.cleaned_data["hostname"]
                    ip_address = form.cleaned_data["ip_address"]
                    note = form.cleaned_data["note"]

                    # Check that no two names are the same
                    if hostname:
                        if hostname.lower() in hostnames:
                            duplicate_fqdn = True
                        hostnames.append(hostname.lower())
                    if duplicate_fqdn:
                        form.add_error(
                            "hostname",
                            ValidationError(
                                _("Your targets should be unique"),
                                code="duplicate",
                            ),
                        )
                    if ip_address:
                        if ip_address in ip_addresses:
                            duplicate_addy = True
                        ip_addresses.append(ip_address)
                    if duplicate_addy:
                        form.add_error(
                            "ip_address",
                            ValidationError(
                                _("Your targets should be unique"),
                                code="duplicate",
                            ),
                        )
                    if note and not hostname and not ip_address:
                        form.add_error(
                            "note",
                            ValidationError(
                                _(
                                    "You must provide a hostname or IP address with your note"
                                ),
                                code="duplicate",
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
        widgets = {
            "start_date": forms.DateInput(
                format=("%Y-%m-%d"),
            ),
            "end_date": forms.DateInput(
                format=("%Y-%m-%d"),
            ),
        }

    def __init__(self, *args, **kwargs):
        super(ProjectAssignmentForm, self).__init__(*args, **kwargs)
        self.fields["operator"].queryset = self.fields["operator"].queryset.order_by(
            "-is_active", "username", "name"
        )
        self.fields["operator"].label_from_instance = lambda obj: obj.get_display_name
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs["rows"] = 5
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "Additional Information or Notes"
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
                        <h6>Assignment #<span class="counter">{{ forloop.counter }}</span></h6>
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
                            Button(
                                "formset-del-button",
                                "Delete Assignment",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-4 offset-md-4",
                        ),
                        Column(
                            Field("DELETE", style="display: none;"),
                            css_class="form-group col-md-4 text-center",
                        ),
                        css_class="form-row",
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
        fields = (
            "deadline",
            "objective",
            "complete",
            "status",
            "description",
            "priority",
        )
        widgets = {
            "deadline": forms.DateInput(
                format=("%Y-%m-%d"),
            ),
        }

    def __init__(self, *args, **kwargs):
        super(ProjectObjectiveForm, self).__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["autocomplete"] = "off"
        self.fields["deadline"].widget.input_type = "date"
        self.fields["objective"].widget.attrs["rows"] = 5
        self.fields["objective"].widget.attrs["autocomplete"] = "off"
        self.fields["objective"].widget.attrs["placeholder"] = "High-Level Objective"
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Description, Notes, and Context"
        self.fields["priority"].empty_label = "-- Prioritize Objective --"
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
                        <h6>Objective #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    Row(
                        Column("objective", css_class="col-md-6"),
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
                            css_class="col-md-6",
                        ),
                    ),
                    Row(
                        Column(
                            Field("status", css_class="form-select"),
                            css_class="col-md-6",
                        ),
                        Column(
                            Field("priority", css_class="form-select"),
                            css_class="col-md-6",
                        ),
                    ),
                    "description",
                    Row(
                        Column(
                            SwitchToggle(
                                "complete",
                            ),
                            css_class="col-md-4",
                        ),
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Objective",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-4",
                        ),
                        Column(
                            Field("DELETE", style="display: none;"),
                            css_class="form-group col-md-4 text-center",
                        ),
                        css_class="form-row",
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


class ProjectScopeForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectScope` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectScope
        fields = ("name", "scope", "description", "disallowed", "requires_caution")

    def __init__(self, *args, **kwargs):
        super(ProjectScopeForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "Scope Name"
        self.fields["scope"].widget.attrs["rows"] = 5
        self.fields["scope"].widget.attrs["placeholder"] = "Scope List"
        self.fields["description"].widget.attrs["rows"] = 5
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Brief Description or Note"
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
                        <strong>List Deleted!</strong>
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
                        <h6>Scope List #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    "name",
                    Field("scope", css_class="empty-form"),
                    "description",
                    Row(
                        Column("requires_caution", css_class="col-md-6"),
                        Column("disallowed", css_class="col-md-6"),
                    ),
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete List",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-4 offset-md-4",
                        ),
                        Column(
                            Field("DELETE", style="display: none;"),
                            css_class="form-group col-md-4 text-center",
                        ),
                        css_class="form-row",
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


class ProjectTargetForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectTarget` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectTarget
        fields = (
            "ip_address",
            "hostname",
            "note",
        )

    def __init__(self, *args, **kwargs):
        super(ProjectTargetForm, self).__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["ip_address"].widget.attrs["placeholder"] = "IP Address"
        self.fields["hostname"].widget.attrs["placeholder"] = "FQDN"
        self.fields["note"].widget.attrs["rows"] = 5
        self.fields["note"].widget.attrs["placeholder"] = "Brief Description or Note"
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
                        <strong>Target Deleted!</strong>
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
                        <h6>Target #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    Row(
                        Column("ip_address", css_class="col-md-6"),
                        Column("hostname", css_class="col-md-6"),
                    ),
                    "note",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Target",
                                css_class="btn-sm btn-danger formset-del-button",
                            ),
                            css_class="form-group col-md-4 offset-md-4",
                        ),
                        Column(
                            Field("DELETE", style="display: none;"),
                            css_class="form-group col-md-4 text-center",
                        ),
                        css_class="form-row",
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
    extra=EXTRAS,
    can_delete=True,
)


ProjectObjectiveFormSet = inlineformset_factory(
    Project,
    ProjectObjective,
    form=ProjectObjectiveForm,
    formset=BaseProjectObjectiveInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)

ProjectScopeFormSet = inlineformset_factory(
    Project,
    ProjectScope,
    form=ProjectScopeForm,
    formset=BaseProjectScopeInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)

ProjectTargetFormSet = inlineformset_factory(
    Project,
    ProjectTarget,
    form=ProjectTargetForm,
    formset=BaseProjectTargetInlineFormSet,
    extra=EXTRAS,
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
        widgets = {
            "start_date": forms.DateInput(
                format=("%Y-%m-%d"),
            ),
            "end_date": forms.DateInput(
                format=("%Y-%m-%d"),
            ),
        }

    def __init__(self, *args, **kwargs):
        super(ProjectForm, self).__init__(*args, **kwargs)
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["slack_channel"].widget.attrs["placeholder"] = "#slack-channel"
        self.fields["note"].widget.attrs["placeholder"] = "Description of the Project"
        # Hide labels for specific fields because ``form_show_labels`` takes priority
        self.fields["start_date"].label = False
        self.fields["end_date"].label = False
        self.fields["note"].label = False
        self.fields["slack_channel"].label = False
        self.fields["project_type"].label = False
        self.fields["client"].label = False
        self.fields["codename"].label = False
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
                    Row(
                        Column(
                            "client",
                        ),
                        Column(
                            FieldWithButtons(
                                "codename",
                                HTML(
                                    """
                                    <button
                                        class="btn btn-secondary js-roll-codename"
                                        roll-codename-url="{% url 'rolodex:ajax_roll_codename' %}"
                                        type="button"
                                        onclick="copyStartDate($(this).closest('div').find('input'))"
                                    >
                                    <i class="fas fa-dice"></i>
                                    </button>
                                    """
                                ),
                            ),
                            css_class="col-md-6",
                        ),
                    ),
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
                CustomTab(
                    "Scope Lists",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("scopes", object_context_name="Scope"),
                    Button(
                        "add-scope",
                        "Add Scope List",
                        css_class="btn-block btn-secondary formset-add-scope",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="tab-icon list-icon",
                    css_id="scopes",
                ),
                CustomTab(
                    "Targets",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("targets", object_context_name="Target"),
                    Button(
                        "add-target",
                        "Add Target",
                        css_class="btn-block btn-secondary formset-add-target",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="tab-icon list-icon",
                    css_id="targets",
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
            if not slack_channel.startswith("#") and not slack_channel.startswith("@"):
                raise ValidationError(
                    _(
                        "Slack channels should start with # or @ – check this channel name"
                    ),
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
