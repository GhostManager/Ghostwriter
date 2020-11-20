"""This contains the configuration of the CommandCenter application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class CommandCenterConfig(AppConfig):
    name = "ghostwriter.commandcenter"

    def ready(self):
        try:
            import ghostwriter.commandcenter.signals  # noqa F401
        except ImportError:
            pass
