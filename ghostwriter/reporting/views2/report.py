
from datetime import datetime
import io
import os
import logging
import zipfile
from socket import gaierror
from asgiref.sync import async_to_sync

from django.db.models import Q
from django.http import (
    FileResponse,
    Http404,
    HttpResponse,
    HttpResponseRedirect,
)
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.views.generic.list import ListView
from django.views.generic import View
from django.conf import settings
from django.contrib import messages
from channels.layers import get_channel_layer
from taggit.models import Tag

from ghostwriter.api.utils import RoleBasedAccessControlMixin, get_reports_list, get_templates_list, verify_user_is_privileged
from ghostwriter.commandcenter.models import ExtraFieldSpec, ReportConfiguration
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.modules.exceptions import MissingTemplate
from ghostwriter.modules.reportwriter import report_generation_queryset
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx
from ghostwriter.modules.reportwriter.report.xlsx import ExportReportXlsx
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.reporting.archive import archive_report
from ghostwriter.reporting.filters import ReportFilter, ReportTemplateFilter
from ghostwriter.reporting.forms import ReportForm, ReportTemplateForm, SelectReportTemplateForm
from ghostwriter.reporting.models import Archive, Finding, Observation, Report, ReportTemplate
from ghostwriter.rolodex.models import Project

logger = logging.getLogger(__name__)
channel_layer = get_channel_layer()

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
        return render(
            request,
            "reporting/report_list.html",
            {"filter": reports_filter, "tags": Tag.objects.all()}
        )


class ArchiveView(RoleBasedAccessControlMixin, DetailView):
    """
    Generate all report types for an individual :model:`reporting.Report`, collect all
    related :model:`reporting.Evidence` and related files, and compress the files into a
    single Zip file for archiving.
    """

    model = Report
    template_name = "confirm_archive.html"
    queryset = report_generation_queryset()

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        return ctx

    def post(self, *args, **kwargs):
        report_instance = self.get_object()
        try:
            archive_report(report_instance)
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
        return self.get_object().project.user_can_edit(self.request.user)

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
        return self.get_object().user_can_view(self.request.user)

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
                    if project.user_can_edit(self.request.user):
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
        return self.get_object().user_can_edit(self.request.user)

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
        return self.get_object().user_can_delete(self.request.user)

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


class ReportExtraFieldEdit(CollabModelUpdate):
    model = Report
    template_name = "reporting/report_update_extra_field.html"

    @property
    def collab_editing_script_path(self) -> str:
        return "assets/collab_forms_report_field.js"

    def get(self, request, pk, extra_field_name):
        self.extra_field_name = extra_field_name
        return super().get(request, pk=pk)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        field = get_object_or_404(ExtraFieldSpec.for_model(self.model), internal_name=self.extra_field_name)
        ctx["target_field"] = field
        return ctx


class ReportTemplateListView(RoleBasedAccessControlMixin, ListView):
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
            return client.user_can_view(self.request.user)
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
        return {
            "changelog": initial_upload,
            "p_style": "Normal",
            "evidence_image_width": 6.5,
        }

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
        obj: ReportTemplate = self.get_object()
        if obj.protected:
            return verify_user_is_privileged(self.request.user)
        if obj.client:
            return obj.client.user_can_edit(self.request.user)
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

class GenerateReportBase(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Base class for report generation"""
    model = Report
    queryset = Report.objects.all().prefetch_related(
        "tags",
        "reportfindinglink_set",
        "reportfindinglink_set__evidence_set",
        "reportobservationlink_set",
        "evidence_set",
        "project__oplog_set",
        "project__oplog_set__entries",
        "project__oplog_set__entries__tags",
    ).select_related()

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def dispatch(self, request, *args, **kwargs):
        self.object = self.get_object()
        return super().dispatch(request, *args, **kwargs)

class GenerateReportJSON(GenerateReportBase):
    """Generate a JSON report for an individual :model:`reporting.Report`."""

    def get(self, *args, **kwargs):
        obj = self.object

        logger.info(
            "Generating JSON report for %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )

        json_report = ExportReportJson(obj).run()
        return HttpResponse(json_report.getvalue(), "application/json")


class GenerateReportDOCX(GenerateReportBase):
    """Generate a DOCX report for an individual :model:`reporting.Report`."""

    model = Report

    def test_func(self):
        return self.object.user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, *args, **kwargs):
        obj = self.object

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
        except ReportExportTemplateError as error:
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


class GenerateReportXLSX(GenerateReportBase):
    """Generate an XLSX report for an individual :model:`reporting.Report`."""

    def get(self, *args, **kwargs):
        obj = self.object

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


class GenerateReportPPTX(GenerateReportBase):
    """Generate a PPTX report for an individual :model:`reporting.Report`."""

    def get(self, *args, **kwargs):
        obj = self.object

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
        except ReportExportTemplateError as error:
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


class GenerateReportAll(GenerateReportBase):
    """Generate all report types for an individual :model:`reporting.Report`."""

    def get(self, *args, **kwargs):
        obj = self.object

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
        except ReportExportTemplateError as error:
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
