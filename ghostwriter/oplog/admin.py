"""This contains customizations for displaying the Oplog application models in the admin panel."""

# Django Imports
from django.contrib import admin

# 3rd Party Libraries
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Ghostwriter Libraries
from ghostwriter.oplog.models import Oplog, OplogEntry, OplogEntryEvidence, OplogEntryRecording
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


@admin.register(OplogEntryEvidence)
class OplogEntryEvidenceAdmin(admin.ModelAdmin):
    list_display = ("oplog_entry", "evidence")
    list_filter = ("oplog_entry",)
    list_display_links = ("oplog_entry", "evidence")


@admin.register(OplogEntryRecording)
class OplogEntryRecordingAdmin(admin.ModelAdmin):
    list_display = ("oplog_entry", "filename", "uploaded_date", "uploaded_by")
    list_filter = ("uploaded_date",)
    list_display_links = ("oplog_entry",)
