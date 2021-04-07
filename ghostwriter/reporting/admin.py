"""This contains customizations for displaying the Reporting application models in the admin panel."""

# Django Imports
from django.contrib import admin

# 3rd Party Libraries
from import_export.admin import ImportExportModelAdmin

from .models import (
    Archive,
    DocType,
    Evidence,
    Finding,
    FindingNote,
    FindingType,
    LocalFindingNote,
    Report,
    ReportFindingLink,
    ReportTemplate,
    Severity,
)
from .resources import FindingResource


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass


@admin.register(DocType)
class DocTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("document", "upload_date", "uploaded_by")
    list_filter = ("uploaded_by",)
    list_display_links = ("document", "upload_date", "uploaded_by")
    fieldsets = (
        (
            "Evidence Document",
            {"fields": ("friendly_name", "caption", "description", "document")},
        ),
        (
            "Report Information",
            {
                "fields": (
                    "finding",
                    "uploaded_by",
                )
            },
        ),
    )


@admin.register(FindingType)
class FindingTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Finding)
class FindingAdmin(ImportExportModelAdmin):
    resource_class = FindingResource
    list_display = ("title", "severity", "finding_type")
    list_filter = ("severity", "finding_type")
    list_editable = ("severity", "finding_type")
    list_display_links = ("title",)
    fieldsets = (
        ("General Information", {"fields": ("title", "severity", "finding_type")}),
        ("Finding Guidance", {"fields": ("finding_guidance",)}),
        (
            "Finding Details",
            {
                "fields": (
                    "description",
                    "impact",
                    "mitigation",
                    "replication_steps",
                    "host_detection_techniques",
                    "network_detection_techniques",
                    "references",
                )
            },
        ),
    )


@admin.register(FindingNote)
class FindingNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "finding")
    list_display_links = ("operator", "timestamp", "finding")


@admin.register(LocalFindingNote)
class LocalFindingNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "finding")
    list_display_links = ("operator", "timestamp", "finding")


@admin.register(Report)
class ReportAdmin(admin.ModelAdmin):
    list_display = ("title", "project", "complete", "archived", "created_by")
    list_filter = ("complete", "archived")
    list_editable = ("complete",)
    list_display_links = ("title", "project")
    fieldsets = (
        ("Report Details", {"fields": ("project", "title", "created_by")}),
        ("Current Status", {"fields": ("complete", "delivered", "archived")}),
    )


@admin.register(ReportFindingLink)
class ReportFindingLinkAdmin(admin.ModelAdmin):
    list_display = ("report", "severity", "finding_type", "title", "complete")
    list_filter = ("severity", "finding_type", "complete")
    list_editable = (
        "severity",
        "finding_type",
        "complete",
    )
    list_display_links = ("report", "title")
    fieldsets = (
        (
            "General Information",
            {"fields": ("title", "severity", "finding_type", "position")},
        ),
        ("Finding Status", {"fields": ("complete", "assigned_to", "report")}),
        ("Finding Guidance", {"fields": ("finding_guidance",)}),
        (
            "Finding Details",
            {
                "fields": (
                    "description",
                    "impact",
                    "mitigation",
                    "replication_steps",
                    "host_detection_techniques",
                    "network_detection_techniques",
                    "references",
                )
            },
        ),
    )


@admin.register(Severity)
class SeverityAdmin(admin.ModelAdmin):
    pass


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "get_status",
        "name",
        "client",
        "last_update",
    )
    readonly_fields = ("get_status",)
    list_filter = ("client",)
    list_display_links = ("name",)
    fieldsets = (
        (
            "Report Template",
            {
                "fields": (
                    "name",
                    "document",
                    "description",
                    "client",
                    "doc_type",
                )
            },
        ),
        (
            "Template Linting",
            {
                "fields": (
                    "get_status",
                    "lint_result",
                )
            },
        ),
        (
            "Admin Settings",
            {"fields": ("protected",)},
        ),
    )
