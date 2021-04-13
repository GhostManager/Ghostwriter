"""This contains all of the URL mappings used by the Oplog application."""


from django.urls import include, path
from rest_framework import routers

from . import views

app_name = "ghostwriter.oplog"

router = routers.DefaultRouter()
router.register("entries", views.OplogEntryViewSet)
router.register("oplogs", views.OplogViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("api/", include(router.urls)),
    path("create/<int:pk>", views.OplogCreate.as_view(), name="oplog_create"),
    path("create/", views.OplogCreate.as_view(), name="oplog_create_no_project"),
    path(
        "<int:pk>/entries/create",
        views.OplogEntryCreate.as_view(),
        name="oplog_entry_create",
    ),
    path(
        "<int:pk>/entries/update",
        views.OplogEntryUpdate.as_view(),
        name="oplog_entry_update",
    ),
    path(
        "<int:pk>/entries/delete",
        views.OplogEntryDelete.as_view(),
        name="oplog_entry_delete",
    ),
    path("<int:pk>/entries", views.OplogListEntries, name="oplog_entries"),
    path("import", views.OplogEntriesImport, name="oplog_import"),
]
