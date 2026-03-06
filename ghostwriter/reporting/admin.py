"""This contains customizations for displaying the Reporting application models in the admin panel."""

# Standard Library Imports
import os

# Django Imports
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

# 3rd Party Libraries
from import_export.admin import ImportExportMixin

# Ghostwriter Libraries
from ghostwriter.commandcenter.admin import CollabAdminBase
from ghostwriter.reporting.forms import SeverityForm
from ghostwriter.reporting.models import (
    Archive,
    DocType,
    Evidence,
    Finding,
    FindingNote,
    FindingType,
    LocalFindingNote,
    Observation,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    ReportTemplate,
    Severity,
)
from ghostwriter.reporting.resources import FindingResource, ObservationResource


@admin.register(Archive)
class ArchiveAdmin(admin.ModelAdmin):
    pass


@admin.register(DocType)
class DocTypeAdmin(admin.ModelAdmin):
    list_display = ("name", "doc_type", "extension")
    list_display_links = ("name", "doc_type", "extension")

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Evidence)
class EvidenceAdmin(admin.ModelAdmin):
    list_display = ("friendly_name", "document_link", "upload_date", "uploaded_by", "tag_list")
    list_filter = ("uploaded_by", "tags")
    list_display_links = ("friendly_name", "upload_date", "uploaded_by")
    readonly_fields = ("document_download_link",)
    fieldsets = (
        (
            "Evidence Document",
            {"fields": ("friendly_name", "caption", "description", "document", "document_download_link", "tags")},
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

    class Media:
        js = ('js/admin/evidence_admin.js',)

    def document_link(self, obj):
        """Display the document filename as a clickable link in the list view for viewing."""
        if obj.document and os.path.exists(obj.document.path):
            return format_html(
                '<a href="{url}?view=true">{filename}</a>',
                url=reverse("reporting:evidence_download", args=[obj.id]),
                filename=os.path.basename(obj.document.name)
            )
        return "No File"
    document_link.short_description = "Document"

    def document_download_link(self, obj):
        """Display a download link in the detail view."""
        if obj.document and obj.id and os.path.exists(obj.document.path):
            filename = os.path.basename(obj.document.name)
            return format_html(
                '<a href="{url}" download="{filename}">{filename}</a>',
                url=reverse("reporting:evidence_download", args=[obj.id]),
                filename=filename
            )
        return "File missing or not available for download"
    document_download_link.short_description = "Download File"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(FindingType)
class FindingTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(Finding)
class FindingAdmin(ImportExportMixin, CollabAdminBase):
    resource_class = FindingResource
    list_display = ("title", "severity", "finding_type", "tag_list")
    list_filter = (
        "severity",
        "finding_type",
        "tags",
    )
    list_editable = ("severity", "finding_type")
    list_display_links = ("title",)
    fieldsets = (
        (
            "General Information",
            {
                "fields": (
                    "title",
                    "finding_type",
                    "severity",
                    "cvss_score",
                    "cvss_vector",
                    "tags",
                )
            },
        ),
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

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


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
    list_display = ("title", "project", "complete", "archived", "tag_list")
    list_filter = (
        "complete",
        "archived",
        "tags",
    )
    list_editable = ("complete",)
    list_display_links = ("title", "project")
    fieldsets = (
        ("Report Details", {"fields": ("project", "title", "created_by", "tags")}),
        ("Current Status", {"fields": ("complete", "delivered", "archived")}),
        ("Templates", {"fields": ("docx_template", "pptx_template", "include_bloodhound_data")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(ReportFindingLink)
class ReportFindingLinkAdmin(CollabAdminBase):
    list_display = ("report", "severity", "finding_type", "title", "complete", "tag_list")
    list_filter = ("severity", "finding_type", "complete", "tags")
    list_editable = (
        "severity",
        "finding_type",
        "complete",
    )
    list_display_links = ("report", "title")
    fieldsets = (
        (
            "General Information",
            {
                "fields": (
                    "position",
                    "title",
                    "finding_type",
                    "severity",
                    "cvss_score",
                    "cvss_vector",
                    "tags",
                )
            },
        ),
        (
            "Finding Status",
            {"fields": ("complete", "added_as_blank", "assigned_to", "report")},
        ),
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

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(Severity)
class SeverityAdmin(admin.ModelAdmin):
    list_display = ("severity", "color", "weight")
    form = SeverityForm


@admin.register(ReportTemplate)
class ReportTemplateAdmin(admin.ModelAdmin):
    list_display = (
        "get_status",
        "name",
        "client",
        "last_update",
        "tag_list",
    )
    readonly_fields = ("get_status", "template_download_link")
    list_filter = (
        "client",
        "tags",
    )
    list_display_links = ("name",)
    fieldsets = (
        (
            "Report Template",
            {
                "fields": (
                    "name",
                    "document",
                    "template_download_link",
                    "description",
                    "client",
                    "doc_type",
                    "p_style",
                    "evidence_image_width",
                    "contains_bloodhound_data",
                    "tags",
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

    class Media:
        js = ('js/admin/template_admin.js',)

    def template_download_link(self, obj):
        """Display a download link in the detail view."""
        if obj.document and obj.id and os.path.exists(obj.document.path):
            filename = os.path.basename(obj.document.name)
            return format_html(
                '<a href="{url}" download="{filename}">{filename}</a>',
                url=reverse("reporting:template_download", args=[obj.id]),
                filename=filename
            )
        return "File missing or not available for download"
    template_download_link.short_description = "Download File"

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(Observation)
class ObservationAdmin(ImportExportMixin, CollabAdminBase):
    resource_class = ObservationResource
    list_display = (
        "title",
        "tag_list",
    )
    list_filter = ("tags",)
    list_display_links = ("title",)

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())

@admin.register(ReportObservationLink)
class ReportObservationLinkAdmin(CollabAdminBase):
    list_display = ("report", "title")
    list_display_links = ("report", "title")
