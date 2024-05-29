"""This contains all the database models used by the Oplog application."""

# Standard Libraries
import logging
from datetime import datetime

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

# 3rd Party Libraries
from taggit.managers import TaggableManager

# Using __name__ resolves to ghostwriter.oplog.models
logger = logging.getLogger(__name__)


class NoLengthLimitCharField(models.TextField):
    def formfield(self, **kwargs):
        kwargs["widget"] = forms.TextInput
        return super().formfield(**kwargs)


class Oplog(models.Model):
    """Stores an individual operation log."""

    name = NoLengthLimitCharField()
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project that will own this oplog",
    )
    mute_notifications = models.BooleanField(
        default=False,
        help_text="Mute activity monitoring notifications for this log",
    )

    class Meta:
        unique_together = ["name", "project"]
        ordering = ["id", "project", "name"]
        verbose_name = "Activity log"
        verbose_name_plural = "Activity logs"

    def __str__(self):
        return f"{self.name} : {self.project}"

    def get_absolute_url(self):
        return reverse("oplog:oplog_entries", args=[str(self.id)])


class OplogEntry(models.Model):
    """Stores an individual log entry, related to :model:`oplog.Oplog`."""

    entry_identifier = models.CharField(
        "Identifier",
        default="",
        blank=True,
        help_text="Integrations may use this to track log entries.",
        max_length=65535,
    )
    start_date = models.DateTimeField(
        "Start Date",
        null=True,
        blank=True,
        help_text="Provide the date and time the action began.",
    )
    end_date = models.DateTimeField(
        "End Date",
        null=True,
        blank=True,
        help_text="Provide the date and time the action concluded.",
    )
    source_ip = NoLengthLimitCharField(
        "Source IP / Hostname",
        null=True,
        blank=True,
        help_text="Provide the source hostname / IP from which the command originated.",
    )
    dest_ip = NoLengthLimitCharField(
        "Destination IP / Hostname",
        null=True,
        blank=True,
        help_text="Provide the destination hostname / ip on which the command was ran.",
    )
    tool = NoLengthLimitCharField(
        "Tool Name",
        null=True,
        blank=True,
        help_text="Name the tool you used to execute the action.",
    )
    user_context = NoLengthLimitCharField(
        "User Context",
        null=True,
        blank=True,
        help_text="The user context under which the command executed.",
    )
    command = models.TextField(
        "Command",
        default="",
        blank=True,
        help_text="Provide the command you executed.",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="A description of why you executed the command.",
    )
    output = models.TextField(
        "Output",
        default="",
        blank=True,
        help_text="The output of the executed command.",
    )
    comments = models.TextField(
        "Comments",
        default="",
        blank=True,
        help_text="Any additional comments or useful information.",
    )
    operator_name = NoLengthLimitCharField(
        "Operator",
        null=True,
        blank=True,
        help_text="The operator that performed the action.",
    )
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)

    # Foreign Keys
    oplog_id = models.ForeignKey(
        "Oplog",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the log to which this entry will be inserted.",
        related_name="entries",
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Stash the initial date values for future operations
        self.initial_start_date = self.start_date
        self.initial_end_date = self.end_date

    class Meta:
        ordering = ["-start_date", "-end_date", "oplog_id"]
        verbose_name = "Activity log entry"
        verbose_name_plural = "Activity log entries"
        indexes = [
            models.Index(fields=["oplog_id", "entry_identifier"]),
        ]

    def clean(self, *args, **kwargs):
        if isinstance(self.start_date, str):
            try:
                self.start_date = datetime.strptime(self.start_date, "%Y-%m-%d %H:%M:%S")
            except ValidationError:
                logger.exception("Received an invalid time value: %s", self.start_date)
                self.start_date = self.initial_start_date
            except ValueError:
                logger.exception("Received an incomplete time value: %s", self.start_date)
                self.start_date = self.initial_start_date

        if isinstance(self.end_date, str):
            try:
                self.end_date = datetime.strptime(self.end_date, "%Y-%m-%d %H:%M:%S")
            except ValidationError:
                logger.exception("Received an invalid time value: %s", self.end_date)
                self.end_date = self.initial_end_date
            except ValueError:
                logger.exception("Received an incomplete time value: %s", self.end_date)
                self.end_date = self.initial_end_date
        super().clean(*args, **kwargs)
