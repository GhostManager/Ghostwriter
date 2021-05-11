"""This contains custom validators for the Reporting application."""

# Django Imports
from django.core.validators import FileExtensionValidator


def validate_evidence_extension(value):
    """
    Enforce a limited allowlist for filetypes. Allowed filetypes are limited to
    text and image files that will work for report documents.
    """
    allowlist = ["txt", "md", "log", "jpg", "jpeg", "png"]
    return FileExtensionValidator(allowed_extensions=allowlist)(value)
