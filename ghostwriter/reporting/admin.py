"""This contains customizations for the models in the Django admin panel."""

from django.contrib import admin
from .models import (Finding, Report, Severity, FindingType,
    ReportFindingLink, Evidence, Archive, FindingNote,
    LocalFindingNote)


# Define the admin classes and register models
@admin.register(Finding)
class FindingAdmin(admin.ModelAdmin):
    list_display = ('severity', 'title', 'finding_type')
    list_filter = ('severity', 'title', 'finding_type')
    fieldsets = (
        (None, {
            'fields': ('severity', 'title', 'finding_type')
        }),
        ('Finding Details', {
            'fields': ('description', 'impact', 'mitigation',
                       'replication_steps', 'host_detection_techniques',
                       'network_detection_techniques', 'references')
        })
    )


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ('project', 'title', 'complete', 'created_by', 'archived')
    list_filter = ('project',)
    fieldsets = (
        (None, {
            'fields': ('project', 'title', 'created_by')
        }),
        ('Current Status', {
            'fields': ('complete',)
        })
    )


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ('upload_date', 'uploaded_by')
    list_filter = ('upload_date',)


@admin.register(ReportFindingLink)
class ReportFindingLinkAdmin(admin.ModelAdmin):
    pass


@admin.register(Severity)
class SeverityAdmin(admin.ModelAdmin):
    pass


@admin.register(FindingType)
class FindingTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass


@admin.register(FindingNote)
class FindingNoteAdmin(admin.ModelAdmin):
    pass


@admin.register(LocalFindingNote)
class LocalFindingNoteAdmin(admin.ModelAdmin):
    pass
