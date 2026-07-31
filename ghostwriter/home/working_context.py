"""Helpers for a user's working report and pinned workspace objects."""

from collections import OrderedDict

# Django Imports
from django.urls import reverse

WORKSPACE_PREFERENCES_VERSION = 1
PINNABLE_WORK_TYPES = ("client", "project", "report")
RECENT_REPORT_LIMIT = 6


def normalize_workspace_preferences(preferences):
    """Return a safe, versioned workspace preference payload."""
    if (
        not isinstance(preferences, dict)
        or preferences.get("version") != WORKSPACE_PREFERENCES_VERSION
    ):
        preferences = {}

    pinned = []
    seen = set()
    raw_pinned = preferences.get("pinned", ())
    if not isinstance(raw_pinned, (list, tuple)):
        raw_pinned = ()
    for item in raw_pinned:
        if not isinstance(item, dict):
            continue
        item_type = item.get("type")
        try:
            object_id = int(item.get("id"))
        except (TypeError, ValueError):
            continue
        key = (item_type, object_id)
        if item_type not in PINNABLE_WORK_TYPES or object_id < 1 or key in seen:
            continue
        pinned.append({"type": item_type, "id": object_id})
        seen.add(key)

    recent_reports = []
    raw_recent = preferences.get("recent_reports", ())
    if not isinstance(raw_recent, (list, tuple)):
        raw_recent = ()
    for report_id in raw_recent:
        try:
            report_id = int(report_id)
        except (TypeError, ValueError):
            continue
        if report_id > 0 and report_id not in recent_reports:
            recent_reports.append(report_id)
        if len(recent_reports) == RECENT_REPORT_LIMIT:
            break

    return {
        "version": WORKSPACE_PREFERENCES_VERSION,
        "pinned": pinned,
        "recent_reports": recent_reports,
    }


def get_workspace_preferences(user):
    """Return normalized workspace preferences for ``user``."""
    return normalize_workspace_preferences(getattr(user, "workspace_preferences", {}))


def save_workspace_preferences(user, preferences):
    """Normalize and persist workspace preferences for ``user``."""
    normalized = normalize_workspace_preferences(preferences)
    user.workspace_preferences = normalized
    user.save(update_fields=["workspace_preferences"])
    return normalized


def record_recent_report(user, report_id):
    """Put ``report_id`` at the front of the user's recent report history."""
    preferences = get_workspace_preferences(user)
    recent_reports = [
        item for item in preferences["recent_reports"] if item != int(report_id)
    ]
    preferences["recent_reports"] = [int(report_id), *recent_reports][
        :RECENT_REPORT_LIMIT
    ]
    save_workspace_preferences(user, preferences)


def toggle_pinned_work(user, item_type, object_id):
    """Toggle a permission-checked work object in the user's pinned list."""
    preferences = get_workspace_preferences(user)
    key = {"type": item_type, "id": int(object_id)}
    is_pinned = key in preferences["pinned"]
    if is_pinned:
        preferences["pinned"].remove(key)
    else:
        preferences["pinned"].append(key)
    save_workspace_preferences(user, preferences)
    return not is_pinned


def _serialize_client(client):
    return {
        "type": "client",
        "id": client.id,
        "label": client.name,
        "meta": "Client",
        "url": client.get_absolute_url(),
        "icon": "fas fa-building",
    }


def _serialize_project(project):
    return {
        "type": "project",
        "id": project.id,
        "label": str(project),
        "meta": project.client.name,
        "url": project.get_absolute_url(),
        "icon": "fas fa-project-diagram",
    }


def _serialize_report(report, active_report_id=None):
    return {
        "type": "report",
        "id": report.id,
        "label": report.title,
        "meta": str(report.project),
        "url": report.get_absolute_url(),
        "icon": "fas fa-file-alt",
        "working": report.id == active_report_id,
        "activate_url": reverse(
            "reporting:ajax_activate_report", kwargs={"pk": report.id}
        ),
    }


def get_pinned_work(user, active_report_id=None):
    """Return visible pinned work in the user's chosen order."""
    # Import here to avoid loading application models during migration discovery.
    from ghostwriter.reporting.models import Report
    from ghostwriter.rolodex.models import Client, Project

    preferences = get_workspace_preferences(user)
    pinned = preferences["pinned"]
    ids_by_type = {
        item_type: [item["id"] for item in pinned if item["type"] == item_type]
        for item_type in PINNABLE_WORK_TYPES
    }

    clients = {
        client.id: client
        for client in Client.for_user(user).filter(id__in=ids_by_type["client"])
    }
    projects = {
        project.id: project
        for project in Project.user_viewable(user)
        .select_related("client", "project_type")
        .filter(id__in=ids_by_type["project"])
    }
    reports = {
        report.id: report
        for report in Report.user_viewable(user)
        .select_related("project", "project__client", "project__project_type")
        .filter(id__in=ids_by_type["report"])
    }

    serialized = []
    for item in pinned:
        obj = {
            "client": clients,
            "project": projects,
            "report": reports,
        }[
            item["type"]
        ].get(item["id"])
        if obj is None:
            continue
        serializer = {
            "client": _serialize_client,
            "project": _serialize_project,
            "report": lambda report: _serialize_report(report, active_report_id),
        }[item["type"]]
        serialized.append(serializer(obj))
    return serialized


def build_working_context_catalog(user, active_report_id=None):
    """Return report choices grouped by client and project for the switcher."""
    # Import here to avoid loading application models during migration discovery.
    from ghostwriter.reporting.models import Report

    preferences = get_workspace_preferences(user)
    pinned_keys = {(item["type"], item["id"]) for item in preferences["pinned"]}
    recent_positions = {
        report_id: index
        for index, report_id in enumerate(preferences["recent_reports"])
    }

    reports = list(
        Report.user_viewable(user)
        .select_related("project", "project__client", "project__project_type")
        .filter(archived=False)
    )
    reports.sort(
        key=lambda report: (
            report.id != active_report_id,
            ("report", report.id) not in pinned_keys,
            recent_positions.get(report.id, RECENT_REPORT_LIMIT + 1),
            report.complete,
            report.project.end_date,
            report.project.client.name.lower(),
            report.title.lower(),
        )
    )

    grouped_projects = OrderedDict()
    for report in reports:
        project = report.project
        client = project.client
        group = grouped_projects.setdefault(
            project.id,
            {
                "client": {
                    **_serialize_client(client),
                    "pinned": ("client", client.id) in pinned_keys,
                },
                "project": {
                    **_serialize_project(project),
                    "pinned": ("project", project.id) in pinned_keys,
                    "complete": project.complete,
                },
                "reports": [],
            },
        )
        group["reports"].append(
            {
                **_serialize_report(report, active_report_id),
                "pinned": ("report", report.id) in pinned_keys,
                "complete": report.complete,
                "delivered": report.delivered,
                "recent": report.id in recent_positions,
            }
        )

    return {
        "active_report_id": active_report_id,
        "groups": list(grouped_projects.values()),
        "pinned_items": get_pinned_work(user, active_report_id),
    }
