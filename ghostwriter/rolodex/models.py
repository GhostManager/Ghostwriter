"""This contains all of the database models used by the Rolodex application."""

# Django Imports
from django.conf import settings
from django.db import models
from django.urls import reverse

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink


class Client(models.Model):
    """
    Stores an individual client.
    """

    name = models.CharField(
        "Client Name",
        max_length=255,
        unique=True,
        help_text="Provide the client's full name as you want it to appear in a report",
    )
    short_name = models.CharField(
        "Client Short Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide an abbreviated name to be used in reports",
    )
    codename = models.CharField(
        "Client Codename",
        max_length=255,
        null=True,
        blank=True,
        help_text="Give the client a codename (might be a ticket number, CMS reference, or something else)",
    )
    note = models.TextField(
        "Client Note",
        null=True,
        blank=True,
        help_text="Describe the client or provide some additional information",
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
        "Name", help_text="Enter the contact's full name", max_length=255, null=True
    )
    job_title = models.CharField(
        "Title or Role",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the contact's job title or project role as you want it to appear in a report",
    )
    email = models.CharField(
        "Email",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter an email address for this contact",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would involve human involvement
    # The `max_length` allows for people adding spaces, other chars, and extension numbers
    phone = models.CharField(
        "Phone",
        max_length=50,
        null=True,
        blank=True,
        help_text="Enter a phone number for this contact",
    )
    note = models.TextField(
        "Client Note",
        null=True,
        blank=True,
        help_text="Provide additional information about the contact",
    )
    # Foreign keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False, blank=False)

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
        max_length=255,
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
        max_length=255,
        null=True,
        blank=True,
        help_text="Give the project a codename (might be a ticket number, PMO reference, or something else)",
    )
    start_date = models.DateField(
        "Start Date", max_length=12, help_text="Enter the start date of this project"
    )
    end_date = models.DateField(
        "End Date", max_length=12, help_text="Enter the end date of this project"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Provide additional information about the project and planning",
    )
    slack_channel = models.CharField(
        "Project Slack Channel",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide an Slack channel to be used for project notifications",
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark this project as complete"
    )
    # Foreign keys
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client to which this project should be attached",
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

        ordering = ["start_date", "end_date", "client", "project_type"]
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
        "Project Role",
        max_length=255,
        unique=True,
        help_text="Enter an operator role used for project assignments",
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
        null=True,
        blank=True,
        help_text="Enter the start date of the project",
    )
    end_date = models.DateField(
        "End Date",
        null=True,
        blank=True,
        help_text="Enter the end date of the project",
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Provide additional information about the project role and assignment",
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
        max_length=255,
        unique=True,
        help_text="Objective's status",
    )

    class Meta:

        ordering = ["objective_status"]
        verbose_name = "Objective status"
        verbose_name_plural = "Objective status"

    def __str__(self):
        return self.objective_status


class ObjectivePriority(models.Model):
    """
    Stores an individual objective priority category.
    """

    weight = models.IntegerField(
        "Priority Weight",
        default=1,
        help_text="Weight for sorting this priority when viewing objectives (lower numbers are higher priority)",
    )
    priority = models.CharField(
        "Objective Priority",
        max_length=255,
        unique=True,
        help_text="Objective's priority",
    )

    class Meta:

        ordering = ["weight", "priority"]
        verbose_name = "Objective priority"
        verbose_name_plural = "Objective priorities"

    def __str__(self):
        return self.priority


class ProjectObjective(models.Model):
    """
    Stores an individual project objective, related to an individual :model:`rolodex.Project`
    and :model:`rolodex.ObjectiveStatus`.
    """

    def get_status():
        """Get the default status for the status field."""
        try:
            active_status = ObjectiveStatus.objects.get(objective_status="Active")
            return active_status.id
        except ObjectiveStatus.DoesNotExist:
            return 1

    objective = models.CharField(
        "Objective",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide a high-level objective – add sub-tasks later for planning or as you discover obstacles",
    )
    description = models.TextField(
        "Description",
        null=True,
        blank=True,
        help_text="Provide a more detailed description, purpose, or context",
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark the objective as complete"
    )
    deadline = models.DateField(
        "Due Date",
        max_length=12,
        null=True,
        blank=True,
        help_text="Objective's deadline/due date",
    )
    marked_complete = models.DateField(
        "Marked Complete",
        null=True,
        blank=True,
        help_text="Date the objective was marked complete",
    )
    position = models.IntegerField(
        "List Position",
        default=1,
    )
    # Foreign Keys
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=False,
    )
    status = models.ForeignKey(
        ObjectiveStatus,
        on_delete=models.PROTECT,
        default=get_status,
        help_text="Set the status for this objective",
    )
    priority = models.ForeignKey(
        ObjectivePriority,
        on_delete=models.PROTECT,
        null=True,
        help_text="Assign a priority category",
    )

    class Meta:

        ordering = [
            "project",
            "position",
            "complete",
            "priority__weight",
            "deadline",
            "status",
            "objective",
        ]
        verbose_name = "Project objective"
        verbose_name_plural = "Project objectives"

    def __str__(self):
        return f"{self.project} - {self.objective} {self.status})"

    def calculate_status(self):
        """
        Calculate and return a percentage complete estimate based on ``complete`` value
        and any status of related :model:`ProjectSubTask` entries.
        """
        total_tasks = self.projectsubtask_set.all().count()
        completed_tasks = 0
        if self.complete:
            return 100.0
        elif total_tasks > 0:
            for task in self.projectsubtask_set.all():
                if task.complete:
                    completed_tasks += 1
            return round(completed_tasks / total_tasks * 100, 1)
        else:
            return 0


class ProjectSubTask(models.Model):
    """
    Stores an individual sub-task, related to an individual :model:`rolodex.ProjectObjective`
    and :model:`rolodex.ObjectiveStatus`.
    """

    def get_status():
        """Get the default status for the status field."""
        try:
            active_status = ObjectiveStatus.objects.get(objective_status="Active")
            return active_status.id
        except ObjectiveStatus.DoesNotExist:
            return 1

    task = models.TextField(
        "Task", null=True, blank=True, help_text="Provide a concise objective"
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark the objective as complete"
    )
    deadline = models.DateField(
        "Due Date",
        max_length=12,
        null=True,
        blank=True,
        help_text="Provide a deadline for this objective",
    )
    marked_complete = models.DateField(
        "Marked Complete",
        null=True,
        blank=True,
        help_text="Date the task was marked complete",
    )
    # Foreign Keys
    parent = models.ForeignKey(ProjectObjective, on_delete=models.CASCADE, null=False)
    status = models.ForeignKey(
        ObjectiveStatus,
        on_delete=models.PROTECT,
        default=get_status,
        help_text="Set the status for this objective",
    )

    class Meta:

        ordering = ["parent", "complete", "deadline", "status", "task"]
        verbose_name = "Objective sub-task"
        verbose_name_plural = "Objective sub-tasks"

    def __str__(self):
        return f"{self.parent.project} : {self.task} ({self.status})"


class ClientNote(models.Model):
    """
    Stores an individual note, related to an individual :model:`rolodex.Client` and :model:`users.User`.
    """

    # This field is automatically filled with the current date
    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Leave the client or related projects",
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
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Leave a note about the project or related client",
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


class ProjectScope(models.Model):
    """
    Stores an individual scope list, related to an indiviudal :model:`rolodex.Project`.
    """

    name = models.CharField(
        "Scope Name",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide a descriptive name for this list (e.g., External IPs, Cardholder Data Environment)",
    )
    scope = models.TextField(
        "Scope",
        null=True,
        blank=True,
        help_text="Provide a list of IP addresses, ranges, hostnames, or a mix with each entry on a new line",
    )
    description = models.TextField(
        "Description",
        null=True,
        blank=True,
        help_text="Provide a brief description of this list",
    )
    disallowed = models.BooleanField(
        "Disallowed",
        default=False,
        help_text="Flag this list as off limits / not to be touched",
    )
    requires_caution = models.BooleanField(
        "Requires Caution",
        default=False,
        help_text="Flag this list as requiring caution or prior warning before testing",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:

        ordering = ["project", "name"]
        verbose_name = "Project scope list"
        verbose_name_plural = "Project scope lists"

    def __str__(self):
        return f"{self.project}: {self.name}"

    def count_lines(self):
        """Returns the number of lines in the scope list."""
        count = 0
        for line in self.scope.splitlines():
            count += 1
        return count

    def count_lines_str(self):
        """Returns the number of lines in the scope list as a string."""
        count = 0
        for line in self.scope.splitlines():
            count += 1
        if count > 1:
            return f"{count} Lines"
        else:
            return f"{count} Line"


class ProjectTarget(models.Model):
    """
    Stores an individual target host, related to an indiviudal :model:`rolodex.Project`.
    """

    ip_address = models.GenericIPAddressField(
        "IP Address",
        max_length=255,
        null=True,
        blank=True,
        help_text="Enter the target's IP address",
    )
    hostname = models.CharField(
        "Hostname / FQDN",
        max_length=255,
        null=True,
        blank=True,
        help_text="Provide the target's hostname or fully qualified domain name",
    )
    note = models.TextField(
        "Scope",
        null=True,
        blank=True,
        help_text="Provide a list of IP addresses, ranges, hostnames, or a mix with each entry on a new line",
    )
    compromised = models.BooleanField(
        "Compromised", default=False, help_text="Flag this host as compromised"
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:

        ordering = ["project", "compromised", "ip_address", "hostname"]
        verbose_name = "Project target"
        verbose_name_plural = "Project targets"

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"

    # Link to Oplog
    # Link to Obj
    # Link to open port/service
