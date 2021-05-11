"""This contains the configuration of the Home application."""

# Django Imports
from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = "ghostwriter.home"

    def ready(self):
        try:
            import ghostwriter.home.signals  # noqa F401 isort:skip
        except ImportError:
            pass
