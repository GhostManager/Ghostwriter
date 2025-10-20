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
            Field("assigned_to"),
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML("""
                    <a href="{{cancel_link}}" class="btn btn-outline-secondary col-md-4">Cancel</a>
                """)
            )
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

        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["docx_template"].label = "DOCX Template"
        self.fields["pptx_template"].label = "PPTX Template"
        self.fields["docx_template"].required = False
        self.fields["pptx_template"].required = False
        self.fields["tags"].widget.attrs["placeholder"] = "draft, QA2, ..."
        self.fields["title"].widget.attrs["placeholder"] = "Red Team Report for Project Foo"

        report_config = ReportConfiguration.get_solo()
        self.fields["docx_template"].initial = report_config.default_docx_template
        self.fields["pptx_template"].initial = report_config.default_pptx_template
        self.fields["docx_template"].empty_label = "-- Pick a Word Template --"
        self.fields["pptx_template"].empty_label = "-- Pick a PowerPoint Template --"

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("title", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "project",
            HTML(
                """
                <h4 class="icon file-icon">Assign Templates</h4>
                <hr />
                <p>Select a template to use for the Word and PowerPoint versions of the report.
                If you do not select a template, the global default template will be used.
                If a default is not configured, you will need to select one here or on the report page.</p>
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
                    <button onclick="window.location.href='{{ cancel_link }}'"
                    class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
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
            "tags",
        )
        widgets = {
            "document": forms.FileInput(attrs={"class": "form-control"}),
        }
        field_classes = {
            "description": JinjaRichTextField,
        }

    def __init__(self, *args, **kwargs):
        self.is_modal = kwargs.pop("is_modal", None)
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
        # Don't set form buttons for a modal pop-up
        if self.is_modal:
            submit = None
            cancel_button = None
        else:
            submit = Submit("submit-button", "Submit", css_class="btn btn-primary col-md-4")
            cancel_button = HTML(
                """
                <button onclick="window.location.href='{{ cancel_link }}'"
                class="btn btn-outline-secondary col-md-4" type="button">Cancel
                </button>
                """
            )
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_errors = False
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.form_id = "evidence-upload-form"
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon signature-icon">Report Information</h4>
                <hr>
                <p>The friendly name is used to reference this evidence in the report and the caption appears below
                the figures in the generated reports.</p>
                """
            ),
            Row(
                Column("friendly_name", css_class="form-group col-md-6 mb-0"),
                Column("tags", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            "caption",
            "description",
            HTML(
                """
                <h4 class="icon upload-icon">Upload a File</h4>
                <hr>
                <p>Attach text evidence (*.txt, *.log, or *.md) or image evidence (*.png, *.jpg, or *.jpeg).
                Previews for images will appear below.</p>
                <p><span class="bold">Tip:</span> You copy and paste an image (file or screenshot) into this page!
                Make sure to <span class="italic">click outside of any form fields first</span>.</p>
                <div id="findingPreview" class="pb-3"></div>
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
                    <label id="filename" class="custom-file-label" for="customFile">
                    Click here to select or drag and drop your file...</label>
                    """
                ),
                css_class="custom-file",
            ),
            ButtonHolder(submit, cancel_button, css_class="mt-3"),
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
        filename_override = self.cleaned_data["filename_override"]
        if not filename_override:
            return

        doc_typ = self.cleaned_data["doc_type"]
        try:
            if doc_typ.doc_type == "docx":
                ExportReportBase.check_filename_template(filename_override)
            elif doc_typ.doc_type == "pptx" or doc_typ.doc_type == "project_docx":
                ExportProjectBase.check_filename_template(filename_override)
        except ValidationError as e:
            self.add_error("filename_override", e)

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
        self.fields["evidence_image_width"].label = "Evidence Image Width"
        self.fields["evidence_image_width"].initial = "6.5"

        clients = get_client_list(user)
        self.fields["client"].queryset = clients

        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_method = "post"
        self.helper.attrs = {"enctype": "multipart/form-data"}
        self.helper.layout = Layout(
            HTML(
                """
                <h4 class="icon file-icon">Template Information</h4>
                <hr>
                <p>The name appears in the template dropdown menus in reports.</p>
                """
            ),
            Row(
                Column("name", css_class="form-group col-md-6 mb-0"),
                Column("client", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("doc_type", css_class="form-group col-md-6 mb-0"),
                Column("p_style", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column("tags", css_class="form-group col-md-6 mb-0"),
                Column("evidence_image_width", css_class="form-group col-md-6 mb-0"),
                css_class="form-row",
            ),
            Row(
                Column(
                    SwitchToggle(
                        "protected",
                    ),
                    css_class="form-group col-md-6 mb-0",
                ),
                Column(
                    SwitchToggle(
                        "landscape",
                    ),
                    css_class="form-group col-md-6 mb-0",
                ),
                css_class="form-row pb-2",
            ),
            "filename_override",
            "description",
            HTML(
                """
                <h4 class="icon upload-icon">Upload a File</h4>
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
        fields = ("docx_template", "pptx_template")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["docx_template"].help_text = None
        self.fields["pptx_template"].help_text = None
        self.fields["docx_template"].empty_label = "-- Select a DOCX Template --"
        self.fields["pptx_template"].empty_label = "-- Select a PPTX Template --"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = False
        self.helper.form_method = "post"
        self.helper.form_id = "report-template-swap-form"
        self.helper.form_tag = True
        self.helper.form_action = reverse("reporting:ajax_swap_report_template", kwargs={"pk": self.instance.id})
        self.helper.layout = Layout(
            Row(
                Column(
                    HTML(
                        """
                        <p class="text-left mt-1">Template for DOCX</p>
                        """
                    ),
                    css_class="col-md-2",
                ),
                Column(
                    FieldWithButtons(
                        "docx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-default word-btn js-generate-report"
                                type="button"
                                href="{% url 'reporting:generate_docx' report.id %}"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Generate a DOCX report"
                            >
                            </a>
                            """
                        ),
                        HTML(
                            """
                            <a
                                class="btn btn-default jump-btn js-jump-to-word-template"
                                type="button"
                                href="#"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Jump to Word template details"
                                target="_blank"
                            >
                            </a>
                            """
                        ),
                    ),
                    css_class="col-md-4",
                ),
                css_class="justify-content-md-center",
            ),
            Row(
                Column(
                    HTML(
                        """
                        <p class="text-left mt-1">Template for PPTX</p>
                        """
                    ),
                    css_class="col-md-2",
                ),
                Column(
                    FieldWithButtons(
                        "pptx_template",
                        HTML(
                            """
                            <a
                                class="btn btn-default pptx-btn"
                                type="button"
                                href="{% url 'reporting:generate_pptx' report.id %}"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Generate a PPTX report"
                            >
                            </a>
                            """
                        ),
                        HTML(
                            """
                            <a
                                class="btn btn-default jump-btn js-jump-to-pptx-template"
                                type="button"
                                href="#"
                                data-toggle="tooltip"
                                data-placement="top"
                                title="Jump to PowerPoint template details"
                                target="_blank"
                            >
                            </a>
                            """
                        ),
                    ),
                    css_class="col-md-4",
                ),
                css_class="justify-content-md-center",
            ),
            HTML(
                """
                <p class="mb-2">Other report types do not use templates:</p>
                <div class="btn-group">
                    <a class="btn btn-default excel-btn-icon" href="{% url 'reporting:generate_xlsx' report.id %}"
                    data-toggle="tooltip" data-placement="top" title="Generate an XLSX report"></i></a>
                    <a class="btn btn-default json-btn-icon" href="{% url 'reporting:generate_json' report.id %}"
                    data-toggle="tooltip" data-placement="top" title="Generate exportable JSON"></a>
                    <a class="btn btn-default archive-btn-icon js-generate-report"
                    href="{% url 'reporting:generate_all' report.id %}" data-toggle="tooltip" data-placement="top"
                    title="Generate and package all report types and evidence in a Zip"></a>
                </div>
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
