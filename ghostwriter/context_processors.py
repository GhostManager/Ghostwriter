# Django Imports
from django.conf import settings

# Ghostwriter Libraries
from ghostwriter.home.editor_shortcuts import get_editor_shortcuts_date_config
from ghostwriter.home.navigation import get_sidebar_navigation
from ghostwriter.home.working_context import get_pinned_work


def get_active_engagement(request):
    """Return the user's working report and its engagement context."""
    if not request.user.is_authenticated:
        return None

    active_report = request.session.get("active_report") or {}
    try:
        report_id = int(active_report.get("id"))
    except (TypeError, ValueError):
        return None

    # Import here to keep application startup and migration discovery lightweight.
    # Ghostwriter Libraries
    from ghostwriter.reporting.models import Report

    report = (
        Report.user_viewable(request.user)
        .select_related("project", "project__client", "project__project_type")
        .filter(pk=report_id)
        .first()
    )
    if not report:
        return None

    return {
        "report": report,
        "project": report.project,
        "client": report.project.client,
    }


def selected_settings(request):
    active_engagement = get_active_engagement(request)
    active_report_id = (
        active_engagement["report"].id if active_engagement else None
    )
    return {
        "VERSION": settings.VERSION,
        "RELEASE_DATE": settings.RELEASE_DATE,
        "active_engagement": active_engagement,
        "pinned_work": (
            get_pinned_work(request.user, active_report_id)
            if request.user.is_authenticated
            else []
        ),
        "sidebar_navigation": get_sidebar_navigation(request),
        "EDITOR_SHORTCUTS_DATE_CONFIG": (
            get_editor_shortcuts_date_config()
            if request.user.is_authenticated
            else None
        ),
    }
