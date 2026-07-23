"""This contains customizations for displaying the Oplog application models in the admin panel."""

# Standard Library Imports
import os

# Django Imports
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

# 3rd Party Libraries
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Ghostwriter Libraries
from ghostwriter.oplog.models import (
    Oplog,
    OplogEntry,
    OplogEntryEvidence,
    OplogEntryRecording,
    OplogSanitization,
)
from ghostwriter.oplog.resources import OplogEntryResource


class OplogResource(resources.ModelResource):
    class Meta:
        model = Oplog


@admin.register(OplogEntry)
class OplogEntryAdmin(ImportExportModelAdmin):
    resource_class = OplogEntryResource
    list_display = ("oplog_id", "operator_name", "start_date")
    list_filter = (
        "oplog_id",
        "operator_name",
        "start_date",
    )
    list_display_links = (
        "oplog_id",
        "operator_name",
        "start_date",
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(Oplog)
class OplogAdmin(ImportExportModelAdmin):
    resource_class = OplogResource


@admin.register(OplogSanitization)
class OplogSanitizationAdmin(admin.ModelAdmin):
    """Expose immutable sanitization audit events to administrators."""

    list_display = ("oplog", "sanitized_at", "sanitized_by_name", "fields")
    list_filter = ("sanitized_at",)
    readonly_fields = (
        "oplog",
        "sanitized_at",
        "sanitized_by",
        "sanitized_by_name",
        "fields",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(OplogEntryEvidence)
class OplogEntryEvidenceAdmin(admin.ModelAdmin):
    list_display = ("oplog_entry", "evidence")
    list_filter = ("oplog_entry",)
    list_display_links = ("oplog_entry", "evidence")


@admin.register(OplogEntryRecording)
class OplogEntryRecordingAdmin(admin.ModelAdmin):
    list_display = (
        "oplog_entry",
        "recording_download_link",
        "uploaded_date",
        "uploaded_by",
    )
    list_filter = ("uploaded_date",)
    list_display_links = ("oplog_entry",)
    readonly_fields = ("recording_file_download_link",)
    fieldsets = (
        (
            "Recording",
            {
                "fields": (
                    "oplog_entry",
                    "recording_file",
                    "recording_file_download_link",
                    "uploaded_by",
                    "recording_text",
                )
            },
        ),
    )

    class Media:
        js = ("js/admin/oplog_recording_admin.js",)

    def recording_download_link(self, obj):
        """Display the filename as a clickable download link in the list view."""
        if obj.recording_file and os.path.exists(obj.recording_file.path):
            return format_html(
                '<a href="{url}">{filename}</a>',
                url=reverse("oplog:oplog_entry_recording_download", args=[obj.id]),
                filename=obj.filename,
            )
        return "No File"

    recording_download_link.short_description = "Recording"

    def recording_file_download_link(self, obj):
        """Display a download link in the detail view."""
        if obj.recording_file and obj.id and os.path.exists(obj.recording_file.path):
            return format_html(
                '<a href="{url}" download="{filename}">{filename}</a>',
                url=reverse("oplog:oplog_entry_recording_download", args=[obj.id]),
                filename=obj.filename,
            )
        return "File missing or not available for download"

    recording_file_download_link.short_description = "Download File"
