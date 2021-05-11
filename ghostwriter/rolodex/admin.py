"""This contains customizations for displaying the Rolodex application models in the admin panel."""

# Django Imports
from django.contrib import admin

from .models import (
    Client,
    ClientContact,
    ClientNote,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectNote,
    ProjectObjective,
    ProjectRole,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    ProjectType,
)


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "codename")
    list_filter = ("name",)
    list_display_links = ("name", "short_name", "codename")
    fieldsets = (
        ("General Information", {"fields": ("name", "short_name", "codename")}),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title", "client")
    list_filter = ("client",)
    list_display_links = ("name", "job_title", "client")
    fieldsets = (
        (
            "Contact Information",
            {"fields": ("client", "name", "job_title", "email", "phone")},
        ),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = (
        "client",
        "codename",
        "project_type",
        "start_date",
        "end_date",
        "complete",
    )
    list_filter = ("client",)
    list_display_links = ("client", "codename")
    fieldsets = (
        ("General Information", {"fields": ("client", "codename", "project_type")}),
        (
            "Execution Dates and Status",
            {"fields": ("start_date", "end_date", "complete")},
        ),
        ("Misc", {"fields": ("slack_channel", "note")}),
    )


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    list_display = ("operator", "project", "start_date", "end_date")
    list_filter = ("operator", "project")
    list_display_links = ("operator", "project")
    fieldsets = (
        ("Operator Information", {"fields": ("operator", "role", "project")}),
        (
            "Assignment Dates",
            {"fields": ("start_date", "end_date")},
        ),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "client")
    list_filter = ("client",)
    list_display_links = ("operator", "timestamp", "client")


@admin.register(ProjectNote)
class ProjectNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "project")
    list_filter = ("project",)
    list_display_links = ("operator", "timestamp", "project")


@admin.register(ObjectiveStatus)
class ObjectiveStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectObjective)
class ProjectObjectiveAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectTarget)
class ProjectTargetAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectScope)
class ProjectScopeAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectSubTask)
class ProjectSubTaskAdmin(admin.ModelAdmin):
    pass


@admin.register(ObjectivePriority)
class ObjectivePriorityAdmin(admin.ModelAdmin):
    list_display = ("priority", "weight")
    list_display_links = ("priority",)
