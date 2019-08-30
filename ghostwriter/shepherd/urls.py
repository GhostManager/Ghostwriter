"""This contains all of the URL mappings for the Shepherd application. The
`urlpatterns` list routes URLs to views. For more information please see:

https://docs.djangoproject.com/en/2.1/topics/http/urls/
"""

from . import views
from django.urls import path

app_name = "shepherd"

# URLs for the basic domain views
urlpatterns = [
    path('', views.index, name='index'),
    path('domains/', views.domain_list, name='domains'),
    path('domains/<int:pk>', views.DomainDetailView.as_view(),
         name='domain_detail'),
    # path('graveyard/', views.GraveyardListView.as_view(), name='graveyard'),
    path('servers/', views.server_list, name='servers'),
    path('servers/<int:pk>', views.ServerDetailView.as_view(),
         name='server_detail'),
    path('user/active_assets', views.user_assets, name='user_assets'),
    path('ajax/load_projects/', views.ajax_load_projects,
         name='ajax_load_projects'),
]

# URLs for domain status change functions
urlpatterns += [
    path('domains/<int:pk>/checkout', views.HistoryCreate.as_view(),
         name='checkout'),
    path('domains/<int:pk>/release', views.domain_release,
         name='domain_release'),
    path('domains/<int:pk>/burn', views.burn, name='burn')
]

# URLs for server status change functions
urlpatterns += [
    path('servers/<int:pk>/checkout', views.ServerHistoryCreate.as_view(),
         name='server_checkout'),
    path('servers/<int:pk>/release', views.server_release,
         name='server_release')
]

# URLs for creating, updating, and deleting domains
urlpatterns += [
    path('domains/create/', views.DomainCreate.as_view(),
         name='domain_create'),
    path('domains/<int:pk>/update/', views.DomainUpdate.as_view(),
         name='domain_update'),
    path('domains/<int:pk>/delete/', views.DomainDelete.as_view(),
         name='domain_delete'),
    path('domains/<int:pk>/add_note/', views.DomainNoteCreate.as_view(),
         name='domain_note_add'),
    path('domains/<int:pk>/edit_note/', views.DomainNoteUpdate.as_view(),
         name='domain_note_edit'),
    path('domains/<int:pk>/delete_note/', views.DomainNoteDelete.as_view(),
         name='domain_note_delete'),
    path('domains/import/', views.import_domains, name='domain_import'),
]

# URLs for creating, updating, and deleting static servers
urlpatterns += [
    path('servers/create/', views.ServerCreate.as_view(),
         name='server_create'),
    path('servers/<int:pk>/update/', views.ServerUpdate.as_view(),
         name='server_update'),
    path('servers/<int:pk>/delete/', views.ServerDelete.as_view(),
         name='server_delete'),
    path('servers/<int:pk>/add_note/', views.ServerNoteCreate.as_view(),
         name='server_note_add'),
    path('servers/<int:pk>/edit_note/', views.ServerNoteUpdate.as_view(),
         name='server_note_edit'),
    path('servers/<int:pk>/delete_note/', views.ServerNoteDelete.as_view(),
         name='server_note_delete'),
    path('servers/create_vps/<int:pk>', views.TransientServerCreate.as_view(),
         name='vps_create'),
    path('servers/<int:pk>/update_vps/', views.TransientServerUpdate.as_view(),
         name='vps_update'),
    path('servers/<int:pk>/delete_vps/', views.TransientServerDelete.as_view(),
         name='vps_delete'),
    path('project/<int:pk>/create_link/',
         views.DomainServerConnectionCreate.as_view(),
         name='link_create'),
    path('project/<int:pk>/update_link/',
         views.DomainServerConnectionUpdate.as_view(),
         name='link_update'),
    path('project/<int:pk>/delete_link/',
         views.DomainServerConnectionDelete.as_view(),
         name='link_delete'),
    path('servers/import/', views.import_servers, name='server_import'),
]

# URLs for creating, updating, and deleting project histories
urlpatterns += [
    path('domains/history/<int:pk>/create/', views.HistoryCreate.as_view(),
         name='history_create'),
    path('domains/history/<int:pk>/update/', views.HistoryUpdate.as_view(),
         name='history_update'),
    path('domains/history/<int:pk>/delete/', views.HistoryDelete.as_view(),
         name='history_delete'),
    path('servers/history/<int:pk>/create/',
         views.ServerHistoryCreate.as_view(),
         name='server_history_create'),
    path('servers/history/<int:pk>/update/',
         views.ServerHistoryUpdate.as_view(),
         name='server_history_update'),
    path('servers/history/<int:pk>/delete/',
         views.ServerHistoryDelete.as_view(),
         name='server_history_delete'),
]

# URLs for management functions
urlpatterns += [
    path('update/', views.update, name='update'),
    path('update_category/', views.update_cat, name='update_cat'),
    path('update_category/<int:pk>/', views.update_cat_single,
         name='update_cat_single'),
    path('update_dns/', views.update_dns, name='update_dns'),
    path('update_dns/<int:pk>/', views.update_dns_single,
         name='update_dns_single'),
    path('update_namecheap/', views.pull_domains_namecheap,
         name='update_namecheap'),
]
