"""This contains all the URL mappings used by the Oplog application."""

# Django Imports
from django.urls import include, path

# 3rd Party Libraries
from rest_framework import routers

# Ghostwriter Libraries
from ghostwriter.oplog import views

app_name = "ghostwriter.oplog"

router = routers.DefaultRouter()
router.register("entries", views.OplogEntryViewSet)
router.register("oplogs", views.OplogViewSet)

urlpatterns = [
    path("", views.index, name="index"),
    path("api/", include(router.urls)),
    path("create/<int:pk>", views.OplogCreate.as_view(), name="oplog_create"),
    path("create/", views.OplogCreate.as_view(), name="oplog_create_no_project"),
    path("update/<int:pk>", views.OplogUpdate.as_view(), name="oplog_update"),
    path(
        "entry/create/<int:pk>",
        views.OplogEntryCreate.as_view(),
        name="oplog_entry_create",
    ),
    path(
        "entry/update/<int:pk>",
        views.OplogEntryUpdate.as_view(),
        name="oplog_entry_update",
    ),
    path(
        "entry/delete/<int:pk>",
        views.OplogEntryDelete.as_view(),
        name="oplog_entry_delete",
    ),
    path("<int:pk>/entries", views.OplogListEntries.as_view(), name="oplog_entries"),
    path("import", views.OplogEntriesImport, name="oplog_import"),
]

# URLs for AJAX requests
urlpatterns += [
    path("ajax/oplog/mute/<int:pk>", views.OplogMuteToggle.as_view(), name="ajax_oplog_mute_toggle"),
]
