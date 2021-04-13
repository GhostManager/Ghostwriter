"""This contains the configuration of the CommandCenter application."""

# Django Imports
from django.apps import AppConfig


class CommandCenterConfig(AppConfig):
    name = "ghostwriter.commandcenter"

    def ready(self):
        try:
            import ghostwriter.commandcenter.signals  # noqa F401 isort:skip
        except ImportError:
            pass
