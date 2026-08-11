"""This contains all the forms used by the Oplog application."""

# Django Imports
from django import forms
from django.urls import reverse
from django.utils import timezone

# 3rd Party Libraries
from crispy_forms.bootstrap import FieldWithButtons, StrictButton, TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import ButtonHolder, Column, Div, Field, HTML, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.api.utils import get_project_list
from ghostwriter.commandcenter.forms import ExtraFieldsField
from ghostwriter.modules.custom_layout_object import CustomTab
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.reporting.models import Evidence, Report
from ghostwriter.rolodex.models import Project


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
        self.helper.form_class = "resource-edit-form"
        self.helper.layout = Layout(
            Div(
                HTML(
                    """
                    <div class="resource-form-section-heading">
                      <span class="resource-form-section-icon"><i class="fas fa-stream" aria-hidden="true"></i></span>
                      <div>
                        <h4>Log identity</h4>
                        <p>Name this timeline for quick recognition and connect it to the engagement it supports.</p>
                      </div>
                    </div>
                    """
                ),
                "name",
                "project",
                css_class="resource-form-card",
            ),
            Div(
                HTML("""<span class="resource-form-actions-context">{% if object.pk %}Editing {{ object.name }}{% else %}Creating an operation log{% endif %}</span>"""),
                Div(
                    HTML("""<a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>"""),
                    Submit(
                        "submit_btn",
                        "Save Changes" if self.instance.pk else "Create Log",
                        css_class="btn btn-primary",
                    ),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions",
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
        self.fields["start_date"].initial = timezone.now()
        self.fields["start_date"].label = "Start Date & Time"
        self.fields["start_date"].help_text = "Date and time the action started"
        self.fields["end_date"].widget.input_type = "datetime-local"
        self.fields["end_date"].initial = timezone.now()
        self.fields["end_date"].label = "End Date & Time"
        self.fields["end_date"].help_text = "Date and time the action completed or halted"
        self.fields["extra_fields"].label = ""

        self.fields["command"].widget.attrs["rows"] = 2
        self.fields["output"].widget.attrs["rows"] = 2
        self.fields["description"].widget.attrs["rows"] = 2
        self.fields["comments"].widget.attrs["rows"] = 2
        for field_name in ("command", "output"):
            existing_classes = self.fields[field_name].widget.attrs.get("class", "").split()
            if "no-auto-rich-text" not in existing_classes:
                existing_classes.append("no-auto-rich-text")
            self.fields[field_name].widget.attrs["class"] = " ".join(existing_classes)
        for field_name in ("description", "comments"):
            existing_classes = (
                self.fields[field_name].widget.attrs.get("class", "").split()
            )
            if "gw-tiptap-compact" not in existing_classes:
                existing_classes.append("gw-tiptap-compact")
            self.fields[field_name].widget.attrs["class"] = " ".join(existing_classes)

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

        tabs = [
            CustomTab(
                "Activity",
                HTML(
                    """
                    <div class="form-section-heading mb-3">
                        <h2>Activity context</h2>
                        <p>Record when and where the command ran, the tool and user context, and who performed it.</p>
                    </div>
                    """
                ),
                Row(
                    Column(
                        Field("start_date", step=1),
                        css_class="col-md-6 mb-0",
                    ),
                    Column(
                        FieldWithButtons(
                            Field("end_date", step=1),
                            StrictButton(
                                "Now",
                                css_class="btn btn-outline-secondary js-set-oplog-end-date-now",
                                title="Set end date and time to now",
                            ),
                        ),
                        css_class="col-md-6 mb-0",
                    ),
                    css_class="row g-3",
                ),
                Row(
                    Column("source_ip", css_class="col-md-6 mb-0"),
                    Column("dest_ip", css_class="col-md-6 mb-0"),
                    css_class="row g-3",
                ),
                Row(
                    Column("tool", css_class="col-md-6 mb-0"),
                    Column("user_context", css_class="col-md-6 mb-0"),
                    css_class="row g-3",
                ),
                Div("command", css_class="empty-form"),
                Row(
                    Column("operator_name", css_class="col-md-6 mb-0"),
                    Column("entry_identifier", css_class="col-md-6 mb-0"),
                    css_class="row g-3",
                ),
                css_id="activity",
            ),
            CustomTab(
                "Notes & Output",
                HTML(
                    """
                    <div class="form-section-heading mb-3">
                        <h2>Supporting details</h2>
                        <p>Add output, narrative context, and tags when they help explain or organize the activity.</p>
                    </div>
                    """
                ),
                "output",
                Row(
                    Column("description", css_class="col-md-6 mb-0"),
                    Column("comments", css_class="col-md-6 mb-0"),
                    css_class="row g-3",
                ),
                "tags",
                css_id="notes-output",
            ),
        ]

        if has_extra_fields:
            tabs.append(
                CustomTab(
                    "Extra Fields",
                    HTML(
                        """
                        <div class="form-section-heading mb-3">
                            <h2>Additional details</h2>
                            <p>Capture organization-specific metadata configured for operation log entries.</p>
                        </div>
                        """
                    ),
                    "extra_fields",
                    link_css_class="tab-icon custom-field-icon",
                    css_id="extra-fields",
                )
            )

        self.helper.layout = Layout(
            TabHolder(
                *tabs,
                template="tab.html",
                css_class="oplog-entry-tabs nav-fill",
                css_id="oplog-entry-tab-bar",
            ),
            Div(
                HTML(
                    """
                    <span class="resource-form-actions-context">
                        Editing entry #{{ object.pk }} &middot; Ctrl/Cmd + Enter to save
                    </span>
                    """
                ),
                Div(
                    HTML(
                        """
                        <button data-bs-dismiss="modal" class="btn btn-outline-secondary" type="button">Cancel</button>
                        """
                    ),
                    Submit("submit_btn", "Save Entry", css_class="btn btn-primary"),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions oplog-entry-form-actions",
            ),
        )
        self.helper.form_class = "resource-edit-form oplog-entry-edit-form"


class OplogEvidenceForm(forms.ModelForm):
    """Upload evidence and link it to an :model:`oplog.OplogEntry`."""

    report = forms.ModelChoiceField(
        queryset=Report.objects.none(),
        required=True,
        help_text="Select the report this evidence belongs to.",
    )

    class Meta:
        model = Evidence
        fields = (
            "friendly_name",
            "document",
            "report",
            "caption",
            "description",
            "tags",
        )
        widgets = {
            "document": forms.FileInput(attrs={"class": "resource-file-input"}),
            "description": forms.Textarea(attrs={"rows": 1}),
        }

    def __init__(self, *args, **kwargs):
        self.project = kwargs.pop("project", None)
        active_report_id = kwargs.pop("active_report_id", None)
        super().__init__(*args, **kwargs)
        self.fields["friendly_name"].required = True
        self.fields["friendly_name"].widget.attrs["autocomplete"] = "off"
        self.fields["friendly_name"].widget.attrs["placeholder"] = "Friendly Name"
        self.fields["caption"].required = True
        self.fields["caption"].widget.attrs["autocomplete"] = "off"
        self.fields["caption"].widget.attrs["placeholder"] = "Report Caption"
        self.fields["description"].widget.attrs["placeholder"] = "Brief Description or Note"
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["document"].label = "Evidence File"

        if self.project:
            reports = Report.objects.filter(project=self.project).order_by("title")
            self.fields["report"].queryset = reports
            # Prefer: 1) active report (if valid for this project), 2) first report in list
            initial_report = None
            if active_report_id:
                initial_report = reports.filter(pk=active_report_id).first()
            if initial_report is None:
                initial_report = reports.first()
            if initial_report is not None:
                self.fields["report"].initial = initial_report

        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_id = "oplog-evidence-form"
        self.helper.form_class = "oplog-evidence-upload-form"

    def clean(self):
        cleaned_data = super().clean()
        friendly_name = cleaned_data.get("friendly_name")
        report = cleaned_data.get("report")
        if friendly_name and report:
            qs = report.evidence_set.filter(friendly_name=friendly_name)
            if self.instance.pk:
                qs = qs.exclude(pk=self.instance.pk)
            if qs.exists():
                raise forms.ValidationError(
                    "An evidence item with this friendly name already exists for the selected report."
                )
        return cleaned_data
