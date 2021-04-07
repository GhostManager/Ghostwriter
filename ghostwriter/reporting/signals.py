"""This contains all of the model Signals used by the Reporting application."""

# Standard Libraries
import logging
import os

# Django Imports
from django.db.models.signals import post_init, post_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter import TemplateLinter
from ghostwriter.reporting.models import Evidence, ReportTemplate

# Using __name__ resolves to ghostwriter.reporting.signals
logger = logging.getLogger(__name__)


@receiver(post_init, sender=Evidence)
def backup_evidence_path(sender, instance, **kwargs):
    """
    Backup the file path of the old evidence file in the :model:`reporting.Evidence`
    instance when a new file is uploaded.
    """
    instance._current_evidence = instance.document


@receiver(post_save, sender=Evidence)
def delete_old_evidence(sender, instance, **kwargs):
    """
    Delete the old evidence file in the :model:`reporting.Evidence` instance when a
    new file is uploaded.
    """
    if hasattr(instance, "_current_evidence"):
        if instance._current_evidence:
            if instance._current_evidence.path not in instance.document.path:
                try:
                    os.remove(instance._current_evidence.path)
                    logger.info(
                        "Deleted old evidence file %s", instance._current_evidence.path
                    )
                except Exception:
                    logger.exception(
                        "Failed deleting old evidence file: %s",
                        instance._current_evidence.path,
                    )


@receiver(post_init, sender=ReportTemplate)
def backup_template_attr(sender, instance, **kwargs):
    """
    Backup the file path and document type of the old template file in the
    :model:`reporting.ReportTemplate` instance when a new file is uploaded.
    """
    instance._current_template = instance.document
    instance._current_type = instance.doc_type


@receiver(post_save, sender=ReportTemplate)
def clean_template(sender, instance, created, **kwargs):
    """
    Delete the old template file and lint the replacement file for an instance of
    :model:`reporting.ReportTemplate`.
    """
    lint_template = False
    if hasattr(instance, "_current_template"):
        if instance._current_template:
            if instance._current_template.path not in instance.document.path:
                lint_template = True
                try:
                    if os.path.exists(instance._current_template.path):
                        try:
                            os.remove(instance._current_template.path)
                            logger.info(
                                "Deleted old template file %s",
                                instance._current_template.path,
                            )
                        except Exception:
                            logger.exception(
                                "Failed to delete old template file: %s",
                                instance._current_template.path,
                            )
                    else:
                        logger.warning(
                            "Old template file could not be found at %s",
                            instance._current_template.path,
                        )
                except Exception:
                    logger.exception(
                        "Failed deleting old template file: %s",
                        instance._current_template.path,
                    )
        else:
            logger.info(
                "Template file paths match, so will not re-run the linter or delete any files"
            )

    if hasattr(instance, "_current_type"):
        if instance._current_type != instance.doc_type:
            lint_template = True

    if created or lint_template:
        logger.info("Template file change detected, so starting linter")
        logger.info(
            "Linting newly uploaded template: %s",
            instance.document.path,
        )
        try:
            template_loc = instance.document.path
            linter = TemplateLinter(template_loc=template_loc)
            if instance.doc_type.doc_type == "docx":
                results = linter.lint_docx()
            elif instance.doc_type.doc_type == "pptx":
                results = linter.lint_pptx()
            else:
                logger.warning(
                    "Template had an unknown filetype not supported by the linter: %s",
                    instance.doc_type,
                )
                results = {}
            instance.lint_result = results
            # Disconnect signal to save model and avoid infinite loop
            post_save.disconnect(clean_template, sender=ReportTemplate)
            instance.save()
            post_save.connect(clean_template, sender=ReportTemplate)
        except Exception:
            logger.exception("Failed to update new template with linting results")
