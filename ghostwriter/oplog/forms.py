"""This contains all the forms used by the Oplog application."""

# Standard Libraries
from datetime import datetime

# Django Imports
from django import forms
from django.urls import reverse
from django.utils.timezone import make_aware

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Field, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.api.utils import get_project_list
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.rolodex.models import Project
from ghostwriter.commandcenter.forms import ExtraFieldsField


class OplogForm(forms.ModelForm):
    """Save an individual :model:`oplog.Oplog`."""

    class Meta:
        model = Oplog
        fields = "__all__"

    def __init__(self, user=None, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # If this is an update, mark the project field as read-only
        instance = getattr(self, "instance", None)
        if instance and instance.pk:
            self.fields["project"].disabled = True

        # Limit the list to the pre-selected project and disable the field
        if project:
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)
            self.fields["project"].disabled = True

        # Limit the list to active projects if this is a new log made from the sidebar
        if not project:
            projects = get_project_list(user)
            active_projects = projects.filter(complete=False).order_by("-start_date").defer("extra_fields")
            if active_projects:
                self.fields["project"].empty_label = "-- Select an Active Project --"
            else:
                self.fields["project"].empty_label = "-- No Active Projects --"
            self.fields["project"].queryset = active_projects

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["name"].widget.attrs["placeholder"] = "Descriptive Name for Identification"
        self.fields["name"].label = "Name for the Log"
        self.fields["name"].help_text = "Enter a name for this log that will help you identify it"

        # Design form layout with Crispy's ``FormHelper``
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            "name",
            "project",
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class OplogEntryForm(forms.ModelForm):
    """Save an individual :model:`oplog.OplogEntry`."""

    start_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M"],
    )
    end_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M"],
        required=False,
    )
    extra_fields = ExtraFieldsField(OplogEntry._meta.label)

    class Meta:
        model = OplogEntry
        exclude = ["oplog_id"]

    def __init__(self, *args, **kwargs):
        self.oplog = kwargs.pop("oplog", None)
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["source_ip"].widget.attrs["placeholder"] = "Source IP or hostname"
        self.fields["dest_ip"].widget.attrs["placeholder"] = "Targeted IP or hostname"
        self.fields["operator_name"].widget.attrs["placeholder"] = "Operator name"
        self.fields["tool"].widget.attrs["placeholder"] = "Command or script"
        self.fields["command"].widget.attrs["placeholder"] = "Complete executed command"
        self.fields["user_context"].widget.attrs["placeholder"] = "GW\\BENNY"
        self.fields["output"].widget.attrs["placeholder"] = "Command output"
        self.fields["description"].widget.attrs["placeholder"] = "Description"
        self.fields["comments"].widget.attrs["placeholder"] = "Comments"
        self.fields["tags"].widget.attrs["placeholder"] = "att&ck:T1059, att&ck:T1078, att&ck:T1086, objective:1, ..."

        self.fields["start_date"].widget.input_type = "datetime-local"
        self.fields["start_date"].initial = make_aware(datetime.utcnow())
        self.fields["start_date"].label = "Start Date & Time"
        self.fields["start_date"].help_text = "Date and time the action started"
        self.fields["end_date"].widget.input_type = "datetime-local"
        self.fields["end_date"].initial = make_aware(datetime.utcnow())
        self.fields["end_date"].label = "End Date & Time"
        self.fields["end_date"].help_text = "Date and time the action completed or halted"
        self.fields["extra_fields"].label = ""

        self.fields["command"].widget.attrs["rows"] = 2
        self.fields["output"].widget.attrs["rows"] = 2
        self.fields["description"].widget.attrs["rows"] = 2
        self.fields["comments"].widget.attrs["rows"] = 2

        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.form_id = "oplog-entry-form"

        # Set form action based on whether this is a new or existing entry
        # This form is only used for updates via AJAX so there should always be an instance available, but we handle
        # other possibilities to avoid a server error if someone tries browsing to the URL directly
        post_url = None
        if self.instance.pk:
            post_url = reverse("oplog:oplog_entry_update", kwargs={"pk": self.instance.pk})
        else:
            if self.oplog:
                post_url = reverse("oplog:oplog_entry_create", kwargs={"pk": self.oplog.pk})
        if post_url:
            self.helper.form_action = post_url

        has_extra_fields = bool(self.fields["extra_fields"].specs)

        self.helper.layout = Layout(
            Row(
                Column(Field("start_date", step=1), css_class="form-group col-6 mb-0"),
                Column(Field("end_date", step=1), css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("entry_identifier", css_class="form-group col-6 mb-0"),
                Column("operator_name", css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("source_ip", css_class="form-group col-6 mb-0"),
                Column("dest_ip", css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tool", css_class="form-group col-6 mb-0"),
                Column("user_context", css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("command", css_class="form-group col-6 mb-0"),
                Column("output", css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("description", css_class="form-group col-6 mb-0"),
                Column("comments", css_class="form-group col-6 mb-0"),
                css_class="form-row",
            ),
            "tags",
            HTML(
                """
                <h4 class="icon custom-field-icon">Extra Fields</h4>
                <hr />
                """
            ) if has_extra_fields else None,
            "extra_fields" if has_extra_fields else None,
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button data-dismiss="modal" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )
