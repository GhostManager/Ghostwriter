"""This contains all of the database models used by the Rolodex application."""

from django.conf import settings
from django.db import models
from django.urls import reverse
from tinymce.models import HTMLField

from ghostwriter.reporting.models import ReportFindingLink


class Client(models.Model):
    """
    Stores an individual client.
    """

    name = models.CharField(
        "Client Name",
        max_length=100,
        unique=True,
        help_text="Provide the client's full name as you would want it to appear in a report",
    )
    short_name = models.CharField(
        "Client Short Name",
        max_length=100,
        null=True,
        blank=True,
        help_text="Provide an abbreviation, or short name, that can be used to refer to this client",
    )
    codename = models.CharField(
        "Client Codename",
        max_length=100,
        null=True,
        blank=True,
        help_text="A codename for the client that might be used to discuss the client in public",
    )
    note = models.TextField(
        "Client Note",
        max_length=1000,
        null=True,
        blank=True,
        help_text="Use this field to describe the client or provide some additional information",
    )

    class Meta:
        ordering = ["name"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def get_absolute_url(self):
        return reverse("rolodex:client_detail", args=[str(self.id)])

    def __str__(self):
        return self.name


class ClientContact(models.Model):
    """
    Stores an individual point of contact, related to :model:`rolodex.Client`.
    """

    name = models.CharField(
        "Name", max_length=100, help_text="Enter the contact's full name", null=True
    )
    job_title = models.CharField(
        "Title or Role",
        max_length=100,
        null=True,
        help_text="Enter the contact's job title or role in the project - "
        "this will appear in reports",
    )
    email = models.CharField(
        "Email",
        max_length=100,
        null=True,
        blank=True,
        help_text="Enter an email address for this contact",
    )
    phone = models.CharField(
        "Phone",
        max_length=100,
        null=True,
        blank=True,
        help_text="Enter a phone number for the contact",
    )
    note = models.TextField(
        "Client Note",
        max_length=500,
        null=True,
        blank=True,
        help_text="Use this field to provide additional information about the contact "
        "like their availability or more information about their role",
    )
    # Foreign keys
    client = models.ForeignKey(
        Client, on_delete=models.CASCADE, null=False, blank=False
    )

    class Meta:

        ordering = ["client", "id"]
        verbose_name = "Client POC"
        verbose_name_plural = "Client POCs"

    def __str__(self):
        return f"{self.name} ({self.client})"


class ProjectType(models.Model):
    """
    Stores an individual project type, related to :model:`rolodex.Project`.
    """

    project_type = models.CharField(
        "Project Type",
        max_length=100,
        unique=True,
        help_text="Enter a project type (e.g. red team, penetration test)",
    )

    class Meta:

        ordering = ["project_type"]
        verbose_name = "Project type"
        verbose_name_plural = "Project types"

    def __str__(self):
        return self.project_type


class Project(models.Model):
    """
    Stores an individual project, related to :model:`rolodex.Client`,
    :model:`rolodex.ProjectType`, and :model:`users.User`.
    """

    codename = models.CharField(
        "Project Codename",
        max_length=100,
        null=True,
        blank=True,
        help_text="Create a codename for this project that might be used to refer to it in public",
    )
    start_date = models.DateField(
        "Start Date", max_length=100, help_text="Enter the start date of this project"
    )
    end_date = models.DateField(
        "End Date", max_length=100, help_text="Enter the end date of this project"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide any additional notes about this project that should be recorded",
    )
    slack_channel = models.CharField(
        "Project Slack Channel",
        max_length=100,
        null=True,
        blank=True,
        help_text="Provide an (optional) Slack channel to be used for notifications related to this project",
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark this project as complete/closed"
    )
    # Foreign keys
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client this project should be attached to",
    )
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    project_type = models.ForeignKey(
        "ProjectType",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select a category for this project that best describes the work being performed",
    )

    def count_findings(self):
        """
        Count and return the number of findings across all reports associated with
        an individual :model:`rolodex.Project`.
        """
        finding_queryset = ReportFindingLink.objects.select_related(
            "report", "report__project"
        ).filter(report__project=self.pk)
        return finding_queryset.count()

    count = property(count_findings)

    class Meta:

        ordering = ["client", "start_date", "project_type", "codename"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def get_absolute_url(self):
        return reverse("rolodex:project_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.start_date} {self.client} {self.project_type} ({self.codename})"


class ProjectRole(models.Model):
    """
    Stores an individual project role.
    """

    project_role = models.CharField(
        "Project Role", max_length=100, unique=True, help_text="Enter an operator role"
    )

    class Meta:

        ordering = ["project_role"]
        verbose_name = "Project role"
        verbose_name_plural = "Project roles"

    def __str__(self):
        return self.project_role


class ProjectAssignment(models.Model):
    """
    Stores an individual project assignment, related to :model:`users.User`,
    :model:`rolodex.Project`, and :model:`rolodex.ProjectRole`.
    """

    start_date = models.DateField(
        "Start Date",
        max_length=100,
        blank=True,
        help_text="Enter the start date of the project",
    )
    end_date = models.DateField(
        "End Date",
        max_length=100,
        blank=True,
        help_text="Enter the end date of the project",
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to provide any additional notes about this assignment",
    )
    # Foreign keys
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a user to assign to this project",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select a role that best describes the selected user's role in this project",
    )

    class Meta:

        ordering = ["project", "start_date", "operator"]
        verbose_name = "Project assignment"
        verbose_name_plural = "Project assignments"

    def save(self, *args, **kwargs):
        if self.start_date < self.project.start_date:
            self.start_date = self.project.start_date
        elif self.end_date > self.project.end_date:
            self.end_date = self.project.end_date
        super(ProjectAssignment, self).save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse("rolodex:project_detail", args=[str(self.project.id)])

    def __str__(self):
        return f"{self.operator} - {self.project} {self.end_date})"


class ObjectiveStatus(models.Model):
    """
    Stores an individual objective status.
    """

    objective_status = models.CharField(
        "Objective Status",
        max_length=100,
        unique=True,
        help_text="Enter an objective status (e.g. Active, On Hold)",
    )

    class Meta:

        ordering = ["objective_status"]
        verbose_name = "Objective status"
        verbose_name_plural = "Objective statuses"

    def __str__(self):
        return self.objective_status


class ProjectObjective(models.Model):
    """
    Stores an individual project objective, related to :model:`rolodex.Project` and :model:`rolodex.ObjectiveStatus`.
    """

    def get_status():
        """Get the default status for the status field."""
        active_status = ObjectiveStatus.objects.get(objective_status="Active")
        return active_status

    objective = HTMLField(
        "Objective", null=True, blank=True, help_text="Provide a concise objective"
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark the objective as complete"
    )
    deadline = models.DateField(
        "Due Date",
        max_length=100,
        blank=True,
        help_text="Provide a deadline for this objective",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    status = models.ForeignKey(
        ObjectiveStatus,
        on_delete=models.PROTECT,
        default=get_status,
        help_text="Set the status for this objective",
    )

    class Meta:

        ordering = ["project", "complete", "deadline", "status", "objective"]
        verbose_name = "Project objective"
        verbose_name_plural = "Project objectives"

    def save(self, *args, **kwargs):
        if self.deadline < self.project.start_date:
            self.deadline = self.project.start_date
        elif self.deadline > self.project.end_date:
            self.deadline = self.project.end_date
        super(ProjectObjective, self).save(*args, **kwargs)

    def __str__(self):
        return f"{self.project} - {self.objective} {self.status})"


class ClientNote(models.Model):
    """
    Stores an individual note, related to :model:`rolodex.Client` and :model:`users.User`.
    """

    # This field is automatically filled with the current date
    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, max_length=100, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to add a note to this client - it can be "
        "anything you want others to see/know about the client",
    )
    # Foreign Keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:

        ordering = ["client", "timestamp"]
        verbose_name = "Client note"
        verbose_name_plural = "Client notes"

    def __str__(self):
        return f"{self.client}: {self.timestamp} - {self.note}"


class ProjectNote(models.Model):
    """
    Stores an individual note, related to :model:`rolodex.Project` and :model:`users.User`.
    """

    # This field is automatically filled with the current date
    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, max_length=100, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Use this area to add a note to this project - it can be anything "
        "you want others to see/know about the project",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:

        ordering = ["project", "timestamp"]
        verbose_name = "Project note"
        verbose_name_plural = "Project notes"

    def __str__(self):
        return f"{self.project}: {self.timestamp} - {self.note}"
