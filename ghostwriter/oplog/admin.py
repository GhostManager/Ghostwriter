from django.contrib import admin
from import_export import resources

# Register your models here.
from .models import OplogEntry, Oplog

from import_export.admin import ImportExportModelAdmin

class OplogEntryResource(resources.ModelResource):
    class Meta:
        model = OplogEntry

class OplogResource(resources.ModelResource):
    class Meta:
        model = Oplog

@admin.register(OplogEntry)
class OplogEntryAdmin(ImportExportModelAdmin):
    resource_class = OplogEntryResource

@admin.register(Oplog)
class OplogAdmin(ImportExportModelAdmin):
    resource_class = OplogResource