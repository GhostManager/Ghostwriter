"""This contains all the forms used by the API application."""

# Standard Libraries
import base64
from binascii import Error as BinAsciiError
from datetime import timedelta
import logging
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
from pptx import Presentation
from docx import Document

# Ghostwriter Libraries
from ghostwriter.api.utils import get_client_list
from ghostwriter.reporting.models import Evidence, ReportFindingLink, ReportTemplate
from ghostwriter.reporting.validators import (
    DOCX_ALLOWED_EXTENSIONS,
    EVIDENCE_ALLOWED_EXTENSIONS,
    PPTX_ALLOWED_EXTENSIONS,
    TEMPLATE_ALLOWED_EXTENSIONS,
)


logger = logging.getLogger(__name__)


class ApiKeyForm(forms.Form):
    """Save an individual :model:`api.APIKey`."""

    name = forms.CharField()
    expiry_date = forms.DateTimeField(
        input_formats=["%Y-%m-%dT%H:%M:%S", "%Y-%m-%d%H:%M:%S", "%Y-%m-%dT%H:%M:%S.%f", "%Y-%m-%dT%H:%M"],
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
        self.fields["name"].help_text = "Enter a name to help you identify this API key later"
        self.fields["name"].widget.attrs["placeholder"] = "API Token – Automation Script"
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
        fields = ("friendly_name", "description", "caption", "tags", "finding", "report")

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj")
        report_queryset = kwargs.pop("report_queryset")
        finding_queryset = ReportFindingLink.objects.filter(report__in=report_queryset)
        super().__init__(*args, **kwargs)
        self.fields["report"].queryset = report_queryset
        self.fields["finding"].queryset = finding_queryset

    def clean_filename(self):
        _, ext = splitext(self.cleaned_data["filename"])
        if not ext.startswith(".") or ext[1:].lower() not in EVIDENCE_ALLOWED_EXTENSIONS:
            raise ValidationError(f'File extension "{ext}" is not allowed', code="invalid")
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
                        _("This friendly name has already been used for a file attached to this report."),
                        "duplicate",
                    ),
                )

        return cleaned_data

    def save(self, commit=True):
        instance = super().save(False)
        blob = ContentFile(self.cleaned_data["file_base64"], name=self.cleaned_data["filename"])
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
        exclude = ("document", "upload_date", "last_update", "lint_result", "uploaded_by")

    def __init__(self, *args, **kwargs):
        self.user_obj = kwargs.pop("user_obj")
        super().__init__(*args, **kwargs)
        self.fields["client"].queryset = get_client_list(self.user_obj)

    def clean(self):
        cleaned_data = super().clean()

        # Validate the file extension is allowed for support templates
        _, ext = splitext(self.cleaned_data["filename"])
        if not ext.startswith(".") or ext[1:].lower() not in TEMPLATE_ALLOWED_EXTENSIONS:
            self.add_error(
                "filename",
                ValidationError(f'File extension "{ext}" is not allowed for a report template', code="invalid"),
            )

        # Check if the file extension matches the selected document type
        if "doc_type" in cleaned_data:
            doc_type = cleaned_data["doc_type"]
            if (ext[1:].lower() in DOCX_ALLOWED_EXTENSIONS and doc_type.extension not in DOCX_ALLOWED_EXTENSIONS) or (
                ext[1:].lower() in PPTX_ALLOWED_EXTENSIONS and doc_type.extension not in PPTX_ALLOWED_EXTENSIONS
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
                    Document(ContentFile(self.cleaned_data["file_base64"], name=self.cleaned_data["filename"]))
                except ValueError as e:
                    logger.error(
                        "Could not open this template. %s, from %s as a Microsoft Word document: %s",
                        self.cleaned_data["filename"],
                        self.user_obj,
                        e,
                    )
                    self.add_error(
                        "file_base64",
                        ValidationError("Could not open this template as a Microsoft Word document", code="invalid"),
                    )

            if ext[1:].lower() in PPTX_ALLOWED_EXTENSIONS:
                try:
                    Presentation(ContentFile(self.cleaned_data["file_base64"], name=self.cleaned_data["filename"]))
                except ValueError as e:
                    logger.error(
                        "Could not open this template. %s, from %s as a Microsoft PowerPoint document: %s",
                        self.cleaned_data["filename"],
                        self.user_obj,
                        e,
                    )
                    self.add_error(
                        "file_base64",
                        ValidationError(
                            "Could not open this template as a Microsoft PowerPoint document", code="invalid"
                        ),
                    )
        return cleaned_data

    def save(self, commit=True):
        instance = super().save(False)
        blob = ContentFile(self.cleaned_data["file_base64"], name=self.cleaned_data["filename"])
        instance.document = blob
        instance.uploaded_by = self.user_obj
        if commit:
            instance.save()
            self.save_m2m()
        return instance
