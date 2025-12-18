"""This contains customizations for displaying the Rolodex application models in the admin panel."""

# Django Imports
from django.contrib import admin

# 3rd Party Libraries
from import_export.admin import ImportExportMixin

# Ghostwriter Libraries
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    ClientInvite,
    ClientNote,
    DNSCapMapping,
    DNSSOACapMapping,
    DNSFindingMapping,
    DNSRecommendationMapping,
    ADThresholdMapping,
    GeneralCapMapping,
    PasswordCapMapping,
    VulnerabilityMatrixEntry,
    WebIssueMatrixEntry,
    Deconfliction,
    DeconflictionStatus,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectInvite,
    ProjectNote,
    ProjectObjective,
    ProjectRole,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    ProjectType,
    WhiteCard,
)
from ghostwriter.rolodex.resources import (
    VulnerabilityMatrixEntryResource,
    WebIssueMatrixEntryResource,
)


@admin.register(DNSFindingMapping)
class DNSFindingMappingAdmin(admin.ModelAdmin):
    list_display = ("issue_text", "finding_text")
    search_fields = ("issue_text", "finding_text")


@admin.register(DNSRecommendationMapping)
class DNSRecommendationMappingAdmin(admin.ModelAdmin):
    list_display = ("issue_text", "recommendation_text")
    search_fields = ("issue_text", "recommendation_text")


@admin.register(DNSCapMapping)
class DNSCapMappingAdmin(admin.ModelAdmin):
    list_display = ("issue_text", "cap_text")
    search_fields = ("issue_text", "cap_text")


@admin.register(GeneralCapMapping)
class GeneralCapMappingAdmin(admin.ModelAdmin):
    list_display = ("issue_text", "score", "recommendation_text")
    search_fields = ("issue_text", "recommendation_text")


@admin.register(DNSSOACapMapping)
class DNSSOACapMappingAdmin(admin.ModelAdmin):
    list_display = ("soa_field", "cap_text")
    search_fields = ("soa_field", "cap_text")


@admin.register(PasswordCapMapping)
class PasswordCapMappingAdmin(admin.ModelAdmin):
    list_display = ("setting", "cap_text")
    search_fields = ("setting", "cap_text")


@admin.register(ADThresholdMapping)
class ADThresholdMappingAdmin(admin.ModelAdmin):
    list_display = ("label", "key", "threshold_type", "value", "issue_text")
    search_fields = ("label", "issue_text", "key")


@admin.register(VulnerabilityMatrixEntry)
class VulnerabilityMatrixEntryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = VulnerabilityMatrixEntryResource
    list_display = ("vulnerability", "category", "action_required")
    search_fields = (
        "vulnerability",
        "category",
        "action_required",
        "remediation_impact",
        "vulnerability_threat",
    )


@admin.register(WebIssueMatrixEntry)
class WebIssueMatrixEntryAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = WebIssueMatrixEntryResource
    list_display = ("title", "impact", "fix")
    search_fields = ("title", "impact", "fix")


@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "short_name", "codename", "tag_list")
    list_filter = ("name", "tags")
    list_display_links = ("name", "short_name", "codename")
    fieldsets = (
        (
            "General Information",
            {"fields": ("name", "short_name", "codename", "timezone", "address")},
        ),
        ("Misc", {"fields": ("description",)}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


@admin.register(ClientContact)
class ClientContactAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title", "client")
    list_filter = ("client",)
    list_display_links = ("name", "job_title", "client")
    fieldsets = (
        (
            "Contact Information",
            {"fields": ("client", "name", "job_title", "email", "phone", "timezone")},
        ),
        ("Misc", {"fields": ("description",)}),
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
        "tags",
    )
    list_filter = ("client", "complete", "tags")
    list_display_links = ("client", "codename")
    fieldsets = (
        ("General Information", {"fields": ("client", "codename", "project_type")}),
        (
            "Execution Dates and Status",
            {
                "fields": (
                    "start_date",
                    "end_date",
                    "start_time",
                    "end_time",
                    "timezone",
                    "complete",
                )
            },
        ),
        ("Misc", {"fields": ("slack_channel", "description")}),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).prefetch_related("tags")

    def tag_list(self, obj):
        return ", ".join(o.name for o in obj.tags.all())


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
        ("Misc", {"fields": ("description",)}),
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


@admin.register(ProjectInvite)
class ProjectInviteAdmin(admin.ModelAdmin):
    list_display = ("project", "user")
    list_filter = ("project", "user")
    list_display_links = ("project", "user")
    fieldsets = (
        ("Invitation", {"fields": ("user", "project")}),
        ("Misc", {"fields": ("comment",)}),
    )


@admin.register(ClientInvite)
class ClientInviteAdmin(admin.ModelAdmin):
    list_display = ("client", "user")
    list_filter = ("client", "user")
    list_display_links = ("client", "user")
    fieldsets = (
        ("Invitation", {"fields": ("user", "client")}),
        ("Misc", {"fields": ("comment",)}),
    )


@admin.register(DeconflictionStatus)
class DeconflictionStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(Deconfliction)
class DeconflictionAdmin(admin.ModelAdmin):
    list_display = ("project", "status", "title")
    list_filter = ("project", "status")
    list_display_links = ("project", "status", "title")
    fieldsets = (
        (
            "Deconfliction",
            {"fields": ("status", "title", "description", "alert_source", "project")},
        ),
        (
            "Timestamps",
            {
                "fields": (
                    "report_timestamp",
                    "alert_timestamp",
                    "response_timestamp",
                )
            },
        ),
    )


@admin.register(WhiteCard)
class WhiteCardAdmin(admin.ModelAdmin):
    list_display = ("project", "title")
    list_filter = [
        "project__complete",
    ]
    list_display_links = ("project", "title")
    fieldsets = (
        (
            "White Card",
            {"fields": ("issued", "title", "description")},
        ),
    )


@admin.register(ProjectContact)
class ProjectContactAdmin(admin.ModelAdmin):
    list_display = ("name", "job_title", "project", "primary")
    list_filter = ("project",)
    list_display_links = ("name", "job_title", "project")
    fieldsets = (
        (
            "Contact Information",
            {"fields": ("project", "name", "job_title", "email", "phone", "timezone", "primary")},
        ),
        ("Misc", {"fields": ("description",)}),
    )
