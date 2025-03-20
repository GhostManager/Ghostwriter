
import logging
import json

from django.http import JsonResponse
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic.detail import SingleObjectMixin
from django.template.loader import render_to_string
from django.contrib.auth.decorators import login_required
from django.db.models import Q

from ghostwriter.api.utils import ForbiddenJsonResponse, RoleBasedAccessControlMixin, verify_access
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.reporting.models import Finding, FindingType, Report, ReportFindingLink, Severity

logger = logging.getLogger(__name__)


def get_position(report_pk, severity):
    findings = ReportFindingLink.objects.filter(Q(report__pk=report_pk) & Q(severity=severity)).order_by("-position")
    if findings:
        # Set new position to be one above the last/largest position
        last_position = findings[0].position
        return last_position + 1
    return 1


class AssignFinding(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Copy an individual :model:`reporting.Finding` to create a new
    :model:`reporting.ReportFindingLink` connected to the user's active
    :model:`reporting.Report`.
    """

    model = Finding

    def post(self, *args, **kwargs):
        finding: Finding = self.get_object()

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

        if not ReportFindingLink.user_can_create(self.request.user, report):
            return ForbiddenJsonResponse()

        position = get_position(report.id, finding.severity)

        rfl = ReportFindingLink(
            title=finding.title,
            description=finding.description,
            impact=finding.impact,
            mitigation=finding.mitigation,
            replication_steps=finding.replication_steps,
            host_detection_techniques=finding.host_detection_techniques,
            network_detection_techniques=finding.network_detection_techniques,
            references=finding.references,
            finding_guidance=finding.finding_guidance,
            severity=finding.severity,
            finding_type=finding.finding_type,
            cvss_score=finding.cvss_score,
            cvss_vector=finding.cvss_vector,
            extra_fields=finding.extra_fields,

            assigned_to=self.request.user,
            position=position,
            added_as_blank=False,
            report=report,
        )
        rfl.save()
        rfl.tags.set(finding.tags.names())

        logger.info(
            "Copied %s %s to %s %s (%s %s) by request of %s",
            finding.__class__.__name__,
            finding.id,
            report.__class__.__name__,
            report.id,
            rfl.__class__.__name__,
            rfl.id,
            self.request.user,
        )

        return JsonResponse({
            "result": "success",
            "message": "{} successfully added to your active report.".format(rfl),
            "table_html": render_to_string(
                "snippets/report_findings_table.html", {"report": report}, request=self.request
            )
        })


class AssignBlankFinding(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Create a blank :model:`reporting.ReportFindingLink` entry linked to an individual
    :model:`reporting.Report`.
    """

    model = Report

    def test_func(self):
        return ReportFindingLink.user_can_create(self.request.user, self.get_object())

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def __init__(self):
        self.severity = Severity.objects.order_by("weight").last()
        self.finding_type = FindingType.objects.all().first()
        super().__init__()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            report_link = ReportFindingLink(
                title="Blank Template",
                severity=self.severity,
                finding_type=self.finding_type,
                report=obj,
                assigned_to=self.request.user,
                position=get_position(obj.id, self.severity),
                added_as_blank=True,
                extra_fields=ExtraFieldSpec.initial_json(Finding),
            )
            report_link.save()

            logger.info(
                "Added a blank finding to %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )

            message = "Successfully added a blank finding to the report."
            table_html = render_to_string("snippets/report_findings_table.html", {"report": obj}, request=self.request)
            data = {
                "result": "success",
                "message": message,
                "table_html": table_html,
            }
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.exception(log_message)

            message = f"Encountered an error while trying to add a blank finding to your report: {exception.args}."
            data = {"result": "error", "message": message}

        return JsonResponse(data)


class ReportFindingLinkDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`reporting.ReportFindingLink`."""

    model = ReportFindingLink

    def test_func(self):
        return self.get_object().user_can_delete(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        finding = self.get_object()
        finding.delete()
        data = {
            "result": "success",
            "message": "Successfully deleted {finding} and cleaned up evidence.".format(finding=finding),
        }
        logger.info(
            "Deleted %s %s by request of %s",
            finding.__class__.__name__,
            finding.id,
            self.request.user,
        )

        return JsonResponse(data)


class ReportFindingLinkUpdate(CollabModelUpdate):
    model = ReportFindingLink
    template_name = "reporting/report_finding_link_update.html"
    unauthorized_redirect = "home:dashboard"
    has_extra_fields = Finding


class ReportFindingStatusUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Update the ``complete`` field of an individual :model:`reporting.ReportFindingLink`."""

    model = ReportFindingLink

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        # Get ``status`` kwargs from the URL
        status = self.kwargs["status"]
        finding = self.get_object()

        try:
            result = "success"
            if status.lower() == "edit":
                finding.complete = False
                message = "Successfully flagged finding for editing."
                display_status = "Needs Editing"
                classes = "burned"
            elif status.lower() == "complete":
                finding.complete = True
                message = "Successfully marking finding as complete."
                display_status = "Ready"
                classes = "healthy"
            else:
                result = "error"
                message = "Could not update the finding's status to: {}".format(status)
                display_status = "Error"
                classes = "burned"
            finding.save()
            # Prepare the JSON response data
            data = {
                "result": result,
                "status": display_status,
                "classes": classes,
                "message": message,
            }
            logger.info(
                "Set status of %s %s to %s by request of %s",
                finding.__class__.__name__,
                finding.id,
                status,
                self.request.user,
            )
        # Return an error message if the query for the requested status returned DoesNotExist
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update finding's status!"}

        return JsonResponse(data)


@login_required
def ajax_update_report_findings(request):
    """
    Update the ``position`` and ``severity`` fields of all :model:`reporting.ReportFindingLink`
    attached to an individual :model:`reporting.Report`.
    """
    if request.method == "POST" and request.is_ajax():
        pos = request.POST.get("positions")
        report_id = request.POST.get("report")
        weight = request.POST.get("weight")
        order = json.loads(pos)

        report = get_object_or_404(Report, pk=report_id)
        if verify_access(request.user, report.project):
            logger.info(
                "Received AJAX POST to update report %s's %s severity group findings in this order: %s",
                report_id,
                weight,
                ", ".join(order),
            )
            data = {"result": "success"}

            try:
                severity = Severity.objects.get(weight=weight)
            except Severity.DoesNotExist:
                severity = None
                logger.exception("Failed to get Severity object for weight %s", weight)

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
                data = {"result": "error", "message": "Specified severity weight, {}, is invalid.".format(weight)}
        else:
            logger.error(
                "AJAX request submitted by user %s without access to report %s",
                request.user,
                report_id,
            )
            data = {"result": "error"}
    else:
        data = {"result": "error"}
    return JsonResponse(data)


# class ReportFindingLinkUpdate(RoleBasedAccessControlMixin, UpdateView):
#     """
#     Update an individual instance of :model:`reporting.ReportFindingLink`.

#     **Context**

#     ``cancel_link``
#         Link for the form's Cancel button to return to report's detail page

#     **Template**

#     :template:`reporting/local_edit.html.html`
#     """

#     model = ReportFindingLink
#     form_class = ReportFindingLinkUpdateForm
#     template_name = "reporting/local_edit.html"
#     success_url = reverse_lazy("reporting:reports")

#     def test_func(self):
#         return verify_access(self.request.user, self.get_object().report.project)

#     def handle_no_permission(self):
#         messages.error(self.request, "You do not have permission to access that.")
#         return redirect("home:dashboard")

#     def get_context_data(self, **kwargs):
#         ctx = super().get_context_data(**kwargs)
#         ctx["cancel_link"] = reverse("reporting:report_detail", kwargs={"pk": self.object.report.pk}) + "#findings"
#         return ctx

#     def form_valid(self, form):
#         if form.changed_data:
#             changed_at = dateformat.format(timezone.now(), "H:i:s e")
#             async_to_sync(channel_layer.group_send)(
#                 "finding_{}".format(self.object.id),
#                 {
#                     "type": "message",
#                     "message": {
#                         "message": f"User {self.request.user.username} updated this finding at {changed_at}.",
#                         "level": "warning",
#                         "title": "Content Has Changed",
#                     },
#                 },
#             )

#         # Send Websockets messages if assignment changed
#         if "assigned_to" in form.changed_data:
#             # Get the entries current values (those being changed)
#             old_entry = ReportFindingLink.objects.get(pk=self.object.pk)
#             old_assignee = old_entry.assigned_to
#             # Notify new assignee over WebSockets
#             if "assigned_to" in form.changed_data:
#                 # Only notify if the assignee is not the user who made the change
#                 if self.request.user != self.object.assigned_to:
#                     try:
#                         # Send a message to the assigned user
#                         async_to_sync(channel_layer.group_send)(
#                             f"notify_{self.object.assigned_to.get_clean_username() if self.object.assigned_to else None}",
#                             {
#                                 "type": "message",
#                                 "message": {
#                                     "message": "You have been assigned to this finding for {}:\n{}".format(
#                                         self.object.report, self.object.title
#                                     ),
#                                     "level": "info",
#                                     "title": "New Assignment",
#                                 },
#                             },
#                         )
#                     except gaierror:
#                         # WebSocket are unavailable (unit testing)
#                         pass
#                 if self.request.user != old_assignee:
#                     try:
#                         # Send a message to the unassigned user
#                         async_to_sync(channel_layer.group_send)(
#                             f"notify_{old_assignee.get_clean_username() if old_assignee else None}",
#                             {
#                                 "type": "message",
#                                 "message": {
#                                     "message": "You have been unassigned from this finding for {}:\n{}".format(
#                                         self.object.report, self.object.title
#                                     ),
#                                     "level": "info",
#                                     "title": "Assignment Change",
#                                 },
#                             },
#                         )
#                     except gaierror:
#                         # WebSocket are unavailable (unit testing)
#                         pass
#         return super().form_valid(form)

#     def get_form(self, form_class=None):
#         form = super().get_form(form_class)
#         user_primary_keys = ProjectAssignment.objects.filter(project=self.object.report.project).values_list(
#             "operator", flat=True
#         )
#         form.fields["assigned_to"].queryset = User.objects.filter(id__in=user_primary_keys)
#         return form

#     def get_success_url(self):
#         messages.success(
#             self.request,
#             "Successfully updated {}.".format(self.get_object().title),
#             extra_tags="alert-success",
#         )
#         return reverse("reporting:report_detail", kwargs={"pk": self.object.report.id}) + "#findings"

