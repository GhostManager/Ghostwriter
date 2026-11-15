"""This contains custom validators for the Reporting application."""

# Django Imports
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator

# 3rd Party Libraries
from PIL import Image, UnidentifiedImageError

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


def validate_edited_evidence_image(upload):
    """
    Validate a staged edited image and return its verified PNG or JPEG format.
    """
    if upload.size > settings.GHOSTWRITER_MAX_FILE_SIZE:
        raise ValidationError(
            "The image exceeds the upload size limit.", code="file_too_large"
        )
    try:
        with Image.open(upload) as image:
            image_format = image.format
            image.verify()
    except (
        UnidentifiedImageError,
        Image.DecompressionBombError,
        OSError,
        SyntaxError,
        ValueError,
    ) as error:
        raise ValidationError(
            "The uploaded file is not a valid image.", code="invalid_image"
        ) from error
    finally:
        upload.seek(0)
    if image_format not in {"PNG", "JPEG"}:
        raise ValidationError(
            "Images must be PNG or JPEG files.", code="invalid_image_format"
        )
    return image_format
