"""This contains all the forms used by the API application."""

# Standard Libraries
import base64
import logging
from binascii import Error as BinAsciiError
from datetime import timedelta
from os.path import splitext

# Django Imports
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.base import ContentFile
from django.utils import timezone
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Field, Layout, Row, Submit
from docx import Document
from pptx import Presentation

# Ghostwriter Libraries
from ghostwriter.api.models import (
    ServicePrincipal,
    ServiceTokenPreset,
    ServiceTokenProjectScope,
)
from ghostwriter.api.utils import get_client_list
from ghostwriter.oplog.models import Oplog
from ghostwriter.reporting.models import (
    Evidence,
    EvidenceImageAlignmentOverride,
    ReportFindingLink,
    ReportTemplate,
)
from ghostwriter.reporting.validators import (
    DOCX_ALLOWED_EXTENSIONS,
    EVIDENCE_ALLOWED_EXTENSIONS,
    PPTX_ALLOWED_EXTENSIONS,
    TEMPLATE_ALLOWED_EXTENSIONS,
)
from ghostwriter.rolodex.models import Project

logger = logging.getLogger(__name__)


class ApiKeyForm(forms.Form):
    """Save an individual :model:`api.APIKey`."""

    name = forms.CharField()
    expiry_date = forms.DateTimeField(
        input_formats=[
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M",
        ],
    )

    class Meta:
        fields = [
            "name",
            "expiry_date",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["expiry_date"].label = "Expiry Date & Time"
        self.fields["expiry_date"].widget.input_type = "datetime-local"
        self.fields["expiry_date"].initial = timezone.now() + timedelta(days=1)
        self.fields[
            "expiry_date"
        ].help_text = f"Pick a date / time and then select AM or PM (uses server's time zone–{settings.TIME_ZONE})"
        self.fields[
            "name"
        ].help_text = "Enter a name to help you identify this API key later"
        self.fields["name"].widget.attrs[
            "placeholder"
        ] = "API Token – Automation Script"
        # Design form layout with Crispy FormHelper
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("name", css_class="form-group col-6 mb-0"),
                Column(Field("expiry_date", step=1), css_class="form-group col-6 mb-0"),
                css_class="form-group",
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

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data["expiry_date"]

        # Check if expiration comes before the creation date
        if expiry_date:
            if expiry_date < timezone.now():
                raise ValidationError(
                    "The API key expiration date cannot be in the past",
                    code="invalid_expiry_date",
                )
        return expiry_date


class TokenExpiryForm(forms.Form):
    """Update an existing token's expiry date."""

    expiry_date = forms.DateTimeField(
        input_formats=[
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M",
        ],
    )

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data["expiry_date"]
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError(
                "The token expiration date cannot be in the past",
                code="invalid_expiry_date",
            )
        return expiry_date


class ServiceTokenForm(forms.Form):
    """Create a scoped service token."""

    token_preset = forms.ChoiceField(
        choices=[
            (ServiceTokenPreset.OPLOG_RW, ServiceTokenPreset.OPLOG_RW.label),
            (ServiceTokenPreset.PROJECT_READ, ServiceTokenPreset.PROJECT_READ.label),
        ]
    )
    project_scope = forms.ChoiceField(
        choices=[
            (
                ServiceTokenProjectScope.SELECTED,
                ServiceTokenProjectScope.SELECTED.label,
            ),
            (
                ServiceTokenProjectScope.ALL_ACCESSIBLE,
                ServiceTokenProjectScope.ALL_ACCESSIBLE.label,
            ),
        ],
        initial=ServiceTokenProjectScope.SELECTED,
        required=False,
    )
    name = forms.CharField()
    service_principal = forms.ModelChoiceField(
        queryset=ServicePrincipal.objects.none(), required=False
    )
    new_service_principal_name = forms.CharField(required=False)
    oplog = forms.ModelChoiceField(
        queryset=Oplog.objects.none(), empty_label=None, required=False
    )
    projects = forms.ModelMultipleChoiceField(
        queryset=Project.objects.none(),
        required=False,
        widget=forms.SelectMultiple(attrs={"size": 10}),
    )
    expiry_date = forms.DateTimeField(
        input_formats=[
            "%Y-%m-%dT%H:%M:%S",
            "%Y-%m-%d%H:%M:%S",
            "%Y-%m-%dT%H:%M:%S.%f",
            "%Y-%m-%dT%H:%M",
        ],
    )

    class Meta:
        fields = [
            "token_preset",
            "name",
            "service_principal",
            "new_service_principal_name",
            "oplog",
            "project_scope",
            "projects",
            "expiry_date",
        ]

    def __init__(self, *args, **kwargs):
        user = kwargs.pop("user")
        super().__init__(*args, **kwargs)
        self.user = user
        self.fields["service_principal"].queryset = ServicePrincipal.objects.filter(
            active=True,
            created_by=user,
        ).order_by("name", "id")
        self.fields["service_principal"].empty_label = "Create a New Service Principal"
        self.fields["oplog"].queryset = Oplog.for_user(user).select_related(
            "project", "project__client"
        )
        self.fields["projects"].queryset = Project.for_user(user).select_related(
            "client"
        )
        for field in self.fields:
            self.fields[field].widget.attrs["autocomplete"] = "off"
        self.fields["token_preset"].label = "Token Type"
        self.fields[
            "token_preset"
        ].help_text = "Choose the scoped permissions this service token should receive"
        self.fields["expiry_date"].label = "Expiry Date & Time"
        self.fields["expiry_date"].widget.input_type = "datetime-local"
        self.fields["expiry_date"].initial = timezone.now() + timedelta(days=1)
        self.fields[
            "expiry_date"
        ].help_text = f"Pick a date / time and then select AM or PM (uses server's time zone–{settings.TIME_ZONE})"
        self.fields[
            "name"
        ].help_text = (
            "Enter a token name to identify the assessment or environment later"
        )
        self.fields["name"].widget.attrs["placeholder"] = "Acme Q2 Assessment"
        self.fields["service_principal"].label = "Service Principal"
        self.fields[
            "service_principal"
        ].help_text = "Reuse an existing service principal, or leave blank and create a new one below"
        self.fields["new_service_principal_name"].label = "New Service Principal Name"
        self.fields[
            "new_service_principal_name"
        ].help_text = (
            "Create a reusable service principal for the integration or automation"
        )
        self.fields["new_service_principal_name"].widget.attrs[
            "placeholder"
        ] = "Automation Service"
        self.fields[
            "oplog"
        ].help_text = "Select the oplog this token can read from and write to"
        self.fields["project_scope"].label = "Project Scope"
        self.fields[
            "project_scope"
        ].help_text = "Choose selected projects, or dynamically track all projects this user can access now and later"
        self.fields["projects"].help_text = (
            "Select one or more projects this token can read. "
            "Use Ctrl/Cmd-click to select multiple."
        )
        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"
        self.helper.layout = Layout(
            Row(
                Column("token_preset", css_class="form-group col-12 mb-0"),
                css_class="form-group",
            ),
            Row(
                Column("name", css_class="form-group col-6 mb-0"),
                Column(Field("expiry_date", step=1), css_class="form-group col-6 mb-0"),
                css_class="form-group",
            ),
            Row(
                Column("service_principal", css_class="form-group col-6 mb-0"),
                Column("new_service_principal_name", css_class="form-group col-6 mb-0"),
                css_class="form-group",
            ),
            Row(
                Column("oplog", css_class="form-group col-12 mb-0"),
                css_class="form-group",
                css_id="service-token-oplog-row",
            ),
            Row(
                Column("project_scope", css_class="form-group col-12 mb-0"),
                css_class="form-group",
                css_id="service-token-project-scope-row",
            ),
            Row(
                Column("projects", css_class="form-group col-12 mb-0"),
                css_class="form-group",
                css_id="service-token-projects-row",
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

    def clean_expiry_date(self):
        expiry_date = self.cleaned_data["expiry_date"]
        if expiry_date and expiry_date < timezone.now():
            raise ValidationError(
                "The service token expiration date cannot be in the past",
                code="invalid_expiry_date",
            )
        return expiry_date

    def clean_oplog(self):
        oplog = self.cleaned_data.get("oplog")
        if oplog is None:
            return oplog
        if not oplog.user_can_edit(self.user):
            raise ValidationError(
                "You do not have permission to create a service token for this oplog"
            )
        return oplog

    def clean_projects(self):
        projects = self.cleaned_data.get("projects")
        if projects is None:
            return projects
        for project in projects:
            if not project.user_can_view(self.user):
                raise ValidationError(
                    "You do not have permission to create a service token for this project"
                )
        return projects

    def clean(self):
        cleaned_data = super().clean()
        token_preset = cleaned_data.get("token_preset")
        service_principal = cleaned_data.get("service_principal")
        new_service_principal_name = (
            cleaned_data.get("new_service_principal_name") or ""
        ).strip()
        oplog = cleaned_data.get("oplog")
        project_scope = (
            cleaned_data.get("project_scope") or ServiceTokenProjectScope.SELECTED
        )
        projects = cleaned_data.get("projects")

        if service_principal and new_service_principal_name:
            msg = "Select an existing service principal or enter a new one, not both"
            self.add_error("service_principal", msg)
            self.add_error("new_service_principal_name", msg)
        elif not service_principal and not new_service_principal_name:
            msg = "Select an existing service principal or enter a new one"
            self.add_error("service_principal", msg)
            self.add_error("new_service_principal_name", msg)
        elif new_service_principal_name:
            existing = ServicePrincipal.objects.filter(
                active=True,
                created_by=self.user,
                name__iexact=new_service_principal_name,
            ).first()
            if existing:
                cleaned_data["service_principal"] = existing
                cleaned_data["new_service_principal_name"] = ""
            else:
                cleaned_data["new_service_principal_name"] = new_service_principal_name

        if token_preset == ServiceTokenPreset.OPLOG_RW:
            if oplog is None:
                self.add_error("oplog", "Select an oplog for an oplog read/write token")
            cleaned_data["project_scope"] = ServiceTokenProjectScope.SELECTED
            cleaned_data["projects"] = Project.objects.none()
        elif token_preset == ServiceTokenPreset.PROJECT_READ:
            if project_scope == ServiceTokenProjectScope.SELECTED and not projects:
                self.add_error(
                    "projects",
                    "Select at least one project for a project read-only token",
                )
            if project_scope == ServiceTokenProjectScope.ALL_ACCESSIBLE:
                cleaned_data["projects"] = Project.objects.none()
            cleaned_data["oplog"] = None

        return cleaned_data


class Base64BytesField(forms.Field):
    def to_python(self, value):
        value = super().to_python(value)
        if value is None:
            return None
        try:
            blob = base64.b64decode(value, validate=True)
        except BinAsciiError as err:
            raise ValidationError("Invalid base64 data", code="invalid") from err
        return blob


class ApiEvidenceForm(forms.ModelForm):
    file_base64 = Base64BytesField(required=True)
    filename = forms.CharField(required=True)

    class Meta:
        model = Evidence
        fields = (
            "friendly_name",
            "description",
            "caption",
            "tags",
            "finding",
            "report",
        )

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj")
        report_queryset = kwargs.pop("report_queryset")
        finding_queryset = ReportFindingLink.objects.filter(report__in=report_queryset)
        super().__init__(*args, **kwargs)
        self.fields["report"].queryset = report_queryset
        self.fields["finding"].queryset = finding_queryset

    def clean_filename(self):
        _, ext = splitext(self.cleaned_data["filename"])
        if (
            not ext.startswith(".")
            or ext[1:].lower() not in EVIDENCE_ALLOWED_EXTENSIONS
        ):
            raise ValidationError(
                f'File extension "{ext}" is not allowed', code="invalid"
            )
        return self.cleaned_data["filename"]

    def clean(self):
        cleaned_data = super().clean()

        report = None
        if "finding" in cleaned_data and "report" in cleaned_data:
            # Ensure only one of `finding` or `report` is specified
            finding = cleaned_data["finding"]
            report = cleaned_data["report"]
            if (finding is None) == (report is None):
                # Above is effectively XOR.
                msg = _("Must specify only one of either 'finding' or 'report'")
                self.add_error("finding", msg)
                self.add_error("report", msg)
            elif finding is not None:
                report = finding.report

        if report is not None and "friendly_name" in cleaned_data:
            # Validate that evidence name is unique
            name = cleaned_data["friendly_name"]
            if report.all_evidences().filter(friendly_name=name).exists():
                self.add_error(
                    "friendly_name",
                    ValidationError(
                        _(
                            "This friendly name has already been used for a file attached to this report."
                        ),
                        "duplicate",
                    ),
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(False)
        blob = ContentFile(
            self.cleaned_data["file_base64"], name=self.cleaned_data["filename"]
        )
        instance.document = blob
        instance.uploaded_by = self.user_obj
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ApiReportTemplateForm(forms.ModelForm):
    file_base64 = Base64BytesField(required=True)
    filename = forms.CharField(required=True)

    class Meta:
        model = ReportTemplate
        fields = (
            "name",
            "description",
            "protected",
            "changelog",
            "landscape",
            "filename_override",
            "tags",
            "doc_type",
            "client",
            "p_style",
            "bloodhound_heading_offset",
            "evidence_image_width",
            "evidence_image_alignment",
        )

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj")
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = get_client_list(self.user_obj)
        self.fields["evidence_image_width"].required = False
        self.fields["evidence_image_alignment"].required = False

    def clean_evidence_image_alignment(self):
        value = self.cleaned_data.get("evidence_image_alignment")
        if not value:
            return EvidenceImageAlignmentOverride.USE_GLOBAL
        return value

    def clean(self):
        cleaned_data = super().clean()

        # Validate the file extension is allowed for support templates
        filename = cleaned_data.get("filename", "")
        _, ext = splitext(filename)
        if (
            not ext.startswith(".")
            or ext[1:].lower() not in TEMPLATE_ALLOWED_EXTENSIONS
        ):
            self.add_error(
                "filename",
                ValidationError(
                    f'File extension "{ext}" is not allowed for a report template',
                    code="invalid",
                ),
            )

        # Check if the file extension matches the selected document type
        if "doc_type" in cleaned_data:
            doc_type = cleaned_data["doc_type"]
            if (
                ext[1:].lower() in DOCX_ALLOWED_EXTENSIONS
                and doc_type.extension not in DOCX_ALLOWED_EXTENSIONS
            ) or (
                ext[1:].lower() in PPTX_ALLOWED_EXTENSIONS
                and doc_type.extension not in PPTX_ALLOWED_EXTENSIONS
            ):
                self.add_error(
                    "filename",
                    ValidationError(
                        f"File extension '{ext}' does not match the selected document type '{doc_type.name}'",
                        code="mismatch",
                    ),
                )

        # Check if the file is a valid Microsoft Word or PowerPoint document
        if "filename" in cleaned_data:
            if ext[1:].lower() in DOCX_ALLOWED_EXTENSIONS:
                try:
                    Document(
                        ContentFile(self.cleaned_data["file_base64"], name=filename)
                    )
                except ValueError as e:
                    logger.error(
                        "Could not open this template. %s, from %s as a Microsoft Word document: %s",
                        filename,
                        self.user_obj,
                        e,
                    )
                    self.add_error(
                        "file_base64",
                        ValidationError(
                            "Could not open this template as a Microsoft Word document",
                            code="invalid",
                        ),
                    )

            if ext[1:].lower() in PPTX_ALLOWED_EXTENSIONS:
                try:
                    Presentation(
                        ContentFile(self.cleaned_data["file_base64"], name=filename)
                    )
                except ValueError as e:
                    logger.error(
                        "Could not open this template. %s, from %s as a Microsoft PowerPoint document: %s",
                        filename,
                        self.user_obj,
                        e,
                    )
                    self.add_error(
                        "file_base64",
                        ValidationError(
                            "Could not open this template as a Microsoft PowerPoint document",
                            code="invalid",
                        ),
                    )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(False)
        blob = ContentFile(
            self.cleaned_data["file_base64"], name=self.cleaned_data["filename"]
        )
        instance.document = blob
        instance.uploaded_by = self.user_obj
        if commit:
            instance.save()
            self.save_m2m()
        return instance


class ApiOplogRecordingForm(forms.Form):
    """Validate and prepare an Asciinema recording upload for an :model:`oplog.OplogEntry`."""

    file_base64 = Base64BytesField(required=True)
    filename = forms.CharField(required=True)
    oplog_entry_id = forms.IntegerField(required=True)

    def clean_filename(self):
        filename = self.cleaned_data["filename"]
        filename_lower = filename.lower()
        # Accept .cast or .cast.gz extensions
        if not (
            filename_lower.endswith(".cast") or filename_lower.endswith(".cast.gz")
        ):
            raise ValidationError(
                "File extension is not allowed. Only .cast and .cast.gz files are accepted.",
                code="invalid",
            )
        return filename
