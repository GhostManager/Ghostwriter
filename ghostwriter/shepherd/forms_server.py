"""This contains all server-related forms used by the Shepherd application."""

# Django Imports
from django import forms
from django.contrib.postgres.forms import SplitArrayField
from django.core.exceptions import ValidationError
from django.forms.models import BaseInlineFormSet, inlineformset_factory
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.bootstrap import Alert, TabHolder
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
from ghostwriter.api.utils import get_client_list
from ghostwriter.modules.custom_layout_object import CustomTab, Formset, SwitchToggle
from ghostwriter.rolodex.models import Project
from ghostwriter.shepherd.models import (
    AuxServerAddress,
    ServerHistory,
    ServerNote,
    ServerStatus,
    StaticServer,
    TransientServer,
)

# Number of "extra" formsets created by default
# Higher numbers can increase page load times with WYSIWYG editors
EXTRAS = 0


class BaseServerAddressInlineFormSet(BaseInlineFormSet):
    """
    BaseInlineFormset template for :model:`shepherd.AuxServerAddress` that adds validation
    for this model.
    """

    def clean(self):
        addresses = []
        primary_addresses = []
        duplicates = False
        super().clean()
        if any(self.errors):  # pragma: no cover
            return
        for form in self.forms:
            if form.cleaned_data:
                # Only validate if the form is NOT marked for deletion
                if form.cleaned_data["DELETE"] is False:
                    primary = form.cleaned_data["primary"]
                    ip_address = form.cleaned_data["ip_address"]
                    # Flag incomplete forms
                    if primary and (ip_address == "" or ip_address is None):
                        form.add_error(
                            "ip_address",
                            ValidationError(
                                _("This address entry is incomplete."),
                                code="incomplete",
                            ),
                        )

                    if ip_address:
                        if ip_address in addresses:
                            duplicates = True
                        addresses.append(ip_address)
                    if duplicates:
                        form.add_error(
                            "ip_address",
                            ValidationError(
                                _("This address is already assigned to this server."),
                                code="duplicate",
                            ),
                        )

                    # Check that only one address is marked as the primary
                    if primary and ip_address:
                        primary_addresses.append(ip_address)
                    if len(primary_addresses) > 1:
                        form.add_error(
                            "primary",
                            ValidationError(
                                _("You can not mark two addresses as the primary address."),
                                code="duplicate",
                            ),
                        )


class AuxServerAddressForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.AuxServerAddress` associated with an individual
    :model:`shepherd.StaticServer.
    """

    class Meta:
        model = AuxServerAddress
        exclude = ("static_server",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "chrome-off"
        self.fields["primary"].label = "Make Primary Address"
        self.fields["ip_address"].label = "IP Address"
        self.fields["ip_address"].widget.attrs["placeholder"] = "192.168.13.37"
        self.fields["ip_address"].widget.attrs["autocomplete"] = "off"
        self.helper = FormHelper()
        # Disable the <form> tags because this will be part of an instance of ``ServerForm()``
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
                        <strong>Address Deleted!</strong>
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
                        <p><strong>Address #<span class="counter">{{ forloop.counter }}</span></strong></p>
                        <hr>
                        """
                    ),
                    Row(
                        Column("ip_address", css_class="form-group col-md-6 mb-0"),
                        Column(
                            SwitchToggle(
                                "primary",
                                css_class="primary-checkbox",
                                onchange="checkboxUpdate(this)",
                            ),
                            css_class="form-group col-md-6 mb-0 pt-5",
                        ),
                        css_class="form-row",
                    ),
                    Row(
                        Column(
                            Button(
                                "formset-del-button",
                                "Delete Address",
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
                        css_class="form-row",
                    ),
                    css_class="formset",
                ),
                css_class="formset-container",
            )
        )


ServerAddressFormSet = inlineformset_factory(
    StaticServer,
    AuxServerAddress,
    form=AuxServerAddressForm,
    formset=BaseServerAddressInlineFormSet,
    extra=EXTRAS,
    can_delete=True,
)


class ServerForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.StaticServer`.
    """

    class Meta:
        model = StaticServer
        exclude = ("last_used_by",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["ip_address"].widget.attrs["placeholder"] = "192.168.13.37"
        self.fields["name"].widget.attrs["placeholder"] = "hashcat.ghostwriter.local"
        self.fields["name"].label = "Hostname"
        self.fields["server_status"].empty_label = "-- Select Status --"
        self.fields["server_status"].label = "Server Status"
        self.fields["server_provider"].empty_label = "-- Select a Server Provider --"
        self.fields["server_provider"].label = "Server Provider"
        self.fields["note"].widget.attrs["placeholder"] = "This server has 8 GPUs, hashcat installed, and ..."
        self.fields["tags"].widget.attrs["placeholder"] = "hashcat, GPU:8, ..."
        self.helper = FormHelper()
        # Turn on <form> tags for this parent form
        self.helper.form_tag = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Server Information",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Row(
                        Column("ip_address", css_class="form-group col-md-6 mb-0"),
                        Column("name", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("server_status", css_class="form-group col-md-6 mb-0"),
                        Column("server_provider", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    "tags",
                    "note",
                    link_css_class="icon server-icon",
                    css_id="server",
                ),
                CustomTab(
                    "Additional Addresses",
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    Formset("addresses", object_context_name="Address"),
                    Button(
                        "add-address",
                        "Add Address",
                        css_class="btn-block btn-secondary formset-add-address",
                    ),
                    HTML(
                        """
                        <p class="form-spacer"></p>
                        """
                    ),
                    link_css_class="icon route-icon",
                    css_id="addresses",
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


class TransientServerForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.TransientServer` associated with an individual
    :model:`rolodex.Project`.
    """

    aux_address = SplitArrayField(forms.GenericIPAddressField(), size=3, remove_trailing_nulls=True)

    class Meta:
        model = TransientServer
        exclude = ("project",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["ip_address"].widget.attrs["placeholder"] = "18.231.194.9"
        self.fields["name"].widget.attrs["placeholder"] = "mail.legitdomain.com"
        self.fields["note"].widget.attrs[
            "placeholder"
        ] = "This is the SMTP host for the first phishing campaign and ..."
        self.fields["activity_type"].empty_label = "-- Select an Activity --"
        self.fields["server_role"].empty_label = "-- Select a Server Role --"
        self.fields["server_provider"].empty_label = "-- Select a Server Provider --"
        self.fields["name"].label = "Hostname"
        self.fields["activity_type"].label = "Activity Type"
        self.fields["server_role"].label = "Server Role"
        self.fields["server_provider"].label = "Server Provider"
        self.fields["aux_address"].label = "Additional IP Addresses"
        # Below is necessary due to a bug that sets `SplitArrayField` fields to `required`
        # even when the field is set as `required=False` above
        self.fields["aux_address"].required = False
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon server-icon">Server Information</h4>
                <hr>
                """
            ),
            Row(
                Column("name", css_class="form-group col-md-6 mb-0"),
                Column("ip_address", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("activity_type", css_class="form-group col-md-4 mb-0"),
                Column("server_role", css_class="form-group col-md-4 mb-0"),
                Column("server_provider", css_class="form-group col-md-4 mb-0"),
                css_class="form-row",
            ),
            HTML(
                """
                <p>Include up to three additional IP addresses below:</p>
                """
            ),
            "aux_address",
            HTML(
                """
                <h4 class="icon comment-icon">Additional Information</h4>
                <hr>
                """
            ),
            "note",
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


class ServerNoteForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.ServerNote` associated with an individual
    :model:`shepherd.StaticServer`.
    """

    class Meta:
        model = ServerNote
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


class ServerCheckoutForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.ServerHistory` associated with an individual
    :model:`shepherd.StaticServer`.
    """

    class Meta:
        model = ServerHistory
        fields = "__all__"
        widgets = {
            "server": forms.HiddenInput(),
            "start_date": forms.DateInput(
                format="%Y-%m-%d",
            ),
            "end_date": forms.DateInput(
                format="%Y-%m-%d",
            ),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        data_projects_url = reverse("shepherd:ajax_load_projects")
        data_project_url = reverse("shepherd:ajax_load_project")

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"

        clients = get_client_list(user)
        self.fields["client"].queryset = clients
        self.fields["client"].empty_label = "-- Select a Client --"
        self.fields["client"].label = ""

        self.fields["activity_type"].empty_label = "-- Select Activity --"
        self.fields["activity_type"].label = "Activity Type"
        self.fields["server_role"].empty_label = "-- Select Role --"
        self.fields["server_role"].label = "Server Role"
        self.fields["project"].empty_label = "-- Select a Client First --"
        self.fields["project"].queryset = Project.objects.none()
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs["placeholder"] = "This server will host Mythic C2 and ..."
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {
            "data-projects-url": data_projects_url,
            "data-project-url": data_project_url,
        }
        self.helper.form_id = "checkout-form"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon project-icon">Project & Activity Information</h4>
                <hr>
                """
            ),
            "client",
            "project",
            Row(
                Column("start_date", css_class="form-group col-md-6 mb-0"),
                Column("end_date", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "activity_type",
            "server_role",
            HTML(
                """
                <h4 class="icon comment-icon">Additional Information</h4>
                <hr>
                """
            ),
            "note",
            "server",
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

        # Prevent "not one of the valid options" errors from AJAX project filtering
        if "client" in self.data:
            try:
                client_id = int(self.data.get("client"))
                self.fields["project"].queryset = Project.objects.filter(client_id=client_id).order_by("codename")
            except (ValueError, TypeError):  # pragma: no cover
                pass
        elif self.instance.pk:
            self.fields["project"].queryset = self.instance.client.project_set.order_by("codename")

    def clean_end_date(self):
        end_date = self.cleaned_data["end_date"]
        start_date = self.cleaned_data["start_date"]

        # Check if end_date comes before the start_date
        if end_date < start_date:
            raise ValidationError(_("The provided end date comes before the start date."), code="invalid")
        return end_date

    def clean_server(self):
        insert = bool(self.instance.pk is None)
        server = self.cleaned_data["server"]
        if insert:
            unavailable = ServerStatus.objects.get(server_status="Unavailable")
            if server.server_status == unavailable:
                raise ValidationError(
                    _("Someone beat you to it – This server has already been checked out!"),
                    code="unavailable",
                )
        return server
