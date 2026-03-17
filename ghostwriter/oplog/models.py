"""This contains all the database models used by the Oplog application."""

# Standard Libraries
import logging
import os
from datetime import datetime

# Django Imports
from django import forms
from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models
from django.urls import reverse

# 3rd Party Libraries
from taggit.managers import TaggableManager

from ghostwriter.reporting.models import Evidence
from ghostwriter.rolodex.models import Project

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

    @classmethod
    def user_can_create(cls, user, project: Project) -> bool:
        return project.user_can_edit(user)

    def user_can_view(self, user) -> bool:
        return self.project.user_can_view(user)

    @classmethod
    def user_viewable(cls, user):
        if user.is_privileged:
            return cls.objects.all()
        return cls.objects.filter(project__in=Project.user_viewable(user))

    def user_can_edit(self, user) -> bool:
        return self.project.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.project.user_can_edit(user)

    @classmethod
    def for_user(cls, user):
        return cls.user_viewable(user)


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

    @classmethod
    def user_can_create(cls, user, log: Oplog) -> bool:
        return log.user_can_edit(user)

    def user_can_view(self, user) -> bool:
        return self.oplog_id.user_can_view(user)

    @classmethod
    def user_viewable(cls, user):
        if user.is_privileged:
            return cls.objects.all()
        return cls.objects.filter(oplog_id__in=Oplog.user_viewable(user))

    def user_can_edit(self, user) -> bool:
        return self.oplog_id.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.oplog_id.user_can_edit(user)

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


class OplogEntryEvidence(models.Model):
    """Links an :model:`oplog.OplogEntry` to a :model:`reporting.Evidence` file."""

    oplog_entry = models.ForeignKey(
        OplogEntry,
        on_delete=models.CASCADE,
        related_name="evidence_links",
        help_text="The oplog entry this evidence is attached to.",
    )
    evidence = models.ForeignKey(
        Evidence,
        on_delete=models.CASCADE,
        related_name="oplog_entry_links",
        help_text="The evidence file linked to this oplog entry.",
    )

    class Meta:
        unique_together = ["oplog_entry", "evidence"]
        verbose_name = "Oplog entry evidence link"
        verbose_name_plural = "Oplog entry evidence links"
        ordering = ["-id"]

    def __str__(self):
        return f"{self.oplog_entry} <-> {self.evidence}"

    def user_can_view(self, user) -> bool:
        return self.oplog_entry.user_can_view(user)

    def user_can_edit(self, user) -> bool:
        return self.oplog_entry.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.oplog_entry.user_can_edit(user)


def set_recording_upload_destination(instance, filename):
    """Sets the ``upload_to`` destination for recordings under the associated project ID."""
    return os.path.join("recordings", str(instance.oplog_entry.oplog_id.project_id), filename)


class OplogEntryRecording(models.Model):
    """Stores an Asciinema terminal recording for an individual :model:`oplog.OplogEntry`."""

    oplog_entry = models.OneToOneField(
        OplogEntry,
        on_delete=models.CASCADE,
        related_name="recording",
        help_text="The oplog entry this recording is attached to.",
    )
    recording_file = models.FileField(
        upload_to=set_recording_upload_destination,
        max_length=255,
    )
    uploaded_date = models.DateTimeField(
        "Upload Date",
        auto_now_add=True,
        help_text="Date and time the recording was uploaded.",
    )
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="The user who uploaded this recording.",
    )

    class Meta:
        ordering = ["-uploaded_date"]
        verbose_name = "Oplog entry recording"
        verbose_name_plural = "Oplog entry recordings"

    def __str__(self):
        return f"Recording for entry {self.oplog_entry_id}"

    @property
    def filename(self):
        return os.path.basename(self.recording_file.name)

    def user_can_view(self, user) -> bool:
        return self.oplog_entry.user_can_view(user)

    def user_can_edit(self, user) -> bool:
        return self.oplog_entry.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.oplog_entry.user_can_edit(user)
