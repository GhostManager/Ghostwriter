"""This contains all the model Signals used by the Reporting application."""

# Standard Libraries
import logging
import os

# Django Imports
from django.db.models.signals import post_delete, post_init, post_save, pre_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter import TemplateLinter
from ghostwriter.reporting.models import (
    Evidence,
    ReportFindingLink,
    ReportTemplate,
    Severity,
)

# Using __name__ resolves to ghostwriter.reporting.signals
logger = logging.getLogger(__name__)


@receiver(post_init, sender=Evidence)
def backup_evidence_values(sender, instance, **kwargs):
    """
    Backup the file path of the old evidence file in the :model:`reporting.Evidence`
    instance when a new file is uploaded and backup the `friendly_name` value.
    """
    instance._current_evidence = instance.document
    instance._current_friendly_name = instance.friendly_name


@receiver(post_save, sender=Evidence)
def evidence_update(sender, instance, **kwargs):
    """
    On change, delete the old evidence file in the :model:`reporting.Evidence` instance when a
    new file is uploaded and update teh related :model:`reporting.ReportFindingLink` instance if
    the `friendly_name` value changed.
    """
    if hasattr(instance, "_current_evidence"):
        if instance._current_evidence:
            if instance._current_evidence.path not in instance.document.path:
                try:
                    os.remove(instance._current_evidence.path)
                    logger.info("Deleted old evidence file %s", instance._current_evidence.path)
                except Exception:  # pragma: no cover
                    logger.exception(
                        "Failed deleting old evidence file: %s",
                        instance._current_evidence.path,
                    )

    if hasattr(instance, "_current_friendly_name"):
        if instance._current_friendly_name != instance.friendly_name:
            ignore = [
                "id",
                "evidence",
                "localfindingnote",
                "complete",
                "report",
                "assigned_to",
                "finding_type",
                "tags",
                "tagged_items",
                "cvss_score",
                "cvss_vector",
                "severity",
                "added_as_blank",
                "position",
                "finding_guidance",
                "title",
            ]
            friendly = f"{{{{.{instance.friendly_name}}}}}"
            friendly_ref = f"{{{{.ref {instance.friendly_name}}}}}"
            prev_friendly = f"{{{{.{instance._current_friendly_name}}}}}"
            prev_friendly_ref = f"{{{{.ref {instance._current_friendly_name}}}}}"
            if friendly_ref != prev_friendly_ref:
                logger.info(
                    "Updating content of ReportFindingLink instances with updated name for Evidence %s", instance.id
                )
                try:
                    link = ReportFindingLink.objects.get(id=instance.finding.id)
                    for field in link._meta.get_fields():
                        if field.name not in ignore:
                            current = getattr(link, field.name)
                            if current:
                                new = current.replace(prev_friendly, friendly)
                                new = new.replace(prev_friendly_ref, friendly_ref)
                                setattr(link, field.name, new)
                    link.save()
                except ReportFindingLink.DoesNotExist:
                    logger.exception("Could not find ReportFindingLink for Evidence %s", instance.id)


@receiver(post_delete, sender=Evidence)
def remove_evidence_on_delete(sender, instance, **kwargs):
    """Deletes file from filesystem when related :model:`reporting.Evidence` entry is deleted."""
    if instance.document:
        if os.path.isfile(instance.document.path):
            try:
                os.remove(instance.document.path)
                logger.info("Deleted report template at %s", instance.document.path)
            except Exception:  # pragma: no cover
                logger.warning(
                    "Failed to delete file associated with %s %s: %s",
                    instance.__class__.__name__,
                    instance.id,
                    instance.document.path,
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
                        except Exception:  # pragma: no cover
                            logger.exception(
                                "Failed to delete old template file: %s",
                                instance._current_template.path,
                            )
                    else:  # pragma: no cover
                        logger.warning(
                            "Old template file could not be found at %s",
                            instance._current_template.path,
                        )
                except Exception:  # pragma: no cover
                    logger.exception(
                        "Failed deleting old template file: %s",
                        instance._current_template.path,
                    )
        else:  # pragma: no cover
            logger.info("Template file paths match, so will not re-run the linter or delete any files")

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
            linter = TemplateLinter(template=instance)
            if instance.doc_type.doc_type == "docx":
                results = linter.lint_docx()
            elif instance.doc_type.doc_type == "pptx":
                results = linter.lint_pptx()
            else:  # pragma: no cover
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
        except Exception:  # pragma: no cover
            logger.exception("Failed to update new template with linting results")


@receiver(post_delete, sender=ReportTemplate)
def remove_template_on_delete(sender, instance, **kwargs):
    """Deletes file from filesystem when related :model:`reporting.ReportTemplate` entry is deleted."""
    if instance.document:
        if os.path.isfile(instance.document.path):
            try:
                os.remove(instance.document.path)
                logger.info("Deleted report template at %s", instance.document.path)
            except Exception:  # pragma: no cover
                logger.warning(
                    "Failed to delete file associated with %s %s: %s",
                    instance.__class__.__name__,
                    instance.id,
                    instance.document.path,
                )


@receiver(pre_save, sender=Severity)
def adjust_severity_weight_with_changes(sender, instance, **kwargs):
    """
    Execute the :model:`reporting.Severity` ``clean()`` function prior to ``save()``
    to adjust the ``weight`` values of entries.
    """
    instance.clean()


@receiver(post_delete, sender=Severity)
def adjust_severity_weight_after_delete(sender, instance, **kwargs):
    """
    After deleting a :model:`reporting.Severity` entry, adjust the ``weight`` values
    of entries.
    """
    severity_queryset = Severity.objects.all()
    if severity_queryset:
        counter = 1
        for category in severity_queryset:
            # Adjust weight to close gap created by the removed severity category
            severity_queryset.filter(id=category.id).update(weight=counter)
            counter += 1
