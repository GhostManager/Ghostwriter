"""This contains customizations for the models in the Django admin panel."""

from django.contrib import admin
from .models import (Client, Project, ProjectType, ClientContact,
    ProjectAssignment, ProjectRole, ClientNote, ProjectNote,
    ProjectObjective, ObjectiveStatus)


# Define the admin classes and register models
@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('name', 'short_name', 'codename')
    list_filter = ('name',)
    fieldsets = (
        (None, {
            'fields': ('name', 'short_name', 'codename')
        }),
        ('Misc', {
            'fields': ('note',)
        })
    )


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'job_title', 'client')
    list_filter = ('client',)
    fieldsets = (
        (None, {
            'fields': ('client', 'name', 'job_title', 'email', 'phone')
        }),
        ('Misc', {
            'fields': ('note',)
        })
    )


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('client', 'codename', 'project_type', 'start_date',
                    'end_date')
    list_filter = ('client',)
    fieldsets = (
        (None, {
            'fields': ('client', 'codename', 'project_type')
        }),
        ('Execution Dates', {
            'fields': ('start_date', 'end_date')
        }),
        ('Misc', {
            'fields': ('slack_channel', 'note')
        })
    )


@admin.register(ProjectType)
class ProjectTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectAssignment)
class ProjectAssignmentAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectRole)
class ProjectRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ClientNote)
class ClientNoteAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectNote)
class ProjectNoteAdmin(admin.ModelAdmin):
    pass


@admin.register(ObjectiveStatus)
class ObjectiveStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ProjectObjective)
class ProjectObjectiveAdmin(admin.ModelAdmin):
    pass
