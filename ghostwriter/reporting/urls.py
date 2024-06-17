"""This contains all the URL mappings used by the Reporting application."""

# Django Imports
from django.urls import path

# Ghostwriter Libraries
from ghostwriter.reporting import views

app_name = "reporting"

# URLs for the basic views
urlpatterns = [
    path("", views.index, name="index"),
    path("findings/", views.FindingListView.as_view(), name="findings"),
    path("reports/", views.ReportListView.as_view(), name="reports"),
    path("templates/", views.ReportTemplateListView.as_view(), name="templates"),
    path("reports/archive", views.archive_list, name="archived_reports"),
    path(
        "reports/archive/download/<int:pk>/",
        views.ArchiveDownloadView.as_view(),
        name="download_archive",
    ),
    path("observations/", views.ObservationListView.as_view(), name="observations"),
]

# URLs for AJAX requests – deletion and toggle views
urlpatterns += [
    path(
        "ajax/report/finding/order",
        views.ajax_update_report_findings,
        name="update_report_findings",
    ),
    path(
        "ajax/report/observation/order",
        views.ajax_update_report_observations,
        name="update_report_observations",
    ),
    path(
        "ajax/report/activate/<int:pk>",
        views.ReportActivate.as_view(),
        name="ajax_activate_report",
    ),
    path(
        "ajax/report/finding/status/<int:pk>/<str:status>",
        views.ReportFindingStatusUpdate.as_view(),
        name="ajax_set_finding_status",
    ),
    path(
        "ajax/report/status/toggle/<int:pk>",
        views.ReportStatusToggle.as_view(),
        name="ajax_toggle_report_status",
    ),
    path(
        "ajax/report/delivery/<int:pk>",
        views.ReportDeliveryToggle.as_view(),
        name="ajax_toggle_report_delivery",
    ),
    path(
        "ajax/report/note/delete/<int:pk>",
        views.LocalFindingNoteDelete.as_view(),
        name="ajax_delete_local_finding_note",
    ),
    path(
        "ajax/finding/note/delete/<int:pk>",
        views.FindingNoteDelete.as_view(),
        name="ajax_delete_finding_note",
    ),
    path(
        "ajax/finding/assign/<int:pk>",
        views.AssignFinding.as_view(),
        name="ajax_assign_finding",
    ),
    path(
        "ajax/finding/delete/<int:pk>",
        views.ReportFindingLinkDelete.as_view(),
        name="ajax_delete_local_finding",
    ),
    path(
        "ajax/observation/assign/<int:pk>",
        views.AssignObservation.as_view(),
        name="ajax_assign_observation",
    ),
    path(
        "ajax/obseravation/delete/<int:pk>",
        views.ReportObservationLinkDelete.as_view(),
        name="ajax_delete_local_observation",
    ),
    path(
        "ajax/report/template/swap/<int:pk>",
        views.ReportTemplateSwap.as_view(),
        name="ajax_swap_report_template",
    ),
    path(
        "ajax/report/template/lint/<int:pk>",
        views.ReportTemplateLint.as_view(),
        name="ajax_lint_report_template",
    ),
    path(
        "ajax/report/template/lint/results/<int:pk>",
        views.UpdateTemplateLintResults.as_view(),
        name="ajax_update_template_lint_results",
    ),
]

# URLs for creating, updating, and deleting findings
urlpatterns += [
    path("findings/<int:pk>", views.FindingDetailView.as_view(), name="finding_detail"),
    path("findings/create/", views.FindingCreate.as_view(), name="finding_create"),
    path("findings/update/<int:pk>", views.FindingUpdate.as_view(), name="finding_update"),
    path("findings/delete/<int:pk>", views.FindingDelete.as_view(), name="finding_delete"),
    path(
        "findings/notes/create/<int:pk>",
        views.FindingNoteCreate.as_view(),
        name="finding_note_add",
    ),
    path(
        "findings/notes/update/<int:pk>",
        views.FindingNoteUpdate.as_view(),
        name="finding_note_edit",
    ),
]

# URLs for creating, updating, and deleting observations
urlpatterns += [
    path("observations/<int:pk>", views.ObservationDetailView.as_view(), name="observation_detail"),
    path("observations/create/", views.ObservationCreate.as_view(), name="observation_create"),
    path("observations/update/<int:pk>", views.ObservationUpdate.as_view(), name="observation_update"),
    path("observations/delete/<int:pk>", views.ObservationDelete.as_view(), name="observation_delete"),
]

# URLs for creating, updating, and deleting reports
urlpatterns += [
    path("reports/<int:pk>", views.ReportDetailView.as_view(), name="report_detail"),
    path("reports/create/<int:pk>", views.ReportCreate.as_view(), name="report_create"),
    path(
        "reports/create/",
        views.ReportCreate.as_view(),
        name="report_create_no_project",
    ),
    path("reports/update/<int:pk>", views.ReportUpdate.as_view(), name="report_update"),
    path("reports/delete/<int:pk>", views.ReportDelete.as_view(), name="report_delete"),
    path("reports/archive/<int:pk>", views.ArchiveView.as_view(), name="archive"),
    path("reports/clone/<int:pk>", views.ReportClone.as_view(), name="report_clone"),
    path(
        "reports/create/blank/<int:pk>",
        views.AssignBlankFinding.as_view(),
        name="assign_blank_finding",
    ),
    path(
        "reports/create/blank-observation/<int:pk>",
        views.AssignBlankObservation.as_view(),
        name="assign_blank_observation",
    ),
    path(
        "reports/<int:pk>/edit-extra-field/<str:extra_field_name>",
        views.ReportExtraFieldEdit.as_view(),
        name="report_extra_field_edit",
    ),
    path(
        "templates/<int:pk>",
        views.ReportTemplateDetailView.as_view(),
        name="template_detail",
    ),
    path(
        "templates/create",
        views.ReportTemplateCreate.as_view(),
        name="template_create",
    ),
    path(
        "templates/update/<int:pk>",
        views.ReportTemplateUpdate.as_view(),
        name="template_update",
    ),
    path(
        "templates/delete/<int:pk>",
        views.ReportTemplateDelete.as_view(),
        name="template_delete",
    ),
    path(
        "templates/download/<int:pk>",
        views.ReportTemplateDownload.as_view(),
        name="template_download",
    ),
    path(
        "evidence/download/<int:pk>",
        views.EvidenceDownload.as_view(),
        name="evidence_download",
    ),
    path(
        "evidence/preview/<int:pk>",
        views.EvidencePreview.as_view(),
        name="evidence_preview",
    ),
]

# URLs for local edits
urlpatterns += [
    path(
        "reports/findings/update/<int:pk>",
        views.ReportFindingLinkUpdate.as_view(),
        name="local_edit",
    ),
    path(
        "reports/observations/update/<int:pk>",
        views.ReportObservationLinkUpdate.as_view(),
        name="local_observation_edit",
    ),
    path(
        "reports/evidence/upload/<str:parent_type>/<int:pk>",
        views.EvidenceCreate.as_view(),
        name="upload_evidence",
    ),
    path(
        "reports/evidence/upload/<str:parent_type>/<int:pk>/<str:modal>",
        views.EvidenceCreate.as_view(),
        name="upload_evidence_modal",
    ),
    path(
        "reports/evidence/modal/success",
        views.upload_evidence_modal_success,
        name="upload_evidence_modal_success",
    ),
    path(
        "reports/evidence/<int:pk>",
        views.EvidenceDetailView.as_view(),
        name="evidence_detail",
    ),
    path(
        "reports/evidence/update/<int:pk>",
        views.EvidenceUpdate.as_view(),
        name="evidence_update",
    ),
    path(
        "reports/evidence/delete/<int:pk>",
        views.EvidenceDelete.as_view(),
        name="evidence_delete",
    ),
    path(
        "reports/notes/create/<int:pk>",
        views.LocalFindingNoteCreate.as_view(),
        name="local_finding_note_add",
    ),
    path(
        "reports/notes/update/<int:pk>",
        views.LocalFindingNoteUpdate.as_view(),
        name="local_finding_note_edit",
    ),
    path(
        "reports/findings/convert/<int:pk>",
        views.ConvertFinding.as_view(),
        name="convert_finding",
    ),
    path(
        "reports/observations/convert/<int:pk>",
        views.ConvertObservation.as_view(),
        name="convert_observation",
    ),
]

# URLs for generating reports
urlpatterns += [
    path(
        "reports/<int:pk>/docx/",
        views.GenerateReportDOCX.as_view(),
        name="generate_docx",
    ),
    path(
        "reports/<int:pk>/xlsx/",
        views.GenerateReportXLSX.as_view(),
        name="generate_xlsx",
    ),
    path(
        "reports/<int:pk>/pptx/",
        views.GenerateReportPPTX.as_view(),
        name="generate_pptx",
    ),
    path(
        "reports/<int:pk>/raw/",
        views.GenerateReportJSON.as_view(),
        name="generate_json",
    ),
    path("reports/<int:pk>/all/", views.GenerateReportAll.as_view(), name="generate_all"),
]

# URLs for management functions
urlpatterns += [
    path("export/findings/csv/", views.export_findings_to_csv, name="export_findings_to_csv"),
    path("export/observations/csv/", views.export_observations_to_csv, name="export_observations_to_csv"),
]
