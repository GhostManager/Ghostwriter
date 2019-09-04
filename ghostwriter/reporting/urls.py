"""
This contains all of the URL mappings for the Reporting application.
"""

from django.urls import path

# from . import views
from .views import (
    EvidenceDelete,
    EvidenceUpdate,
    FindingCreate,
    FindingDelete,
    FindingDetailView,
    FindingUpdate,
    ReportCreate,
    ReportDelete,
    ReportDetailView,
    ReportFindingLinkDelete,
    ReportFindingLinkUpdate,
    ReportUpdate,
    activate_report,
    archive,
    archive_list,
    assign_blank_finding,
    assign_finding,
    clone_report,
    download_archive,
    finding_status_toggle,
    findings_list,
    generate_all,
    generate_docx,
    generate_json,
    generate_pptx,
    generate_xlsx,
    import_findings,
    index,
    position_decrease,
    position_increase,
    report_status_toggle,
    report_delivery_toggle,
    reports_list,
    upload_evidence,
    view_evidence,
    FindingNoteCreate,
    FindingNoteUpdate,
    FindingNoteDelete,
    LocalFindingNoteCreate,
    LocalFindingNoteUpdate,
    LocalFindingNoteDelete,
    convert_finding
) 

app_name = "reporting"

# URLs for the basic views
urlpatterns = [
                path('', index, name='index'),
                path('findings/', findings_list, name='findings'),
                path('reports/', reports_list, name='reports'),
                path('reports/archive', archive_list,
                     name='archived_reports'),
                path('reports/archive/download/<int:pk>/',
                     download_archive, name='download_archive'),
              ]

# URLs for creating, updating, and deleting findings
urlpatterns += [
                path('findings/create/', FindingCreate.as_view(),
                     name='finding_create'),
                path('findings/<int:pk>', FindingDetailView.as_view(),
                     name='finding_detail'),
                path('findings/<int:pk>/update/',
                     FindingUpdate.as_view(), name='finding_update'),
                path('findings/<int:pk>/delete/',
                     FindingDelete.as_view(), name='finding_delete'),
                path('findings/<int:pk>/assign/', assign_finding,
                     name='assign_finding'),
                path('findings/<int:pk>/add_note/', FindingNoteCreate.as_view(),
                    name='finding_note_add'),
                path('findings/<int:pk>/edit_note/', FindingNoteUpdate.as_view(),
                    name='finding_note_edit'),
                path('findings/<int:pk>/delete_note/', FindingNoteDelete.as_view(),
                    name='finding_note_delete'),
               ]

# URLs for creating, updating, and deleting reports
urlpatterns += [
                path('reports/<int:pk>', ReportDetailView.as_view(),
                     name='report_detail'),
                path('reports/<int:pk>/create/', ReportCreate.as_view(),
                     name='report_create'),
                path('reports/<int:pk>/update/', ReportUpdate.as_view(),
                     name='report_update'),
                path('reports/<int:pk>/delete/', ReportDelete.as_view(),
                     name='report_delete'),
                path('reports/<int:pk>/activate/', activate_report,
                     name='activate_report'),
                path('reports/<int:pk>/archive/', archive,
                     name='archive'),
                path('reports/<int:pk>/clone/', clone_report,
                     name='report_clone'),
                path('reports/<int:pk>/create_blank/',
                     assign_blank_finding, name='assign_blank_finding'),
               ]

# URLs for local edits
urlpatterns += [
                path('reports/<int:pk>/local_edit/',
                     ReportFindingLinkUpdate.as_view(),
                     name='local_edit'),
                path('reports/<int:pk>/local_remove/',
                     ReportFindingLinkDelete.as_view(),
                     name='local_remove'),
                path('reports/<int:pk>/evidence/', upload_evidence,
                     name='upload_evidence'),
                path('reports/evidence/<int:pk>', view_evidence,
                     name='evidence_detail'),
                path('reports/evidence/<int:pk>/edit',
                     EvidenceUpdate.as_view(), name='evidence_update'),
                path('reports/evidence/<int:pk>/delete',
                     EvidenceDelete.as_view(), name='evidence_delete'),
                path('reports/<int:pk>/up/', position_increase,
                     name='position_increase'),
                path('reports/<int:pk>/down/', position_decrease,
                     name='position_decrease'),
                path('reports/<int:pk>/add_note/', LocalFindingNoteCreate.as_view(),
                    name='local_finding_note_add'),
                path('reports/<int:pk>/edit_note/', LocalFindingNoteUpdate.as_view(),
                    name='local_finding_note_edit'),
                path('reports/<int:pk>/delete_note/', LocalFindingNoteDelete.as_view(),
                    name='local_finding_note_delete'),
                path('reports/<int:pk>/up/', position_increase,
                     name='position_increase'),
                path('reports/<int:pk>/convert_finding/', convert_finding,
                     name='convert_finding'),
               ]

# URLs for status toggles
urlpatterns += [
                path('reports/<int:pk>/report_status/',
                     report_status_toggle, name='report_status_toggle'),
                path('reports/<int:pk>/finding_status/',
                     finding_status_toggle,
                     name='finding_status_toggle'),
                path('reports/<int:pk>/delivery_status/',
                     report_delivery_toggle, name='report_delivery_toggle'),
               ]

# URLs for generating reports
urlpatterns += [
                path('reports/<int:pk>/generate_docx/',
                     generate_docx, name='generate_docx'),
                path('reports/<int:pk>/generate_xlsx/',
                     generate_xlsx, name='generate_xlsx'),
                path('reports/<int:pk>/generate_pptx/',
                     generate_pptx, name='generate_pptx'),
                path('reports/<int:pk>/generate_json/',
                     generate_json, name='generate_json'),
                path('reports/<int:pk>/generate_all/',
                     generate_all, name='generate_all'),
               ]

# URLs for management functions
urlpatterns += [
                path('import/csv/', import_findings,
                     name='import_findings'),
               ]
