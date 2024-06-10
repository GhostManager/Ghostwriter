"""This contains all the forms used by the Shepherd application."""

# Standard Libraries
from datetime import date

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.api.utils import get_client_list
from ghostwriter.commandcenter.forms import ExtraFieldsField
from ghostwriter.modules.custom_layout_object import SwitchToggle
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from ghostwriter.rolodex.models import Project
from ghostwriter.shepherd.models import (
    Domain,
    DomainNote,
    DomainServerConnection,
    DomainStatus,
    History,
    ServerHistory,
    TransientServer,
)


class CheckoutForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.History` associated with an individual
    :model:`shepherd.Domain`.
    """

    class Meta:
        model = History
        fields = "__all__"
        widgets = {
            "domain": forms.HiddenInput(),
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
        overwatch_url = reverse("shepherd:ajax_domain_overwatch")

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"

        clients = get_client_list(user)
        self.fields["client"].queryset = clients
        self.fields["client"].empty_label = "-- Select a Client --"
        self.fields["client"].label = ""

        self.fields["activity_type"].empty_label = "-- Select Activity --"
        self.fields["activity_type"].label = ""
        self.fields["project"].empty_label = "-- Select a Client First --"
        self.fields["project"].label = ""
        self.fields["project"].queryset = Project.objects.none()
        self.fields["start_date"].widget.input_type = "date"
        self.fields["end_date"].widget.input_type = "date"
        self.fields["note"].widget.attrs["placeholder"] = "This domain will be used for..."
        self.fields["note"].label = ""
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.attrs = {
            "data-projects-url": data_projects_url,
            "data-project-url": data_project_url,
            "overwatch-url": overwatch_url,
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
            HTML(
                """
                <h4 class="icon comment-icon">Additional Information</h4>
                <hr>
                """
            ),
            "note",
            "domain",
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
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

    def clean_domain(self):
        insert = bool(self.instance.pk is None)
        domain = self.cleaned_data["domain"]

        if insert:
            unavailable = DomainStatus.objects.get(domain_status="Unavailable")
            if (domain.expiration < date.today() and domain.auto_renew is False) or domain.expired:
                raise ValidationError(_("This domain has expired!"), code="expired")
            if domain.domain_status == unavailable:
                raise ValidationError(
                    _("Someone beat you to it – This domain has already been checked out!"),
                    code="unavailable",
                )
        return domain


class DomainForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.Domain`.
    """

    extra_fields = ExtraFieldsField(Domain._meta.label)

    class Meta:
        model = Domain
        exclude = (
            "last_used_by",
            "burned_explanation",
            "categorization",
            "dns",
            "expired",
        )
        widgets = {
            "creation": forms.DateInput(
                format="%Y-%m-%d",
            ),
            "expiration": forms.DateInput(
                format="%Y-%m-%d",
            ),
        }
        field_classes = {
            "note": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "ghostwriter.wiki"
        self.fields["registrar"].widget.attrs["placeholder"] = "NameCheap"
        self.fields["domain_status"].empty_label = "-- Select Status --"
        self.fields["whois_status"].empty_label = "-- Select Status --"
        self.fields["health_status"].empty_label = "-- Select Status --"
        self.fields["creation"].widget.input_type = "date"
        self.fields["expiration"].widget.input_type = "date"
        self.fields["note"].widget.attrs["placeholder"] = "This domain was purchased for..."
        self.fields["note"].label = ""
        self.fields["tags"].widget.attrs["placeholder"] = "phishing, categorized, ..."
        self.fields["name"].label = "Domain Name"
        self.fields["whois_status"].label = "WHOIS Status"
        self.fields["health_status"].label = "Health Status"
        self.fields["extra_fields"].label = ""

        has_extra_fields = bool(self.fields["extra_fields"].specs)

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_errors = False
        self.helper.form_id = "checkout-form"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon domain-icon">Domain Information</h4>
                <hr>
                """
            ),
            Row(
                Column("name", css_class="form-group col-md-6 mb-0"),
                Column("registrar", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("domain_status", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("creation", css_class="form-group col-md-6 mb-0"),
                Column("expiration", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column(SwitchToggle("auto_renew"), css_class="form-group col-md-6 mb-0"),
                Column(SwitchToggle("reset_dns"), css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            HTML(
                """
                <h4 class="icon heartbeat-icon">Health & Category Information</h4>
                <hr>
                """
            ),
            Row(
                Column("whois_status", css_class="form-group col-md-6 mb-0"),
                Column("health_status", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            HTML(
                """
                <h4 class="icon comment-icon">Additional Information</h4>
                <hr>
                """
            ),
            "note",
            HTML(
                """
                <h4 class="icon custom-field-icon">Extra Fields</h4>
                <hr />
                """
            ) if has_extra_fields else None,
            "extra_fields" if has_extra_fields else None,
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

    def clean_name(self):
        domain = None
        name = self.cleaned_data["name"]
        try:
            domain = Domain.objects.get(name=name.lower())
        except Domain.DoesNotExist:
            pass
        if domain and domain.pk != self.instance.pk:
            raise ValidationError(
                _("Domain names must be unique and this one already exists in the library."),
                code="unique",
            )
        return name

    def clean(self):
        expiration = self.cleaned_data["expiration"]
        creation = self.cleaned_data["creation"]

        # Check if expiration comes before the creation date
        if expiration < creation:
            raise ValidationError(
                _("The provided expiration date comes before the purchase date."),
                code="invalid_date",
            )


class DomainLinkForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.DomainServerConnection` linking an individual
    :model:`shepherd.Domain` with an individual :model:`shepherd.StaticServer` or
    :model:`shepherd.TransientServer`.
    """

    class Meta:
        model = DomainServerConnection
        exclude = ("project",)

    def __init__(self, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if project:
            self.fields["static_server"].queryset = ServerHistory.objects.filter(project=project).order_by(
                "activity_type", "server_role"
            )
            self.fields["transient_server"].queryset = TransientServer.objects.filter(project=project).order_by(
                "activity_type", "server_role"
            )
            self.fields["domain"].queryset = History.objects.filter(project=project).order_by("activity_type")
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["domain"].empty_label = "-- Select a Domain [Required] --"
        self.fields["domain"].label_from_instance = lambda obj: f"{obj.domain.name} ({obj.activity_type})"

        self.fields["static_server"].empty_label = "-- Select Static Server --"
        self.fields[
            "static_server"
        ].label_from_instance = lambda obj: f"{obj.server.ip_address} ({obj.server_role} | {obj.activity_type})"

        self.fields["transient_server"].empty_label = "-- Select VPS --"
        self.fields[
            "transient_server"
        ].label_from_instance = lambda obj: f"{obj.ip_address} ({obj.server_role} | {obj.activity_type})"

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_errors = False
        self.helper.form_show_labels = False
        self.helper.layout = Layout(
            HTML(
                """
                <p>First, select a domain checked-out for this project:</p>
                """
            ),
            "domain",
            HTML(
                """
                <p>Then set your subdomain (or "*" for a wildcard) and CDN endpoint (if any) used with this link:</p>
                """
            ),
            "subdomain",
            "endpoint",
            HTML(
                """
                <p>Finally, select either a static server checked-out for this project
                <em>or</em> a transient server to associate with the selected domain:</p>
                """
            ),
            Row(
                Column("static_server", css_class="form-group col-md-6 mb-0"),
                Column("transient_server", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "project",
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

    def clean(self):
        if self.cleaned_data["static_server"] and self.cleaned_data["transient_server"]:
            raise ValidationError(_("Select only one server."), code="invalid_selection")
        if not self.cleaned_data["static_server"] and not self.cleaned_data["transient_server"]:
            raise ValidationError(_("You must select one server."), code="invalid_selection")


class DomainNoteForm(forms.ModelForm):
    """
    Save an individual :model:`shepherd.DomainNote` associated with an individual
    :model:`shepherd.Domain`.
    """

    class Meta:
        model = DomainNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
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


class BurnForm(forms.ModelForm):
    """
    Update the ``burned_explanation`` field for an individual :model:`shepherd.Domain`.
    """

    class Meta:
        model = Domain
        fields = ("burned_explanation",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["burned_explanation"].widget.attrs["placeholder"] = "This domain was flagged for..."
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_show_labels = False
        self.helper.form_show_errors = False
        self.helper.layout = Layout(
            "burned_explanation",
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
