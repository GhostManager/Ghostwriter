"""This contains all the views used by the Status application."""

# Django Imports
from django.apps import AppConfig


class StatusConfig(AppConfig):
    name = "ghostwriter.status"

    def ready(self):
        try:
            import ghostwriter.status.signals  # noqa F401 isort:skip
        except ImportError:
            pass
