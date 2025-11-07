"""This contains all the views used by the Reporting application."""

# Standard Libraries
import logging
import os
from datetime import datetime
from os.path import exists

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.files import File
from django.db import transaction
from django.db.models import Q, Max
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
from django.views.generic import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView

# 3rd Party Libraries
from channels.layers import get_channel_layer

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    ForbiddenJsonResponse,
    get_archives_list,
    verify_user_is_privileged,
    RoleBasedAccessControlMixin,
)
from ghostwriter.commandcenter.models import ReportConfiguration
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.reporting.filters import ArchiveFilter
from ghostwriter.reporting.forms import (
    EvidenceForm,
    LocalFindingNoteForm,
)
from ghostwriter.reporting.models import (
    Evidence,
    FindingNote,
    LocalFindingNote,
    Report,
    ReportFindingLink,
    ReportObservationLink,
    ReportTemplate,
)
from ghostwriter.reporting.resources import FindingResource, ObservationResource

channel_layer = get_channel_layer()

User = get_user_model()

# Using __name__ resolves to ghostwriter.reporting.views
logger = logging.getLogger(__name__)

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
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        report = self.get_object()
        try:
            self.request.session["active_report"] = {}
            self.request.session["active_report"]["id"] = report.id
            self.request.session["active_report"]["title"] = report.title
            message = "{report} is now your active report and you can open it with the button at the top of the sidebar.".format(
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
        return self.get_object().user_can_edit(self.request.user)

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
        return self.get_object().user_can_edit(self.request.user)

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
        return self.get_object().user_can_edit(self.request.user)

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
        obj = self.get_object()
        return obj.user_can_view(self.request.user) and Report.user_can_create(self.request.user, obj.project)

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

# CBVs related to :model:`reporting.Evidence`


class EvidenceDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual instance of :model:`reporting.Evidence`.

    **Template**

    :template:`reporting/evidence_detail.html`
    """

    model = Evidence

    def test_func(self):
        return self.get_object().associated_report.user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")


class EvidencePreview(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return HTML for displaying a preview of a file in an individual instance of :model:`reporting.Evidence`.
    """

    model = Evidence

    def test_func(self):
        return self.get_object().associated_report.user_can_view(self.request.user)

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
            report = self.finding_instance.report
        else:
            report = self.report_instance
        return report.user_can_edit(self.request.user)

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
        if self.kwargs.get("modal", False):
            return ["reporting/evidence_form_modal.html"]
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

    def form_valid(self, form: EvidenceForm):
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
        if self.request.accepts("text/html") or not self.request.accepts("application/json"):
            return HttpResponseRedirect(self.get_success_url())
        return JsonResponse({
            "pk": obj.pk,
        })

    def form_invalid(self, form: EvidenceForm):
        if self.request.accepts("text/html") or not self.request.accepts("application/json"):
            return super().form_invalid(form)
        return JsonResponse(form.errors, status=400, safe=True)


    def get_success_url(self):
        if "modal" in self.kwargs:
            return reverse("reporting:upload_evidence_modal_success")
        if self.report_instance:
            report_pk = self.report_instance.pk
            fragment = "#evidence"
        else:
            report_pk = self.finding_instance.report.pk
            fragment = "#findings"
        return reverse("reporting:report_detail", args=(report_pk,)) + fragment


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
        return self.get_object().associated_report.user_can_edit(self.request.user)

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
        return reverse("reporting:evidence_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        res = super().form_valid(form)
        messages.success(
            self.request,
            "Successfully updated {}.".format(self.object.friendly_name),
            extra_tags="alert-success",
        )
        return res


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
        return self.get_object().associated_report.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        if self.object.finding:
            fragment = "#findings"
        else:
            fragment = "#evidence"
        return reverse("reporting:report_detail", kwargs={"pk": self.object.associated_report.pk}) + fragment

    def form_valid(self, form):
        res = super().form_valid(form)
        message = "Successfully deleted the evidence and associated file."
        if os.path.isfile(self.object.document.name):
            message = "Successfully deleted the evidence, but could not delete the associated file."
        messages.success(
            self.request,
            message,
            extra_tags="alert-success",
        )
        return res

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["cancel_link"] = self.get_success_url()
        ctx["object_type"] = "evidence file (and associated file on disk)"
        ctx["object_to_be_deleted"] = queryset.friendly_name
        return ctx


class EvidenceDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Return the target :model:`reporting.Evidence` file for download."""

    model = Evidence

    def test_func(self):
        return self.get_object().associated_report.user_can_view(self.request.user)

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
        return self.finding_instance.report.user_can_edit(self.request.user)

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
