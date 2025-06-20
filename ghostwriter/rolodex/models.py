"""This contains all the database models used by the Rolodex application."""

# Standard Libraries
from datetime import time, timedelta

# Django Imports
from django.conf import settings
from django.contrib.auth import get_user_model
from django.db import models
from django.urls import reverse
from django.db.models import Q

# 3rd Party Libraries
from taggit.managers import TaggableManager
from timezone_field import TimeZoneField

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink
from ghostwriter.rolodex.validators import validate_ip_range

User = get_user_model()


class Client(models.Model):
    """Stores an individual client."""

    name = models.CharField(
        "Client Name",
        max_length=255,
        unique=True,
        help_text="Provide the client's full name as you want it to appear in a report",
    )
    short_name = models.CharField(
        "Client Short Name",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide an abbreviated name to be used in reports",
    )
    codename = models.CharField(
        "Client Codename",
        max_length=255,
        default="",
        blank=True,
        help_text="Give the client a codename (might be a ticket number, CMS reference, or something else)",
    )
    note = models.TextField(
        "Client Note",
        default="",
        blank=True,
        help_text="Describe the client or provide some additional information",
    )
    timezone = TimeZoneField(
        "Client Timezone",
        default="America/Los_Angeles",
        help_text="Primary timezone of the client",
    )
    address = models.TextField(
        "Client Business Address",
        default="",
        blank=True,
        help_text="An address to be used for reports or shipping",
    )
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ["name"]
        verbose_name = "Client"
        verbose_name_plural = "Clients"

    def get_absolute_url(self):
        return reverse("rolodex:client_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"

    @classmethod
    def for_user(cls, user):
        """
        Retrieve a filtered list of :model:`rolodex.Client` entries based on the user's role.

        Privileged users will receive all entries. Non-privileged users will receive only those entries to which they
        have access.
        """
        if user.is_privileged:
            return cls.objects.all().order_by("name")
        return (
            cls.objects.filter(
                Q(clientinvite__user=user)
                | Q(project__projectinvite__user=user)
                | Q(project__projectassignment__operator=user)
            )
            .order_by("name")
            .distinct()
        )

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged

    def user_can_view(self, user) -> bool:
        return self in self.for_user(user)

    def user_can_edit(self, user) -> bool:
        return self.user_can_view(user)

    def user_can_delete(self, user) -> bool:
        return self.user_can_view(user)


class ClientContact(models.Model):
    """Stores an individual point of contact, related to :model:`rolodex.Client`."""

    name = models.CharField("Name", help_text="Enter the contact's full name", max_length=255)
    job_title = models.CharField(
        "Title or Role",
        max_length=255,
        help_text="Enter the contact's job title or project role as you want it to appear in a report",
    )
    email = models.CharField(
        "Email",
        max_length=255,
        help_text="Enter an email address for this contact",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would involve human involvement
    # The `max_length` allows for people adding spaces, other chars, and extension numbers
    phone = models.CharField(
        "Phone",
        max_length=50,
        default="",
        blank=True,
        help_text="Enter a phone number for this contact",
    )
    timezone = TimeZoneField(
        "Timezone",
        default="America/Los_Angeles",
        help_text="The contact's timezone",
    )
    note = models.TextField(
        "Contact Note",
        default="",
        blank=True,
        help_text="Provide additional information about the contact",
    )
    # Foreign keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        unique_together = ["name", "client"]
        ordering = ["client", "id"]
        verbose_name = "Client POC"
        verbose_name_plural = "Client POCs"

    def __str__(self):
        return f"{self.name} ({self.client})"


class ProjectType(models.Model):
    """Stores an individual project type, related to :model:`rolodex.Project`."""

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
        return f"{self.project_type}"


class Project(models.Model):
    """
    Stores an individual project, related to :model:`rolodex.Client`,
    :model:`rolodex.ProjectType`, and :model:`users.User`.
    """

    codename = models.CharField(
        "Project Codename",
        max_length=255,
        default="",
        blank=True,
        help_text="Give the project a codename (might be a ticket number, PMO reference, or something else)",
    )
    start_date = models.DateField("Start Date", max_length=12, help_text="Enter the start date of this project")
    end_date = models.DateField("End Date", max_length=12, help_text="Enter the end date of this project")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the project and planning",
    )
    slack_channel = models.CharField(
        "Project Slack Channel",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide an Slack channel to be used for project notifications",
    )
    complete = models.BooleanField("Completed", default=False, help_text="Mark this project as complete")
    timezone = TimeZoneField(
        "Project Timezone",
        default="America/Los_Angeles",
        help_text="Timezone of the project / working hours",
    )
    start_time = models.TimeField(
        "Start Time",
        default=time(9, 00),
        null=True,
        blank=True,
        help_text="Select the start time for each day",
    )
    end_time = models.TimeField(
        "End Time",
        default=time(17, 00),
        null=True,
        blank=True,
        help_text="Select the end time for each day",
    )
    tags = TaggableManager(blank=True)
    # Foreign keys
    client = models.ForeignKey(
        "Client",
        on_delete=models.CASCADE,
        null=False,
        help_text="Select the client to which this project should be attached",
    )
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    project_type = models.ForeignKey(
        "ProjectType",
        on_delete=models.PROTECT,
        null=False,
        help_text="Select a category for this project that best describes the work being performed",
    )

    extra_fields = models.JSONField(default=dict)

    def count_findings(self):
        """
        Count and return the number of findings across all reports associated with
        an individual :model:`rolodex.Project`.
        """
        finding_queryset = ReportFindingLink.objects.select_related("report", "report__project").filter(
            report__project=self.pk
        )
        return finding_queryset.count()

    count = property(count_findings)

    class Meta:
        ordering = ["-start_date", "end_date", "client", "project_type"]
        verbose_name = "Project"
        verbose_name_plural = "Projects"

    def get_absolute_url(self):
        return reverse("rolodex:project_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.start_date} {self.client} {self.project_type} ({self.codename})"

    @classmethod
    def for_user(cls, user):
        """
        Retrieve a filtered list of :model:`rolodex.Project` entries based on the user's role.

        Privileged users will receive all entries. Non-privileged users will receive only those entries to which they
        have access.
        """
        if user.is_privileged:
            return cls.objects.select_related("client").all().order_by("complete", "client")
        return (
            cls.objects.select_related("client")
            .filter(
                Q(client__clientinvite__user=user)
                | Q(projectinvite__user=user)
                | Q(projectassignment__operator=user)
            )
            .order_by("complete", "client")
        )

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged

    def user_can_view(self, user) -> bool:
        return self in self.for_user(user)

    def user_can_edit(self, user) -> bool:
        return self.user_can_view(user)

    def user_can_delete(self, user) -> bool:
        return self.user_can_view(user)


class ProjectRole(models.Model):
    """Stores an individual project role."""

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
        return f"{self.project_role}"


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
        default="",
        blank=True,
        help_text="Provide additional information about the project role and assignment",
    )
    # Foreign keys
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Select a user to assign to this project",
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    role = models.ForeignKey(
        ProjectRole,
        on_delete=models.PROTECT,
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


class ProjectContact(models.Model):
    """Stores an individual point of contact, related to :model:`rolodex.Project`."""

    name = models.CharField("Name", help_text="Enter the contact's full name", max_length=255)
    job_title = models.CharField(
        "Title or Role",
        max_length=255,
        help_text="Enter the contact's job title or project role as you want it to appear in a report",
    )
    email = models.CharField(
        "Email",
        max_length=255,
        help_text="Enter an email address for this contact",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would involve human involvement
    # The `max_length` allows for people adding spaces, other chars, and extension numbers
    phone = models.CharField(
        "Phone",
        max_length=50,
        default="",
        blank=True,
        help_text="Enter a phone number for this contact",
    )
    timezone = TimeZoneField(
        "Timezone",
        default="America/Los_Angeles",
        help_text="The contact's timezone",
    )
    note = models.TextField(
        "Contact Note",
        default="",
        blank=True,
        help_text="Provide additional information about the contact",
    )
    primary = models.BooleanField(
        "Primary Contact",
        default=False,
        help_text="Flag this contact as the primary point of contact / report recipient for the project",
    )
    # Foreign keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False, blank=False)

    class Meta:
        unique_together = ["name", "project"]
        ordering = ["project", "id"]
        verbose_name = "Project POC"
        verbose_name_plural = "Project POCs"

    def __str__(self):
        return f"{self.name}"


class ObjectiveStatus(models.Model):
    """Stores an individual objective status."""

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
        return f"{self.objective_status}"


class ObjectivePriority(models.Model):
    """Stores an individual objective priority category."""

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
        return f"{self.priority}"


def _get_default_status():
    """Get the default status for the status field."""
    try:
        active_status = ObjectiveStatus.objects.get(objective_status="Active")
        return active_status.id
    except ObjectiveStatus.DoesNotExist:
        return 1


class ProjectObjective(models.Model):
    """
    Stores an individual project objective, related to an individual :model:`rolodex.Project`
    and :model:`rolodex.ObjectiveStatus`.
    """

    objective = models.CharField(
        "Objective",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide a high-level objective – add sub-tasks later for planning or as you discover obstacles",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a more detailed description, purpose, or context",
    )
    complete = models.BooleanField("Completed", default=False, help_text="Mark the objective as complete")
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
    result = models.TextField(
        "Result",
        default="",
        blank=True,
        help_text="Provide a detailed result or outcome for this objective",
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
        default=_get_default_status,
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

        if total_tasks > 0:
            for task in self.projectsubtask_set.all():
                if task.complete:
                    completed_tasks += 1
            return round(completed_tasks / total_tasks * 100, 1)

        return 0


class ProjectSubTask(models.Model):
    """
    Stores an individual sub-task, related to an individual :model:`rolodex.ProjectObjective`
    and :model:`rolodex.ObjectiveStatus`.
    """

    task = models.TextField("Task", blank=True, default="", help_text="Provide a concise objective")
    complete = models.BooleanField("Completed", default=False, help_text="Mark the objective as complete")
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
        default=_get_default_status,
        help_text="Set the status for this objective",
    )

    class Meta:
        ordering = ["parent", "complete", "deadline", "status", "task"]
        verbose_name = "Objective sub-task"
        verbose_name_plural = "Objective sub-tasks"

    def __str__(self):
        return f"{self.parent.project} : {self.task} ({self.status})"


class ClientNote(models.Model):
    """Stores an individual note, related to an individual :model:`rolodex.Client` and :model:`users.User`."""

    # This field is automatically filled with the current date
    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Leave the client or related projects",
    )
    # Foreign Keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["client", "timestamp"]
        verbose_name = "Client note"
        verbose_name_plural = "Client notes"

    def __str__(self):
        return f"{self.client}: {self.timestamp} - {self.note}"


class ProjectNote(models.Model):
    """Stores an individual note, related to :model:`rolodex.Project` and :model:`users.User`."""

    # This field is automatically filled with the current date
    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Leave a note about the project or related client",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["project", "timestamp"]
        verbose_name = "Project note"
        verbose_name_plural = "Project notes"

    def __str__(self):
        return f"{self.project}: {self.timestamp} - {self.note}"


class ProjectScope(models.Model):
    """Stores an individual scope list, related to an individual :model:`rolodex.Project`."""

    name = models.CharField(
        "Scope Name",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide a descriptive name for this list (e.g., External IPs, Cardholder Data Environment)",
    )
    scope = models.TextField(
        "Scope",
        default="",
        blank=True,
        help_text="Provide a list of IP addresses, ranges, hostnames, or a mix with each entry on a new line",
    )
    description = models.TextField(
        "Description",
        default="",
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
        return len(self.scope.splitlines())

    def count_lines_str(self):
        """Returns the number of lines in the scope list as a string."""
        count = len(self.scope.splitlines())
        if count > 1:
            return f"{count} Lines"
        return f"{count} Line"


class ProjectTarget(models.Model):
    """Stores an individual target host, related to an individual :model:`rolodex.Project`."""

    ip_address = models.CharField(
        "IP Address",
        max_length=45,
        default="",
        blank=True,
        validators=[validate_ip_range],
        help_text="Enter the IP address or range of the target host(s)",
    )
    hostname = models.CharField(
        "Hostname / FQDN",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide the target's hostname, fully qualified domain name, or other identifier",
    )
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the target(s) or the environment",
    )
    compromised = models.BooleanField("Compromised", default=False, help_text="Flag this target as compromised")
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project", "compromised", "ip_address", "hostname"]
        verbose_name = "Project target"
        verbose_name_plural = "Project targets"

    def __str__(self):
        return f"{self.hostname} ({self.ip_address})"


class ClientInvite(models.Model):
    """
    Links an individual :model:`users.User` to a :model:`rolodex.Client` to
    which they have been granted access.
    """

    comment = models.TextField(
        "Comment",
        default="",
        blank=True,
        help_text="Optional explanation for this invite",
    )
    # Foreign Keys
    client = models.ForeignKey(Client, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["client_id", "user_id"]
        verbose_name = "Client invite"
        verbose_name_plural = "Client invites"

    def __str__(self):
        return f"{self.user} ({self.client})"


class ProjectInvite(models.Model):
    """
    Links an individual :model:`users.User` to a :model:`rolodex.Project` to
    which they have been granted access.
    """

    comment = models.TextField(
        "Comment",
        default="",
        blank=True,
        help_text="Optional explanation for this invite",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project_id", "user_id"]
        verbose_name = "Project invite"
        verbose_name_plural = "Project invites"

    def __str__(self):
        return f"{self.user} ({self.project})"


class DeconflictionStatus(models.Model):
    """Stores an individual deconfliction status."""

    status = models.CharField(
        "Status",
        max_length=255,
        unique=True,
        help_text="Status for a deconfliction request (e.g., Undetermined, Confirmed, Unrelated)",
    )
    weight = models.IntegerField(
        "Status Weight",
        default=1,
        help_text="Weight for sorting status",
    )

    class Meta:
        ordering = ["weight", "status"]
        verbose_name = "Deconfliction status"
        verbose_name_plural = "Deconfliction status"

    def __str__(self):
        return f"{self.status}"


class Deconfliction(models.Model):
    """Stores an individual deconfliction, related to an individual :model:`rolodex.Project`."""

    created_at = models.DateTimeField(
        "Timestamp",
        auto_now_add=True,
        help_text="Date and time this deconfliction was created",
    )
    report_timestamp = models.DateTimeField(
        "Report Timestamp",
        help_text="Date and time the client informed you and requested deconfliction",
    )
    alert_timestamp = models.DateTimeField(
        "Alert Timestamp",
        null=True,
        blank=True,
        help_text="Date and time the alert fired",
    )
    response_timestamp = models.DateTimeField(
        "Response Timestamp",
        null=True,
        blank=True,
        help_text="Date and time you responded to the report",
    )
    title = models.CharField(
        "Deconfliction Title",
        max_length=255,
        help_text="Provide a descriptive title or headline for this deconfliction",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a brief description of this deconfliction request",
    )
    alert_source = models.CharField(
        "Alert Source",
        max_length=255,
        default="",
        blank=True,
        help_text="Source of the alert (e.g., user reported, EDR, MDR, etc.)",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)
    status = models.ForeignKey(
        "DeconflictionStatus",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a status that best reflects the current state of this deconfliction (e.g., undetermined, confirmed assessment activity, or unrelated to assessment activity)",
    )

    class Meta:
        ordering = ["project", "-created_at", "status__weight", "title"]
        verbose_name = "Project deconfliction"
        verbose_name_plural = "Project deconflictions"

    @property
    def log_entries(self):
        """Get log entries that precede the alert by one hour."""
        from ghostwriter.oplog.models import OplogEntry
        logs = None
        if self.alert_timestamp:
            one_hour_ago = self.alert_timestamp - timedelta(hours=1)
            logs = OplogEntry.objects.filter(
                models.Q(oplog_id__project=self.project)
                & models.Q(start_date__range=(one_hour_ago, self.alert_timestamp))
            )
        return logs

    def __str__(self):
        return f"{self.project}: {self.title}"


class WhiteCard(models.Model):
    """Stores an individual white card, related to an individual :model:`rolodex.Project`."""

    issued = models.DateTimeField(
        "Issued",
        blank=True,
        null=True,
        help_text="Date and time the client issued this white card",
    )
    title = models.CharField(
        "Title",
        max_length=255,
        blank=True,
        default="",
        help_text="Provide a descriptive headline for this white card (e.g., a username, hostname, or short sentence",
    )
    description = models.TextField(
        "Description",
        blank=True,
        default="",
        help_text="Provide a brief description of this white card",
    )
    # Foreign Keys
    project = models.ForeignKey(Project, on_delete=models.CASCADE, null=False)

    class Meta:
        ordering = ["project", "-issued", "title"]
        verbose_name = "Project white card"
        verbose_name_plural = "Project white cards"

    def __str__(self):
        return f"{self.project}: {self.title}"
