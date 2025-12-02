"""This contains all the URL mappings used by the Rolodex application."""

# Django Imports
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Ghostwriter Libraries
from ghostwriter.rolodex import views, views_matrices

app_name = "rolodex"

# URLs for the basic views
urlpatterns = [
    path("", views.index, name="index"),
    path("clients/", views.ClientListView.as_view(), name="clients"),
    path("projects/", views.ProjectListView.as_view(), name="projects"),
]

urlpatterns += [
    path(
        "matrices/vulnerabilities/",
        views_matrices.VulnerabilityMatrixListView.as_view(),
        name="vulnerability_matrix",
    ),
    path(
        "matrices/vulnerabilities/add/",
        views_matrices.VulnerabilityMatrixCreateView.as_view(),
        name="vulnerability_matrix_add",
    ),
    path(
        "matrices/vulnerabilities/<int:pk>/edit/",
        views_matrices.VulnerabilityMatrixUpdateView.as_view(),
        name="vulnerability_matrix_edit",
    ),
    path(
        "matrices/vulnerabilities/upload/",
        views_matrices.VulnerabilityMatrixImportView.as_view(),
        name="vulnerability_matrix_import",
    ),
    path(
        "matrices/vulnerabilities/download/",
        views_matrices.VulnerabilityMatrixExportView.as_view(),
        name="vulnerability_matrix_export",
    ),
    path(
        "matrices/web-issues/",
        views_matrices.WebIssueMatrixListView.as_view(),
        name="web_issue_matrix",
    ),
    path(
        "matrices/web-issues/add/",
        views_matrices.WebIssueMatrixCreateView.as_view(),
        name="web_issue_matrix_add",
    ),
    path(
        "matrices/web-issues/<int:pk>/edit/",
        views_matrices.WebIssueMatrixUpdateView.as_view(),
        name="web_issue_matrix_edit",
    ),
    path(
        "matrices/web-issues/upload/",
        views_matrices.WebIssueMatrixImportView.as_view(),
        name="web_issue_matrix_import",
    ),
    path(
        "matrices/web-issues/download/",
        views_matrices.WebIssueMatrixExportView.as_view(),
        name="web_issue_matrix_export",
    ),
]

# URLs for AJAX requests – deletion and toggle views
urlpatterns += [
    path(
        "ajax/codename/roll",
        views.roll_codename,
        name="ajax_roll_codename",
    ),
    path(
        "ajax/project/toggle/<int:pk>",
        views.ProjectStatusToggle.as_view(),
        name="ajax_toggle_project",
    ),
    path(
        "ajax/project/objective/status/<int:pk>",
        views.ProjectObjectiveStatusUpdate.as_view(),
        name="ajax_set_objective_status",
    ),
    path(
        "ajax/project/objective/order",
        views.ajax_update_project_objectives,
        name="ajax_update_objective_order",
    ),
    path(
        "ajax/project/objective/toggle/<int:pk>",
        views.ProjectObjectiveToggle.as_view(),
        name="ajax_toggle_project_objective",
    ),
    path(
        "ajax/project/objective/refresh/<int:pk>",
        views.ProjectObjectiveRefresh.as_view(),
        name="ajax_update_objective_row",
    ),
    path(
        "ajax/project/objective/delete/<int:pk>",
        views.ProjectObjectiveDelete.as_view(),
        name="ajax_delete_project_objective",
    ),
    path(
        "ajax/project/deconfliction/delete/<int:pk>",
        views.DeconflictionDelete.as_view(),
        name="ajax_delete_project_deconfliction",
    ),
    path(
        "ajax/project/assignment/delete/<int:pk>",
        views.ProjectAssignmentDelete.as_view(),
        name="ajax_delete_project_assignment",
    ),
    path(
        "ajax/project/note/delete/<int:pk>",
        views.ProjectNoteDelete.as_view(),
        name="ajax_delete_project_note",
    ),
    path(
        "ajax/client/contact/delete/<int:pk>",
        views.ClientContactDelete.as_view(),
        name="ajax_delete_client_poc",
    ),
    path(
        "ajax/client/invite/delete/<int:pk>",
        views.ClientInviteDelete.as_view(),
        name="ajax_delete_client_invite",
    ),
    path(
        "ajax/project/invite/delete/<int:pk>",
        views.ProjectInviteDelete.as_view(),
        name="ajax_delete_project_invite",
    ),
    path(
        "ajax/client/note/delete/<int:pk>",
        views.ClientNoteDelete.as_view(),
        name="ajax_delete_client_note",
    ),
    path(
        "ajax/project/refresh/<int:pk>",
        views.update_project_badges,
        name="ajax_update_project_badges",
    ),
    path(
        "ajax/project/contacts/refresh/<int:pk>",
        views.update_project_contacts,
        name="ajax_update_project_contacts",
    ),
    path(
        "ajax/contact/assign/<int:pk>",
        csrf_exempt(views.AssignProjectContact.as_view()),
        name="ajax_assign_project_contact",
    ),
    path(
        "ajax/client/refresh/<int:pk>",
        views.update_client_badges,
        name="ajax_update_client_badges",
    ),
    path(
        "ajax/project/target/compromise/<int:pk>",
        views.ProjectTargetToggle.as_view(),
        name="ajax_toggle_project_target",
    ),
    path(
        "ajax/project/target/delete/<int:pk>",
        views.ProjectTargetDelete.as_view(),
        name="ajax_delete_project_target",
    ),
    path(
        "ajax/project/scope/delete/<int:pk>",
        views.ProjectScopeDelete.as_view(),
        name="ajax_delete_project_scope",
    ),
    path(
        "ajax/project/scope/export/<int:pk>",
        views.ProjectScopeExport.as_view(),
        name="ajax_export_project_scope",
    ),
    path(
        "ajax/project/task/create/<int:pk>",
        views.ProjectTaskCreate.as_view(),
        name="ajax_create_project_task",
    ),
    path(
        "ajax/project/task/toggle/<int:pk>",
        views.ProjectTaskToggle.as_view(),
        name="ajax_toggle_project_task",
    ),
    path(
        "ajax/project/task/delete/<int:pk>",
        views.ProjectTaskDelete.as_view(),
        name="ajax_delete_project_task",
    ),
    path(
        "ajax/project/task/update/<int:pk>",
        views.ProjectTaskUpdate.as_view(),
        name="ajax_update_project_task",
    ),
    path(
        "ajax/project/task/refresh/<int:pk>",
        views.ProjectTaskRefresh.as_view(),
        name="ajax_update_objective_tasks",
    ),
    path(
        "ajax/projects/export/<int:pk>/<str:type_or_template_id>",
        views.GenerateProjectReport.as_view(),
        name="ajax_project_generate_report",
    ),
]

# URLs for :model:`Client` Class Based Views
urlpatterns += [
    path("clients/<int:pk>", views.ClientDetailView.as_view(), name="client_detail"),
    path("clients/create/", views.ClientCreate.as_view(), name="client_create"),
    path("clients/update/<int:pk>", views.ClientUpdate.as_view(), name="client_update"),
    path("clients/delete/<int:pk>", views.ClientDelete.as_view(), name="client_delete"),
    path(
        "clients/notes/create/<int:pk>",
        views.ClientNoteCreate.as_view(),
        name="client_note_add",
    ),
    path(
        "clients/notes/update/<int:pk>",
        views.ClientNoteUpdate.as_view(),
        name="client_note_edit",
    ),
]

# URLs for :model:`Project` Class Based Views
urlpatterns += [
    path("projects/<int:pk>", views.ProjectDetailView.as_view(), name="project_detail"),
    path("projects/<int:pk>/workbook/", views.ProjectWorkbookUpload.as_view(), name="project_workbook"),
    path(
        "projects/<int:pk>/workbook/data/",
        views.ProjectWorkbookDataUpdate.as_view(),
        name="project_workbook_data_update",
    ),
    path("projects/<int:pk>/data/files/", views.ProjectDataFileUpload.as_view(), name="project_data_file_upload"),
    path(
        "projects/<int:pk>/nexpose-missing/",
        views.ProjectNexposeMissingMatrixDownload.as_view(),
        name="project_nexpose_missing_download",
    ),
    path(
        "projects/<int:pk>/web-issue-missing/",
        views.ProjectWebIssueMissingDownload.as_view(),
        name="project_web_issue_missing_download",
    ),
    path(
        "projects/<int:pk>/nexpose-data/",
        views.ProjectNexposeDataDownload.as_view(),
        name="project_nexpose_data_download",
    ),
    path(
        "projects/<int:pk>/web-data/",
        views.ProjectWebDataDownload.as_view(),
        name="project_web_data_download",
    ),
    path(
        "projects/<int:pk>/endpoint-data/",
        views.ProjectEndpointDataDownload.as_view(),
        name="project_endpoint_data_download",
    ),
    path(
        "projects/<int:pk>/firewall-data/",
        views.ProjectFirewallDataDownload.as_view(),
        name="project_firewall_data_download",
    ),
    path(
        "projects/<int:pk>/nexpose-distilled/",
        views.ProjectNexposeDistilledUpdate.as_view(),
        name="project_nexpose_distilled_update",
    ),
    path(
        "projects/<int:pk>/data/ip-list/",
        views.ProjectIPArtifactUpload.as_view(),
        name="project_ip_artifact_upload",
    ),
    path(
        "projects/data-files/<int:pk>/delete/",
        views.ProjectDataFileDelete.as_view(),
        name="project_data_file_delete",
    ),
    path(
        "projects/<int:pk>/data/responses/",
        views.ProjectDataResponsesUpdate.as_view(),
        name="project_data_responses",
    ),
    path(
        "projects/create",
        views.ProjectCreate.as_view(),
        name="project_create_no_client",
    ),
    path("projects/create/<int:pk>", views.ProjectCreate.as_view(), name="project_create"),
    path(
        "projects/update/<int:pk>",
        views.ProjectUpdate.as_view(),
        name="project_update",
    ),
    path(
        "projects/delete/<int:pk>",
        views.ProjectDelete.as_view(),
        name="project_delete",
    ),
    path(
        "projects/notes/create/<int:pk>",
        views.ProjectNoteCreate.as_view(),
        name="project_note_add",
    ),
    path(
        "projects/notes/update/<int:pk>",
        views.ProjectNoteUpdate.as_view(),
        name="project_note_edit",
    ),
    path(
        "projects/deconfliction/create/<int:pk>",
        views.DeconflictionCreate.as_view(),
        name="project_deconfliction_create",
    ),
    path(
        "projects/deconfliction/update/<int:pk>",
        views.DeconflictionUpdate.as_view(),
        name="project_deconfliction_update",
    ),
    path(
        "projects/update/components/<int:pk>",
        views.ProjectComponentsUpdate.as_view(),
        name="project_component_update",
    ),
]
