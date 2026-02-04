"""This contains customizations for displaying the Reporting application models in the admin panel."""

# Standard Libraries
import logging

# Django Imports
from django.contrib import admin, messages
from django.shortcuts import redirect, render
from django.urls import path

# 3rd Party Libraries
from import_export.admin import ImportExportMixin

# Ghostwriter Libraries
from ghostwriter.commandcenter.admin import CollabAdminBase
from ghostwriter.reporting.forms import AcronymYAMLUploadForm, SeverityForm
from ghostwriter.reporting.utils import import_acronyms_from_yaml
from ghostwriter.reporting.models import (
    Acronym,
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
    list_display = ("document", "upload_date", "uploaded_by", "tag_list")
    list_filter = ("uploaded_by", "tags")
    list_display_links = ("document", "upload_date", "uploaded_by")
    fieldsets = (
        (
            "Evidence Document",
            {"fields": ("friendly_name", "caption", "description", "document", "tags")},
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
        (
            "Templates",
            {"fields": ("docx_template", "pptx_template", "include_bloodhound_data")},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(ReportFindingLink)
class ReportFindingLinkAdmin(CollabAdminBase):
    list_display = (
        "report",
        "severity",
        "finding_type",
        "title",
        "complete",
        "tag_list",
    )
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
    readonly_fields = ("get_status",)
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


@admin.register(Acronym)
class AcronymAdmin(admin.ModelAdmin):
    """Admin interface for Acronym model."""

    list_display = (
        "acronym",
        "expansion",
        "priority",
        "override_builtin",
        "is_active",
        "created_by",
    )
    list_filter = ("is_active", "override_builtin", "created_by")
    search_fields = ("acronym", "expansion")
    list_editable = ("is_active", "priority")
    list_display_links = ("acronym", "expansion")
    ordering = ("acronym", "-priority")
    readonly_fields = ("created_by", "created_at", "updated_at")
    change_list_template = "admin/reporting/acronym_changelist.html"

    fieldsets = (
        (
            "General Information",
            {
                "fields": (
                    "acronym",
                    "expansion",
                )
            },
        ),
        (
            "Metadata",
            {
                "fields": (
                    "priority",
                    "override_builtin",
                    "is_active",
                    "created_by",
                    "created_at",
                    "updated_at",
                )
            },
        ),
    )

    actions = ["activate_acronyms", "deactivate_acronyms"]

    def get_urls(self):
        """Add custom URL for YAML upload."""
        urls = super().get_urls()
        custom_urls = [
            path(
                "upload-yaml/",
                self.admin_site.admin_view(self.upload_yaml_view),
                name="reporting_acronym_upload_yaml",
            ),
        ]
        return custom_urls + urls

    def upload_yaml_view(self, request):
        """Handle YAML file upload within admin interface."""

        if request.method == "POST":
            form = AcronymYAMLUploadForm(request.POST, request.FILES)

            if form.is_valid():
                yaml_file = form.cleaned_data["yaml_file"]
                override = form.cleaned_data["override_existing"]

                try:
                    # Read and import acronyms
                    content = yaml_file.read().decode("utf-8")
                    stats = import_acronyms_from_yaml(
                        content, override=override, user=request.user
                    )

                    # Build success message
                    msg_parts = []
                    if stats["created"] > 0:
                        msg_parts.append(f"{stats['created']} acronym(s) created")
                    if stats["updated"] > 0:
                        msg_parts.append(f"{stats['updated']} acronym(s) updated")
                    if stats["skipped"] > 0:
                        msg_parts.append(f"{stats['skipped']} acronym(s) skipped")

                    message = "Successfully imported acronyms: " + ", ".join(msg_parts)

                    if stats["errors"]:
                        message += f". {len(stats['errors'])} error(s) encountered."
                        for error in stats["errors"][:5]:  # Show first 5 errors
                            messages.warning(request, error)

                    messages.success(request, message)

                    # Redirect back to acronym changelist
                    return redirect("..")

                except (ValueError, UnicodeDecodeError) as e:
                    messages.error(
                        request,
                        f"Failed to import acronyms: {str(e)}",
                    )
        else:
            form = AcronymYAMLUploadForm()

        context = {
            **self.admin_site.each_context(request),
            "form": form,
            "opts": self.model._meta,
            "title": "Upload Acronyms YAML",
        }

        return render(request, "admin/reporting/acronym_upload_yaml.html", context)

    def activate_acronyms(self, request, queryset):
        """Mark selected acronyms as active."""
        updated = queryset.update(is_active=True)
        self.message_user(request, f"{updated} acronym(s) marked as active.")

    activate_acronyms.short_description = "Activate selected acronyms"

    def deactivate_acronyms(self, request, queryset):
        """Mark selected acronyms as inactive."""
        updated = queryset.update(is_active=False)
        self.message_user(request, f"{updated} acronym(s) marked as inactive.")

    deactivate_acronyms.short_description = "Deactivate selected acronyms"

    def save_model(self, request, obj, form, change):
        """Auto-set created_by on new objects only."""
        if not change and not obj.created_by:
            obj.created_by = request.user
        super().save_model(request, obj, form, change)
