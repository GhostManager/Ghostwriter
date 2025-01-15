"""This contains custom validators for the Reporting application."""

# Django Imports
from django.core.validators import FileExtensionValidator

EVIDENCE_ALLOWED_EXTENSIONS = ["txt", "md", "log", "jpg", "jpeg", "png"]

DOCX_ALLOWED_EXTENSIONS = ["docx", "doc", "docm", "dotx", "dotm"]
PPTX_ALLOWED_EXTENSIONS = ["pptx", "ppt", "pptm", "potx", "potm", "ppsx", "ppsm"]
TEMPLATE_ALLOWED_EXTENSIONS = DOCX_ALLOWED_EXTENSIONS + PPTX_ALLOWED_EXTENSIONS


def validate_evidence_extension(value):
    """
    Enforce a limited allowlist for filetypes. Allowed filetypes are limited to
    text and image files that will work for report documents.
    """
    return FileExtensionValidator(allowed_extensions=EVIDENCE_ALLOWED_EXTENSIONS)(value)
