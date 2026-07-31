"""This contains all the forms used by the Reporting application."""

# Standard Libraries
import re

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.urls import reverse
from django.utils.translation import gettext_lazy as _
from django.db.models import Q

# 3rd Party Libraries
from crispy_forms.bootstrap import FieldWithButtons
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

# Ghostwriter Libraries
from ghostwriter.api.utils import get_client_list, get_project_list, verify_user_is_privileged
from ghostwriter.commandcenter.forms import ExtraFieldsField
from ghostwriter.commandcenter.models import ReportConfiguration
from ghostwriter.modules.custom_layout_object import SwitchToggle
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.reporting.models import (
    Evidence,
    FindingNote,
    LocalFindingNote,
    Observation,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    ReportTemplate,
    Severity,
)
from ghostwriter.rolodex.models import Project


def _report_template_queryset(doc_type, project=None):
    queryset = ReportTemplate.objects.filter(
        doc_type__doc_type__iexact=doc_type,
    ).select_related("doc_type", "client")
    if project:
        return queryset.filter(Q(client_id=project.client_id) | Q(client__isnull=True))
    return queryset.filter(client__isnull=True)


class AssignReportFindingForm(forms.ModelForm):
    class Meta:
        model = ReportFindingLink
        fields = ("assigned_to",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Div(
                HTML("""
                    <div class="resource-form-section-heading">
                      <span class="resource-form-section-icon"><i class="fas fa-user-check" aria-hidden="true"></i></span>
                      <div>
                        <h4>Finding ownership</h4>
                        <p>Choose the operator responsible for progressing and reviewing this finding.</p>
                      </div>
                    </div>
                """),
                Field("assigned_to"),
                css_class="resource-form-card",
            ),
            Div(
                HTML("""<span class="resource-form-actions-context">Updating finding ownership</span>"""),
                Div(
                    HTML("""<a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>"""),
                    Submit("submit_btn", "Save Assignment", css_class="btn btn-primary"),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions resource-form-actions-compact",
            ),
        )

class AssignReportObservationForm(forms.ModelForm):
    class Meta:
        model = ReportObservationLink
        fields = ("assigned_to",)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Div(
                HTML("""
                    <div class="resource-form-section-heading">
                      <span class="resource-form-section-icon"><i class="fas fa-user-check" aria-hidden="true"></i></span>
                      <div>
                        <h4>Observation ownership</h4>
                        <p>Choose the operator responsible for progressing and reviewing this observation.</p>
                      </div>
                    </div>
                """),
                Field("assigned_to"),
                css_class="resource-form-card",
            ),
            Div(
                HTML("""<span class="resource-form-actions-context">Updating observation ownership</span>"""),
                Div(
                    HTML("""<a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>"""),
                    Submit("submit_btn", "Save Assignment", css_class="btn btn-primary"),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions resource-form-actions-compact",
            ),
        )


class ReportForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.Report` associated with an individual
    :model:`rolodex.Project`.
    """

    class Meta:
        model = Report
        exclude = ("creation", "last_update", "created_by", "complete", "extra_fields")

    def __init__(self, user=None, project=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Don't allow non-manager users to move a report's project
        instance = getattr(self, "instance", None)
        user_is_privileged = verify_user_is_privileged(user)
        if instance and instance.pk:
            if user is None or not user_is_privileged:
                self.fields["project"].disabled = True

        # If there is a project and user is not privileged,
        # limit the list to the pre-selected project and disable the field
        if project and not user_is_privileged:
            self.fields["project"].queryset = Project.objects.filter(pk=project.pk)
            self.fields["project"].disabled = True

        # If no project is selected, limit the list to what the user can access
        # Checks for privilege so that privileged users get a list with only active projects
        if not project or user_is_privileged:
            projects = get_project_list(user)
            active_projects = (
                projects.filter(complete=False).order_by("-start_date", "client", "project_type").defer("extra_fields")
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

        selected_project = project
        if selected_project is None and getattr(self.instance, "project_id", None):
            selected_project = self.instance.project
        if self.is_bound and not self.fields["project"].disabled:
            project_id = self.data.get(self.add_prefix("project"))
            if project_id:
                try:
                    selected_project = self.fields["project"].queryset.filter(pk=project_id).first()
                except (TypeError, ValueError):
                    selected_project = None

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["docx_template"].label = "DOCX Template"
        self.fields["pptx_template"].label = "PPTX Template"
        self.fields["docx_template"].required = False
        self.fields["pptx_template"].required = False
        self.fields["tags"].widget.attrs["placeholder"] = "draft, QA2, ..."
        self.fields["title"].widget.attrs["placeholder"] = "Red Team Report for Project Foo"

        report_config = ReportConfiguration.get_solo()
        template_fields = (
            ("docx_template", "docx", report_config.default_docx_template),
            ("pptx_template", "pptx", report_config.default_pptx_template),
        )
        for field_name, doc_type, default_template in template_fields:
            self.fields[field_name].queryset = _report_template_queryset(doc_type, selected_project)
            if default_template and (
                default_template.client_id is None
                or (selected_project and default_template.can_apply_to_project(selected_project))
            ):
                self.fields[field_name].initial = default_template
        self.fields["docx_template"].empty_label = "-- Pick a Word Template --"
        self.fields["pptx_template"].empty_label = "-- Pick a PowerPoint Template --"

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_class = "resource-edit-form"
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-fingerprint" aria-hidden="true"></i></span>
                          <div>
                            <h4>Report identity</h4>
                            <p>Name the deliverable as operators and reviewers should see it throughout Ghostwriter.</p>
                          </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("title", css_class="form-group col-md-7"),
                        Column("tags", css_class="form-group col-md-5"),
                        css_class="form-row",
                    ),
                    "project",
                    css_class="resource-form-card",
                ),
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-file-export" aria-hidden="true"></i></span>
                          <div>
                            <h4>Output templates</h4>
                            <p>Choose document-specific templates or leave a selection blank to use the configured default.</p>
                          </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("docx_template", css_class="form-group col-md-6"),
                        Column("pptx_template", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    css_class="resource-form-card",
                ),
                css_class="resource-form-grid report-form-grid",
            ),
            Div(
                HTML(
                    """
                    <span class="resource-form-actions-context">
                        {% if object.pk %}Editing {{ object.title }}{% else %}Creating a new report{% endif %}
                    </span>
                    """
                ),
                Div(
                    HTML("""<a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>"""),
                    Submit(
                        "submit",
                        "Save Changes" if self.instance.pk else "Create Report",
                        css_class="btn btn-primary",
                    ),
                    css_class="resource-form-actions-buttons",
                ),
                css_class="resource-form-actions",
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
            "tags",
        )
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }
        field_classes = {
            "description": JinjaRichTextField,
    }

    def __init__(self, *args, **kwargs):
        self.evidence_queryset = kwargs.pop("evidence_queryset", None)
        super().__init__(*args, **kwargs)
        self.fields["caption"].required = True
        self.fields["caption"].widget.attrs["autocomplete"] = "off"
        self.fields["caption"].widget.attrs["placeholder"] = "Report Caption"
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["friendly_name"].required = True
        self.fields["friendly_name"].widget.attrs["autocomplete"] = "off"
        self.fields["friendly_name"].widget.attrs["placeholder"] = "Friendly Name"
        self.fields["description"].widget.attrs["placeholder"] = "Brief Description or Note"
        self.fields["document"].label = ""
        submit_label = "Save Changes" if self.instance.pk else "Upload Evidence"
        submit = Submit("submit-button", submit_label, css_class="btn btn-primary")
        cancel_button = HTML(
            """
            <a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>
            """
        )
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_id = "evidence-upload-form"
        self.helper.form_class = "resource-edit-form"
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-fingerprint" aria-hidden="true"></i></span>
                          <div>
                            <h4>Evidence Identity</h4>
                            <p>Name the file for operators and define how it will be labelled in report output.</p>
                          </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("friendly_name", css_class="form-group col-md-6"),
                        Column("tags", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    "caption",
                    "description",
                    css_class="resource-form-card",
                ),
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-paperclip" aria-hidden="true"></i></span>
                          <div>
                            <h4>Evidence File</h4>
                            <p>Attach text evidence (*.txt, *.log, or *.md) or image evidence (*.png, *.jpg, or *.jpeg).</p>
                          </div>
                        </div>
                        <div class="detail-guidance mb-3">
                          Paste an image while focus is outside a form field, or choose a replacement file below.
                        </div>
                        <div id="findingPreview" class="evidence-form-preview"></div>
                        """
                    ),
                    Div(
                        Field(
                            "document",
                            id="id_document",
                            css_class="custom-file-input",
                        ),
                        HTML(
                            """
                            <label id="filename" class="custom-file-label" for="id_document">
                              <i class="fas fa-cloud-upload-alt" aria-hidden="true"></i>
                              <span>Choose a file or drag it here</span>
                            </label>
                            """
                        ),
                        css_class="custom-file resource-file-dropzone",
                    ),
                    css_class="resource-form-card resource-upload-card",
                ),
                css_class="resource-form-grid evidence-form-grid",
            ),
            ButtonHolder(
                cancel_button,
                submit,
                css_class="resource-form-actions resource-form-actions-compact",
            ),
        )

    def clean_document(self):
        document = self.cleaned_data["document"]
        # Check if evidence file is missing
        if not document:
            raise ValidationError(
                _("You must provide an evidence file"),
                "incomplete",
            )
        return document

    def clean_friendly_name(self):
        friendly_name = self.cleaned_data["friendly_name"]
        if self.evidence_queryset:
            # Check if provided name has already been used for another file for this report
            if self.evidence_queryset.filter(Q(friendly_name=friendly_name) & ~Q(id=self.instance.id)).exists():
                raise ValidationError(
                    _("This friendly name has already been used for a file attached to this report."),
                    "duplicate",
                )
        return friendly_name


class FindingNoteForm(forms.ModelForm):
    """
    Save an individual :model:`reporting.FindingNote` associated with an individual
    :model:`reporting.Finding`.
    """

    class Meta:
        model = FindingNote
        fields = ("note",)
        field_classes = {
            "note": JinjaRichTextField,
        }

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
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
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
        field_classes = {
            "note": JinjaRichTextField,
        }

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
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
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
    """Save an individual :model:`reporting.ReportTemplate`."""

    def clean(self):
        filename_override = self.cleaned_data.get("filename_override")
        if not filename_override:
            return self.cleaned_data

        doc_typ = self.cleaned_data.get("doc_type")
        if not doc_typ:
            return self.cleaned_data

        try:
            if doc_typ.doc_type == "docx":
                ExportReportBase.check_filename_template(filename_override)
            elif doc_typ.doc_type == "pptx" or doc_typ.doc_type == "project_docx":
                ExportProjectBase.check_filename_template(filename_override)
        except ValidationError as e:
            self.add_error("filename_override", e)

        return self.cleaned_data

    class Meta:
        model = ReportTemplate
        exclude = ("upload_date", "last_update", "lint_result", "uploaded_by")
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }

    def __init__(self, user=None, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"

        if kwargs.get("instance"):
            self.fields[
                "client"
            ].help_text += ". Changing this will unset this template as the global default template and the default templates on reports for other clients."
            self.fields[
                "doc_type"
            ].help_text += ". Changing this will unset this template as the global default template and the default templates on reports."

        self.fields["document"].label = ""
        self.fields["document"].widget.attrs["class"] = "custom-file-input"
        self.fields["name"].widget.attrs["placeholder"] = "Default Red Team Report"
        self.fields["description"].widget.attrs["placeholder"] = "Use this template for any red team work unless ..."
        self.fields["changelog"].widget.attrs["placeholder"] = "Track Template Modifications"
        self.fields["doc_type"].empty_label = "-- Select a Matching Template Type --"
        self.fields["client"].empty_label = "-- Attach to a Client (Optional) --"
        self.fields["tags"].widget.attrs["placeholder"] = "language:en_US, cvss, ..."
        self.fields["p_style"].widget.attrs["placeholder"] = "Normal"
        self.fields["p_style"].initial = "Normal"
        self.fields["doc_type"].label = "Document Type"
        self.fields["doc_type"].required = True
        self.fields["evidence_image_width"].label = "Evidence Image Width"
        self.fields["evidence_image_width"].required = False
        self.fields["evidence_image_width"].help_text = (
            "Leave blank to use the global default evidence image width. If the global default is blank, 6.5 inches is used."
        )

        clients = get_client_list(user)
        self.fields["client"].queryset = clients

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_class = "resource-edit-form"
        self.helper.layout = Layout(
            Div(
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-fingerprint" aria-hidden="true"></i></span>
                          <div>
                            <h4>Template Identity</h4>
                            <p>Set where this template appears and help operators recognize when to use it.</p>
                          </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("name", css_class="form-group col-md-6"),
                        Column("client", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("doc_type", css_class="form-group col-md-6"),
                        Column("tags", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    Div(
                        Div(SwitchToggle("protected"), css_class="resource-toggle-item"),
                        Div(SwitchToggle("landscape"), css_class="resource-toggle-item"),
                        Div(SwitchToggle("contains_bloodhound_data"), css_class="resource-toggle-item"),
                        css_class="resource-toggle-grid",
                    ),
                    css_class="resource-form-card",
                ),
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-sliders-h" aria-hidden="true"></i></span>
                          <div>
                            <h4>Document Behavior</h4>
                            <p>Control generated paragraph, evidence, filename, and BloodHound formatting.</p>
                          </div>
                        </div>
                        """
                    ),
                    Row(
                        Column("p_style", css_class="form-group col-md-6"),
                        Column("filename_override", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    Row(
                        Column("evidence_image_alignment", css_class="form-group col-md-6"),
                        Column("evidence_image_width", css_class="form-group col-md-6"),
                        css_class="form-row",
                    ),
                    "bloodhound_heading_offset",
                    css_class="resource-form-card",
                ),
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-file-upload" aria-hidden="true"></i></span>
                          <div>
                            <h4>Template File</h4>
                            <p>Upload a document that matches the selected document type.</p>
                          </div>
                        </div>
                        """
                    ),
                    Div(
                        "document",
                        HTML(
                            """
                            <label id="filename" class="custom-file-label" for="id_document">
                              <i class="fas fa-cloud-upload-alt" aria-hidden="true"></i>
                              <span>Choose a template file or drag it here</span>
                            </label>
                            """
                        ),
                        css_class="custom-file resource-file-dropzone",
                    ),
                    css_class="resource-form-card resource-upload-card",
                ),
                Div(
                    HTML(
                        """
                        <div class="resource-form-section-heading">
                          <span class="resource-form-section-icon"><i class="fas fa-align-left" aria-hidden="true"></i></span>
                          <div>
                            <h4>Operator Guidance</h4>
                            <p>Explain the template’s purpose and record changes that matter to report authors.</p>
                          </div>
                        </div>
                        """
                    ),
                    "description",
                    "changelog",
                    css_class="resource-form-card resource-form-card-wide",
                ),
                css_class="resource-form-grid template-form-grid",
            ),
            ButtonHolder(
                HTML(
                    """
                    <a href="{{ cancel_link }}" class="btn btn-outline-secondary">Cancel</a>
                    """
                ),
                Submit(
                    "submit",
                    "Save Changes" if self.instance.pk else "Create Template",
                    css_class="btn btn-primary",
                ),
                css_class="resource-form-actions resource-form-actions-compact",
            ),
        )

    def clean_document(self):
        document = self.cleaned_data["document"]
        # Check if template file is missing
        if not document:
            raise ValidationError(
                _("You must provide a template file"),
                "incomplete",
            )
        return document


class SelectReportTemplateForm(forms.ModelForm):
    """
    Modify the ``docx_template`` and ``pptx_template`` values of an individual
    :model:`reporting.Report`.
    """

    class Meta:
        model = Report
        fields = ("docx_template", "pptx_template", "include_bloodhound_data")

    def __init__(self, *args, **kwargs):
        has_bloodhound = kwargs.pop("has_bloodhound", False)
        super().__init__(*args, **kwargs)
        self.fields["docx_template"].help_text = None
        self.fields["docx_template"].required = False
        self.fields["pptx_template"].help_text = None
        self.fields["pptx_template"].required = False
        self.fields["docx_template"].queryset = _report_template_queryset("docx", self.instance.project)
        self.fields["pptx_template"].queryset = _report_template_queryset("pptx", self.instance.project)
        self.fields["docx_template"].empty_label = "-- Select a DOCX Template --"
        self.fields["pptx_template"].empty_label = "-- Select a PPTX Template --"
        self.fields["include_bloodhound_data"].required = False
        self.fields["include_bloodhound_data"].label = "Include BloodHound Data"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "post"
        self.helper.form_id = "report-template-swap-form"
        self.helper.form_tag = True
        self.helper.form_action = reverse("reporting:ajax_swap_report_template", kwargs={"pk": self.instance.id})
        self.helper.layout = Layout(
            HTML(
                """
                <div class="generation-guidance mb-4">
                    <span class="generation-guidance-icon" aria-hidden="true">
                        <i class="fas fa-file-export"></i>
                    </span>
                    <div>
                        <h5>Build a report package</h5>
                        <p>Choose a template for Word or PowerPoint, then generate the format you need. Template selections are saved automatically for this report.</p>
                    </div>
                </div>
                """
            ),
            Div(
                HTML(
                    """
                    <span class="generation-option-icon" aria-hidden="true">
                        <i class="fas fa-project-diagram"></i>
                    </span>
                    """
                ),
                SwitchToggle("include_bloodhound_data"),
                css_class="generation-option-card mb-4",
            ) if has_bloodhound else None,
            Div(
                Div(
                    HTML(
                        """
                        <header class="generation-template-header">
                            <span class="generation-format-icon generation-format-icon-word" aria-hidden="true">
                                <i class="fas fa-file-word"></i>
                            </span>
                            <div>
                                <div class="generation-template-title-row">
                                    <h5>Word document</h5>
                                    <span class="generation-format-badge">DOCX</span>
                                </div>
                                <p>Generate the complete narrative report.</p>
                            </div>
                        </header>
                        <label class="visually-hidden" for="id_docx_template">Word report template</label>
                        """
                    ),
                    FieldWithButtons(
                        "docx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-outline-secondary generation-template-detail js-jump-to-word-template"
                                href="#"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                title="Open Word template details"
                                target="_blank"
                            >
                                <i class="fas fa-external-link-alt" aria-hidden="true"></i>
                                <span class="visually-hidden">Open Word template details</span>
                            </a>
                            """
                        ),
                    ),
                    HTML(
                        """
                        <button
                            class="btn generation-create-button generation-create-word js-generate-report mt-3"
                            type="submit"
                            formaction="{% url 'reporting:generate_docx' report.id %}"
                            formmethod="get"
                        >
                            <i class="fas fa-file-word" aria-hidden="true"></i>
                            Generate Word report
                        </button>
                        """
                    ),
                    css_class="generation-template-card",
                ),
                Div(
                    HTML(
                        """
                        <header class="generation-template-header">
                            <span class="generation-format-icon generation-format-icon-powerpoint" aria-hidden="true">
                                <i class="fas fa-file-powerpoint"></i>
                            </span>
                            <div>
                                <div class="generation-template-title-row">
                                    <h5>PowerPoint presentation</h5>
                                    <span class="generation-format-badge">PPTX</span>
                                </div>
                                <p>Generate a presentation-ready slide deck.</p>
                            </div>
                        </header>
                        <label class="visually-hidden" for="id_pptx_template">PowerPoint report template</label>
                        """
                    ),
                    FieldWithButtons(
                        "pptx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-outline-secondary generation-template-detail js-jump-to-pptx-template"
                                href="#"
                                data-bs-toggle="tooltip"
                                data-bs-placement="top"
                                title="Open PowerPoint template details"
                                target="_blank"
                            >
                                <i class="fas fa-external-link-alt" aria-hidden="true"></i>
                                <span class="visually-hidden">Open PowerPoint template details</span>
                            </a>
                            """
                        ),
                    ),
                    HTML(
                        """
                        <button
                            class="btn generation-create-button generation-create-powerpoint mt-3"
                            type="submit"
                            formaction="{% url 'reporting:generate_pptx' report.id %}"
                            formmethod="get"
                        >
                            <i class="fas fa-file-powerpoint" aria-hidden="true"></i>
                            Generate PowerPoint
                        </button>
                        """
                    ),
                    css_class="generation-template-card",
                ),
                css_class="generation-template-grid",
            ),
            HTML(
                """
                <section class="generation-export-section mt-4">
                    <header class="generation-export-header">
                        <div>
                            <h5>Data and package exports</h5>
                            <p>These formats use the report data directly and do not require a template.</p>
                        </div>
                    </header>
                    <div class="generation-export-grid">
                        <button
                            class="btn btn-outline-secondary generation-export-button"
                            type="submit"
                            formaction="{% url 'reporting:generate_xlsx' report.id %}"
                            formmethod="get"
                        >
                            <i class="fas fa-file-excel generation-export-icon generation-export-icon-excel" aria-hidden="true"></i>
                            <span><strong>Spreadsheet</strong><small>XLSX workbook</small></span>
                        </button>
                        <button
                            class="btn btn-outline-secondary generation-export-button"
                            type="submit"
                            formaction="{% url 'reporting:generate_json' report.id %}"
                            formmethod="get"
                        >
                            <i class="fas fa-file-code generation-export-icon generation-export-icon-json" aria-hidden="true"></i>
                            <span><strong>Structured data</strong><small>Exportable JSON</small></span>
                        </button>
                        <button
                            class="btn btn-primary generation-export-button js-generate-report"
                            type="submit"
                            formaction="{% url 'reporting:generate_all' report.id %}"
                            formmethod="get"
                        >
                            <i class="fas fa-file-archive generation-export-icon" aria-hidden="true"></i>
                            <span><strong>Complete package</strong><small>All formats and evidence</small></span>
                        </button>
                    </div>
                </section>
                """
            ),
        )


class SeverityForm(forms.ModelForm):
    """Save an individual :model:`reporting.Severity`."""

    class Meta:
        model = Severity
        fields = "__all__"

    def clean_color(self, *args, **kwargs):
        color = self.cleaned_data["color"]
        regex = "^(?:[0-9a-fA-F]{1,2}){3}$"
        valid_hex_regex = re.compile(regex)
        if color:
            if "#" in color:
                raise ValidationError(
                    _("Do not include the # symbol in the color field."),
                    "invalid",
                )
            if len(color) < 6:
                raise ValidationError(
                    _("Your hex color code should be six characters in length."),
                    "invalid",
                )
            if not re.search(valid_hex_regex, color):
                raise ValidationError(
                    _("Please enter a valid hex color, three pairs of characters using A-F and 0-9 (e.g., 7A7A7A)."),
                    "invalid",
                )

        return color


class ReportObservationLinkUpdateForm(forms.ModelForm):
    """
    Update an individual :model:`reporting.ReportObservationLink` associated with an
    individual :model:`reporting.Report`.
    """

    # Note: since ReportObservationLinks are essentially an observation bound to a report, it uses
    # the observation's extra field specifications, rather than having its own.
    extra_fields = ExtraFieldsField(Observation._meta.label)

    class Meta:
        model = ReportObservationLink
        exclude = (
            "report",
            "position",
            "added_as_blank",
            "assigned_to",
            "complete",
        )
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["title"].widget.attrs["placeholder"] = "Observation Title"
        self.fields["description"].widget.attrs["placeholder"] = "What is this ..."
        self.fields["tags"].widget.attrs["placeholder"] = "ATT&CK:T1555, privesc, ..."
        self.fields["extra_fields"].label = ""

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.form_id = "report-observation-form"
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Field("description", css_class="enable-evidence-upload"),
            Field("extra_fields", css_class="enable-evidence-upload"),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel
                    </button>
                    """
                ),
            ),
        )
