# Django Imports
from django.conf import settings

# Ghostwriter Libraries
from ghostwriter.home.editor_shortcuts import get_editor_shortcuts_date_config


def selected_settings(request):
    return {
        "VERSION": settings.VERSION,
        "RELEASE_DATE": settings.RELEASE_DATE,
        "EDITOR_SHORTCUTS_DATE_CONFIG": (
            get_editor_shortcuts_date_config()
            if request.user.is_authenticated
            else None
        ),
    }
