from django.db import models

from tinymce.models import HTMLField


class Oplog(models.Model):
    name = models.CharField(max_length=50)
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project that will own this oplog"
    )

    class Meta:
        unique_together = ["name", "project"]

    def __str__(self):
        return f'{self.name} : {self.project}'


# Create your models here.
class OplogEntry(models.Model):
    """
    A model representing a single entry in the operational log. This
    represents a single action taken by an operator in a target network.
    """
    oplog_id = models.ForeignKey(
        'Oplog',
        on_delete=models.CASCADE,
        null=True,
        help_text="Select which log to which this entry will be inserted."
    )
    start_date = models.DateTimeField(auto_now_add=True)
    end_date = models.DateTimeField(auto_now_add=True)
    source_ip = models.CharField(
        'Source IP / Hostname',
        blank=True,
        help_text="Provide the source hostname / IP from which the command originated.",
        max_length=50,
    )

    dest_ip = models.CharField(
        'Destination IP/Hostname',
        blank=True,
        help_text="Provide the destination hostname / ip on which the command was ran.",
        max_length=50,
    )

    tool = models.CharField(
        'Tool name',
        blank=True,
        help_text="The tool used to execute the action",
        max_length=50,
    )

    user_context = models.CharField(
        'User Context',
        blank=True,
        help_text='The user context that executed the command',
        max_length=50,
    )
    
    command = models.CharField(
        'Command',
        blank=True,
        help_text='The command that was executed',
        max_length=50,
    )

    description = models.CharField(
        'Description',
        blank=True,
        help_text='A description of why the command was executed and expected results.',
        max_length=50,
    )

    output = HTMLField(
        'Output',
        null=True,
        blank=True,
        help_text='The output of the executed command',
    )

    comments = models.CharField(
        'Comments',
        blank=True,
        help_text='Any additional comments or useful information.',
        max_length=50,
    )

    operator_name = models.CharField(
        'Operator',
        blank=True,
        help_text='The operator that performed the action.',
        max_length=50,
    )

