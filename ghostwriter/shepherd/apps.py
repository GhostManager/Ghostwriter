"""This contains the configuration of the Shepherd application."""

# Django Imports
from django.apps import AppConfig


class ShepherdConfig(AppConfig):
    name = "ghostwriter.shepherd"

    def ready(self):
        try:
            import ghostwriter.shepherd.signals  # noqa F401 isort:skip
        except ImportError:
            pass
