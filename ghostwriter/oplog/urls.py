from django.urls import path
from django.urls import include

from rest_framework import routers

from .views import (
    index,
    OplogCreateWithoutProject,
    OplogEntryCreate,
    OplogEntryUpdate,
    OplogEntryDelete,
    OplogListEntries,
    OplogEntryViewSet,
    OplogViewSet,
)

app_name = "ghostwriter.oplog"

router = routers.DefaultRouter()
router.register("entries", OplogEntryViewSet)
router.register("oplogs", OplogViewSet)

urlpatterns = [
    path("", index, name="index"),
    path("api/", include(router.urls)),
    path("create/", OplogCreateWithoutProject.as_view(), name="oplog_create"),
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
]

