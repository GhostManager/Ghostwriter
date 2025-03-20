"""This contains all the views used by the Reporting application."""

# Standard Libraries
import io
import logging.config
import os
import zipfile
from asgiref.sync import async_to_sync
from datetime import datetime
from os.path import exists
from socket import gaierror

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.db import transaction
from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import generic
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View
from django.views.generic.list import ListView

# 3rd Party Libraries
from channels.layers import get_channel_layer
from crispy_forms.layout import Field

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    ForbiddenJsonResponse,
    get_archives_list,
    get_project_list,
    get_reports_list,
    get_templates_list,
    verify_finding_access,
    verify_access,
    verify_user_is_privileged,
    RoleBasedAccessControlMixin,
)
from ghostwriter.commandcenter.forms import SingleExtraFieldForm
from ghostwriter.commandcenter.models import ExtraFieldSpec, ReportConfiguration
from ghostwriter.modules.exceptions import MissingTemplate
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.modules.reportwriter.base import ReportExportError
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx
from ghostwriter.modules.reportwriter.report.xlsx import ExportReportXlsx
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.reporting.filters import (
    ArchiveFilter,
    ReportFilter,
    ReportTemplateFilter,
)
from ghostwriter.reporting.forms import (
    EvidenceForm,
    FindingForm,
    FindingNoteForm,
    LocalFindingNoteForm,
    ReportFindingLinkUpdateForm,
    ReportForm,
    ReportTemplateForm,
    SelectReportTemplateForm,
)
from ghostwriter.reporting.models import (
    Archive,
    Evidence,
    Finding,
    FindingNote,
    FindingType,
    LocalFindingNote,
    Observation,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    ReportTemplate,
    Severity,
)
from ghostwriter.reporting.resources import FindingResource, ObservationResource
from ghostwriter.rolodex.models import Project, ProjectAssignment

channel_layer = get_channel_layer()

User = get_user_model()

# Using __name__ resolves to ghostwriter.reporting.views
logger = logging.getLogger(__name__)

def zip_directory(path, zip_handler):
    """Compress the target directory as a Zip file for archiving."""
    # Walk the target directory
    abs_src = os.path.abspath(path)
    for root, _, files in os.walk(path):
        # Add each file to the zip file handler
        for file in files:
            absname = os.path.abspath(os.path.join(root, file))
            arcname = absname[len(abs_src) + 1 :]
            zip_handler.write(os.path.join(root, file), "evidence/" + arcname)


##################
# AJAX Functions #
##################

class UpdateTemplateLintResults(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following a request to update linter results
    for an individual :model:`reporting.ReportTemplate`.

    **Template**

    :template:`snippets/template_lint_results.html`
    """

    model = ReportTemplate

    def get(self, *args, **kwargs):
        template = self.get_object()
        html = render_to_string(
            "snippets/template_lint_results.html",
            {"reporttemplate": template},
        )
        return HttpResponse(html)


class LocalFindingNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`reporting.LocalFindingNote`."""

    model = LocalFindingNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("reporting:local_edit", kwargs={"pk": self.get_object().finding.pk}))

    def post(self, *args, **kwargs):
        note = self.get_object()
        note.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            note.__class__.__name__,
            note.id,
            self.request.user,
        )
        return JsonResponse(data)


class FindingNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`reporting.FindingNote`."""

    model = FindingNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("reporting:finding_detail", kwargs={"pk": self.get_object().finding.pk}))

    def post(self, *args, **kwargs):
        note = self.get_object()
        note.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            note.__class__.__name__,
            note.id,
            self.request.user,
        )
        return JsonResponse(data)


class ReportActivate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Set an individual :model:`reporting.Report` as active for the current user session."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        report = self.get_object()
        try:
            self.request.session["active_report"] = {}
            self.request.session["active_report"]["id"] = report.id
            self.request.session["active_report"]["title"] = report.title
            message = "{report} is now your active report and you will be redirected there in 5 seconds...".format(
                report=report.title
            )
            data = {
                "result": "success",
                "report": report.title,
                "report_url": report.get_absolute_url(),
                "message": message,
            }
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not set the selected report as your active report!",
            }

        return JsonResponse(data)


class ReportStatusToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the ``complete`` field of an individual :model:`rolodex.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        report = self.get_object()
        try:
            if report.complete:
                report.complete = False
                data = {
                    "result": "success",
                    "message": "Report successfully marked as incomplete.",
                    "status": "Draft",
                    "toggle": 0,
                }
            else:
                report.complete = True
                data = {
                    "result": "success",
                    "message": "Report successfully marked as complete.",
                    "status": "Complete",
                    "toggle": 1,
                }
            report.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                report.__class__.__name__,
                report.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update report's status!"}

        return JsonResponse(data)


class ReportDeliveryToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the ``delivered`` field of an individual :model:`rolodex.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        report = self.get_object()
        try:
            if report.delivered:
                report.delivered = False
                data = {
                    "result": "success",
                    "message": "Report successfully marked as not delivered.",
                    "status": "Not Delivered",
                    "toggle": 0,
                }
            else:
                report.delivered = True
                data = {
                    "result": "success",
                    "message": "Report successfully marked as delivered.",
                    "status": "Delivered",
                    "toggle": 1,
                }
            report.save()
            logger.info(
                "Toggled delivery status of %s %s by request of %s",
                report.__class__.__name__,
                report.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not update report's delivery status!",
            }

        return JsonResponse(data)


class ReportTemplateSwap(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Update the ``template`` value for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        report = self.get_object()
        docx_template_id = self.request.POST.get("docx_template", None)
        pptx_template_id = self.request.POST.get("pptx_template", None)
        if docx_template_id and pptx_template_id:
            docx_template_query = None
            pptx_template_query = None
            try:
                docx_template_id = int(docx_template_id)
                pptx_template_id = int(pptx_template_id)

                if docx_template_id < 0:
                    report.docx_template = None
                if pptx_template_id < 0:
                    report.pptx_template = None
                if docx_template_id >= 0:
                    docx_template_query = ReportTemplate.objects.get(pk=docx_template_id)
                    report.docx_template = docx_template_query
                if pptx_template_id >= 0:
                    pptx_template_query = ReportTemplate.objects.get(pk=pptx_template_id)
                    report.pptx_template = pptx_template_query
                data = {
                    "result": "success",
                    "message": "Templates successfully updated.",
                }
                report.save()

                # Check template for linting issues
                try:
                    if docx_template_query:
                        template_status = docx_template_query.get_status()
                        data["docx_lint_result"] = template_status
                        if template_status != "success":
                            if template_status == "warning":
                                data[
                                    "docx_lint_message"
                                ] = "Selected Word template has warnings from linter. Check the template before generating a report."
                            elif template_status == "error":
                                data[
                                    "docx_lint_message"
                                ] = "Selected Word template has linting errors and cannot be used to generate a report."
                            elif template_status == "failed":
                                data[
                                    "docx_lint_message"
                                ] = "Selected Word template failed basic linter checks and can't be used to generate a report."
                            else:
                                data[
                                    "docx_lint_message"
                                ] = "Selected Word template has an unknown linter status. Check and lint the template before generating a report."
                            data["docx_url"] = docx_template_query.get_absolute_url()
                except Exception:  # pragma: no cover
                    logger.exception("Failed to get the template status")
                    data["docx_lint_result"] = "failed"
                    data[
                        "docx_lint_message"
                    ] = "Could not retrieve the Word template's linter status. Check and lint the template before generating a report."
                try:
                    if pptx_template_query:
                        template_status = pptx_template_query.get_status()
                        data["pptx_lint_result"] = template_status
                        if template_status != "success":
                            if template_status == "warning":
                                data[
                                    "pptx_lint_message"
                                ] = "Selected PowerPoint template has warnings from linter. Check the template before generating a report."
                            elif template_status == "error":
                                data[
                                    "pptx_lint_message"
                                ] = "Selected PowerPoint template has linting errors and cannot be used to generate a report."
                            elif template_status == "failed":
                                data[
                                    "pptx_lint_message"
                                ] = "Selected PowerPoint template failed basic linter checks and can't be used to generate a report."
                            else:
                                data[
                                    "pptx_lint_message"
                                ] = "Selected PowerPoint template has an unknown linter status. Check and lint the template before generating a report."
                            data["pptx_url"] = pptx_template_query.get_absolute_url()
                except Exception:  # pragma: no cover
                    logger.exception("Failed to get the template status")
                    data["pptx_lint_result"] = "failed"
                    data[
                        "pptx_lint_message"
                    ] = "Could not retrieve the PowerPoint template's linter status. Check and lint the template before generating a report."
                logger.info(
                    "Swapped template for %s %s by request of %s",
                    report.__class__.__name__,
                    report.id,
                    self.request.user,
                )
            except ValueError:
                data = {
                    "result": "error",
                    "message": "Submitted template ID was not an integer.",
                }
                logger.error(
                    "Received one or two invalid (non-integer) template IDs (%s & %s) from a request submitted by %s",
                    docx_template_id,
                    pptx_template_id,
                    self.request.user,
                )
            except ReportTemplate.DoesNotExist:
                data = {
                    "result": "error",
                    "message": "Submitted template ID does not exist.",
                }
                logger.error(
                    "Received one or two invalid (non-existent) template IDs (%s & %s) from a request submitted by %s",
                    docx_template_id,
                    pptx_template_id,
                    self.request.user,
                )
            except Exception:  # pragma: no cover
                data = {
                    "result": "error",
                    "message": "An exception prevented the template change.",
                }
                logger.exception(
                    "Encountered an error trying to update %s %s with template IDs %s & %s from a request submitted by %s",
                    report.__class__.__name__,
                    report.id,
                    docx_template_id,
                    pptx_template_id,
                    self.request.user,
                )
        else:
            data = {"result": "error", "message": "Submitted request was incomplete."}
            logger.warning(
                "Received bad template IDs (%s & %s) from a request submitted by %s",
                docx_template_id,
                pptx_template_id,
                self.request.user,
            )
        return JsonResponse(data)


class ReportTemplateLint(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Check an individual :model:`reporting.ReportTemplate` for Jinja2 syntax errors
    and undefined variables.
    """

    model = ReportTemplate

    def post(self, *args, **kwargs):
        template = self.get_object()
        data = template.lint()
        template.save()
        return JsonResponse(data)


class ReportClone(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Create an identical copy of an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def get(self, *args, **kwargs):
        new_pk = None
        try:
            with transaction.atomic():
                report_to_clone = self.get_object()
                old_pk = report_to_clone.pk

                findings = ReportFindingLink.objects.select_related("report").filter(report=report_to_clone.pk)
                observations = ReportObservationLink.objects.select_related("report").filter(report=report_to_clone.pk)

                report_to_clone.title = report_to_clone.title + " Copy"
                report_to_clone.complete = False
                report_to_clone.pk = None
                report_to_clone.save()
                new_pk = report_to_clone.pk
                for finding in findings:
                    # Get any evidence files attached to the original finding
                    evidences = Evidence.objects.filter(finding=finding.pk)
                    # Create a clone of this finding attached to the new report
                    finding.report = report_to_clone
                    finding.pk = None
                    finding.save()
                    # Clone evidence files and attach them to the new finding
                    for evidence in evidences:
                        if exists(evidence.document.path):
                            evidence_file = File(evidence.document, os.path.basename(evidence.document.name))
                            evidence.finding = finding
                            evidence._current_evidence = None
                            evidence.document = evidence_file
                            evidence.pk = None
                            evidence.save()
                        else:
                            logger.warning(
                                "Evidence file not found: %s",
                                evidence.document.path,
                            )
                            messages.warning(
                                self.request,
                                f"An evidence file was missing and could not be copied: {evidence.friendly_name} ({os.path.basename(evidence.document.name)})",
                                extra_tags="alert-warning",
                            )

                for observation in observations:
                    observation.report = report_to_clone
                    observation.pk = None
                    observation.save()

                for evidence in Evidence.objects.filter(report_id=old_pk):
                    if exists(evidence.document.path):
                        evidence_file = File(evidence.document, os.path.basename(evidence.document.name))
                        evidence.report = report_to_clone
                        evidence._current_evidence = None
                        evidence.document = evidence_file
                        evidence.pk = None
                        evidence.save()
                    else:
                        logger.warning(
                            "Evidence file not found: %s",
                            evidence.document.path,
                        )
                        messages.warning(
                            self.request,
                            f"An evidence file was missing and could not be copied: {evidence.friendly_name} ({os.path.basename(evidence.document.name)})",
                            extra_tags="alert-warning",
                        )

                logger.info(
                    "Cloned %s %s by request of %s",
                    report_to_clone.__class__.__name__,
                    report_to_clone.id,
                    self.request.user,
                )

                messages.success(
                    self.request,
                    "Successfully cloned your report: {}".format(report_to_clone.title),
                    extra_tags="alert-error",
                )
        except Exception as exception:  # pragma: no cover
            logger.exception("Exception while cloning")
            messages.error(
                self.request,
                "Encountered an error while trying to clone your report: {}".format(exception.args),
                extra_tags="alert-error",
            )

        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": new_pk}))


##################
# View Functions #
##################


@login_required
def index(request):
    """Display the main homepage."""
    return HttpResponseRedirect(reverse("home:dashboard"))


@login_required
def archive_list(request):
    """
    Display a list of all :model:`reporting.Report` marked as archived.

    **Context**

    ``filter``
        Instance of :filter:`reporting.ArchiveFilter`

    **Template**

    :template:`reporting/archives.html`
    """
    archives = get_archives_list(request.user)
    archive_filter = ArchiveFilter(request.GET, queryset=archives)
    return render(request, "reporting/archives.html", {"filter": archive_filter})


@login_required
def upload_evidence_modal_success(request):
    """
    Display message following the successful creation of an individual
    :model:`reporting.Evidence` using a TinyMCE URLDialog.

    **Template**

    :template:`reporting/evidence_modal_success.html`
    """
    return render(request, "reporting/evidence_modal_success.html")


@login_required
def export_findings_to_csv(request):
    """Export all :model:`reporting.Finding` to a csv file for download."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    finding_resource = FindingResource()
    dataset = finding_resource.export()
    response = HttpResponse(dataset.csv, content_type="text/csv")
    add_content_disposition_header(response, f"{timestamp}_findings.csv")

    return response


@login_required
def export_observations_to_csv(request):
    """Export all :model:`reporting.Observation` to a csv file for download."""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    observation_resource = ObservationResource()
    dataset = observation_resource.export()
    response = HttpResponse(dataset.csv, content_type="text/csv")
    add_content_disposition_header(response, f"{timestamp}_observations.csv")

    return response


################
# View Classes #
################

# CBVs related to :model:`reporting.Report`


class ReportListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`reporting.Report`.

    **Template**

    :template:`reporting/report_list.html`
    """

    model = Finding
    template_name = "reporting/report_list.html"

    def get_queryset(self):
        return get_reports_list(self.request.user)

    def get(self, request, *args, **kwarg):
        reports_filter = ReportFilter(request.GET, queryset=self.get_queryset())
        return render(request, "reporting/report_list.html", {"filter": reports_filter})


class ArchiveView(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Generate all report types for an individual :model:`reporting.Report`, collect all
    related :model:`reporting.Evidence` and related files, and compress the files into a
    single Zip file for archiving.
    """

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        report_instance = self.get_object()
        try:
            archive_loc = os.path.join(settings.MEDIA_ROOT, "archives/")
            evidence_loc = os.path.join(settings.MEDIA_ROOT, "evidence", str(report_instance.id))

            # Get the templates for Word and PowerPoint
            report_config = ReportConfiguration.get_solo()
            if report_instance.docx_template:
                docx_template = report_instance.docx_template.document.path
            else:
                docx_template = report_config.default_docx_template
                if not docx_template:
                    raise MissingTemplate
            if report_instance.pptx_template:
                pptx_template = report_instance.pptx_template.document.path
            else:
                pptx_template = report_config.default_pptx_template
                if not pptx_template:
                    raise MissingTemplate

            word_exp = ExportReportDocx(report_instance, template_loc=docx_template)
            report_filename = word_exp.render_filename(ReportConfiguration.get_solo().report_filename, ext="zip")
            try:
                word_doc = word_exp.run()
                ppt_doc = ExportReportPptx(report_instance, template_loc=pptx_template).run()
                excel_doc = ExportReportXlsx(report_instance).run()
                json_doc = ExportReportJson(report_instance).run()
            except ReportExportError as error:
                logger.error(
                    "Generation failed for %s %s and user %s: %s",
                    report_instance.__class__.__name__,
                    report_instance.id,
                    self.request.user,
                    error,
                )
                messages.error(
                    self.request,
                    error,
                    extra_tags="alert-danger",
                )
                return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": report_instance.id}))

            # Create a zip file in memory and add the reports to it
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a") as zf:
                zf.writestr("report.json", json_doc.getvalue())
                zf.writestr("report.docx", word_doc.getvalue())
                zf.writestr("report.xlsx", excel_doc.getvalue())
                zf.writestr("report.pptx", ppt_doc.getvalue())
                zip_directory(evidence_loc, zf)
            zip_buffer.seek(0)
            with open(os.path.join(archive_loc, report_filename), "wb+") as archive_file:
                archive_file.write(zip_buffer.getvalue())
            new_archive = Archive(
                project=report_instance.project,
                report_archive=File(zip_buffer, name=report_filename),
            )
            new_archive.save()
            messages.success(
                self.request,
                "Successfully archived {}!".format(report_instance.title),
                extra_tags="alert-success",
            )
            return HttpResponseRedirect(reverse("reporting:archived_reports"))
        except MissingTemplate:
            logger.error(
                "Archive generation failed for %s %s and user %s because no template was configured.",
                report_instance.__class__.__name__,
                report_instance.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "You do not have a Word or PowerPoint template selected and have not configured a default template.",
                extra_tags="alert-danger",
            )
        except Exception:
            logger.exception("Error archiving report.")
            messages.error(
                self.request,
                "Failed to generate one or more documents for the archive.",
                extra_tags="alert-danger",
            )
        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": report_instance.id}))


class ArchiveDownloadView(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Return the target :model:`reporting.Report` archive file for download."""

    model = Archive

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        archive_instance = self.get_object()
        file_path = os.path.join(settings.MEDIA_ROOT, archive_instance.report_archive.path)
        if os.path.exists(file_path):
            with open(file_path, "rb") as archive_file:
                response = HttpResponse(archive_file.read(), content_type="application/x-zip-compressed")
                add_content_disposition_header(response, os.path.basename(file_path))
                return response
        raise Http404


class ReportDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`reporting.Report`.

    **Template**

    :template:`reporting/report_detail.html`
    """

    model = Report

    def __init__(self):
        super().__init__()
        self.finding_autocomplete = []
        self.observation_autocomplete = []

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("reporting:reports")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        form = SelectReportTemplateForm(instance=self.object)
        form.fields["docx_template"].queryset = (
            ReportTemplate.objects.filter(
                doc_type__doc_type="docx",
            )
            .filter(Q(client=self.object.project.client) | Q(client__isnull=True))
            .select_related(
                "doc_type",
                "client",
            )
        )
        form.fields["pptx_template"].queryset = (
            ReportTemplate.objects.filter(
                doc_type__doc_type="pptx",
            )
            .filter(Q(client=self.object.project.client) | Q(client__isnull=True))
            .select_related(
                "doc_type",
                "client",
            )
        )
        ctx["form"] = form

        # Build autocomplete list
        findings = (
            Finding.objects.select_related("severity", "finding_type")
            .all()
            .order_by("severity__weight", "-cvss_score", "finding_type", "title")
        )
        for finding in findings:
            self.finding_autocomplete.append(finding)
        ctx["finding_autocomplete"] = self.finding_autocomplete

        observations = Observation.objects.all().order_by("title")
        for obs in observations:
            self.observation_autocomplete.append(obs)
        ctx["observation_autocomplete"] = self.observation_autocomplete

        ctx["report_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=Report._meta.label)

        ctx["report_config"] = ReportConfiguration.get_solo()

        return ctx


class ReportCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.Report`.

    **Context**

    ``project``
        Instance of :model:`rolodex.Project` associated with this report
    ``cancel_link``
        Link for the form's Cancel button to return to report list or details page

    **Template**

    :template:`reporting/report_form.html`
    """

    model = Report
    form_class = ReportForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Check if this request is for a specific project or not
        self.project = ""
        # Determine if ``pk`` is in the kwargs
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk")
            # Try to get the project from :model:`rolodex.Project`
            if pk:
                try:
                    project = get_object_or_404(Project, pk=self.kwargs.get("pk"))
                    if verify_access(self.request.user, project):
                        self.project = project
                except Project.DoesNotExist:
                    logger.info(
                        "Received report create request for Project ID %s, but that Project does not exist",
                        pk,
                    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"project": self.project, "user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        if self.project:
            ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.project.pk})
        else:
            ctx["cancel_link"] = reverse("reporting:reports")
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not form.fields["project"].queryset:
            messages.error(
                self.request,
                "There are no active projects for a new report",
                extra_tags="alert-error",
            )
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user

        # Add defaults for extra fields
        for spec in ExtraFieldSpec.objects.filter(target_model=Report._meta.label):
            form.instance.extra_fields[spec.internal_name] = spec.initial_value()

        self.request.session["active_report"] = {}
        self.request.session["active_report"]["title"] = form.instance.title
        return super().form_valid(form)

    def get_initial(self):
        if self.project:
            title = "{} {} ({}) Report".format(self.project.client, self.project.project_type, self.project.start_date)
            return {"title": title, "project": self.project.id}
        return super().get_initial()

    def get_success_url(self):
        self.request.session["active_report"]["id"] = self.object.pk
        self.request.session.modified = True
        messages.success(
            self.request,
            "Successfully created new report and set it as your active report",
            extra_tags="alert-success",
        )
        return reverse("reporting:report_detail", kwargs={"pk": self.object.pk})


class ReportUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.Report`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to report's detail page

    **Template**

    :template:`reporting/report_form.html`
    """

    model = Report
    form_class = ReportForm

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("reporting:reports")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update(
            {
                "project": self.get_object().project,
                "user": self.request.user,
            }
        )
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.object.project
        ctx["cancel_link"] = reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
        return ctx

    def form_valid(self, form):
        self.request.session["active_report"] = {}
        self.request.session["active_report"]["id"] = form.instance.id
        self.request.session["active_report"]["title"] = form.instance.title
        self.request.session.modified = True
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Successfully updated the report", extra_tags="alert-success")
        return reverse("reporting:report_detail", kwargs={"pk": self.object.pk})


class ReportDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.Report`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.Report`
    ``cancel_link``
        Link for the form's Cancel button to return to report's detail page

    **Template**

    :template:`confirm_delete.html`
    """

    model = Report
    template_name = "confirm_delete.html"

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("reporting:reports")

    def get_success_url(self):
        # Clear user's session if deleted report is their active report
        if self.object.pk == self.request.session.get("active_report", {}).get("id"):
            self.request.session["active_report"] = {}
            self.request.session["active_report"]["id"] = ""
            self.request.session["active_report"]["title"] = ""
        self.request.session.modified = True
        messages.warning(
            self.request,
            "Successfully deleted the report and associated evidence files",
            extra_tags="alert-warning",
        )
        return "{}#reports".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        ctx["object_type"] = "entire report, evidence and all"
        ctx["object_to_be_deleted"] = queryset.title
        return ctx


class ReportExtraFieldEdit(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def run(self, request, pk, extra_field_name):
        report = self.get_object()
        field_spec = get_object_or_404(ExtraFieldSpec, target_model=Report._meta.label, internal_name=extra_field_name)
        form = SingleExtraFieldForm(
            field_spec,
            request.POST if request.method == "POST" else None,
            initial={field_spec.internal_name: report.extra_fields.get(field_spec.internal_name)},
            create_crispy_field=self._create_crispy_field,
        )
        if request.method == "POST":
            if form.is_valid():
                report.extra_fields[field_spec.internal_name] = form.cleaned_data[field_spec.internal_name]
                report.save()
                return redirect(reverse("reporting:report_detail", kwargs={"pk": report.pk}) + "#extra-fields")

        return render(
            request,
            "reporting/report_extra_field_edit.html",
            {
                "form": form,
                "report": report,
                "field_spec": field_spec,
                "evidence_upload_url": reverse(
                    "reporting:upload_evidence_modal",
                    kwargs={"parent_type": "report", "pk": report.id, "modal": "modal"},
                ),
                "cancel_link": reverse("reporting:report_detail", kwargs={"pk": report.pk}) + "#extra-fields",
            },
        )

    def get(self, request, pk, extra_field_name):
        return self.run(request, pk, extra_field_name)

    def post(self, request, pk, extra_field_name):
        return self.run(request, pk, extra_field_name)

    @staticmethod
    def _create_crispy_field(spec):
        if spec.type == "rich_text":
            return Field(spec.internal_name, css_class="enable-evidence-upload")
        return Field(spec.internal_name)


class ReportTemplateListView(RoleBasedAccessControlMixin, generic.ListView):
    """
    Display a list of all :model:`reporting.ReportTemplate`.

    **Template**

    :template:`reporting/report_template_list.html`
    """

    model = ReportTemplate
    template_name = "reporting/report_templates_list.html"

    def get_queryset(self):
        user = self.request.user
        queryset = get_templates_list(user)
        return queryset

    def get(self, request, *args, **kwarg):
        templates_filter = ReportTemplateFilter(request.GET, queryset=self.get_queryset())
        return render(request, "reporting/report_templates_list.html", {"filter": templates_filter})


class ReportTemplateDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`reporting.ReportTemplate`.

    **Template**

    :template:`reporting/report_template_list.html`
    """

    model = ReportTemplate
    template_name = "reporting/report_template_detail.html"

    def test_func(self):
        client = self.get_object().client
        if client:
            return verify_access(self.request.user, client)
        return self.request.user.is_active

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("reporting:templates")


class ReportTemplateCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.ReportTemplate`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to template list page

    **Template**

    :template:`report_template_form.html`
    """

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = "reporting/report_template_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:templates")
        return ctx

    def get_initial(self):
        date = datetime.now().strftime("%d %B %Y")
        initial_upload = f'<p><span class="bold">{date}</span></p><p>Initial upload</p>'
        return {"changelog": initial_upload, "p_style": "Normal"}

    def get_success_url(self):
        messages.success(
            self.request,
            "Template successfully uploaded",
            extra_tags="alert-success",
        )
        return reverse("reporting:template_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.uploaded_by = self.request.user
        self.object.save()
        form.save_m2m()
        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class ReportTemplateUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Save an individual instance of :model:`reporting.ReportTemplate`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to template list page

    **Template**

    :template:`report_template_form.html`
    """

    model = ReportTemplate
    form_class = ReportTemplateForm
    template_name = "reporting/report_template_form.html"

    def test_func(self):
        obj = self.get_object()
        if obj.protected:
            return verify_user_is_privileged(self.request.user)
        return self.request.user.is_active

    def handle_no_permission(self):
        obj = self.get_object()
        messages.error(self.request, "That template is protected – only an admin can edit it.")
        return HttpResponseRedirect(
            reverse(
                "reporting:template_detail",
                args=(obj.pk,),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:templates")
        ctx["report_configuration"] = ReportConfiguration.get_solo()
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Template successfully updated",
            extra_tags="alert-success",
        )
        return reverse("reporting:template_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.uploaded_by = self.request.user
        obj.save()
        form.save_m2m()

        Report.clear_incorrect_template_defaults(self.object)

        report_config = ReportConfiguration.get_solo()
        if report_config.clear_incorrect_template_defaults(self.object):
            report_config.save()

        return HttpResponseRedirect(self.get_success_url())

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class ReportTemplateDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.ReportTemplate`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.ReportTemplate`
    ``cancel_link``
        Link for the form's Cancel button to return to template's detail page

    **Template**

    :template:`confirm_delete.html`
    """

    model = ReportTemplate
    template_name = "confirm_delete.html"

    def test_func(self):
        obj = self.get_object()
        if obj.protected:
            return verify_user_is_privileged(self.request.user)
        if obj.client:
            return verify_access(self.request.user, obj.client)
        return self.request.user.is_active

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return HttpResponseRedirect(
            reverse(
                "reporting:templates",
            )
        )

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully deleted the template and associated file.",
            extra_tags="alert-success",
        )
        return reverse("reporting:templates")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse("reporting:template_detail", kwargs={"pk": queryset.pk})
        ctx["object_type"] = "report template file (and associated file on disk)"
        ctx["object_to_be_deleted"] = queryset.filename
        return ctx


class ReportTemplateDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Return the target :model:`reporting.ReportTemplate` template file for download."""

    model = ReportTemplate

    def get(self, *args, **kwargs):
        obj = self.get_object()
        file_path = os.path.join(settings.MEDIA_ROOT, obj.document.path)
        if os.path.exists(file_path):
            return FileResponse(
                open(file_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(file_path),
            )
        raise Http404


class EvidenceDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Return the target :model:`reporting.Evidence` file for download."""

    model = Evidence

    def test_func(self):
        return verify_access(self.request.user, self.get_object().associated_report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()
        file_path = os.path.join(settings.MEDIA_ROOT, obj.document.path)
        if os.path.exists(file_path):
            return FileResponse(
                open(file_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(file_path),
            )
        raise Http404


class GenerateReportJSON(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generate a JSON report for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        logger.info(
            "Generating JSON report for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        json_report = ExportReportJson(obj).run()
        return HttpResponse(json_report.getvalue(), "application/json")


class GenerateReportDOCX(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generate a DOCX report for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        logger.info(
            "Generating DOCX report for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        report_config = ReportConfiguration.get_solo()

        # Get the template for this report
        if obj.docx_template:
            report_template = obj.docx_template
        else:
            report_template = report_config.default_docx_template
            if not report_template:
                logger.error(
                    "DOCX generation failed for %s %s and user %s because no template was configured",
                    obj.__class__.__name__,
                    obj.id,
                    self.request.user,
                )
                messages.error(
                    self.request,
                    "You do not have a Word template selected and have not configured a default template.",
                    extra_tags="alert-danger",
                )
                return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.id}))
        template_loc = report_template.document.path

        # Check template's linting status
        template_status = report_template.get_status()
        if template_status in ("error", "failed"):
            messages.error(
                self.request,
                "The selected report template has linting errors and cannot be used to render a DOCX document",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.pk}) + "#generate")

        # Template available and passes linting checks, so proceed with generation

        try:
            exporter = ExportReportDocx(obj, template_loc=template_loc)
            report_name = exporter.render_filename(report_template.filename_override or report_config.report_filename)
            docx = exporter.run()
        except ReportExportError as error:
            logger.error(
                "DOCX generation failed for %s %s and user %s: %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
                error,
            )
            messages.error(
                self.request,
                f"Error: {error}",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.id}))

        response = HttpResponse(
            docx.getvalue(), content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        )
        add_content_disposition_header(response, report_name)

        # Send WebSocket message to update user's webpage
        try:
            async_to_sync(channel_layer.group_send)(
                "report_{}".format(obj.pk),
                {
                    "type": "status_update",
                    "message": {"status": "success"},
                },
            )
        except gaierror:
            # WebSocket are unavailable (unit testing)
            pass

        return response


class GenerateReportXLSX(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generate an XLSX report for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        logger.info(
            "Generating XLSX report for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        try:
            report_config = ReportConfiguration.get_solo()
            exporter = ExportReportXlsx(obj)
            report_name = exporter.render_filename(report_config.report_filename, ext="xlsx")
            output = exporter.run()
            response = HttpResponse(
                output.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            add_content_disposition_header(response, report_name)
            output.close()

            return response
        except Exception as error:
            logger.exception(
                "XLSX generation failed unexpectedly for %s %s and user %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the spreadsheet: {}".format(error),
                extra_tags="alert-danger",
            )
        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.pk}) + "#generate")


class GenerateReportPPTX(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generate a PPTX report for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        logger.info(
            "Generating PPTX report for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        report_config = ReportConfiguration.get_solo()

        try:
            # Get the template for this report
            if obj.pptx_template:
                report_template = obj.pptx_template
            else:
                report_template = report_config.default_pptx_template
                if not report_template:
                    raise MissingTemplate
            template_loc = report_template.document.path

            # Check template's linting status
            template_status = report_template.get_status()
            if template_status in ("error", "failed"):
                messages.error(
                    self.request,
                    "The selected report template has linting errors and cannot be used to render a PPTX document.",
                    extra_tags="alert-danger",
                )
                return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.pk}) + "#generate")

            # Template available and passes linting checks, so proceed with generation
            exporter = ExportReportPptx(obj, template_loc=template_loc)
            report_name = exporter.render_filename(report_template.filename_override or report_config.report_filename)
            pptx = exporter.run()
            response = HttpResponse(
                pptx.getvalue(),
                content_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            )
            add_content_disposition_header(response, report_name)

            return response
        except ReportExportError as error:
            logger.error(
                "PPTX generation failed for %s %s and user %s: %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
                error,
            )
            messages.error(
                self.request,
                f"Error: {error}",
                extra_tags="alert-danger",
            )
        except Exception as error:
            logger.exception(
                "PPTX generation failed unexpectedly for %s %s and user %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error).replace('"', "").replace("'", "`"),
                extra_tags="alert-danger",
            )

        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.pk}) + "#generate")


class GenerateReportAll(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generate all report types for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        logger.info(
            "Generating all reports for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        try:
            report_config = ReportConfiguration.get_solo()

            # Get the templates for Word and PowerPoint
            if obj.docx_template:
                docx_template = obj.docx_template
            else:
                docx_template = report_config.default_docx_template
                if not docx_template:
                    raise MissingTemplate

            if obj.pptx_template:
                pptx_template = obj.pptx_template
            else:
                pptx_template = report_config.default_pptx_template
                if not pptx_template:
                    raise MissingTemplate

            exporters_and_filename_templates = [
                (
                    ExportReportDocx(obj, template_loc=docx_template.document.path),
                    docx_template.filename_override or report_config.report_filename,
                ),
                (
                    ExportReportPptx(obj, template_loc=pptx_template.document.path),
                    pptx_template.filename_override or report_config.report_filename,
                ),
                (ExportReportXlsx(obj), report_config.report_filename),
                (ExportReportJson(obj), report_config.report_filename),
            ]

            zip_filename = exporters_and_filename_templates[0][0].render_filename(
                report_config.report_filename, ext="zip"
            )

            # Create a zip file in memory and add the reports to it
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a") as zf:
                for (exporter, filename_template) in exporters_and_filename_templates:
                    filename = exporter.render_filename(filename_template)
                    doc = exporter.run()
                    zf.writestr(filename, doc.getvalue())
            zip_buffer.seek(0)

            # Return the buffer in the HTTP response
            response = HttpResponse(content_type="application/x-zip-compressed")
            add_content_disposition_header(response, os.path.basename(zip_filename))
            response.write(zip_buffer.read())

            return response
        except ReportExportError as error:
            logger.exception(
                "All report generation failed unexpectedly for %s %s and user %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
            messages.error(
                self.request,
                f"Error: {error}",
                extra_tags="alert-danger",
            )
        except Exception as error:
            logger.exception(
                "All report generation failed unexpectedly for %s %s and user %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error),
                extra_tags="alert-danger",
            )

        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": obj.pk}) + "#generate")


# CBVs related to :model:`reporting.Evidence`


class EvidenceDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual instance of :model:`reporting.Evidence`.

    **Template**

    :template:`reporting/evidence_detail.html`
    """

    model = Evidence

    def test_func(self):
        return verify_access(self.request.user, self.get_object().associated_report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")


class EvidencePreview(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return HTML for displaying a preview of a file in an individual instance of :model:`reporting.Evidence`.
    """

    model = Evidence

    def test_func(self):
        return verify_access(self.request.user, self.get_object().associated_report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.get_object()
        html = render_to_string(
            "snippets/evidence_display.html",
            {"evidence": obj, "report_config": ReportConfiguration.get_solo()},
        )
        return HttpResponse(html)


class EvidenceCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`reporting.Evidence` entry linked to an individual
    :model:`reporting.ReportFindingLink`.

    **Template**

    :template:`reporting/evidence_form.html`
    """

    model = Evidence
    form_class = EvidenceForm

    def test_func(self):
        if self.finding_instance:
            project = self.finding_instance.report.project
        else:
            project = self.report_instance.project
        return verify_access(self.request.user, project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        pk = self.kwargs.get("pk")
        typ = self.kwargs.get("parent_type")
        if typ == "report":
            self.finding_instance = None
            self.report_instance = get_object_or_404(Report, pk=pk)
            report = self.report_instance
        elif typ == "finding":
            self.finding_instance = get_object_or_404(ReportFindingLink, pk=pk)
            self.report_instance = None
            report = self.finding_instance.report
        else:
            raise Http404("Unrecognized evidence parent model type: {!r}".format(typ))
        self.evidence_queryset = report.all_evidences()

    def get_template_names(self):
        if "modal" in self.kwargs:
            modal = self.kwargs["modal"]
            if modal:
                return ["reporting/evidence_form_modal.html"]
            return ["reporting/evidence_form.html"]
        return ["reporting/evidence_form.html"]

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"evidence_queryset": self.evidence_queryset})
        if "modal" in self.kwargs:
            kwargs.update({"is_modal": True})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        if self.finding_instance:
            report = self.finding_instance.report
        else:
            report = self.report_instance
        ctx["cancel_link"] = reverse("reporting:report_detail", kwargs={"pk": report.pk}) + "#evidence"
        if "modal" in self.kwargs:
            friendly_names = self.evidence_queryset.values_list("friendly_name", flat=True)
            used_friendly_names = []
            # Convert the queryset into a list to pass to JavaScript later
            for name in friendly_names:
                used_friendly_names.append(name)
            ctx["used_friendly_names"] = used_friendly_names

        return ctx

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.uploaded_by = self.request.user
        if self.finding_instance:
            obj.finding = self.finding_instance
        else:
            obj.report = self.report_instance
        obj.save()
        form.save_m2m()
        if os.path.isfile(obj.document.path):
            messages.success(
                self.request,
                "Evidence uploaded successfully.",
                extra_tags="alert-success",
            )
        else:
            messages.error(
                self.request,
                "Evidence file failed to upload!",
                extra_tags="alert-danger",
            )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if "modal" in self.kwargs:
            return reverse("reporting:upload_evidence_modal_success")
        if self.report_instance:
            report_pk = self.report_instance.pk
        else:
            report_pk = self.finding_instance.report.pk
        return reverse("reporting:report_detail", args=(report_pk,)) + "#evidence"


class EvidenceUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.Evidence`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to evidence's detail page

    **Template**

    :template:`reporting/evidence_form.html`
    """

    model = Evidence
    form_class = EvidenceForm

    def test_func(self):
        return verify_access(self.request.user, self.get_object().associated_report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"evidence_queryset": self.object.associated_report.all_evidences()})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:evidence_detail",
            kwargs={"pk": self.object.pk},
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated {}.".format(self.get_object().friendly_name),
            extra_tags="alert-success",
        )
        return reverse("reporting:evidence_detail", kwargs={"pk": self.object.pk})


class EvidenceDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.Evidence`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.Evidence`
    ``cancel_link``
        Link for the form's Cancel button to return to evidence's detail page

    **Template**

    :template:`confirm_delete.html`
    """

    model = Evidence
    template_name = "confirm_delete.html"

    def test_func(self):
        return verify_access(self.request.user, self.get_object().associated_report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        message = "Successfully deleted the evidence and associated file."
        if os.path.isfile(self.object.document.name):
            message = "Successfully deleted the evidence, but could not delete the associated file."
        messages.success(
            self.request,
            message,
            extra_tags="alert-success",
        )
        return reverse("reporting:report_detail", kwargs={"pk": self.object.associated_report.pk}) + "#evidence"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse("reporting:evidence_detail", kwargs={"pk": queryset.pk}) + "#evidence"
        ctx["object_type"] = "evidence file (and associated file on disk)"
        ctx["object_to_be_deleted"] = queryset.friendly_name
        return ctx


# CBVs related to :model:`reporting.LocalFindingNote`


class LocalFindingNoteCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.LocalFindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = LocalFindingNote
    form_class = LocalFindingNoteForm
    template_name = "note_form.html"

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.finding_instance = get_object_or_404(ReportFindingLink, pk=self.kwargs.get("pk"))

    def test_func(self):
        return verify_access(self.request.user, self.finding_instance.report.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:local_edit", kwargs={"pk": self.finding_instance.pk})
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully added your note to this finding.",
            extra_tags="alert-success",
        )
        return reverse("reporting:local_edit", kwargs={"pk": self.object.finding.pk})

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.finding_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class LocalFindingNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.LocalFindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = LocalFindingNote
    form_class = LocalFindingNoteForm
    template_name = "note_form.html"

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("reporting:local_edit", kwargs={"pk": self.get_object().finding.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        note_instance = get_object_or_404(LocalFindingNote, pk=self.kwargs.get("pk"))
        ctx["cancel_link"] = reverse("reporting:local_edit", kwargs={"pk": note_instance.finding.id})
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Successfully updated the note.", extra_tags="alert-success")
        return reverse("reporting:local_edit", kwargs={"pk": self.get_object().finding.pk})
