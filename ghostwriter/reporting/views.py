"""This contains all of the views used by the Reporting application."""

# Standard Libraries
import io
import json
import logging
import logging.config
import os
import zipfile
from datetime import datetime

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, PermissionRequiredMixin
from django.core.files import File
from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
    JsonResponse,
)
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.views import generic
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View

# 3rd Party Libraries
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from docx.image.exceptions import UnrecognizedImageError
from docx.opc.exceptions import PackageNotFoundError as DocxPackageNotFoundError
from pptx.exc import PackageNotFoundError as PptxPackageNotFoundError
from xlsxwriter.workbook import Workbook

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import ReportConfiguration
from ghostwriter.modules import reportwriter
from ghostwriter.modules.exceptions import MissingTemplate
from ghostwriter.rolodex.models import Project, ProjectAssignment

from .filters import ArchiveFilter, FindingFilter, ReportFilter
from .forms import (
    EvidenceForm,
    FindingForm,
    FindingNoteForm,
    LocalFindingNoteForm,
    ReportFindingLinkUpdateForm,
    ReportForm,
    ReportTemplateForm,
    SelectReportTemplateForm,
)
from .models import (
    Archive,
    Evidence,
    Finding,
    FindingNote,
    FindingType,
    LocalFindingNote,
    Report,
    ReportFindingLink,
    ReportTemplate,
    Severity,
)
from .resources import FindingResource

channel_layer = get_channel_layer()

User = get_user_model()

# Using __name__ resolves to ghostwriter.reporting.views
logger = logging.getLogger(__name__)


##################
# AJAX Functions #
##################


@login_required
def ajax_update_report_findings(request):
    """
    Update the ``position`` and ``severity`` fields of all :model:`reporting.ReportFindingLink`
    attached to an individual :model:`reporting.Report`.
    """
    if request.method == "POST" and request.is_ajax():
        data = request.POST.get("positions")
        report_id = request.POST.get("report")
        severity_class = request.POST.get("severity").replace("_severity", "")
        order = json.loads(data)

        logger.info(
            "Received AJAX POST to update report %s's %s severity group findings in this order: %s",
            report_id,
            severity_class,
            ", ".join(order),
        )

        try:
            severity = Severity.objects.get(severity__iexact=severity_class)
        except Severity.DoesNotExist:
            severity = None
        if severity:
            counter = 1
            for finding_id in order:
                if "placeholder" not in finding_id:
                    finding_instance = ReportFindingLink.objects.get(id=finding_id)
                    if finding_instance:
                        finding_instance.severity = severity
                        finding_instance.position = counter
                        finding_instance.save()
                        counter += 1
                    else:
                        logger.error(
                            "Received a finding ID, %s, that did not match an existing finding",
                            finding_id,
                        )
        else:
            data = {"result": "specified severity, {}, is invalid".format(severity_class)}
        # If all went well, return success
        data = {"result": "success"}
    else:
        data = {"result": "error"}
    return JsonResponse(data)


class UpdateTemplateLintResults(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following a request to update linter results
    for an individual :model:`reporting.ReportTemplate`.

    **Template**

    :template:`snippets/template_lint_results.html`
    """

    model = ReportTemplate

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        html = render_to_string(
            "snippets/template_lint_results.html",
            {"reporttemplate": self.object},
        )
        return HttpResponse(html)


class FindingAssignment(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Copy an individual :model:`reporting.Finding` to create a new
    :model:`reporting.ReportFindingLink` connected to the user's active
    :model:`reporting.Report`.
    """

    model = Finding

    def get_position(self, report_pk):
        finding_count = ReportFindingLink.objects.filter(
            Q(report__pk=report_pk) & Q(severity=self.object.severity)
        ).count()
        if finding_count:
            try:
                # Get all other findings of the same severity with last position first
                finding_positions = ReportFindingLink.objects.filter(
                    Q(report__pk=report_pk) & Q(severity=self.object.severity)
                ).order_by("-position")
                # Set new position to be one above the last/largest position
                last_position = finding_positions[0].position
                return last_position + 1
            except Exception:
                return finding_count + 1
        else:
            return 1

    def post(self, *args, **kwargs):
        self.object = self.get_object()

        # The user must have the ``active_report`` session variable
        # Get the variable and default to ``None`` if it does not exist
        active_report = self.request.session.get("active_report", None)
        if active_report:
            try:
                report = Report.objects.get(pk=active_report["id"])
            except Exception:
                message = (
                    "Please select a report to edit before trying to assign a finding"
                )
                data = {"result": "error", "message": message}
                return JsonResponse(data)

            # Clone the selected object to make a new :model:`reporting.ReportFindingLink`
            report_link = ReportFindingLink(
                title=self.object.title,
                description=self.object.description,
                impact=self.object.impact,
                mitigation=self.object.mitigation,
                replication_steps=self.object.replication_steps,
                host_detection_techniques=self.object.host_detection_techniques,
                network_detection_techniques=self.object.network_detection_techniques,
                references=self.object.references,
                severity=self.object.severity,
                finding_type=self.object.finding_type,
                finding_guidance=self.object.finding_guidance,
                report=report,
                assigned_to=self.request.user,
                position=self.get_position(report.id),
            )
            report_link.save()

            message = "{} successfully added to your active report".format(self.object)
            data = {"result": "success", "message": message}
            logger.info(
                "Copied %s %s to %s %s (%s %s) by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                report.__class__.__name__,
                report.id,
                report_link.__class__.__name__,
                report_link.id,
                self.request.user,
            )
        else:
            message = "Please select a report to edit before trying to assign a finding"
            data = {"result": "error", "message": message}
        return JsonResponse(data)


class LocalFindingNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`reporting.LocalFindingNote`.
    """

    model = LocalFindingNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


class FindingNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`reporting.FindingNote`.
    """

    model = FindingNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


class ReportFindingLinkDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`reporting.ReportFindingLink`.
    """

    model = ReportFindingLink

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.report_pk = self.get_object().report.pk

        # Get all other findings with the same severity for this report ID
        findings_queryset = ReportFindingLink.objects.filter(
            Q(report=self.get_object().report.pk) & Q(severity=self.get_object().severity)
        )
        if findings_queryset:
            for finding in findings_queryset:
                # Adjust position to close gap created by removed finding
                if finding.position > self.get_object().position:
                    finding.position -= 1
                    finding.save()

        self.object.delete()
        data = {
            "result": "success",
            "message": "Successfully deleted {finding} and cleaned up evidence".format(
                finding=self.object
            ),
        }
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )

        return JsonResponse(data)


class ReportActivate(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Set an individual :model:`reporting.Report` as active for the current user session.
    """

    model = Report

    # Set the user's session variable
    def post(self, *args, **kwargs):
        self.object = self.get_object()

        try:
            self.request.session["active_report"] = {}
            self.request.session["active_report"]["id"] = self.object.id
            self.request.session["active_report"]["title"] = self.object.title
            message = "{report} is now your active report".format(
                report=self.object.title
            )
            data = {
                "result": "success",
                "report": self.object.title,
                "report_url": self.object.get_absolute_url(),
                "message": message,
            }
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not set the selected report as your active report",
            }

        return JsonResponse(data)


class ReportStatusToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.Report`.
    """

    model = Report

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.complete:
                self.object.complete = False
                data = {
                    "result": "success",
                    "message": "Report successfully marked as incomplete",
                    "status": "Draft",
                    "toggle": 0,
                }
            else:
                self.object.complete = True
                data = {
                    "result": "success",
                    "message": "Report successfully marked as complete",
                    "status": "Complete",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update report's status"}

        return JsonResponse(data)


class ReportDeliveryToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``delivered`` field of an individual :model:`rolodex.Report`.
    """

    model = Report

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.delivered:
                self.object.delivered = False
                data = {
                    "result": "success",
                    "message": "Report successfully marked as not delivered",
                    "status": "Not Delivered",
                    "toggle": 0,
                }
            else:
                self.object.delivered = True
                data = {
                    "result": "success",
                    "message": "Report successfully marked as delivered",
                    "status": "Delivered",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled delivery status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not update report's deliveery status",
            }

        return JsonResponse(data)


class ReportFindingStatusUpdate(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Update the ``complete`` field of an individual :model:`reporting.ReportFindingLink`.
    """

    model = ReportFindingLink

    def post(self, *args, **kwargs):
        data = {}
        # Get ``status`` kwargs from the URL
        status = self.kwargs["status"]
        self.object = self.get_object()

        try:
            result = "success"
            if status.lower() == "edit":
                self.object.complete = False
                message = "Successfully flagged finding for editing"
                display_status = "Needs Editing"
                classes = "burned"
            elif status.lower() == "complete":
                self.object.complete = True
                message = "Successfully marking finding as complete"
                display_status = "Ready"
                classes = "healthy"
            else:
                result = "error"
                message = "Could not update the finding's status to: {}".format(status)
                display_status = "Error"
                classes = "burned"
            self.object.save()
            # Prepare the JSON response data
            data = {
                "result": result,
                "status": display_status,
                "classes": classes,
                "message": message,
            }
            logger.info(
                "Set status of %s %s to %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                status,
                self.request.user,
            )
        # Return an error message if the query for the requested status returned DoesNotExist
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update finding's status"}

        return JsonResponse(data)


class ReportTemplateSwap(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Update the ``template`` value for an individual :model:`reporting.Report`.
    """

    model = Report

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        docx_template_id = self.request.POST.get("docx_template", None)
        pptx_template_id = self.request.POST.get("pptx_template", None)
        if docx_template_id and pptx_template_id:
            docx_template_query = None
            pptx_template_query = None
            try:
                docx_template_id = int(docx_template_id)
                pptx_template_id = int(pptx_template_id)

                if docx_template_id == -1 or pptx_template_id == -1:
                    data = {
                        "result": "warning",
                        "message": "You need to select a template",
                    }
                else:
                    if not docx_template_id == -1:
                        docx_template_query = ReportTemplate.objects.get(
                            pk=docx_template_id
                        )
                        self.object.docx_template = docx_template_query
                    if not pptx_template_id == -1:
                        pptx_template_query = ReportTemplate.objects.get(
                            pk=pptx_template_id
                        )
                        self.object.pptx_template = pptx_template_query
                    data = {
                        "result": "success",
                        "message": "Template successfully swapped",
                    }
                    self.object.save()

                # Check template for linting issues
                try:
                    if docx_template_query:
                        template_status = docx_template_query.get_status()
                        data["lint_result"] = template_status
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
                except Exception:
                    logger.exception("Failed to get the template status")
                    data[
                        "docx_lint_message"
                    ] = "Could not retrieve the Word template's linter status. Check and lint the template before generating a report."
                try:
                    if pptx_template_query:
                        template_status = pptx_template_query.get_status()
                        data["lint_result"] = template_status
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
                except Exception:
                    logger.exception("Failed to get the template status")
                    data[
                        "pptx_lint_message"
                    ] = "Could not retrieve the PowerPoint template's linter status. Check and lint the template before generating a report."
                logger.info(
                    "Swapped template for %s %s by request of %s",
                    self.object.__class__.__name__,
                    self.object.id,
                    self.request.user,
                )
            except ValueError:
                data = {
                    "result": "error",
                    "message": "Submitted template ID was not an integer",
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
                    "message": "Submitted template ID does not exist",
                }
                logger.error(
                    "Received one or two invalid (non-existent) template IDs (%s & %s) from a request submitted by %s",
                    docx_template_id,
                    pptx_template_id,
                    self.request.user,
                )
            except Exception:
                data = {
                    "result": "error",
                    "message": "An exception prevented the template change",
                }
                logger.exception(
                    "Encountered an error trying to update %s %s with template IDs %s & %s from a request submitted by %s",
                    self.object.__class__.__name__,
                    self.object.id,
                    docx_template_id,
                    pptx_template_id,
                    self.request.user,
                )
        else:
            data = {"result": "error", "message": "Submitted request was incomplete"}
            logger.warning(
                "Received bad template IDs (%s & %s) from a request submitted by %s",
                docx_template_id,
                pptx_template_id,
                self.request.user,
            )
        return JsonResponse(data)


class ReportTemplateLint(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Check an individual :model:`reporting.ReportTemplate` for Jinja2 syntax errors
    and undefined variables.
    """

    model = ReportTemplate

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        template_loc = self.object.document.path
        linter = reportwriter.TemplateLinter(template_loc=template_loc)
        if self.object.doc_type.doc_type == "docx":
            results = linter.lint_docx()
        elif self.object.doc_type.doc_type == "pptx":
            results = linter.lint_pptx()
        else:
            logger.warning(
                "Template had an unknown filetype not supported by the linter: %s",
                self.object.doc_type,
            )
            results = {}
        self.object.lint_result = results
        self.object.save()

        data = json.loads(results)
        if data["result"] == "success":
            data[
                "message"
            ] = "Template linter returned results with no errors or warnings"
        elif not data["result"]:
            data[
                "message"
            ] = f"Template had an unknown filetype not supported by the linter: {self.object.doc_type}"
        else:
            data[
                "message"
            ] = "Template linter returned results with issues that require attention"

        return JsonResponse(data)


##################
# View Functions #
##################


@login_required
def index(request):
    """
    Display the main homepage.
    """
    return HttpResponseRedirect(reverse("home:dashboard"))


@login_required
def findings_list(request):
    """
    Display a list of all :model:`reporting.Finding`.

    **Context**

    ``filter``
        Instance of :filter:`reporting.FindingFilter`

    **Template**

    :template:`reporting/finding_list.html`
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get("finding_search")
    except Exception:
        search_term = ""
    if search_term:
        messages.success(
            request,
            "Displaying search results for: {}".format(search_term),
            extra_tags="alert-success",
        )
        findings_list = (
            Finding.objects.select_related("severity", "finding_type")
            .filter(
                Q(title__icontains=search_term) | Q(description__icontains=search_term)
            )
            .order_by("severity__weight", "finding_type", "title")
        )
    else:
        findings_list = (
            Finding.objects.select_related("severity", "finding_type")
            .all()
            .order_by("severity__weight", "finding_type", "title")
        )
    findings_filter = FindingFilter(request.GET, queryset=findings_list)
    return render(request, "reporting/finding_list.html", {"filter": findings_filter})


@login_required
def reports_list(request):
    """
    Display a list of all :model:`reporting.Report`.

    **Template**

    :template:`reporting/report_list.html`
    """
    reports_list = (
        Report.objects.select_related("created_by").all().order_by("complete", "title")
    )
    reports_filter = ReportFilter(request.GET, queryset=reports_list)
    return render(request, "reporting/report_list.html", {"filter": reports_filter})


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
    archive_list = (
        Archive.objects.select_related("project__client")
        .all()
        .order_by("project__client")
    )
    archive_filter = ArchiveFilter(request.GET, queryset=archive_list)
    return render(request, "reporting/archives.html", {"filter": archive_filter})


@login_required
def assign_blank_finding(request, pk):
    """
    Create a blank :model:`reporting.ReportFindingLink` entry linked to an individual
    :model:`reporting.Report`.
    """
    info_sev = Severity.objects.get(severity="Informational")

    def get_position(report_pk):
        finding_count = ReportFindingLink.objects.filter(
            Q(report__pk=pk) & Q(severity=info_sev)
        ).count()
        if finding_count:
            try:
                # Get all other findings of the same severity with last position first
                finding_positions = ReportFindingLink.objects.filter(
                    Q(report__pk=pk) & Q(severity=info_sev)
                ).order_by("-position")
                # Set new position to be one above the last/largest position
                last_position = finding_positions[0].position
                return last_position + 1
            except Exception:
                return finding_count + 1
        else:
            return 1

    try:
        report = Report.objects.get(pk=pk)
    except Exception:
        messages.error(
            request,
            "A valid report could not be found for this blank finding",
            extra_tags="alert-danger",
        )
        return HttpResponseRedirect(reverse("reporting:reports"))
    report_link = ReportFindingLink(
        title="Blank Template",
        description="",
        impact="",
        mitigation="",
        replication_steps="",
        host_detection_techniques="",
        network_detection_techniques="",
        references="",
        severity=info_sev,
        finding_type=FindingType.objects.get(finding_type="Network"),
        report=report,
        assigned_to=request.user,
        position=get_position(report),
    )
    report_link.save()
    messages.success(
        request,
        "Added a blank finding to the report",
        extra_tags="alert-success",
    )
    return HttpResponseRedirect(reverse("reporting:report_detail", args=(report.id,)))


@login_required
def upload_evidence_modal_success(request):
    """
    Display message following the successful creation of an individual
    :model:`reporting.Evidence` using a TinyMCE URLDialog.

    **Template**

    :template:`reporting/evidence_modal_success.html`
    """
    return render(request, "reporting/evidence_modal_success.html")


def generate_report_name(report_instance):
    """
    Generate a filename for a report based on the current time and attributes of an
    individual :model:`reporting.Report`. All periods and commas are removed to keep
    the filename browser-friendly.
    """

    def replace_chars(report_name):
        return report_name.replace(".", "").replace(",", "")

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    client_name = report_instance.project.client
    assessment_type = report_instance.project.project_type
    report_name = replace_chars(f"{timestamp}_{client_name}_{assessment_type}")
    return report_name


@login_required
def zip_directory(path, zip_handler):
    """
    Compress the target directory as a Zip file for archiving.
    """
    # Walk the target directory
    abs_src = os.path.abspath(path)
    for root, dirs, files in os.walk(path):
        # Add each file to the zip file handler
        for file in files:
            absname = os.path.abspath(os.path.join(root, file))
            arcname = absname[len(abs_src) + 1 :]
            zip_handler.write(os.path.join(root, file), "evidence/" + arcname)


@login_required
def archive(request, pk):
    """
    Generate all report types for an individual :model:`reporting.Report`, collect all
    related :model:`reporting.Evidence` and related files, and compress the files into a
    single Zip file for arhciving.
    """
    try:
        report_instance = Report.objects.select_related("project", "project__client").get(
            pk=pk
        )
        output_path = os.path.join(settings.MEDIA_ROOT, report_instance.title)
        evidence_path = os.path.join(settings.MEDIA_ROOT)
        archive_loc = os.path.join(settings.MEDIA_ROOT, "archives")
        evidence_loc = os.path.join(settings.MEDIA_ROOT, "evidence", str(pk))
        report_name = generate_report_name(report_instance)

        # Get the templates for Word and PowerPoint
        if report_instance.docx_template:
            docx_template = report_instance.docx_template
        else:
            docx_template = ReportTemplate.objects.get(
                default=True, doc_type__doc_type="docx"
            )
        if report_instance.pptx_template:
            pptx_template = report_instance.pptx_template
        else:
            pptx_template = ReportTemplate.objects.get(
                default=True, doc_type__doc_type="pptx"
            )

        engine = reportwriter.Reportwriter(
            report_instance, output_path, evidence_path, template_loc=None
        )
        json_doc, word_doc, excel_doc, ppt_doc = engine.generate_all_reports(
            docx_template, pptx_template
        )

        # Convert the dict to pretty JSON output for the file
        pretty_json = json.dumps(json_doc, indent=4)

        # Create a zip file in memory and add the reports to it
        zip_buffer = io.BytesIO()
        zf = zipfile.ZipFile(zip_buffer, "a")
        zf.writestr("report.json", pretty_json)
        zf.writestr("report.docx", word_doc.getvalue())
        zf.writestr("report.xlsx", excel_doc.getvalue())
        zf.writestr("report.pptx", ppt_doc.getvalue())
        zip_directory(evidence_loc, zf)
        zf.close()
        zip_buffer.seek(0)
        with open(os.path.join(archive_loc, report_name + ".zip"), "wb") as archive_file:
            archive_file.write(zip_buffer.read())
            new_archive = Archive(
                client=report_instance.project.client,
                report_archive=File(
                    open(os.path.join(archive_loc, report_name + ".zip"), "rb")
                ),
            )
        new_archive.save()
        messages.success(
            request,
            "Successfully archived {}".format(report_instance.title),
            extra_tags="alert-success",
        )
        return HttpResponseRedirect(reverse("reporting:archived_reports"))
    except Report.DoesNotExist:
        messages.error(
            request,
            "The target report does not exist",
            extra_tags="alert-danger",
        )
    except ReportTemplate.DoesNotExist:
        messages.error(
            request,
            "You do not have templates selected for Word and PowerPoint and have not selected default templates",
            extra_tags="alert-danger",
        )
        return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": pk}))
    except Exception:
        messages.error(
            request,
            "Failed to generate one or more documents for the archive",
            extra_tags="alert-danger",
        )
    return HttpResponseRedirect(reverse("reporting:report_detail", kwargs={"pk": pk}))


@login_required
def download_archive(request, pk):
    """
    Return the target :model:`reporting.Report` archive file for download.
    """
    archive_instance = Archive.objects.get(pk=pk)
    file_path = os.path.join(settings.MEDIA_ROOT, archive_instance.report_archive.path)
    if os.path.exists(file_path):
        with open(file_path, "rb") as archive:
            response = HttpResponse(
                archive.read(), content_type="application/x-zip-compressed"
            )
            response["Content-Disposition"] = "inline; filename=" + os.path.basename(
                file_path
            )
            return response
    raise Http404


@login_required
def clone_report(request, pk):
    """
    Create an identical copy of an individual :model:`reporting.Report`.
    """
    report_instance = ReportFindingLink.objects.select_related("report").filter(report=pk)
    # Clone the report by editing title, setting PK to `None`, and saving it
    report_to_clone = report_instance[0].report
    report_to_clone.title = report_to_clone.title + " Copy"
    report_to_clone.complete = False
    report_to_clone.pk = None
    report_to_clone.save()
    new_report_pk = report_to_clone.pk
    for finding in report_instance:
        finding.report = report_to_clone
        finding.pk = None
        finding.save()
    return HttpResponseRedirect(
        reverse("reporting:report_detail", kwargs={"pk": new_report_pk})
    )


@login_required
def convert_finding(request, pk):
    """
    Create a copy of an individual :model:`reporting.ReportFindingLink` and prepare
    it to be saved as a new :model:`reporting.Finding`.

    **Template**

    :template:`reporting/finding_form.html`
    """
    if request.method == "POST":
        form = FindingForm(request.POST)
        if form.is_valid():
            new_finding = form.save()
            new_finding_pk = new_finding.pk
            return HttpResponseRedirect(
                reverse("reporting:finding_detail", kwargs={"pk": new_finding_pk})
            )
    else:
        finding_instance = get_object_or_404(ReportFindingLink, pk=pk)
        form = FindingForm(
            initial={
                "title": finding_instance.title,
                "description": finding_instance.description,
                "impact": finding_instance.impact,
                "mitigation": finding_instance.mitigation,
                "replication_steps": finding_instance.replication_steps,
                "host_detection_techniques": finding_instance.host_detection_techniques,
                "network_detection_techniques": finding_instance.network_detection_techniques,
                "references": finding_instance.references,
                "severity": finding_instance.severity,
                "finding_type": finding_instance.finding_type,
            }
        )
    return render(request, "reporting/finding_form.html", {"form": form})


@login_required
def export_findings_to_csv(request):
    """
    Export all :model:`reporting.Finding` to a csv file for download.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    fiinding_resource = FindingResource()
    dataset = fiinding_resource.export()
    response = HttpResponse(dataset.csv, content_type="text/csv")
    response["Content-Disposition"] = f'attachment; filename="{timestamp}_findings.csv"'

    return response


################
# View Classes #
################

# CBVs related to :model:`reporting.Finding`


class FindingDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`reporting.Finding`.

    **Template**

    :template:`reporting/finding_detail.html`
    """

    model = Finding


class FindingCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.Finding`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to clients list page

    **Template**

    :template:`reporting/finding_form.html`
    """

    model = Finding
    form_class = FindingForm

    def get_context_data(self, **kwargs):
        ctx = super(FindingCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:findings")
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully added {} to the findings library".format(self.object.title),
            extra_tags="alert-success",
        )
        return reverse("reporting:finding_detail", kwargs={"pk": self.object.pk})


class FindingUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.Finding`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to clients list page

    **Template**

    :template:`reporting/finding_form.html`
    """

    model = Finding
    form_class = FindingForm

    def get_context_data(self, **kwargs):
        ctx = super(FindingUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:finding_detail", kwargs={"pk": self.object.pk}
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Master record for {} was successfully updated".format(
                self.get_object().title
            ),
            extra_tags="alert-success",
        )
        return reverse("reporting:finding_detail", kwargs={"pk": self.object.pk})


class FindingDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.Finding`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.Finding`
    ``cancel_link``
        Link for the form's Cancel button to return to finding list page

    **Template**

    :template:`confirm_delete.html`
    """

    model = Finding
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request,
            "Master record for {} was successfully deleted".format(
                self.get_object().title
            ),
            extra_tags="alert-warning",
        )
        return reverse_lazy("reporting:findings")

    def get_context_data(self, **kwargs):
        ctx = super(FindingDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "finding master record"
        ctx["object_to_be_deleted"] = queryset.title
        ctx["cancel_link"] = reverse("reporting:findings")
        return ctx


# CBVs related to :model:`reporting.Report`


class ReportDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`reporting.Report`.

    **Template**

    :template:`reporting/report_detail.html`
    """

    model = Report

    def get_context_data(self, **kwargs):
        ctx = super(ReportDetailView, self).get_context_data(**kwargs)
        form = SelectReportTemplateForm(instance=self.object)
        form.fields["docx_template"].queryset = ReportTemplate.objects.filter(
            Q(doc_type__doc_type="docx") & Q(client=self.object.project.client)
            | Q(doc_type__doc_type="docx") & Q(client__isnull=True)
        ).select_related(
            "doc_type",
            "client",
        )
        form.fields["pptx_template"].queryset = ReportTemplate.objects.filter(
            Q(doc_type__doc_type="pptx") & Q(client=self.object.project.client)
            | Q(doc_type__doc_type="pptx") & Q(client__isnull=True)
        ).select_related(
            "doc_type",
            "client",
        )
        ctx["form"] = form
        return ctx


class ReportCreate(LoginRequiredMixin, CreateView):
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
                    self.project = get_object_or_404(Project, pk=self.kwargs.get("pk"))
                except Project.DoesNotExist:
                    logger.info(
                        "Received report create request for Project ID %s, but that Project does not exist",
                        pk,
                    )

    def get_form_kwargs(self):
        kwargs = super(ReportCreate, self).get_form_kwargs()
        kwargs.update({"project": self.project})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(ReportCreate, self).get_context_data(**kwargs)
        ctx["project"] = self.project
        if self.project:
            ctx["cancel_link"] = reverse(
                "rolodex:project_detail", kwargs={"pk": self.project.pk}
            )
        else:
            ctx["cancel_link"] = reverse("reporting:reports")
        return ctx

    def get_form(self, form_class=None):
        form = super(ReportCreate, self).get_form(form_class)
        if not form.fields["project"].queryset:
            messages.error(
                self.request,
                "There are no active projects for a new report",
                extra_tags="alert-error",
            )
        return form

    def form_valid(self, form):
        form.instance.created_by = self.request.user
        self.request.session["active_report"] = {}
        self.request.session["active_report"]["title"] = form.instance.title
        return super().form_valid(form)

    def get_initial(self):
        if self.project:
            title = "{} {} ({}) Report".format(
                self.project.client, self.project.project_type, self.project.start_date
            )
            return {"title": title, "project": self.project.id}

    def get_success_url(self):
        self.request.session["active_report"]["id"] = self.object.pk
        self.request.session.modified = True
        messages.success(
            self.request,
            "Successfully created new report and set it as your active report",
            extra_tags="alert-success",
        )
        return reverse("reporting:report_detail", kwargs={"pk": self.object.pk})


class ReportUpdate(LoginRequiredMixin, UpdateView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Check if this request is for a specific project or not
        self.project = "update"

    def get_form_kwargs(self):
        kwargs = super(ReportUpdate, self).get_form_kwargs()
        kwargs.update({"project": self.project})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(ReportUpdate, self).get_context_data(**kwargs)
        ctx["project"] = self.object.project
        ctx["cancel_link"] = reverse(
            "reporting:report_detail", kwargs={"pk": self.object.pk}
        )
        return ctx

    def form_valid(self, form):
        self.request.session["active_report"] = {}
        self.request.session["active_report"]["id"] = form.instance.id
        self.request.session["active_report"]["title"] = form.instance.title
        self.request.session.modified = True
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(
            self.request, "Successfully updated the report", extra_tags="alert-success"
        )
        return reverse("reporting:report_detail", kwargs={"pk": self.object.pk})


class ReportDelete(LoginRequiredMixin, DeleteView):
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

    def get_success_url(self):
        self.request.session["active_report"] = {}
        self.request.session["active_report"]["id"] = ""
        self.request.session["active_report"]["title"] = ""
        self.request.session.modified = True
        messages.warning(
            self.request,
            "Successfully deleted the report and associated evidence files",
            extra_tags="alert-warning",
        )
        return "{}#reports".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ReportDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse(
            "rolodex:project_detail", kwargs={"pk": self.object.project.pk}
        )
        ctx["object_type"] = "entire report, evidence and all"
        ctx["object_to_be_deleted"] = queryset.title
        return ctx


class ReportTemplateListView(LoginRequiredMixin, generic.ListView):
    """
    Display a list of all :model:`reporting.ReportTemplate`.

    **Template**

    :template:`reporting/report_template_list.html`
    """

    model = ReportTemplate
    template_name = "reporting/report_templates_list.html"


class ReportTemplateDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`reporting.ReportTemplate`.

    **Template**

    :template:`reporting/report_template_list.html`
    """

    model = ReportTemplate
    template_name = "reporting/report_template_detail.html"


class ReportTemplateCreate(LoginRequiredMixin, CreateView):
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
        ctx = super(ReportTemplateCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:templates")
        return ctx

    def get_initial(self):
        date = datetime.now().strftime("%d %B %Y")
        initial_upload = f'<p><span class="bold">{date}</span></p><p>Initial upload</p>'
        return {"changelog": initial_upload}

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
        return HttpResponseRedirect(self.get_success_url())


class ReportTemplateUpdate(LoginRequiredMixin, PermissionRequiredMixin, UpdateView):
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
    permission_denied_message = "Only an admin can edit this template"

    def has_permission(self):
        self.object = self.get_object()
        if self.object.protected:
            return self.request.user.is_staff
        else:
            return self.request.user.is_active

    def handle_no_permission(self):
        messages.error(
            self.request, "That template is protected – only an admin can edit it"
        )
        return HttpResponseRedirect(
            reverse(
                "reporting:template_detail",
                args=(self.object.pk,),
            )
        )

    def get_context_data(self, **kwargs):
        ctx = super(ReportTemplateUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:templates")
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Template successfully updated",
            extra_tags="alert-success",
        )
        return reverse("reporting:template_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.uploaded_by = self.request.user
        self.object.save()
        return HttpResponseRedirect(self.get_success_url())


class ReportTemplateDelete(LoginRequiredMixin, DeleteView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            self.message,
            extra_tags="alert-success",
        )
        return reverse("reporting:templates")

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        self.message = "Successfully deleted the template and associated file"
        if os.path.isfile(self.object.document.path):
            try:
                os.remove(self.object.document.path)
                logger.info("Deleted %s", self.object.document.path)
            except Exception:
                self.message = "Successfully deleted the template, but could not delete the associated file{}"
                logger.warning(
                    "Failed to delete file associated with %s %s: %s",
                    self.object.__class__.__name__,
                    self.object.id,
                    self.object.document.path,
                )
        else:
            logger.info(
                "Tried to delete template file, but path did not exist: %s",
                self.object.document.path,
            )
        return super(ReportTemplateDelete, self).delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(ReportTemplateDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse(
            "reporting:template_detail", kwargs={"pk": queryset.pk}
        )
        ctx["object_type"] = "report template file (and associated file on disk)"
        ctx["object_to_be_deleted"] = queryset.filename
        return ctx


class ReportTemplateDownload(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Return the target :model:`reporting.ReportTemplate` template file for download.
    """

    model = ReportTemplate

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        file_path = os.path.join(settings.MEDIA_ROOT, self.object.document.path)
        if os.path.exists(file_path):
            return FileResponse(
                open(file_path, "rb"),
                as_attachment=True,
                filename=os.path.basename(file_path),
            )
        else:
            raise Http404


class GenerateReportJSON(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Generate a JSON report for an individual :model:`reporting.Report`.
    """

    model = Report

    def get(self, *args, **kwargs):
        self.object = self.get_object()

        logger.info(
            "Generating JSON report for %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )

        engine = reportwriter.Reportwriter(self.object, template_loc=None)
        json_report = engine.generate_json()

        return HttpResponse(json_report, "application/json")


class GenerateReportDOCX(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Generate a DOCX report for an individual :model:`reporting.Report`.
    """

    model = Report

    def get(self, *args, **kwargs):
        self.object = self.get_object()

        logger.info(
            "Generating DOCX report for %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )

        try:
            report_name = generate_report_name(self.object)
            engine = reportwriter.Reportwriter(self.object, template_loc=None)

            # Get the template for this report
            if self.object.docx_template:
                report_template = self.object.docx_template
            else:
                report_config = ReportConfiguration.get_solo()
                report_template = report_config.default_docx_template
                if not report_template:
                    raise MissingTemplate
            template_loc = report_template.document.path

            # Check template's linting status
            template_status = report_template.get_status()
            if template_status == "error" or template_status == "failed":
                messages.error(
                    self.request,
                    "The selected report template has linting errors and cannot be used to render a DOCX document",
                    extra_tags="alert-danger",
                )
                return HttpResponseRedirect(
                    reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
                )

            # Template available and passes linting checks, so proceed with generation
            engine = reportwriter.Reportwriter(self.object, template_loc)
            docx = engine.generate_word_docx()

            response = HttpResponse(
                content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            )
            response["Content-Disposition"] = f'attachment; filename="{report_name}.docx"'
            docx.save(response)

            # Send WebSocket message to update user's webpage
            async_to_sync(channel_layer.group_send)(
                "report_{}".format(self.object.pk),
                {
                    "type": "status_update",
                    "message": {"status": "success"},
                },
            )

            return response
        except MissingTemplate:
            logger.error(
                "DOCX generation failed for %s %s and user %s because no template was configured",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "You do not have a Word template selected and have not configured a default template",
                extra_tags="alert-danger",
            )
        except DocxPackageNotFoundError:
            logger.exception(
                "DOCX generation failed for %s %s and user %s because the template file was missing",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Your selected Word template could not be found on the server – try uploading it again",
                extra_tags="alert-danger",
            )
        except FileNotFoundError as error:
            logger.exception(
                "DOCX generation failed for %s %s and user %s because an evidence file was missing",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Halted document generation because an evidence file is missing: {}".format(
                    error
                ),
                extra_tags="alert-danger",
            )
        except UnrecognizedImageError as error:
            logger.exception(
                "DOCX generation failed for %s %s and user %s because of an unrecognized or corrupt image",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error)
                .replace('"', "")
                .replace("'", "`"),
                extra_tags="alert-danger",
            )
        except Exception as error:
            logger.exception(
                "DOCX generation failed unexpectedly for %s %s and user %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error)
                .replace('"', "")
                .replace("'", "`"),
                extra_tags="alert-danger",
            )

        return HttpResponseRedirect(
            reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
        )


class GenerateReportXLSX(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Generate an XLSX report for an individual :model:`reporting.Report`.
    """

    model = Report

    def get(self, *args, **kwargs):
        self.object = self.get_object()

        logger.info(
            "Generating XLSX report for %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        try:
            report_name = generate_report_name(self.object)
            engine = reportwriter.Reportwriter(self.object, template_loc=None)

            output = io.BytesIO()
            workbook = Workbook(output, {"in_memory": True})
            engine.generate_excel_xlsx(workbook)
            output.seek(0)
            response = HttpResponse(
                output.read(),
                content_type="application/application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
            response["Content-Disposition"] = f'attachment; filename="{report_name}.xlsx"'
            output.close()

            return response
        except Exception as error:
            logger.exception(
                "XLSX generation failed unexpectedly for %s %s and user %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the spreadsheet: {}".format(error),
                extra_tags="alert-danger",
            )
        return HttpResponseRedirect(
            reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
        )


class GenerateReportPPTX(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Generate a PPTX report for an individual :model:`reporting.Report`.
    """

    model = Report

    def get(self, *args, **kwargs):
        self.object = self.get_object()

        logger.info(
            "Generating PPTX report for %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )

        try:
            report_name = generate_report_name(self.object)
            engine = reportwriter.Reportwriter(self.object, template_loc=None)

            # Get the template for this report
            if self.object.pptx_template:
                report_template = self.object.pptx_template
            else:
                report_config = ReportConfiguration.get_solo()
                report_template = report_config.default_pptx_template
                if not report_template:
                    raise MissingTemplate
            template_loc = report_template.document.path

            # Check template's linting status
            template_status = report_template.get_status()
            if template_status == "error" or template_status == "failed":
                messages.error(
                    self.request,
                    "The selected report template has linting errors and cannot be used to render a PPTX document",
                    extra_tags="alert-danger",
                )
                return HttpResponseRedirect(
                    reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
                )

            # Template available and passes linting checks, so proceed with generation
            engine = reportwriter.Reportwriter(self.object, template_loc)
            pptx = engine.generate_powerpoint_pptx()
            response = HttpResponse(
                content_type="application/application/vnd.openxmlformats-officedocument.presentationml.presentation"
            )
            response["Content-Disposition"] = f'attachment; filename="{report_name}.pptx"'
            pptx.save(response)

            return response
        except MissingTemplate:
            logger.error(
                "PPTX generation failed for %s %s and user %s because no template was configured",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "You do not have a PowerPoint template selected and have not configured a default template",
                extra_tags="alert-danger",
            )
        except ValueError as exception:
            logger.exception(
                "PPTX generation failed for %s %s and user %s because the template could not be loaded as a PPTX",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                f"Your selected template could not be loaded as a PowerPoint template: {exception}",
                extra_tags="alert-danger",
            )
        except PptxPackageNotFoundError:
            logger.exception(
                "PPTX generation failed for %s %s and user %s because the template file was missing",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Your selected PowerPoint template could not be found on the server – try uploading it again",
                extra_tags="alert-danger",
            )
        except FileNotFoundError as error:
            logger.exception(
                "PPTX generation failed for %s %s and user %s because an evidence file was missing",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Halted document generation because an evidence file is missing: {}".format(
                    error
                ),
                extra_tags="alert-danger",
            )
        except UnrecognizedImageError as error:
            logger.exception(
                "PPTX generation failed for %s %s and user %s because of an unrecognized or corrupt image",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error)
                .replace('"', "")
                .replace("'", "`"),
                extra_tags="alert-danger",
            )
        except Exception as error:
            logger.exception(
                "PPTX generation failed unexpectedly for %s %s and user %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error)
                .replace('"', "")
                .replace("'", "`"),
                extra_tags="alert-danger",
            )

        return HttpResponseRedirect(
            reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
        )


class GenerateReportAll(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Generate all report types for an individual :model:`reporting.Report`.
    """

    model = Report

    def get(self, *args, **kwargs):
        self.object = self.get_object()

        logger.info(
            "Generating PPTX report for %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        try:
            report_name = generate_report_name(self.object)
            engine = reportwriter.Reportwriter(self.object, template_loc=None)

            # Get the templates for Word and PowerPoint
            if self.object.docx_template:
                docx_template = self.object.docx_template
            else:
                report_config = ReportConfiguration.get_solo()
                docx_template = report_config.default_docx_template
                if not docx_template:
                    raise MissingTemplate
            docx_template = docx_template.document.path

            if self.object.pptx_template:
                pptx_template = self.object.pptx_template
            else:
                report_config = ReportConfiguration.get_solo()
                pptx_template = report_config.default_pptx_template
                if not pptx_template:
                    raise MissingTemplate
            pptx_template = pptx_template.document.path

            # Generate all types of reports
            json_doc, docx_doc, xlsx_doc, pptx_doc = engine.generate_all_reports(
                docx_template, pptx_template
            )

            # Convert the dict to pretty JSON output for the file
            pretty_json = json.dumps(json_doc, indent=4)

            # Create a zip file in memory and add the reports to it
            zip_buffer = io.BytesIO()
            zf = zipfile.ZipFile(zip_buffer, "a")
            zf.writestr(f"{report_name}.json", pretty_json)
            zf.writestr(f"{report_name}.docx", docx_doc.getvalue())
            zf.writestr(f"{report_name}.xlsx", xlsx_doc.getvalue())
            zf.writestr(f"{report_name}.pptx", pptx_doc.getvalue())
            zf.close()
            zip_buffer.seek(0)

            # Return the buffer in the HTTP response
            response = HttpResponse(content_type="application/x-zip-compressed")
            response["Content-Disposition"] = f'attachment; filename="{report_name}.zip"'
            response.write(zip_buffer.read())

            return response
        except MissingTemplate:
            messages.error(
                self.request,
                "You do not have a PowerPoint template selected and have not configured a default template",
                extra_tags="alert-danger",
            )
        except ValueError as exception:
            messages.error(
                self.request,
                f"Your selected template could not be loaded as a PowerPoint template: {exception}",
                extra_tags="alert-danger",
            )
        except DocxPackageNotFoundError:
            messages.error(
                self.request,
                "Your selected Word template could not be found on the server – try uploading it again",
                extra_tags="alert-danger",
            )
        except PptxPackageNotFoundError:
            messages.error(
                self.request,
                "Your selected PowerPoint template could not be found on the server – try uploading it again",
                extra_tags="alert-danger",
            )
        except Exception as error:
            messages.error(
                self.request,
                "Encountered an error generating the document: {}".format(error),
                extra_tags="alert-danger",
            )

        return HttpResponseRedirect(
            reverse("reporting:report_detail", kwargs={"pk": self.object.pk})
        )


# CBVs related to :model:`reporting.ReportFindingLink`


class ReportFindingLinkUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.ReportFindingLink`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to report's detail page

    **Template**

    :template:`reporting/local_edit.html.html`
    """

    model = ReportFindingLink
    form_class = ReportFindingLinkUpdateForm
    template_name = "reporting/local_edit.html"
    success_url = reverse_lazy("reporting:reports")

    def get_context_data(self, **kwargs):
        ctx = super(ReportFindingLinkUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:report_detail", kwargs={"pk": self.object.report.pk}
        )
        return ctx

    def form_valid(self, form):
        # Check if severity, position, or assigned_to has changed
        if (
            "severity" in form.changed_data
            or "position" in form.changed_data
            or "assigned_to" in form.changed_data
        ):
            # Get the entries current values (those being changed)
            old_entry = ReportFindingLink.objects.get(pk=self.object.pk)
            old_position = old_entry.position
            old_severity = old_entry.severity
            old_assignee = old_entry.assigned_to
            # Notify new assignee over WebSockets
            if "assigned_to" in form.changed_data:
                new_users_assignments = {}
                old_users_assignments = {}
                # Only notify if the assignee is not the user who made the change
                if self.request.user != self.object.assigned_to:
                    # Count the current user's total assignments
                    new_users_assignments = (
                        ReportFindingLink.objects.select_related(
                            "report", "report__project"
                        )
                        .filter(
                            Q(assigned_to=self.object.assigned_to)
                            & Q(report__complete=False)
                            & Q(complete=False)
                        )
                        .count()
                        + 1
                    )
                    old_users_assignments = (
                        ReportFindingLink.objects.select_related(
                            "report", "report__project"
                        )
                        .filter(
                            Q(assigned_to=old_assignee)
                            & Q(report__complete=False)
                            & Q(complete=False)
                        )
                        .count()
                        - 1
                    )
                    # Send a message to the assigned user
                    async_to_sync(channel_layer.group_send)(
                        "notify_{}".format(self.object.assigned_to),
                        {
                            "type": "task",
                            "message": {
                                "message": "You have been assigned to this finding for {}:\n{}".format(
                                    self.object.report, self.object.title
                                ),
                                "level": "info",
                                "title": "New Assignment",
                            },
                            "assignments": new_users_assignments,
                        },
                    )
                if self.request.user != old_assignee and old_users_assignments:
                    # Send a message to the unassigned user
                    async_to_sync(channel_layer.group_send)(
                        "notify_{}".format(old_assignee),
                        {
                            "type": "task",
                            "message": {
                                "message": "You have been unassigned from this finding for {}:\n{}".format(
                                    self.object.report, self.object.title
                                ),
                                "level": "info",
                                "title": "Assignment Change",
                            },
                            "assignments": old_users_assignments,
                        },
                    )
            # If severity rating changed, adjust previous severity group
            if "severity" in form.changed_data:
                # Get a list of findings for the old severity rating
                old_severity_queryset = ReportFindingLink.objects.filter(
                    Q(report__pk=self.object.report.pk) & Q(severity=old_severity)
                ).order_by("position")
                if old_severity_queryset:
                    for finding in old_severity_queryset:
                        # Adjust position to close gap created by moved finding
                        if finding.position > old_position:
                            finding.position -= 1
                            finding.save(update_fields=["position"])
            # Get all findings in report that share the new/current severity rating
            finding_queryset = ReportFindingLink.objects.filter(
                Q(report__pk=self.object.report.pk) & Q(severity=self.object.severity)
            ).order_by("position")
            # Form sets minimum number to 0, but check again for funny business
            if self.object.position < 1:
                self.object.position = 1
            # Last position should not be larger than total findings
            if self.object.position > finding_queryset.count():
                self.object.position = finding_queryset.count()
            counter = 1
            if finding_queryset:
                # Loop from top position down and look for a match
                for finding in finding_queryset:
                    # Check if finding in loop is NOT the finding being updated
                    if not self.object.pk == finding.pk:
                        # Increment position counter when counter equals form value
                        if self.object.position == counter:
                            counter += 1
                        finding.position = counter
                        finding.save(update_fields=["position"])
                        counter += 1
                    else:
                        # Skip the finding being updated by form
                        pass
            # No other findings with the chosen severity, so make it pos 1
            else:
                self.object.position = 1
        return super().form_valid(form)

    def get_form(self, form_class=None):
        form = super(ReportFindingLinkUpdate, self).get_form(form_class)
        user_primary_keys = ProjectAssignment.objects.filter(
            project=self.object.report.project
        ).values_list("operator", flat=True)
        form.fields["assigned_to"].queryset = User.objects.filter(
            id__in=user_primary_keys
        )
        return form

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated {}".format(self.get_object().title),
            extra_tags="alert-success",
        )
        return reverse("reporting:report_detail", kwargs={"pk": self.object.report.id})


# CBVs related to :model:`reporting.Evidence`


class EvidenceDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual instance of :model:`reporting.Evidence`.

    **Template**

    :template:`reporting/evidence_detail.html`
    """

    model = Evidence

    def get_context_data(self, **kwargs):
        ctx = super(EvidenceDetailView, self).get_context_data(**kwargs)
        file_content = None
        if os.path.isfile(self.object.document.path):
            if (
                self.object.document.name.lower().endswith(".txt")
                or self.object.document.name.lower().endswith(".log")
                or self.object.document.name.lower().endswith(".md")
            ):
                filetype = "text"
                file_content = []
                temp = self.object.document.read().splitlines()
                for line in temp:
                    try:
                        file_content.append(line.decode())
                    except Exception:
                        file_content.append(line)
            elif (
                self.object.document.name.lower().endswith(".jpg")
                or self.object.document.name.lower().endswith(".png")
                or self.object.document.name.lower().endswith(".jpeg")
            ):
                filetype = "image"
            else:
                filetype = "unknown"
        else:
            filetype = "text"
            file_content = []
            file_content.append("FILE NOT FOUND")

        ctx["filetype"] = filetype
        ctx["evidence"] = self.object
        ctx["file_content"] = file_content

        return ctx


class EvidenceCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`reporting.Evidence` entry linked to an individual
    :model:`reporting.ReportFindingLink`.

    **Template**

    :template:`reporting/evidence_form.html`
    """

    model = Evidence
    form_class = EvidenceForm

    def get_template_names(self):
        if "modal" in self.kwargs:
            modal = self.kwargs["modal"]
            if modal:
                return ["reporting/evidence_form_modal.html"]
            else:
                return ["reporting/evidence_form.html"]
        else:
            return ["reporting/evidence_form.html"]

    def get_form_kwargs(self):
        kwargs = super(EvidenceCreate, self).get_form_kwargs()
        finding_pk = self.kwargs.get("pk")
        self.evidence_queryset = Evidence.objects.filter(finding=finding_pk)
        kwargs.update({"evidence_queryset": self.evidence_queryset})
        self.finding_instance = get_object_or_404(ReportFindingLink, pk=finding_pk)
        if "modal" in self.kwargs:
            kwargs.update({"is_modal": True})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(EvidenceCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:report_detail", kwargs={"pk": self.finding_instance.report.pk}
        )
        if "modal" in self.kwargs:
            friendly_names = self.evidence_queryset.values_list(
                "friendly_name", flat=True
            )
            used_friendly_names = []
            # Convert the queryset into a list to pass to JavaScript later
            for name in friendly_names:
                used_friendly_names.append(name)
            ctx["used_friendly_names"] = used_friendly_names

        return ctx

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.uploaded_by = self.request.user
        self.object.finding = self.finding_instance
        self.object.save()
        if os.path.isfile(self.object.document.path):
            messages.success(
                self.request,
                "Evidence uploaded successfully",
                extra_tags="alert-success",
            )
        else:
            messages.error(
                self.request,
                "Evidence file failed to upload",
                extra_tags="alert-danger",
            )
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        if "modal" in self.kwargs:
            return reverse("reporting:upload_evidence_modal_success")
        else:
            return reverse(
                "reporting:report_detail", args=(self.object.finding.report.pk,)
            )


class EvidenceUpdate(LoginRequiredMixin, UpdateView):
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

    def get_form_kwargs(self):
        kwargs = super(EvidenceUpdate, self).get_form_kwargs()
        evidence_queryset = Evidence.objects.filter(finding=self.object.finding.pk)
        kwargs.update({"evidence_queryset": evidence_queryset})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super(EvidenceUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:evidence_detail",
            kwargs={"pk": self.object.pk},
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated {}".format(self.get_object().friendly_name),
            extra_tags="alert-success",
        )
        return reverse(
            "reporting:report_detail", kwargs={"pk": self.object.finding.report.pk}
        )


class EvidenceDelete(LoginRequiredMixin, DeleteView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            self.message,
            extra_tags="alert-success",
        )
        return reverse(
            "reporting:report_detail", kwargs={"pk": self.object.finding.report.pk}
        )

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        self.message = "Successfully deleted the evidence and associated file"
        full_path = os.path.join(settings.MEDIA_ROOT, self.object.document.name)
        directory = os.path.dirname(full_path)
        if os.path.isfile(full_path):
            try:
                os.remove(full_path)
            except Exception:
                self.message = "Successfully deleted the evidence, but could not delete the associated file{}"
                logger.warning(
                    "Failed to delete file associated with %s %s: %s",
                    self.object.__class__.__name__,
                    self.object.id,
                    full_path,
                )
        # Try to delete the directory tree if this was the last/only file
        try:
            os.removedirs(directory)
        except Exception:
            logger.warning(
                "Failed to remove empty directory previously associated with %s %s: %s",
                self.object.__class__.__name__,
                self.object.id,
                directory,
            )
        return super(EvidenceDelete, self).delete(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        ctx = super(EvidenceDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = reverse(
            "reporting:evidence_detail", kwargs={"pk": queryset.pk}
        )
        ctx["object_type"] = "evidence file (and associated file on disk)"
        ctx["object_to_be_deleted"] = queryset.friendly_name
        return ctx


# CBVs related to :model:`reporting.Finding`


class FindingNoteCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.FindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = FindingNote
    form_class = FindingNoteForm
    template_name = "note_form.html"

    def get_context_data(self, **kwargs):
        ctx = super(FindingNoteCreate, self).get_context_data(**kwargs)
        finding_instance = get_object_or_404(Finding, pk=self.kwargs.get("pk"))
        ctx["cancel_link"] = reverse(
            "reporting:finding_detail", kwargs={"pk": finding_instance.pk}
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully added your note to this finding",
            extra_tags="alert-success",
        )
        return "{}#notes".format(
            reverse("reporting:finding_detail", kwargs={"pk": self.object.finding.id})
        )

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.finding_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class FindingNoteUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.FindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = FindingNote
    form_class = FindingNoteForm
    template_name = "note_form.html"

    def get_context_data(self, **kwargs):
        ctx = super(FindingNoteUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "reporting:finding_detail", kwargs={"pk": self.object.finding.pk}
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request, "Successfully updated the note", extra_tags="alert-success"
        )
        return reverse("reporting:finding_detail", kwargs={"pk": self.object.finding.pk})


# CBVs related to :model:`reporting.LocalFindingNote`


class LocalFindingNoteCreate(LoginRequiredMixin, CreateView):
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

    def get_context_data(self, **kwargs):
        ctx = super(LocalFindingNoteCreate, self).get_context_data(**kwargs)
        self.finding_instance = get_object_or_404(
            ReportFindingLink, pk=self.kwargs.get("pk")
        )
        ctx["cancel_link"] = reverse(
            "reporting:local_edit", kwargs={"pk": self.finding_instance.pk}
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully added your note to this finding",
            extra_tags="alert-success",
        )
        return reverse("reporting:local_edit", kwargs={"pk": self.object.finding.pk})

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.finding_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class LocalFindingNoteUpdate(LoginRequiredMixin, UpdateView):
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

    def get_context_data(self, **kwargs):
        ctx = super(LocalFindingNoteUpdate, self).get_context_data(**kwargs)
        note_instance = get_object_or_404(LocalFindingNote, pk=self.kwargs.get("pk"))
        ctx["cancel_link"] = reverse(
            "reporting:local_edit", kwargs={"pk": note_instance.finding.id}
        )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request, "Successfully updated the note", extra_tags="alert-success"
        )
        return reverse("reporting:local_edit", kwargs={"pk": self.object.finding.pk})
