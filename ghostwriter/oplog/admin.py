"""This contains customizations for displaying the Oplog application models in the admin panel."""

# Django & Other 3rd Party Libraries
from django.contrib import admin
from import_export import resources
from import_export.admin import ImportExportModelAdmin

# Ghostwriter Libraries
from .models import Oplog, OplogEntry
from .resources import OplogEntryResource


class OplogResource(resources.ModelResource):
    class Meta:
        model = Oplog


@admin.register(OplogEntry)
class OplogEntryAdmin(ImportExportModelAdmin):
    resource_class = OplogEntryResource


@admin.register(Oplog)
class OplogAdmin(ImportExportModelAdmin):
    resource_class = OplogResource
