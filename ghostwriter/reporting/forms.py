"""This contains all of the forms used by the Reporting application."""

# Django & Other 3rd Party Libraries
from crispy_forms.bootstrap import TabHolder
from crispy_forms.helper import FormHelper
from crispy_forms.layout import (
    HTML,
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
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.modules.custom_layout_object import CustomTab
from ghostwriter.rolodex.models import Project

from .models import (
    Evidence,
    Finding,
    FindingNote,
    LocalFindingNote,
    Report,
    ReportFindingLink,
    ReportTemplate,
)


class FindingForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Finding`.
    """

    class Meta:
        model = Finding
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(FindingForm, self).__init__(*args, **kwargs)
        self.fields["title"].widget.attrs["placeholder"] = "SQL Injection"
        self.fields["title"].widget.attrs["autocomplete"] = "off"
        self.fields["description"].widget.attrs["placeholder"] = "What is this ..."
        self.fields["impact"].widget.attrs["placeholder"] = "What is the impact ..."
        self.fields["mitigation"].widget.attrs[
            "placeholder"
        ] = "What needs to be done ..."
        self.fields["replication_steps"].widget.attrs[
            "placeholder"
        ] = "How to reproduce/find this issue ..."
        self.fields["host_detection_techniques"].widget.attrs[
            "placeholder"
        ] = "How to detect it on an endpoint ..."
        self.fields["network_detection_techniques"].widget.attrs[
            "placeholder"
        ] = "How to detect it on a network ..."
        self.fields["references"].widget.attrs[
            "placeholder"
        ] = "Some useful links and references ..."
        self.fields["finding_guidance"].widget.attrs[
            "placeholder"
        ] = "When using this finding in a report be sure to include ..."
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.layout = Layout(
            TabHolder(
                CustomTab(
                    "Categorization",
                    "title",
                    Row(
                        Column("finding_type", css_class="form-group col-md-6 mb-0"),
                        Column("severity", css_class="form-group col-md-6 mb-0"),
                        css_class="form-row",
                    ),
                    link_css_class="tab-icon  search-icon",
                    css_id="general-tab",
                ),
                CustomTab(
                    "Description",
                    "description",
                    "impact",
                    link_css_class="tab-icon pencil-icon",
                    css_id="description-tab",
                ),
                CustomTab(
                    "Defense",
                    "mitigation",
                    "replication_steps",
                    "host_detection_techniques",
                    "network_detection_techniques",
                    link_css_class="tab-icon shield-icon",
                    css_id="defense-tab",
                ),
                CustomTab(
                    "References",
                    "references",
                    "finding_guidance",
                    link_css_class="tab-icon link-icon",
                    css_id="reference-tab",
                ),
                template="tab.html",
                css_class="nav-justified",
            ),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class ReportForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Report` associated with an indivudal
    :model:`rolodex.Project`.
    """

    class Meta:
        model = Report
        exclude = ("creation", "last_update", "created_by", "complete")

    def __init__(self, project=None, *args, **kwargs):
        super(ReportForm, self).__init__(*args, **kwargs)
        self.project_instance = project
        # Limit the list to just projects not marked as complete
        active_projects = Project.objects.filter(complete=False).order_by(
            "start_date", "client", "project_type"
        )
        if active_projects:
            self.fields["project"].empty_label = "-- Select an Active Project --"
        else:
            self.fields["project"].empty_label = "-- No Active Projects --"
        self.fields["project"].queryset = active_projects
        self.fields[
            "project"
        ].label_from_instance = (
            lambda obj: f"{obj.start_date} {obj.client.name} {obj.project_type} ({obj.codename})"
        )
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.layout = Layout(
            "title",
            "project",
            HTML(
                """
                <h6 class="icon file-icon">Assign Templates</h6>
                <hr />
                """
            ),
            Row(
                Column("docx_template", css_class="form-group col-md-6 mb-0"),
                Column("pptx_template", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
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


class ReportFindingLinkUpdateForm(forms.ModelForm):
    """
    Update an individual :model:`reporting.ReportFindingLink` associated with an
    individual :model:`reporting.Report`.
    """

    class Meta:
        model = ReportFindingLink
        exclude = ("report", "position", "finding_guidance")

    def __init__(self, *args, **kwargs):
        super(ReportFindingLinkUpdateForm, self).__init__(*args, **kwargs)
        evidence_upload_url = reverse(
            "reporting:upload_evidence_modal",
            kwargs={"pk": self.instance.id, "modal": "modal"},
        )
        self.fields["affected_entities"].widget.attrs[
            "placeholder"
        ] = "DC01.TEXTLAB.LOCAL"
        self.fields["title"].widget.attrs["placeholder"] = "SQL Injection"
        self.fields["title"].widget.attrs["autocomplete"] = "off"
        self.fields["description"].widget.attrs["placeholder"] = "What is this ..."
        self.fields["impact"].widget.attrs["placeholder"] = "What is the impact ..."
        self.fields["mitigation"].widget.attrs[
            "placeholder"
        ] = "What needs to be done ..."
        self.fields["replication_steps"].widget.attrs[
            "placeholder"
        ] = "How to reproduce/find this issue ..."
        self.fields["host_detection_techniques"].widget.attrs[
            "placeholder"
        ] = "How to detect it on an endpoint ..."
        self.fields["network_detection_techniques"].widget.attrs[
            "placeholder"
        ] = "How to detect it on a network ..."
        self.fields["references"].widget.attrs[
            "placeholder"
        ] = "Some useful links and references ..."
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.form_id = "report-finding-form"
        self.helper.attrs = {"evidence-upload-modal-url": evidence_upload_url}
        self.helper.layout = Layout(
            HTML(
                """
                <h6 class="icon list-icon">Affected Entities</h6>
                <hr />
                """
            ),
            "assigned_to",
            "affected_entities",
            HTML(
                """
                <h6 class="icon search-icon">Categorization</h6>
                <hr />
                """
            ),
            "title",
            Row(
                Column("finding_type", css_class="form-group col-md-6 mb-0"),
                Column("severity", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            HTML(
                """
                <h6 class="icon pencil-icon">Description</h6>
                <hr />
                """
            ),
            Field("description", css_class="enable-evidence-upload"),
            Field("impact", css_class="enable-evidence-upload"),
            HTML(
                """
                <h6 class="icon shield-icon">Defense</h6>
                <hr />
                """
            ),
            Field("mitigation", css_class="enable-evidence-upload"),
            Field("replication_steps", css_class="enable-evidence-upload"),
            Field("host_detection_techniques", css_class="enable-evidence-upload"),
            Field(
                "network_detection_techniques",
                css_class="enable-evidence-upload",
            ),
            HTML(
                """
                <h6 class="icon link-icon">References</h6>
                <hr />
                """
            ),
            "references",
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class EvidenceForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Evidence` associated with an individual
    :model:`reporting.ReportFindingLink`.
    """

    class Meta:
        model = Evidence
        fields = (
            "friendly_name",
            "document",
            "description",
            "caption",
        )
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.is_modal = kwargs.pop("is_modal", None)
        self.evidence_queryset = kwargs.pop("evidence_queryset", None)
        super(EvidenceForm, self).__init__(*args, **kwargs)
        self.fields["caption"].required = True
        self.fields["caption"].widget.attrs["autocomplete"] = "off"
        self.fields["caption"].widget.attrs[
            "placeholder"
        ] = "Brief one-line caption for the report"
        self.fields["friendly_name"].required = True
        self.fields["friendly_name"].widget.attrs["autocomplete"] = "off"
        self.fields["friendly_name"].widget.attrs["placeholder"] = "BloodHound Graph 1"
        self.fields["description"].widget.attrs[
            "placeholder"
        ] = "Description of the evidence file for your team"
        self.fields["document"].label = ""
        self.fields["document"].widget.attrs["class"] = "custom-file-input"
        # Don't set form buttons for a modal pop-up
        if self.is_modal:
            submit = None
            cancel_button = None
        else:
            submit = Submit(
                "submit-button", "Submit", css_class="btn btn-primary col-md-4"
            )
            cancel_button = HTML(
                """
                <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                """
            )
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_id = "evidence-upload-form"
        self.helper.layout = Layout(
            HTML(
                """
                <i class="fas fa-signature"></i>Report Information
                <hr>
                <p>The friendly name is used to reference this evidence in the report and the caption appears below the figures in the generated reports.</p>
                """
            ),
            Row(
                Column("friendly_name", css_class="form-group col-md-6 mb-0"),
                Column("caption", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "description",
            HTML(
                """
                <i class="far fa-file"></i>Upload a File
                <hr>
                <p>Attach text evidence (*.txt, *.log, or *.md) or image evidence (*.png, *.jpg, or *.jpeg).</p>
                """
            ),
            Div(
                Field(
                    "document",
                    id="id_document",
                ),
                HTML(
                    """
                    <label id="filename" class="custom-file-label" for="customFile">Choose evidence file...</label>
                    """
                ),
                css_class="custom-file",
            ),
            ButtonHolder(submit, cancel_button),
        )

    def clean(self):
        cleaned_data = super(EvidenceForm, self).clean()
        friendly_name = cleaned_data.get("friendly_name")
        # Check if provided name has already been used for another file for this report
        report_queryset = self.evidence_queryset.values_list("id", "friendly_name")
        for evidence in report_queryset:
            if friendly_name == evidence[1] and not self.instance.id == evidence[0]:
                raise ValidationError(
                    _(
                        "This friendly name has already been used for a file attached to this finding."
                    ),
                    "duplicate",
                )
        return cleaned_data


class FindingNoteForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.FindingNote` associated with an individual
    :model:`reporting.Finding`.
    """

    class Meta:
        model = FindingNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super(FindingNoteForm, self).__init__(*args, **kwargs)
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


class LocalFindingNoteForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.LocalFindingNote` associated with an individual
    :model:`ReportFindingLink.
    """

    class Meta:
        model = LocalFindingNote
        fields = ("note",)

    def __init__(self, *args, **kwargs):
        super(LocalFindingNoteForm, self).__init__(*args, **kwargs)
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


class ReportTemplateForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.ReportTemplate`.
    """

    class Meta:
        model = ReportTemplate
        exclude = ("upload_date", "last_update", "lint_result")
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
            "uploaded_by": forms.HiddenInput(),
        }

    def __init__(self, *args, **kwargs):
        super(ReportTemplateForm, self).__init__(*args, **kwargs)
        self.fields["document"].label = ""
        self.fields["document"].widget.attrs["class"] = "custom-file-input"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "newitem"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.layout = Layout(
            HTML(
                """
                <i class="fas fa-signature"></i>Template Information
                <hr>
                <p>The name appears in the template dropdown menus in reports.</p>
                """
            ),
            Row(
                Column("name", css_class="form-group col-md-8 mb-0"),
                Column("doc_type", css_class="form-group col-md-4 mb-0"),
                css_class="form-row",
            ),
            "description",
            HTML(
                """
                <i class="far fa-file"></i>Upload a File
                <hr>
                <p>Attach a document that matches your selected filetype to use as a report template</p>
                """
            ),
            Div(
                "document",
                HTML(
                    """
                    <label id="filename" class="custom-file-label" for="customFile">Choose template file...</label>
                    """
                ),
                css_class="custom-file",
            ),
            "changelog",
            "client",
            "protected",
            "uploaded_by",
            ButtonHolder(
                Submit("submit", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )


class SelectReportTemplateForm(forms.ModelForm):
    """
    Modify the ``docx_template`` and ``pptx_template`` values of an individual
    :model:`reporting.Report`.
    """

    class Meta:
        model = Report
        fields = ("docx_template", "pptx_template")

    def __init__(self, *args, **kwargs):
        super(SelectReportTemplateForm, self).__init__(*args, **kwargs)
        self.fields["docx_template"].help_text = None
        self.fields["pptx_template"].help_text = None
        self.fields["docx_template"].empty_label = "-- Select a Word Template --"
        self.fields["pptx_template"].empty_label = "-- Select a PPT Template --"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "post"
        self.helper.form_id = "report-template-swap-form"
        self.helper.form_tag = True
        self.helper.form_action = reverse(
            "reporting:ajax_swap_report_template", kwargs={"pk": self.instance.id}
        )
        self.helper.layout = Layout(
            Field("docx_template", css_class="col-md-4 offset-md-4"),
            Field("pptx_template", css_class="col-md-4 offset-md-4"),
        )
