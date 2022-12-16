"""This contains all the forms used by the CommandCenter application."""

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import ReportConfiguration


class ReportConfigurationForm(forms.ModelForm):
    """
    Save settings in :model:`commandcenter.ReportConfiguration`.
    """

    class Meta:
        model = ReportConfiguration
        fields = "__all__"

    def clean_default_docx_template(self):
        docx_template = self.cleaned_data["default_docx_template"]
        if docx_template:
            docx_template_status = docx_template.get_status()
            if docx_template_status in ("error", "failed"):
                raise ValidationError(
                    _("Your selected Word template failed linting and cannot be used as a default template"),
                    "invalid",
                )
        return docx_template

    def clean_default_pptx_template(self):
        pptx_template = self.cleaned_data["default_pptx_template"]
        if pptx_template:
            pptx_template_status = pptx_template.get_status()
            if pptx_template_status in ("error", "failed"):
                raise ValidationError(
                    _("Your selected PowerPoint template failed linting and cannot be used as a default template"),
                    "invalid",
                )
        return pptx_template
