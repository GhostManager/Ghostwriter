"""This contains all of the URL mappings for the Rolodex application. The
`urlpatterns` list routes URLs to views. For more information please see:

https://docs.djangoproject.com/en/2.1/topics/http/urls/
"""

from . import views
from django.urls import path

app_name = "rolodex"

# URLs for the basic views
urlpatterns = [
                path('', views.index, name='index'),
                path('clients/', views.ClientListView.as_view(),
                     name='clients'),
                path('projects/', views.ProjectListView.as_view(),
                     name='projects'),
                path('projects/complete',
                     views.CompleteProjectListView.as_view(),
                     name='closed_projects'),
                path('clients/<int:pk>', views.ClientDetailView.as_view(),
                     name='client_detail'),
                path('projects/<int:pk>', views.ProjectDetailView.as_view(),
                     name='project_detail'),
                path('codename/<int:pk>/client', views.assign_client_codename,
                     name='client_codename'),
                path('codename/<int:pk>/project',
                     views.assign_project_codename,
                     name='project_codename'),
              ]

# URLs for creating, updating, and deleting clients
urlpatterns += [
                path('clients/create/', views.ClientCreate.as_view(),
                     name='client_create'),
                path('clients/<int:pk>/update/', views.ClientUpdate.as_view(),
                     name='client_update'),
                path('clients/<int:pk>/delete/', views.ClientDelete.as_view(),
                     name='client_delete'),
                path('clients/<int:pk>/add_poc/',
                     views.ClientContactCreate.as_view(),
                     name='client_poc_add'),
                path('clients/<int:pk>/edit_poc/',
                     views.ClientContactUpdate.as_view(),
                     name='client_poc_edit'),
                path('clients/<int:pk>/delete_poc/',
                     views.ClientContactDelete.as_view(),
                     name='client_poc_delete'),
                path('clients/<int:pk>/add_note/',
                     views.ClientNoteCreate.as_view(),
                     name='client_note_add'),
                path('clients/<int:pk>/edit_note/',
                     views.ClientNoteUpdate.as_view(),
                     name='client_note_edit'),
                path('clients/<int:pk>/delete_note/',
                     views.ClientNoteDelete.as_view(),
                     name='client_note_delete'),
               ]

# URLs for creating, updating, and deleting projects
urlpatterns += [
                path('projects/<int:pk>/create',
                     views.ProjectCreate.as_view(),
                     name='project_create'),
                path('projects/<int:pk>/update/',
                     views.ProjectUpdate.as_view(),
                     name='project_update'),
                path('projects/<int:pk>/delete/',
                     views.ProjectDelete.as_view(),
                     name='project_delete'),
                path('projects/<int:pk>/assignment',
                     views.AssignmentCreate.as_view(),
                     name='assign_operator'),
                path('projects/<int:pk>/assignment_edit',
                     views.AssignmentUpdate.as_view(),
                     name='assignment_edit'),
                path('projects/<int:pk>/assignment_delete',
                     views.AssignmentDelete.as_view(),
                     name='assignment_delete'),
                path('projects/<int:pk>/add_note/',
                     views.ProjectNoteCreate.as_view(),
                     name='project_note_add'),
                path('projects/<int:pk>/edit_note/',
                     views.ProjectNoteUpdate.as_view(),
                     name='project_note_edit'),
                path('projects/<int:pk>/delete_note/',
                     views.ProjectNoteDelete.as_view(),
                     name='project_note_delete'),
                path('projects/<int:pk>/complete/',
                     views.complete_project,
                     name='complete_project'),
                path('projects/<int:pk>/reopen/',
                     views.reopen_project,
                     name='reopen_project'),
               ]
