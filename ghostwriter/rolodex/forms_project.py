"""This contains all project-related forms used by the Rolodex application."""

# Standard Libraries
from collections import namedtuple

# Django Imports
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.bootstrap import Alert, FieldWithButtons, StrictButton, TabHolder
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
from ghostwriter.commandcenter.forms import ExtraFieldsField
from ghostwriter.commandcenter.models import GeneralConfiguration
from ghostwriter.modules.custom_layout_object import CustomTab, Formset, SwitchToggle
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from ghostwriter.rolodex.models import (
    Deconfliction,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectInvite,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectTarget,
    WhiteCard,
)

# Number of "extra" formsets created by default
# Higher numbers can increase page load times with WYSIWYG editors
EXTRAS = 0


# Custom inline formsets for nested forms


class BaseProjectObjectiveInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectObjective` that adds validation
    for this model.
    """

    def clean(self):
        objectives = []
        duplicates = False
        super().clean()
        if any(self.errors):  # pragma: no cover
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
                                _("Your project objectives must be unique."),
                                code="duplicate",
                            ),
                        )
                        duplicates = False
                    # Check that all objective have a deadline and status
                    if deadline and not objective:
                        form.add_error(
                            "objective",
                            ValidationError(
                                _("You set a deadline without an objective."),
                                code="incomplete",
                            ),
                        )
                    elif objective and not deadline:
                        form.add_error(
                            "deadline",
                            ValidationError(
                                _("Your objective still needs a deadline."),
                                code="incomplete",
                            ),
                        )
                    # Check if a description has been filled-out for an empty objective
                    if description and not objective and not deadline:
                        form.add_error(
                            "description",
                            ValidationError(
                                _("Your description is missing an objective"),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if dates are out of bounds
                    if self.instance.start_date and deadline:
                        if deadline < self.instance.start_date:
                            form.add_error(
                                "deadline",
                                ValidationError(
                                    _("Your selected date is before the project start date."),
                                    code="invalid_date",
                                ),
                            )
                        if deadline > self.instance.end_date:
                            form.add_error(
                                "deadline",
                                ValidationError(
                                    _("Your selected date is after the project end date."),
                                    code="invalid_date",
                                ),
                            )


class BaseProjectAssignmentInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectAssignment` that adds validation
    for this model.
    """

    def clean(self):
        Assignment = namedtuple("Assignment", ["user", "role", "start_date", "end_date"])
        assignments = []
        duplicates = False
        super().clean()
        if any(self.errors):  # pragma: no cover
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

                    # Check if the person has already been assigned to this project within the same time period
                    if operator and start_date and end_date:
                        if end_date < start_date:
                            form.add_error(
                                "end_date",
                                ValidationError(
                                    _("Your end date is earlier than your start date."),
                                    code="invalid_date",
                                ),
                            )
                        if any(operator.username in assign.user for assign in assignments):
                            for assign in assignments:
                                if assign.user == operator.username:
                                    latest_start = max(assign.start_date, start_date)
                                    earliest_end = min(assign.end_date, end_date)
                                    delta = (earliest_end - latest_start).days + 1
                                    overlap = max(0, delta)
                                    if overlap > 0:
                                        duplicates = True

                        assignments.append(Assignment(operator.username, role, start_date, end_date))
                        if duplicates:
                            form.add_error(
                                "operator",
                                ValidationError(
                                    _("This operator is assigned more than once for an overlapping time period."),
                                    code="duplicate",
                                ),
                            )
                            duplicates = False

                    # Raise an error if an operator is selected provided without any required details
                    if operator and any(x is None for x in [start_date, end_date, role]):
                        if not start_date:
                            form.add_error(
                                "start_date",
                                ValidationError(
                                    _("Your assigned operator is missing a start date."),
                                    code="incomplete",
                                ),
                            )
                        if not end_date:
                            form.add_error(
                                "end_date",
                                ValidationError(
                                    _("Your assigned operator is missing an end date."),
                                    code="incomplete",
                                ),
                            )
                        if not role:
                            form.add_error(
                                "role",
                                ValidationError(
                                    _("Your assigned operator is missing a project role."),
                                    code="incomplete",
                                ),
                            )
                    # Raise an error if details are present without a selected operator
                    elif operator is None and any(x is not None for x in [start_date, end_date, role]):
                        form.add_error(
                            "operator",
                            ValidationError(
                                _("Your assignment is missing an operator."),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if a form only has a value for the note
                    elif note and any(x is None for x in [operator, start_date, end_date, role]):
                        form.add_error(
                            "note",
                            ValidationError(
                                _("This note is part of an incomplete assignment form."),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if dates are out of bounds
                    if self.instance.start_date and start_date and end_date:
                        if start_date < self.instance.start_date:
                            form.add_error(
                                "start_date",
                                ValidationError(
                                    _("Your selected date is before the project start date."),
                                    code="invalid_date",
                                ),
                            )
                        if end_date > self.instance.end_date:
                            form.add_error(
                                "end_date",
                                ValidationError(
                                    _("Your selected date is after the project end date."),
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
        super().clean()
        if any(self.errors):  # pragma: no cover
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
                                _("Your names must be unique."),
                                code="duplicate",
                            ),
                        )
                        duplicates = False
                    if name or description:
                        if not scope:
                            form.add_error(
                                "scope",
                                ValidationError(
                                    _("You scope list is missing."),
                                    code="incomplete",
                                ),
                            )
                    if scope and not name:
                        form.add_error(
                            "name",
                            ValidationError(
                                _("Your scope list is missing a name."),
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
        super().clean()
        if any(self.errors):  # pragma: no cover
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
                                _("Your targets should be unique."),
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
                                _("Your targets should be unique."),
                                code="duplicate",
                            ),
                        )
                    if note and not hostname and not ip_address:
                        form.add_error(
                            "note",
                            ValidationError(
                                _("You must provide a hostname or IP address with your note."),
                                code="incomplete",
                            ),
                        )


class BaseWhiteCardInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.WhiteCard` that adds validation
    for this model.
    """

    def clean(self):
        super().clean()
        if any(self.errors):  # pragma: no cover
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
                    title = form.cleaned_data["title"]
                    issued = form.cleaned_data["issued"]

                    # Check that all objective have a deadline and status
                    if title and not issued:
                        form.add_error(
                            "issued",
                            ValidationError(
                                _("Your white card still needs an issued date and time."),
                                code="incomplete",
                            ),
                        )
                    elif issued and not title:
                        form.add_error(
                            "title",
                            ValidationError(
                                _("Your white card still needs a title."),
                                code="incomplete",
                            ),
                        )
                    # Raise an error if dates are out of bounds. We only check if ``issued`` is after the project's
                    # end date because white cards can be issued prior to execution.
                    if self.instance.start_date and issued:
                        if issued.date() > self.instance.end_date:
                            form.add_error(
                                "issued",
                                ValidationError(
                                    _("Your selected date is after the project end date."),
                                    code="invalid_datetime",
                                ),
                            )


class BaseProjectContactInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectContact` that adds validation
    for this model.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        contacts = set()
        primary_set = False
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            name = form.cleaned_data["name"]
            primary = form.cleaned_data["primary"]

            # Check that the same person has not been added more than once
            if name:
                if name in contacts:
                    form.add_error(
                        "name",
                        ValidationError(
                            _("This person is already assigned as a contact."),
                            code="duplicate",
                        ),
                    )
                contacts.add(name)

            if primary:
                if primary_set:
                    form.add_error(
                        "primary",
                        ValidationError(
                            _("You can only set one primary contact."),
                            code="duplicate",
                        ),
                    )
                primary_set = True


# Forms used with the inline formsets


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
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
            ),
        }
        field_classes = {
            "note": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["operator"].queryset = self.fields["operator"].queryset.order_by("-is_active", "username", "name")
        self.fields["operator"].label_from_instance = lambda obj: obj.get_display_name
        self.fields["start_date"].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.attrs["autocomplete"] = "off"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs["rows"] = 5
        self.fields["note"].widget.attrs["placeholder"] = "This team member will be responsible for..."
        self.fields["operator"].empty_label = "-- Select a Team Member --"
        self.fields["role"].empty_label = "-- Select a Role --"
        self.helper = FormHelper()
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
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
                                StrictButton(
                                    "Copy",
                                    onclick="copyStartDate($(this).closest('div').find('input'))",
                                    css_class="btn btn-secondary",
                                ),
                            ),
                            css_class="form-group col-md-6 mb-0",
                        ),
                        Column(
                            FieldWithButtons(
                                "end_date",
                                StrictButton(
                                    "Copy",
                                    onclick="copyEndDate($(this).closest('div').find('input'))",
                                    css_class="btn btn-secondary",
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
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-md-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
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
            "result",
        )
        widgets = {
            "deadline": forms.DateInput(
                format="%Y-%m-%d",
            ),
        }
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["deadline"].widget.attrs["autocomplete"] = "off"
        self.fields["deadline"].widget.input_type = "date"
        self.fields["objective"].widget.attrs["rows"] = 5
        self.fields["objective"].widget.attrs["autocomplete"] = "off"
        self.fields["objective"].widget.attrs["placeholder"] = "Escalate Privileges to Domain Admin"
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "The task is to escalate privileges to a domain admin and..."
        self.fields["priority"].empty_label = "-- Prioritize Objective --"
        self.helper = FormHelper()
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
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
                        Column("objective", css_class="col-4"),
                        Column(
                            FieldWithButtons(
                                "deadline",
                                StrictButton(
                                    "Copy",
                                    onclick="setObjectiveDeadline($(this).closest('div').find('input'))",
                                    css_class="btn btn-secondary",
                                ),
                            ),
                            css_class="col-4",
                        ),
                        Column(
                            SwitchToggle(
                                "complete",
                            ),
                            css_class="col-4 mt-5",
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
                    "result",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Objective",
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
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
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "Internal Scope"
        self.fields["scope"].widget.attrs["rows"] = 5
        self.fields["scope"].widget.attrs["placeholder"] = "ghostwriter.local\nwww.ghostwriter.local\n192.168.100.15"
        self.fields["scope"].label = "Scope List"
        self.fields["description"].widget.attrs["rows"] = 5
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "This list contains all internal hosts and services that..."
        self.helper = FormHelper()
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
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
                    Row(
                        Column(SwitchToggle("requires_caution", css_class="col-3")),
                        Column(SwitchToggle("disallowed", css_class="col-3")),
                        Column(
                            StrictButton(
                                "Split Scope to Newlines",
                                onclick="formatScope($(this).closest('div').parent().nextAll('.form-group').first().find('textarea'))",
                                data_toggle="tooltip",
                                title="Split a comma-delimited scope list to newlines",
                                css_class="btn btn-outline-secondary col-6",
                            ),
                        ),
                    ),
                    Field("scope", css_class="empty-form"),
                    "description",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete List",
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
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
        field_classes = {
            "note": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["ip_address"].widget.attrs["placeholder"] = "172.67.179.71"
        self.fields["hostname"].widget.attrs["placeholder"] = "ghostwriter.wiki"
        self.fields["note"].widget.attrs["rows"] = 5
        self.fields["note"].widget.attrs["placeholder"] = "This host is a web server related to objective ..."
        self.helper = FormHelper()
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
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
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


class WhiteCardForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.WhiteCard` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = WhiteCard
        exclude = ("project",)
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["issued"].widget.input_type = "datetime-local"
        self.fields["issued"].label = "Issued Date & Time"
        self.fields["description"].widget.attrs["rows"] = 5
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Additional information about the white card, the reason for it, limitations, how it affects the assessment, etc..."
        self.fields["title"].widget.attrs["placeholder"] = "Provided Initial Access to PCI Network"
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        # Disable the <form> tags because this will be inside an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            # Wrap form in a div so Django renders form instances in their own element
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>White Card Deleted!</strong>
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
                        <h6>White Card #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    Row(
                        Column("title", css_class="col-md-6"),
                        Column(
                            FieldWithButtons(
                                Field(
                                    "issued",
                                    step=1,
                                ),
                                StrictButton(
                                    "Now",
                                    onclick="setNow($(this).closest('div').find('input'))",
                                    css_class="btn btn-secondary",
                                ),
                            ),
                            css_class="col-md-6",
                        ),
                    ),
                    "description",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete White Card",
                                css_class="btn-outline-danger formset-del-button col-5",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


class ProjectContactForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.ProjectContact` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = ProjectContact
        exclude = ("project",)
        field_classes = {
            "email": forms.EmailField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        general_config = GeneralConfiguration.get_solo()
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "Janine Melnitz"
        self.fields["name"].label = "Full Name"
        self.fields["email"].widget.attrs["placeholder"] = "info@getghostwriter.io"
        self.fields["email"].label = "Email Address"
        self.fields["job_title"].widget.attrs["placeholder"] = "COO"
        self.fields["phone"].widget.attrs["placeholder"] = "(212) 897-1964"
        self.fields["phone"].label = "Phone Number"
        self.fields["note"].widget.attrs["placeholder"] = "Janine is our main contact for assessment work and ..."
        self.fields["timezone"].initial = general_config.default_timezone
        self.helper = FormHelper()
        # Disable the <form> tags because this will be part of an instance of `ProjectForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            # Wrap form in a div so Django renders form instances in their own element
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Contact Deleted!</strong>
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
                        <h6>Contact #<span class="counter">{{ forloop.counter }}</span></h6>
                        <hr>
                        """
                    ),
                    Row(
                        Column("name", css_class="form-group col-md-6 mb-0"),
                        Column("job_title", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("email", css_class="form-group col-md-4 mb-0"),
                        Column("phone", css_class="form-group col-md-4 mb-0"),
                        Column("timezone", css_class="form-group col-md-4 mb-0"),
                        css_class="form-row",
                    ),
                    SwitchToggle("primary", onchange="cbChange(this)", css_class="js-cb-toggle"),
                    "note",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Contact",
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


class ProjectInviteForm(forms.ModelForm):
    class Meta:
        model = ProjectInvite
        exclude = ("client",)
        field_classes = {
            "comment": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["user"].label = "Operator"
        self.fields["user"].queryset = self.fields["user"].queryset.order_by("-is_active", "username", "name")
        self.fields["user"].label_from_instance = lambda obj: obj.get_display_name

        self.helper = FormHelper()
        # Disable the <form> tags because this will be part of an instance of `ClientForm()`
        self.helper.form_tag = False
        # Disable CSRF so `csrfmiddlewaretoken` is not rendered multiple times
        self.helper.disable_csrf = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                # These Bootstrap alerts begin hidden and function as undo buttons for deleted forms
                Alert(
                    content=(
                        """
                        <strong>Invite Deleted!</strong>
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
                    Row(
                        Column("user", css_class="form-group col-md-12"),
                        css_class="form-row",
                    ),
                    "comment",
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Invite",
                                css_class="btn-outline-danger formset-del-button col-4",
                            ),
                            css_class="form-group col-6 offset-3",
                        ),
                        Column(
                            Field(
                                "DELETE", style="display: none;", visibility="hidden", template="delete_checkbox.html"
                            ),
                            css_class="form-group col-3 text-center",
                        ),
                    ),
                    css_class="formset",
                ),
                css_class="formset-container"
            )
        )


class BaseProjectInviteInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`rolodex.ProjectInvite` that adds validation
    for this model.
    """

    def clean(self):
        super().clean()
        if any(self.errors):
            return

        invites = set()
        for form in self.forms:
            if not form.cleaned_data or form.cleaned_data["DELETE"]:
                continue
            user = form.cleaned_data["user"]

            # Check that the same person has not been added more than once
            if user:
                if user in invites:
                    form.add_error(
                        "user",
                        ValidationError(
                            _("This person is already invited."),
                            code="duplicate",
                        ),
                    )
                invites.add(user)


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

WhiteCardFormSet = inlineformset_factory(
    Project,
    WhiteCard,
    form=WhiteCardForm,
    formset=BaseWhiteCardInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)

ProjectContactFormSet = inlineformset_factory(
    Project,
    ProjectContact,
    form=ProjectContactForm,
    formset=BaseProjectContactInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)

ProjectInviteFormSet = inlineformset_factory(
    Project,
    ProjectInvite,
    form=ProjectInviteForm,
    formset=BaseProjectInviteInlineFormSet,
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
        exclude = ("operator", "complete", "extra_fields")
        widgets = {
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
            ),
        }
        field_classes = {
            "note": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        general_config = GeneralConfiguration.get_solo()
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["start_time"].widget.input_type = "time"
        self.fields["end_time"].widget.input_type = "time"
        self.fields["slack_channel"].widget.attrs["placeholder"] = "#slack-channel"
        self.fields["note"].widget.attrs["placeholder"] = "This project is..."
        self.fields["timezone"].initial = general_config.default_timezone
        self.fields["tags"].widget.attrs["placeholder"] = "evasive, on-site, travel, ..."
        self.fields["project_type"].label = "Project Type"
        self.fields["client"].empty_label = "-- Select a Client --"
        self.fields["project_type"].empty_label = "-- Select a Project Type --"

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Project Information",
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
                        Column(Field("start_time", step=1), css_class="form-group col-md-4 mb-0"),
                        Column(Field("end_time", step=1), css_class="form-group col-md-4 mb-0"),
                        Column("timezone", css_class="form-group col-md-4 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("project_type", css_class="form-group col-md-4 mb-0"),
                        Column("slack_channel", css_class="form-group col-md-4 mb-0"),
                        Column("tags", css_class="form-group col-md-4 mb-0"),
                        css_class="form-row",
                    ),
                    SwitchToggle("update_checkouts"),
                    "note",
                    link_css_class="project-icon",
                    css_id="project",
                ),
                CustomTab(
                    "Assignments",
                    Formset("assignments", object_context_name="Assignment"),
                    Button(
                        "add-assignment",
                        "Add Assignment",
                        css_class="btn-block btn-secondary formset-add-assign mb-2 offset-4 col-4",
                    ),
                    link_css_class="assignment-icon",
                    css_id="assignments",
                ),
                CustomTab(
                    "Invites",
                    Formset("invites", object_context_name="Invite"),
                    Button(
                        "add-invite",
                        "Add Invite",
                        css_class="btn-block btn-secondary formset-add-invite mb-2 offset-4 col-4",
                    ),
                    link_css_class="tab-icon users-icon",
                    css_id="invites",
                ),
                template="tab.html",
                css_class="nav-justified",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]
        # Check if ``end_date`` comes before the ``start_date``
        if end_date < start_date:
            raise ValidationError(
                _("The provided end date comes before the start date."),
                code="invalid_date",
            )
        return end_date

    def clean_slack_channel(self):
        slack_channel = self.cleaned_data["slack_channel"]
        if slack_channel:
            if not slack_channel.startswith("#") and not slack_channel.startswith("@"):
                raise ValidationError(
                    _("Slack channels should start with # or @."),
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
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            Div("note"),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean_note(self):
        note = self.cleaned_data["note"]
        # Check if note is empty
        if not note:
            raise ValidationError(
                _("You must provide some content for the note."),
                code="required",
            )
        return note


class DeconflictionForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.Deconfliction` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = Deconfliction
        exclude = (
            "created_at",
            "project",
        )
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["report_timestamp"].widget.input_type = "datetime-local"
        self.fields["alert_timestamp"].widget.input_type = "datetime-local"
        self.fields["response_timestamp"].widget.input_type = "datetime-local"
        self.fields["report_timestamp"].label = "Date & Time of Report"
        self.fields["alert_timestamp"].label = "Date & Time the Alert Triggered"
        self.fields["response_timestamp"].label = "Date & Time of Your Response"
        self.fields["title"].label = ""
        self.fields["status"].label = ""
        self.fields["alert_source"].label = ""
        self.fields["description"].label = ""
        self.fields["description"].widget.attrs["rows"] = 5
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Additional information about the alert, source, related activity..."
        self.fields["title"].widget.attrs["placeholder"] = "Brief and Descriptive Title"
        self.fields["alert_source"].widget.attrs["placeholder"] = "Source of the Alert – e.g, EDR"
        self.fields["report_timestamp"].initial = timezone.now()
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="form-group col-12 mb-0"),
                css_class="form-group",
            ),
            Row(
                Column("status", css_class="form-group col-6 mb-0"),
                Column("alert_source", css_class="form-group col-6 mb-0"),
                css_class="form-group",
            ),
            HTML(
                f"""
                <p>You can update these timestamps as you get more information. Use the server's time zone ({settings.TIME_ZONE}).
                """
            ),
            Row(
                Column(Field("alert_timestamp", step=1), css_class="form-group col-4 mb-0"),
                Column(Field("report_timestamp", step=1), css_class="form-group col-4 mb-0"),
                Column(Field("response_timestamp", step=1), css_class="form-group col-4 mb-0"),
                css_class="form-group",
            ),
            Row(
                Column("description", css_class="form-group col-12 mb-0"),
                css_class="form-group",
            ),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )

    def clean(self):
        alert_timestamp = None
        report_timestamp = None
        response_timestamp = None

        cleaned_data = super().clean()
        if "alert_timestamp" in cleaned_data:
            alert_timestamp = cleaned_data["alert_timestamp"]
        if "report_timestamp" in cleaned_data:
            report_timestamp = cleaned_data["report_timestamp"]
        if "response_timestamp" in cleaned_data:
            response_timestamp = cleaned_data["response_timestamp"]

        if response_timestamp and report_timestamp:
            if response_timestamp < report_timestamp:
                self.add_error(
                    "response_timestamp",
                    ValidationError(
                        _("The response timestamp cannot be before the report timestamp."),
                        code="invalid_datetime",
                    ),
                )

        if report_timestamp and alert_timestamp:
            if report_timestamp < alert_timestamp:
                self.add_error(
                    "report_timestamp",
                    ValidationError(
                        _("The report timestamp cannot be before the alert timestamp."),
                        code="invalid_datetime",
                    ),
                )


class ProjectComponentForm(forms.ModelForm):
    """
    Save an individual :model:`rolodex.Project` with instances of
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective` associated
    with an individual :model:`rolodex.Client`.
    """

    extra_fields = ExtraFieldsField(Project._meta.label)

    class Meta:
        model = Project
        fields = ("id", "extra_fields")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["extra_fields"].label = ""

        has_extra_fields = bool(self.fields["extra_fields"].specs)

        tabs = [
            CustomTab(
                "Contacts",
                Formset("contacts", object_context_name="Contact"),
                Button(
                    "add-contact",
                    "Add Contact",
                    css_class="btn-block btn-secondary formset-add-contact mb-2 offset-4 col-4",
                ),
                link_css_class="poc-icon",
                css_id="contacts",
            ),
            CustomTab(
                "White Cards",
                Formset("whitecards", object_context_name="White Card"),
                Button(
                    "add-whitecard",
                    "Add White Card",
                    css_class="btn-block btn-secondary formset-add-card mb-2 offset-4 col-4",
                ),
                link_css_class="tab-icon whitecard-icon",
                css_id="whitecards",
            ),
            CustomTab(
                "Scope Lists",
                Formset("scopes", object_context_name="Scope"),
                Button(
                    "add-scope",
                    "Add Scope List",
                    css_class="btn-block btn-secondary formset-add-scope mb-2 offset-4 col-4",
                ),
                link_css_class="tab-icon list-icon",
                css_id="scopes",
            ),
            CustomTab(
                "Objectives",
                Formset("objectives", object_context_name="Objective"),
                Button(
                    "add-objective",
                    "Add Objective",
                    css_class="btn-block btn-secondary formset-add-obj mb-2 offset-4 col-4",
                ),
                link_css_class="objective-icon",
                css_id="objectives",
            ),
            CustomTab(
                "Targets",
                Formset("targets", object_context_name="Target"),
                Button(
                    "add-target",
                    "Add Target",
                    css_class="btn-block btn-secondary formset-add-target mb-2 offset-4 col-4",
                ),
                link_css_class="tab-icon list-icon",
                css_id="targets",
            ),
        ]

        if has_extra_fields:
            tabs.append(
                CustomTab(
                    "Extra Fields",
                    "extra_fields",
                    link_css_class="tab-icon custom-field-icon",
                    css_id="extra-fields",
                )
            )

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                *tabs,
                template="tab.html",
                css_class="nav-justified",
            ),
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )
