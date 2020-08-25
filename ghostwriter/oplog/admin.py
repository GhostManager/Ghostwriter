from datetime import datetime as dt
from django.contrib import admin
from import_export import resources

# Register your models here.
from .models import OplogEntry, Oplog

from import_export.admin import ImportExportModelAdmin


class OplogEntryResource(resources.ModelResource):
    def before_import_row(self, row, **kwargs):
        if "start_date" in row.keys():
            try:
                timestamp = int(row["start_date"])
                dt_object = dt.fromtimestamp(timestamp / 1000)
                row["start_date"] = str(dt_object)
            except ValueError:
                pass
        if "end_date" in row.keys():
            try:
                timestamp = int(row["end_date"])
                dt_object = dt.fromtimestamp(timestamp / 1000)
                row["end_date"] = str(dt_object)
            except ValueError:
                pass

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
