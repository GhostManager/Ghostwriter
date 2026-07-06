
import json
import logging
from socket import gaierror

import bs4

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Max
from django.http import HttpRequest, HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import UpdateView

from ghostwriter.api.utils import ForbiddenJsonResponse, RoleBasedAccessControlMixin
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.reporting.forms import AssignReportObservationForm
from ghostwriter.reporting.models import Observation, Report, ReportObservationLink
from ghostwriter.rolodex.models import ProjectAssignment

logger = logging.getLogger(__name__)

User = get_user_model()


class CloneObservationLinkToObservation(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Creates a :model:`reporting.Observation` with contents from a :model:`reporting.ReportObservationLink`.
    """

    model = ReportObservationLink

    def test_func(self):
        return self.get_object().user_can_view(self.request.user) and Observation.user_can_create(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to create new observations.")
        return redirect(reverse("reporting:report_detail", kwargs={"pk": self.get_object().report.pk}) + "#observations")

    def post(self, *args, **kwargs):
        rol: ReportObservationLink = self.get_object()
        observation = Observation(
            title=rol.title,
            description=rol.description,
            extra_fields=rol.extra_fields,
        )
        observation.save()
        observation.tags.set(rol.tags.names())
        messages.info(self.request, "Observation cloned to library.")
        return HttpResponseRedirect(reverse("reporting:observation_detail", kwargs={"pk": observation.pk}))


class AssignObservation(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Copy an individual :model:`reporting.Observation` to create a new
    :model:`reporting.ReportObservationLink` connected to the user's active
    :model:`reporting.Report`.
    """

    model = Observation

    def post(self, *args, **kwargs):
        obs: Observation = self.get_object()

        # Get the report object
        try:
            if "report" in self.request.POST:
                # If the POST includes a `report` value, use that
                report_id = self.request.POST["report"]
                report = Report.objects.get(pk=report_id)
            else:
                # Otherwise, use the session variable for the "active" report
                active_report = self.request.session.get("active_report", None)
                if active_report:
                    report = Report.objects.get(pk=active_report["id"])
                else:
                    raise Report.DoesNotExist()
        except (Report.DoesNotExist, ValueError):
            return JsonResponse({
                "result": "error",
                "message": "Please select a report to edit in the sidebar or go to a report's dashboard to assign an observation."
            }, status=400)

        if not report.user_can_edit(self.request.user):
            return ForbiddenJsonResponse()

        position = (
            ReportObservationLink.objects.filter(report__pk=report.id).aggregate(max=Max("position"))["max"]
            or 0 + 1
        )

        rol = ReportObservationLink(
            title=obs.title,
            description=obs.description,
            extra_fields=obs.extra_fields,

            assigned_to=self.request.user,
            report=report,
            added_as_blank=False,
            position=position,
        )
        rol.save()
        rol.tags.set(obs.tags.names())

        logger.info(
            "Copied %s %s to %s %s (%s %s) by request of %s",
            obs.__class__.__name__,
            obs.id,
            report.__class__.__name__,
            report.id,
            rol.__class__.__name__,
            rol.id,
            self.request.user,
        )

        return JsonResponse({
            "result": "success",
            "message": "{} successfully added to your active report.".format(obs),
            "table_html": render_to_string(
                "snippets/report_observations_table.html", {"report": report}, request=self.request
            )
        })


class AssignBlankObservation(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    model = Report

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            position = (
                ReportObservationLink.objects.filter(report__pk=obj.id).aggregate(max=Max("position"))["max"] or 0 + 1
            )
            report_link = ReportObservationLink(
                title="Blank Template",
                report=obj,
                assigned_to=self.request.user,
                position=position,
                added_as_blank=True,
                extra_fields=ExtraFieldSpec.initial_json(Observation),
            )
            report_link.save()

            logger.info(
                "Added a blank observation to %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )

            data = {
                "result": "success",
                "message": "Successfully added a blank observation to the report.",
                "table_html": render_to_string(
                    "snippets/report_observations_table.html", {"report": obj}, request=self.request
                ),
            }
        except Exception as exception:  # pragma: no cover
            logger.exception("Could not add blank observation")

            data = {
                "result": "error",
                "message": f"Encountered an error while trying to add a blank observation to your report: {exception.args}."
            }

        return JsonResponse(data)


class ReportObservationLinkDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`reporting.ReportObservationLink`."""

    model = ReportObservationLink

    def test_func(self):
        return self.get_object().user_can_delete(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        observation = self.get_object()
        observation.delete()
        data = {
            "result": "success",
            "message": "Successfully deleted {observation} and cleaned up evidence.".format(observation=observation),
        }
        logger.info(
            "Deleted %s %s by request of %s",
            observation.__class__.__name__,
            observation.id,
            self.request.user,
        )

        return JsonResponse(data)


class ReportObservationLinkUpdate(CollabModelUpdate):
    """
    Update an individual instance of :model:`reporting.ReportObservationLink`.
    """

    model = ReportObservationLink
    template_name = "reporting/report_observation_link_update.html"
    unauthorized_redirect = "home:dashboard"
    has_extra_fields = Observation


class ReportObservationLinkPreview(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Render a full preview of a reported observation with Jinja2 resolved."""

    model = ReportObservationLink

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        return HttpResponse(
            '<div class="alert alert-danger">You do not have permission to access that.</div>',
            content_type="text/html",
            status=403,
        )

    def get(self, request, *args, **kwargs):
        from django.utils.html import escape

        from ghostwriter.commandcenter.templatetags.extra_fields import (
            _expand_evidence_and_sanitize,
        )
        from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
        from ghostwriter.modules.reportwriter.report.json import ExportReportJson

        obj = self.get_object()
        report = obj.report
        client = report.project.client

        try:
            exporter = ExportReportJson(report)
            base_context = exporter.map_rich_texts()
        except ReportExportTemplateError as error:
            return HttpResponse(
                '<div class="alert alert-danger">'
                f"<strong>Template Error</strong><br>{escape(str(error))}"
                "</div>",
                content_type="text/html",
            )
        except Exception:
            logger.exception(
                "Error building preview for observation %s on report %s",
                obj.pk,
                report.pk,
            )
            return HttpResponse(
                '<div class="alert alert-danger">'
                "<strong>Preview Error</strong><br>"
                "An unexpected error occurred.</div>",
                content_type="text/html",
            )

        obs_data = None
        for o in base_context.get("observations", []):
            if o.get("id") == obj.pk:
                obs_data = o
                break

        if obs_data is None:
            return HttpResponse(
                '<div class="alert alert-warning">Observation not found in report data.</div>',
                content_type="text/html",
            )

        def _render(value):
            if value is None:
                return ""
            try:
                return str(value.__html__()) if hasattr(value, "__html__") else str(value)
            except ReportExportTemplateError as error:
                return (
                    f'<div class="alert alert-danger">'
                    f"<strong>Template Error</strong><br>{escape(str(error))}"
                    f"</div>"
                )

        def _has_content(html_str):
            if not html_str or not html_str.strip():
                return False
            return bool(bs4.BeautifulSoup(html_str, "html.parser").get_text(strip=True))

        def _wrap_plain(value, html_str):
            if isinstance(value, bool):
                icon = "fa-check" if value else "fa-times"
                css = "healthy" if value else "burned"
                return f'<p><span class="{css}"><i class="fas {icon}"></i></span></p>'
            if not hasattr(value, "__html__") and "<" not in html_str:
                return f"<p>{escape(html_str)}</p>"
            return html_str

        parts = []
        title = escape(obs_data.get("title", "Untitled Observation"))
        parts.append(f"<h2>{title}</h2>")
        parts.append(
            '<hr>'
        )

        html = _render(obs_data.get("description_rt"))
        if _has_content(html):
            sanitized = _expand_evidence_and_sanitize(html, report, client=client)
            parts.append("<h3>Description</h3>")
            parts.append(sanitized)

        extra_fields = obs_data.get("extra_fields", {})
        ef_display_names = {
            spec.internal_name: spec.display_name
            for spec in ExtraFieldSpec.objects.filter(target_model=Observation._meta.label)
        }
        for ef_key, ef_value in extra_fields.items():
            html = _render(ef_value)
            if not _has_content(html):
                continue
            html = _wrap_plain(ef_value, html)
            sanitized = _expand_evidence_and_sanitize(html, report, client=client)
            label = escape(ef_display_names.get(ef_key, ef_key))
            parts.append(f"<h3>{label}</h3>")
            parts.append(sanitized)

        return HttpResponse("\n".join(parts), content_type="text/html")


@login_required
def ajax_update_report_observation_order(request: HttpRequest):
    """
    Update the ``position`` fields of all :model:`reporting.ReportObservationLink`
    attached to an individual :model:`reporting.Report`.
    """
    if request.method != "POST":
        return JsonResponse({"result": "error"})

    pos = request.POST.get("positions")
    report_id = request.POST.get("report")
    order = json.loads(pos)

    report = get_object_or_404(Report, pk=report_id)
    if not report.user_can_edit(request.user):
        logger.error(
            "AJAX request submitted by user %s without access to report %s",
            request.user,
            report_id,
        )
        return JsonResponse({"result": "error"})

    logger.info(
        "Received AJAX POST to update report %s's observations in this order: %s",
        report_id,
        ", ".join(order),
    )

    for (i, observation_id) in enumerate(order):
        observation_instance = ReportObservationLink.objects.get(report=report, id=observation_id)
        if observation_instance:
            observation_instance.position = i + 1
            observation_instance.save()
        else:
            logger.error(
                "Received an observation ID, %s, that did not match an existing observation",
                observation_id,
            )
    return JsonResponse({"result": "success"})


class ReportObservationStatusUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Update the ``complete`` field of an individual :model:`reporting.ReportObservationLink`."""

    model = ReportObservationLink

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        status = self.kwargs["status"]
        observation = self.get_object()

        try:
            result = "success"
            if status.lower() == "edit":
                observation.complete = False
                message = "Successfully flagged observation for editing."
                display_status = "Needs Editing"
                classes = "burned"
            elif status.lower() == "complete":
                observation.complete = True
                message = "Successfully marked observation as complete."
                display_status = "Ready"
                classes = "healthy"
            else:
                result = "error"
                message = "Could not update the observation's status to: {}".format(status)
                display_status = "Error"
                classes = "burned"
            observation.save()
            data = {
                "result": result,
                "status": display_status,
                "classes": classes,
                "message": message,
            }
            logger.info(
                "Set status of %s %s to %s by request of %s",
                observation.__class__.__name__,
                observation.id,
                status,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update observation's status!"}

        return JsonResponse(data)


class ReportObservationLinkAssign(RoleBasedAccessControlMixin, UpdateView):
    model = ReportObservationLink
    form_class = AssignReportObservationForm
    template_name = "reporting/report_observation_link_assign.html"

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = (
            reverse("reporting:report_detail", kwargs={"pk": self.object.report.pk}) + "#observations"
        )
        return ctx

    def get_form(self, form_class=None):
        self.old_assignment = self.object.assigned_to
        form = super().get_form(form_class)
        user_primary_keys = ProjectAssignment.objects.filter(
            project=self.object.report.project
        ).values_list("operator", flat=True)
        form.fields["assigned_to"].queryset = User.objects.filter(id__in=user_primary_keys)
        return form

    def form_valid(self, form: AssignReportObservationForm):
        if self.old_assignment == self.object.assigned_to:
            if self.object.assigned_to:
                messages.info(self.request, "The observation was already assigned to this user. No changes made.")
            else:
                messages.info(self.request, "The observation was already unassigned. No changes made.")
            return HttpResponseRedirect(self.get_success_url())
        try:
            # Send a message to the assigned user if `assigned_to` is set
            if self.object.assigned_to:
                async_to_sync(get_channel_layer().group_send)(
                    f"notify_{self.object.assigned_to.get_clean_username()}",
                    {
                        "type": "message",
                        "message": {
                        "message": "You have been assigned to this observation for {}:\n{}".format(
                            self.object.report, self.object.title
                        ),
                        "level": "info",
                        "title": "New Assignment",
                    },
                },
            )
        except gaierror:
            pass
        if self.object.assigned_to:
            messages.success(self.request, "Observation reassigned successfully.")
        else:
            messages.success(self.request, "Observation unassigned successfully.")
        return super().form_valid(form)

    def get_success_url(self):
        return reverse("reporting:report_detail", kwargs={"pk": self.object.report.id}) + "#observations"
