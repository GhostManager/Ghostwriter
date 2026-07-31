"""This contains all the views used by the Home application."""

# Standard Libraries
import logging
import re
from datetime import date, timedelta

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.db.models import Prefetch, Q
from django.http import HttpResponseNotAllowed, JsonResponse
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.cache import never_cache
from django.views.decorators.http import require_GET, require_POST
from django.views.generic.edit import View

# 3rd Party Libraries
from django_q.models import Task
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    RoleBasedAccessControlMixin,
    get_project_list,
    verify_user_is_privileged,
)
from ghostwriter.home.editor_shortcuts import get_editor_shortcuts_date_config
from ghostwriter.home.navigation import (
    DEFAULT_PANEL_ORDER,
    OPTIONAL_NAVIGATION_BY_ID,
    SIDEBAR_PREFERENCES_VERSION,
    get_allowed_optional_ids,
    get_sidebar_navigation,
    normalize_sidebar_preferences,
)
from ghostwriter.home.working_context import (
    PINNABLE_WORK_TYPES,
    build_working_context_catalog,
    get_pinned_work,
    toggle_pinned_work,
)
from ghostwriter.modules.health_utils import DjangoHealthChecks
from ghostwriter.reporting.models import ReportFindingLink, ReportObservationLink
from ghostwriter.rolodex.models import ProjectAssignment

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.views
logger = logging.getLogger(__name__)

DASHBOARD_WORK_ITEM_LIMIT = 12
HEX_COLOR_PATTERN = re.compile(r"^[0-9A-Fa-f]{6}$")


@login_required
@require_GET
@never_cache
def editor_shortcuts_date(request):
    """Return the current server-formatted date for long-lived editor pages."""
    return JsonResponse(get_editor_shortcuts_date_config())


def _format_assignment_operator(assignment):
    if not assignment.operator:
        return "Unassigned"
    operator_name = assignment.operator.name or assignment.operator.username
    return f"{operator_name} ({assignment.role})"


def _calendar_end_date(date_value):
    return date_value + timedelta(days=1)


def _format_project_calendar_title(project):
    project_label = project.codename or f"Project #{project.pk}"
    return (
        f"{project.client} {project.project_type} - {project_label} "
        f"({project.start_date.isoformat()} to {project.end_date.isoformat()})"
    )


def _format_project_assignments(project):
    assignments = []
    seen_assignments = set()
    for assignment in project.assigned_project_assignments:
        label = _format_assignment_operator(assignment)
        if label not in seen_assignments:
            assignments.append(label)
            seen_assignments.add(label)
    return assignments or ["No assigned operators"]


def build_dashboard_calendar_events(user):
    assigned_project_prefetch = Prefetch(
        "projectassignment_set",
        queryset=ProjectAssignment.objects.select_related("operator", "role").filter(
            operator__isnull=False
        ),
        to_attr="assigned_project_assignments",
    )
    ongoing_projects = (
        get_project_list(user)
        .select_related("client", "project_type")
        .prefetch_related(assigned_project_prefetch)
        .filter(complete=False)
        .order_by(
            "start_date", "end_date", "client__name", "project_type__project_type"
        )
        .distinct()
    )
    events = []
    seen_project_ids = set()
    for project in ongoing_projects:
        if project.pk in seen_project_ids:
            continue
        seen_project_ids.add(project.pk)
        events.append(
            {
                "title": _format_project_calendar_title(project),
                "allDay": True,
                "start": project.start_date.isoformat(),
                "end": _calendar_end_date(project.end_date).isoformat(),
                "backgroundColor": "var(--gw-information-slate)",
                "borderColor": "var(--gw-engagement-violet)",
                "classNames": ["calendar-exec-icon"],
                "url": project.get_absolute_url(),
                "extendedProps": {
                    "assignedOperators": _format_project_assignments(project),
                    "calendarKind": "Project",
                },
            }
        )
    return events


def _get_active_report_id(request):
    """Return the working report ID stored in the legacy session key."""
    active_report = request.session.get("active_report") or {}
    try:
        return int(active_report.get("id"))
    except (TypeError, ValueError):
        return None


def _normalize_severity_color(value):
    """Return a safe CSS hex color for a configured severity."""
    if isinstance(value, str) and HEX_COLOR_PATTERN.fullmatch(value):
        return f"#{value.upper()}"
    return "#6C809A"


def _build_dashboard_work_queue(findings, observations, active_report_id):
    """Combine assigned report content into one operator-focused work queue."""
    work_items = []

    for finding in findings:
        work_items.append(
            {
                "kind": "Finding",
                "kind_icon": "fa-bug",
                "object": finding,
                "title": finding.display_title,
                "report": finding.report,
                "project": finding.report.project,
                "client": finding.report.project.client,
                "severity": finding.severity,
                "severity_color": _normalize_severity_color(finding.severity.color),
                "edit_url": finding.get_edit_url(),
                "is_active_report": finding.report_id == active_report_id,
                "sort_weight": finding.severity.weight,
            }
        )

    for observation in observations:
        work_items.append(
            {
                "kind": "Observation",
                "kind_icon": "fa-binoculars",
                "object": observation,
                "title": observation.title,
                "report": observation.report,
                "project": observation.report.project,
                "client": observation.report.project.client,
                "severity": None,
                "severity_color": None,
                "edit_url": reverse(
                    "reporting:local_observation_edit", kwargs={"pk": observation.pk}
                ),
                "is_active_report": observation.report_id == active_report_id,
                "sort_weight": date.max.toordinal(),
            }
        )

    work_items.sort(
        key=lambda item: (
            not item["is_active_report"],
            item["project"].end_date or date.max,
            item["sort_weight"],
            item["kind"],
            item["title"].casefold(),
        )
    )
    return work_items[:DASHBOARD_WORK_ITEM_LIMIT]


def _build_dashboard_engagements(assignments, today):
    """Describe project assignments as a compact operational runway."""
    engagements = []

    for assignment in assignments:
        project = assignment.project
        start_date = assignment.start_date or project.start_date
        end_date = assignment.end_date or project.end_date

        if end_date and end_date < today:
            status = "overdue"
            status_label = "Past end date"
            status_order = 0
        elif end_date and end_date == today:
            status = "ending"
            status_label = "Ends today"
            status_order = 1
        elif (
            end_date
            and 0 < (end_date - today).days <= 7
            and (not start_date or start_date <= today)
        ):
            status = "ending"
            status_label = f"Ends in {(end_date - today).days} days"
            status_order = 1
        elif start_date and start_date > today:
            status = "upcoming"
            days_until_start = (start_date - today).days
            status_label = (
                "Starts tomorrow"
                if days_until_start == 1
                else f"Starts in {days_until_start} days"
            )
            status_order = 3
        else:
            status = "active"
            status_label = "Active"
            status_order = 2

        engagements.append(
            {
                "assignment": assignment,
                "project": project,
                "client": project.client,
                "role": assignment.role,
                "start_date": start_date,
                "end_date": end_date,
                "status": status,
                "status_label": status_label,
                "status_order": status_order,
            }
        )

    engagements.sort(
        key=lambda engagement: (
            engagement["status_order"],
            engagement["end_date"] or date.max,
            engagement["start_date"] or date.max,
            engagement["client"].name.casefold(),
        )
    )
    return engagements


##################
# View Functions #
##################


@login_required
def update_session(request):
    """Update the requesting user's session variable based on ``session_data`` in POST."""
    if request.method == "POST":
        req_data = request.POST.get("session_data", None)
        if req_data:
            if req_data == "sidebar":
                if "sidebar" in request.session.keys():
                    request.session["sidebar"]["sticky"] ^= True
                else:
                    request.session["sidebar"] = {}
                    request.session["sidebar"]["sticky"] = True
            if req_data == "filter":
                if "filter" in request.session.keys():
                    request.session["filter"]["sticky"] ^= True
                else:
                    request.session["filter"] = {}
                    request.session["filter"]["sticky"] = True
            request.session.save()
        data = {
            "result": "success",
            "message": "Session updated",
        }
        return JsonResponse(data)

    return HttpResponseNotAllowed(["POST"])


@login_required
@require_POST
def update_sidebar_preferences(request):
    """Persist a user's permission-filtered sidebar shortcuts."""
    allowed_ids = get_allowed_optional_ids(request.user)

    if request.POST.get("action") == "reset":
        preferences = normalize_sidebar_preferences({}, allowed_ids)
        message = "Sidebar shortcuts reset to the Ghostwriter defaults."
    else:
        current_preferences = normalize_sidebar_preferences(
            getattr(request.user, "sidebar_preferences", {}),
            allowed_ids,
        )
        requested_pins = request.POST.getlist("pinned")
        requested_order = [
            item_id.strip()
            for item_id in request.POST.get("order", "").split(",")
            if item_id.strip() in OPTIONAL_NAVIGATION_BY_ID
        ]
        if "panel_order" in request.POST:
            requested_panel_order = [
                panel_id.strip()
                for panel_id in request.POST.get("panel_order", "").split(",")
                if panel_id.strip() in DEFAULT_PANEL_ORDER
            ]
            requested_visible_panels = request.POST.getlist("visible_panels")
        else:
            # Preserve panel settings submitted by a sidebar form opened before
            # the version-two customizer was deployed.
            requested_panel_order = current_preferences["panel_order"]
            requested_visible_panels = current_preferences["visible_panels"]
        preferences = normalize_sidebar_preferences(
            {
                "version": SIDEBAR_PREFERENCES_VERSION,
                "pinned": requested_pins,
                "order": requested_order,
                "panel_order": requested_panel_order,
                "visible_panels": requested_visible_panels,
            },
            allowed_ids,
        )
        message = "Sidebar shortcuts updated."

    request.user.sidebar_preferences = preferences
    request.user.save(update_fields=["sidebar_preferences"])
    messages.success(request, message)

    next_url = request.POST.get("next", "")
    if not url_has_allowed_host_and_scheme(
        next_url,
        allowed_hosts={request.get_host()},
        require_https=request.is_secure(),
    ):
        return redirect("home:dashboard")
    return redirect(next_url)


@login_required
@require_GET
def working_context_catalog(request):
    """Return permission-filtered working-report and pinned-work choices."""
    active_report_id = _get_active_report_id(request)
    return JsonResponse(
        build_working_context_catalog(request.user, active_report_id)
    )


@login_required
@require_POST
def toggle_workspace_pin(request):
    """Toggle a visible client, project, or report in the sidebar."""
    item_type = request.POST.get("type", "")
    try:
        object_id = int(request.POST.get("id", ""))
    except (TypeError, ValueError):
        object_id = 0

    if item_type not in PINNABLE_WORK_TYPES or object_id < 1:
        return JsonResponse(
            {
                "result": "error",
                "message": "Choose a valid client, project, or report to pin.",
            },
            status=400,
        )

    # Import here to keep application startup and migration discovery lightweight.
    from ghostwriter.reporting.models import Report
    from ghostwriter.rolodex.models import Client, Project

    model = {
        "client": Client,
        "project": Project,
        "report": Report,
    }[item_type]
    obj = model.objects.filter(pk=object_id).first()
    if obj is None or not obj.user_can_view(request.user):
        return JsonResponse(
            {
                "result": "error",
                "message": "You do not have permission to pin that workspace item.",
            },
            status=403,
        )

    pinned = toggle_pinned_work(request.user, item_type, object_id)
    active_report_id = _get_active_report_id(request)
    return JsonResponse(
        {
            "result": "success",
            "pinned": pinned,
            "type": item_type,
            "id": object_id,
            "message": (
                f"Pinned {item_type} to the sidebar."
                if pinned
                else f"Removed {item_type} from the sidebar."
            ),
            "pinned_items": get_pinned_work(
                request.user, active_report_id
            ),
        }
    )


class Dashboard(RoleBasedAccessControlMixin, View):
    """
    Display the home page.

    **Context**

    ``user_projects``
        All :model:`reporting.ProjectAssignment` for current :model:`users.User`
    ``active_projects``
        All :model:`reporting.ProjectAssignment` for active :model:`rolodex.Project` and current :model:`users.User`
    ``failed_tasks``
        Five most recent failed :model:`django_q.Task` entries for privileged users
    ``assigned_findings``
        Incomplete :model:`reporting.ReportFindingLink` for current :model:`users.User`
    ``assigned_observations``
        Incomplete :model:`reporting.ReportObservationLink` for current :model:`users.User`
    ``work_items``
        Assigned findings and observations combined into one prioritized queue
    ``dashboard_engagements``
        Active project assignments prepared for the engagement runway
    ``calendar_events``
        FullCalendar event data for all ongoing projects available to the current user
    ``system_health``
        Current system health based on :func:`ghostwriter.modules.health_utils.DjangoHealthChecks`

    **Template**

    :template:`index.html`
    """

    def get(self, request, *args, **kwargs):
        active_report_id = _get_active_report_id(request)

        assigned_findings_queryset = (
            ReportFindingLink.objects.select_related(
                "report",
                "report__project",
                "report__project__client",
                "report__project__project_type",
                "severity",
            )
            .filter(
                Q(assigned_to=request.user)
                & Q(report__complete=False)
                & Q(complete=False)
            )
            .order_by("report__project__end_date", "severity__weight", "title")
        )
        assigned_observations_queryset = (
            ReportObservationLink.objects.select_related(
                "report",
                "report__project",
                "report__project__client",
                "report__project__project_type",
            )
            .filter(
                Q(assigned_to=request.user)
                & Q(report__complete=False)
                & Q(complete=False)
            )
            .order_by("report__project__end_date", "title")
        )

        assigned_finding_count = assigned_findings_queryset.count()
        assigned_observation_count = assigned_observations_queryset.count()
        assigned_findings = list(
            assigned_findings_queryset[: DASHBOARD_WORK_ITEM_LIMIT + 1]
        )
        assigned_observations = list(
            assigned_observations_queryset[: DASHBOARD_WORK_ITEM_LIMIT + 1]
        )
        work_item_count = assigned_finding_count + assigned_observation_count
        work_items = _build_dashboard_work_queue(
            assigned_findings, assigned_observations, active_report_id
        )

        user_projects = ProjectAssignment.objects.select_related(
            "operator",
            "project",
            "project__client",
            "project__project_type",
            "role",
        ).filter(operator=request.user)
        active_projects = list(
            user_projects.filter(project__complete=False).order_by(
                "project__start_date",
                "project__end_date",
                "project__client__name",
                "role__position",
            )
        )
        dashboard_engagements = _build_dashboard_engagements(
            active_projects, timezone.localdate()
        )

        failed_tasks = []
        system_health = None
        if request.user.is_privileged:
            failed_tasks = list(Task.objects.filter(success=False)[:5])
            system_health = "OK"
            try:
                healthcheck = DjangoHealthChecks()
                db_status = healthcheck.get_database_status()
                cache_status = healthcheck.get_cache_status()
                if not db_status["default"] or not cache_status["default"]:
                    system_health = "WARNING"
            except Exception:  # pragma: no cover
                logger.exception("Unable to retrieve dashboard system health.")
                system_health = "ERROR"

        context = {
            "user_projects": user_projects,
            "active_projects": active_projects,
            "dashboard_engagements": dashboard_engagements,
            "failed_tasks": failed_tasks,
            "assigned_findings": assigned_findings,
            "assigned_observations": assigned_observations,
            "assigned_finding_count": assigned_finding_count,
            "assigned_observation_count": assigned_observation_count,
            "work_items": work_items,
            "work_item_count": work_item_count,
            "work_item_limit": DASHBOARD_WORK_ITEM_LIMIT,
            "calendar_events": build_dashboard_calendar_events(request.user),
            "system_health": system_health,
        }
        return render(request, "index.html", context=context)


class Management(RoleBasedAccessControlMixin, View):
    """
    Display the current Ghostwriter settings.

    **Context**

    ``timezone``
        The current value of ``settings.TIME_ZONE``

    **Template**

    :template:`home/management.html`
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get(self, request, *args, **kwargs):
        context = {
            "timezone": settings.TIME_ZONE,
        }
        return render(request, "home/management.html", context=context)


class TestAWSConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``AWS Test`` with
    :task:`shepherd.tasks.test_aws_keys` to test AWS keys in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``AWS Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_aws_keys",
                self.request.user,
                group="AWS Test",
            )
            message = "AWS access key test has been successfully queued."
        except Exception:  # pragma: no cover
            logger.exception("Unable to queue AWS access key test.")
            result = "error"
            message = "AWS access key test could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestDOConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Digital Ocean Test`` with
    :task:`shepherd.tasks.test_digital_ocean` to test the Digital Ocean API key stored in
    :model:`commandcenter.CloudServicesConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Digital Ocean Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_digital_ocean",
                self.request.user,
                group="Digital Ocean Test",
            )
            message = "Digital Ocean API key test has been successfully queued."
        except Exception:  # pragma: no cover
            logger.exception("Unable to queue Digital Ocean API key test.")
            result = "error"
            message = "Digital Ocean API key test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestNamecheapConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Namecheap Test`` with
    :task:`shepherd.tasks.test_namecheap` to test the Namecheap API configuration stored
    in :model:`commandcenter.NamecheapConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Namecheap Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_namecheap",
                self.request.user,
                group="Namecheap Test",
            )
            message = "Namecheap API test has been successfully queued."
        except Exception:  # pragma: no cover
            logger.exception("Unable to queue Namecheap API key test.")
            result = "error"
            message = "Namecheap API test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestSlackConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Slack Test`` with
    :task:`shepherd.tasks.test_slack_webhook` to test the Slack Webhook configuration
    stored in :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Slack Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_slack_webhook",
                self.request.user,
                group="Slack Test",
            )
            message = "Slack Webhook test has been successfully queued."
        except Exception:  # pragma: no cover
            logger.exception("Unable to queue Slack webhook test.")
            result = "error"
            message = "Slack Webhook test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class TestVirusTotalConnection(RoleBasedAccessControlMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``VirusTotal Test`` with
    :task:`shepherd.tasks.test_virustotal` to test the VirusTotal API key stored in
    :model:`commandcenter.SlackConfiguration`.
    """

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``VirusTotal Test``
        result = "success"
        try:
            async_task(
                "ghostwriter.shepherd.tasks.test_virustotal",
                self.request.user,
                group="Slack Test",
            )
            message = "VirusTotal API test has been successfully queued."
        except Exception:  # pragma: no cover
            logger.exception("Unable to queue VirusTotal API key test.")
            result = "error"
            message = "VirusTotal API test could not be queued."

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)
