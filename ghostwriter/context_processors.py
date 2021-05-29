# Django Imports
from django.conf import settings


def selected_settings(request):
    return {
        "VERSION": settings.VERSION,
        "RELEASE_DATE": settings.RELEASE_DATE,
    }
