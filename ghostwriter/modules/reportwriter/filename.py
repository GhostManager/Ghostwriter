"""Shared report filename template validation."""

# Django Imports
from django.core.exceptions import ValidationError

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase


def validate_filename_template(filename_template, doc_type):
    """Validate a template filename with the matching production exporter context."""
    if not filename_template or not doc_type:
        return

    doc_type_name = str(getattr(doc_type, "doc_type", doc_type)).lower()
    if doc_type_name == "docx":
        ExportReportBase.check_filename_template(filename_template)
    elif doc_type_name in {"pptx", "project_docx"}:
        ExportProjectBase.check_filename_template(filename_template)
    else:
        raise ValidationError(
            f'Filename templates are not supported for document type "{doc_type_name}".',
            code="unsupported_doc_type",
        )
