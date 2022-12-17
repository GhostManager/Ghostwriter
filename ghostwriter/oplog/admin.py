"""This contains customizations for displaying the Oplog application models in the admin panel."""

# Django Imports
from django.contrib import admin

# 3rd Party Libraries
from import_export import resources
from import_export.admin import ImportExportModelAdmin

from ghostwriter.oplog.models import Oplog, OplogEntry
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
