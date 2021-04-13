"""This contains all of the URL mappings used by the Shepherd application."""

# Django Imports
from django.urls import path

from . import views

app_name = "shepherd"

# URLs for the basic domain views
urlpatterns = [
    path("", views.index, name="index"),
    path("domains/", views.domain_list, name="domains"),
    path("domains/<int:pk>", views.DomainDetailView.as_view(), name="domain_detail"),
    path("servers/", views.server_list, name="servers"),
    path("servers/<int:pk>", views.ServerDetailView.as_view(), name="server_detail"),
    path("user/active_assets", views.user_assets, name="user_assets"),
    path("update/", views.update, name="update"),
]

# URLs for AJAX requests – deletion and toggle views
urlpatterns += [
    path("ajax/load_projects/", views.ajax_load_projects, name="ajax_load_projects"),
    path("ajax/load_project/", views.ajax_load_project, name="ajax_load_project"),
    path(
        "ajax/domain/release/<int:pk>",
        views.DomainRelease.as_view(),
        name="ajax_domain_release",
    ),
    path(
        "ajax/server/release/<int:pk>",
        views.ServerRelease.as_view(),
        name="ajax_server_release",
    ),
    path(
        "ajax/project/infrastructure/link/delete/<int:pk>",
        views.DomainServerConnectionDelete.as_view(),
        name="ajax_delete_domain_link",
    ),
    path(
        "ajax/project/infrastructure/vps/delete/<int:pk>",
        views.TransientServerDelete.as_view(),
        name="ajax_delete_vps",
    ),
    path(
        "ajax/domain/note/delete/<int:pk>",
        views.DomainNoteDelete.as_view(),
        name="ajax_delete_domain_note",
    ),
    path(
        "ajax/server/notes/delete/<int:pk>",
        views.ServerNoteDelete.as_view(),
        name="ajax_delete_server_note",
    ),
    path(
        "ajax/update/categories/all",
        views.DomainUpdateHealth.as_view(),
        name="ajax_update_cat",
    ),
    path(
        "ajax/update/categories/<int:pk>",
        views.DomainUpdateHealth.as_view(),
        name="ajax_update_cat_single",
    ),
    path("ajax/update/dns/all", views.DomainUpdateDNS.as_view(), name="ajax_update_dns"),
    path(
        "ajax/update/dns/<int:pk>",
        views.DomainUpdateDNS.as_view(),
        name="ajax_update_dns_single",
    ),
    path(
        "ajax/update/namecheap",
        views.RegistrarSyncNamecheap.as_view(),
        name="ajax_update_namecheap",
    ),
    path(
        "ajax/update/cloud",
        views.MonitorCloudInfrastructure.as_view(),
        name="ajax_cloud_monitor",
    ),
    path(
        "ajax/domain/refresh/<int:pk>",
        views.update_domain_badges,
        name="ajax_update_domain_badges",
    ),
    path(
        "ajax/domain/overwatch",
        views.ajax_domain_overwatch,
        name="ajax_domain_overwatch",
    ),
    path(
        "ajax/project/<int:pk>/domains",
        views.ajax_project_domains,
        name="ajax_project_domains",
    ),
]

# URLs for domain status change functions
urlpatterns += [
    path("domains/checkout/<int:pk>", views.HistoryCreate.as_view(), name="checkout"),
    path("domains/burn/<int:pk>", views.burn, name="burn"),
]

# URLs for server status change functions
urlpatterns += [
    path(
        "servers/checkout/<int:pk>",
        views.ServerHistoryCreate.as_view(),
        name="server_checkout",
    ),
    path("servers/search", views.server_search, name="server_search"),
    path(
        "servers/search/all",
        views.infrastructure_search,
        name="infrastructure_search",
    ),
]

# URLs for creating, updating, and deleting domains
urlpatterns += [
    path("domains/create/", views.DomainCreate.as_view(), name="domain_create"),
    path("domains/update/<int:pk>", views.DomainUpdate.as_view(), name="domain_update"),
    path("domains/delete/<int:pk>", views.DomainDelete.as_view(), name="domain_delete"),
    path(
        "domains/notes/create/<int:pk>",
        views.DomainNoteCreate.as_view(),
        name="domain_note_add",
    ),
    path(
        "domains/notes/update/<int:pk>",
        views.DomainNoteUpdate.as_view(),
        name="domain_note_edit",
    ),
]

# URLs for creating, updating, and deleting servers
urlpatterns += [
    path("servers/create/", views.ServerCreate.as_view(), name="server_create"),
    path("servers/update/<int:pk>", views.ServerUpdate.as_view(), name="server_update"),
    path("servers/delete/<int:pk>", views.ServerDelete.as_view(), name="server_delete"),
    path(
        "servers/notes/create/<int:pk>",
        views.ServerNoteCreate.as_view(),
        name="server_note_add",
    ),
    path(
        "servers/notes/update/<int:pk>",
        views.ServerNoteUpdate.as_view(),
        name="server_note_edit",
    ),
    path(
        "servers/vps/create/<int:pk>",
        views.TransientServerCreate.as_view(),
        name="vps_create",
    ),
    path(
        "servers/vps/update/<int:pk>",
        views.TransientServerUpdate.as_view(),
        name="vps_update",
    ),
    path(
        "project/infrastructure/link/create/<int:pk>",
        views.DomainServerConnectionCreate.as_view(),
        name="link_create",
    ),
    path(
        "project/infrastructure/link/update/<int:pk>",
        views.DomainServerConnectionUpdate.as_view(),
        name="link_update",
    ),
]

# URLs for creating, updating, and deleting project histories
urlpatterns += [
    path(
        "domains/history/create/<int:pk>",
        views.HistoryCreate.as_view(),
        name="history_create",
    ),
    path(
        "domains/history/update/<int:pk>",
        views.HistoryUpdate.as_view(),
        name="history_update",
    ),
    path(
        "domains/history/delete/<int:pk>",
        views.HistoryDelete.as_view(),
        name="history_delete",
    ),
    path(
        "servers/history/create/<int:pk>",
        views.ServerHistoryCreate.as_view(),
        name="server_history_create",
    ),
    path(
        "servers/history/update/<int:pk>",
        views.ServerHistoryUpdate.as_view(),
        name="server_history_update",
    ),
    path(
        "servers/history/delete/<int:pk>",
        views.ServerHistoryDelete.as_view(),
        name="server_history_delete",
    ),
]

# URLs for management functions
urlpatterns += [
    path("export/csv/", views.export_domains_to_csv, name="export_domains_to_csv"),
    path("export/csv/", views.export_servers_to_csv, name="export_servers_to_csv"),
]
