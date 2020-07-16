from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from datetime import datetime
from django.core.serializers import serialize
from django.dispatch import receiver
from django.db import models
from django.db.models.signals import post_save, pre_save
from tinymce.models import HTMLField


class Oplog(models.Model):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project that will own this oplog",
    )

    class Meta:
        unique_together = ["name", "project"]

    def __str__(self):
        return f"{self.name} : {self.project}"


# Create your models here.
class OplogEntry(models.Model):
    """
    A model representing a single entry in the operational log. This
    represents a single action taken by an operator in a target network.
    """

    oplog_id = models.ForeignKey(
        "Oplog",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select which log to which this entry will be inserted.",
        related_name="entries",
    )
    start_date = models.DateTimeField(null=True, blank=True)
    end_date = models.DateTimeField(null=True, blank=True)
    source_ip = models.CharField(
        "Source IP / Hostname",
        blank=True,
        help_text="Provide the source hostname / IP from which the command originated.",
        max_length=50,
    )

    dest_ip = models.CharField(
        "Destination IP/Hostname",
        blank=True,
        help_text="Provide the destination hostname / ip on which the command was ran.",
        max_length=50,
    )

    tool = models.CharField("Tool name", blank=True, help_text="The tool used to execute the action", max_length=50,)

    user_context = models.CharField(
        "User Context", blank=True, help_text="The user context that executed the command", max_length=50,
    )

    command = models.CharField("Command", blank=True, help_text="The command that was executed", max_length=50,)

    description = models.CharField(
        "Description",
        blank=True,
        help_text="A description of why the command was executed and expected results.",
        max_length=50,
    )

    output = HTMLField("Output", null=True, blank=True, help_text="The output of the executed command",)

    comments = models.CharField(
        "Comments", blank=True, help_text="Any additional comments or useful information.", max_length=50,
    )

    operator_name = models.CharField(
        "Operator", blank=True, help_text="The operator that performed the action.", max_length=50,
    )


@receiver(pre_save, sender=OplogEntry)
def oplog_pre_save(sender, instance, **kwargs):
    if not instance.start_date:
        instance.start_date = datetime.utcnow()
    if not instance.end_date:
        instance.end_date = datetime.utcnow()


@receiver(post_save, sender=OplogEntry)
def signal_oplog_entry(sender, instance, **kwargs):
    channel_layer = get_channel_layer()
    oplog_id = instance.oplog_id.id
    json_data = serialize("json", [instance,])
    async_to_sync(channel_layer.group_send)(str(oplog_id), {"type": "send_oplog_entry", "text": json_data})
