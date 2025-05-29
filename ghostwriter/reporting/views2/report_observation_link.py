
import json
import logging

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponseRedirect, JsonResponse
from django.db.models import Max
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse
from django.views import View
from django.views.generic.detail import SingleObjectMixin

from ghostwriter.api.utils import ForbiddenJsonResponse, RoleBasedAccessControlMixin
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.reporting.models import Observation, Report, ReportObservationLink
from ghostwriter.commandcenter.views import CollabModelUpdate

logger = logging.getLogger(__name__)

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

        # Get report
        try:
            if "report" in self.request.POST:
                # If the POST includes an `report` value, use that
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

        if not ReportObservationLink.user_can_create(self.request.user, report):
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
