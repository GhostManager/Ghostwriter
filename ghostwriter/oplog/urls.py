"""This contains all of the URL mappings used by the Oplog application."""
  
# Django & Other 3rd Party Libraries
from django.urls import include, path
from rest_framework import routers

from .views import (
    OplogCreateWithoutProject,
    OplogEntriesImport,
    OplogEntryCreate,
    OplogEntryDelete,
    OplogEntryUpdate,
    OplogEntryViewSet,
    OplogListEntries,
    OplogViewSet,
    index,
    load_projects
)

app_name = "ghostwriter.oplog"

router = routers.DefaultRouter()
router.register("entries", OplogEntryViewSet)
router.register("oplogs", OplogViewSet)

urlpatterns = [
    path("", index, name="index"),
    path("api/", include(router.urls)),
    path("create/", OplogCreateWithoutProject.as_view(), name="oplog_create"),
    path("load-projects/", load_projects, name="load_projects"),
    path(
        "<int:pk>/entries/create", OplogEntryCreate.as_view(), name="oplog_entry_create"
    ),
    path(
        "<int:pk>/entries/update", OplogEntryUpdate.as_view(), name="oplog_entry_update"
    ),
    path(
        "<int:pk>/entries/delete", OplogEntryDelete.as_view(), name="oplog_entry_delete"
    ),
    path("<int:pk>/entries", OplogListEntries, name="oplog_entries"),
    path("import", OplogEntriesImport, name="oplog_import"),
]
