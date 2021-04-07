"""This contains customizations for displaying the Oplog application models in the admin panel."""

from django.contrib import admin


from import_export import resources
from import_export.admin import ImportExportModelAdmin

from .models import Oplog, OplogEntry
from .resources import OplogEntryResource


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


@admin.register(Oplog)
class OplogAdmin(ImportExportModelAdmin):
    resource_class = OplogResource
