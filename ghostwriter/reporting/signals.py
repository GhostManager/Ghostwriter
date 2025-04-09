"""This contains all the model Signals used by the Reporting application."""

# Standard Libraries
import logging
import os

# Django Imports
from django.db.models.signals import post_delete, post_init, post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.reporting.models import (
    ReportTemplate,
    Severity,
)

# Using __name__ resolves to ghostwriter.reporting.signals
logger = logging.getLogger(__name__)


@receiver(post_init, sender=ReportTemplate)
def backup_template_attr(sender, instance, **kwargs):
    """
    Backup the file path and document type of the old template file in the
    :model:`reporting.ReportTemplate` instance when a new file is uploaded.
    """
    instance._current_template = instance.document
    instance._current_type = instance.doc_type


@receiver(pre_save, sender=ReportTemplate)
def update_upload_date(sender, instance, **kwargs):
    if instance.pk:
        try:
            old_instance = ReportTemplate.objects.get(pk=instance.pk)
            # Use name/path comparison instead of direct object comparison
            if old_instance.document.name != instance.document.name:
                instance.upload_date = timezone.now().date()
        except (ReportTemplate.DoesNotExist, ValueError):
            # Handle case where instance exists but has no previous document
            instance.upload_date = timezone.now().date()
    else:
        # New instance, set the upload_date
        instance.upload_date = timezone.now().date()


@receiver(post_save, sender=ReportTemplate)
def clean_template(sender, instance, created, **kwargs):
    """
    Delete the old template file and lint the replacement file for an instance of
    :model:`reporting.ReportTemplate`.
    """
    should_lint_template = False
    if hasattr(instance, "_current_template"):
        if instance._current_template:
            if instance._current_template.path not in instance.document.path:
                should_lint_template = True
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
            should_lint_template = True

    if created or should_lint_template:
        logger.info("Template file change detected, so starting linter")
        logger.info(
            "Linting newly uploaded template: %s",
            instance.document.path,
        )

        try:
            instance.lint()

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
