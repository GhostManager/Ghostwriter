"""This contains all the database models used by the Oplog application."""

# Standard Libraries
import logging
from datetime import datetime

# Django Imports
from django.core.exceptions import ValidationError
from django.db import models

# 3rd Party Libraries
from taggit.managers import TaggableManager

# Using __name__ resolves to ghostwriter.oplog.models
logger = logging.getLogger(__name__)


class Oplog(models.Model):
    """
    Stores an individual operation log.
    """

    name = models.CharField(max_length=255)
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

    def __str__(self):
        return f"{self.name} : {self.project}"


# Create your models here.
class OplogEntry(models.Model):
    """
    Stores an individual log entry, related to :model:`oplog.Oplog`.
    """

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
    source_ip = models.CharField(
        "Source IP / Hostname",
        null=True,
        blank=True,
        help_text="Provide the source hostname / IP from which the command originated.",
        max_length=255,
    )
    dest_ip = models.CharField(
        "Destination IP / Hostname",
        null=True,
        blank=True,
        help_text="Provide the destination hostname / ip on which the command was ran.",
        max_length=255,
    )
    tool = models.CharField(
        "Tool Name",
        null=True,
        blank=True,
        help_text="Name the tool you used to execute the action.",
        max_length=255,
    )
    user_context = models.CharField(
        "User Context",
        null=True,
        blank=True,
        help_text="The user context under which th command executed.",
        max_length=255,
    )
    command = models.TextField(
        "Command",
        null=True,
        blank=True,
        help_text="Provide the command you executed.",
    )
    description = models.TextField(
        "Description",
        null=True,
        blank=True,
        help_text="A description of why you executed the command.",
    )
    output = models.TextField(
        "Output",
        null=True,
        blank=True,
        help_text="The output of the executed command.",
    )
    comments = models.TextField(
        "Comments",
        null=True,
        blank=True,
        help_text="Any additional comments or useful information.",
    )
    operator_name = models.CharField(
        "Operator",
        null=True,
        blank=True,
        help_text="The operator that performed the action.",
        max_length=255,
    )
    tags = TaggableManager(blank=True)
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
