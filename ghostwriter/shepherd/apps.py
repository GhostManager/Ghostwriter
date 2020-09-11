"""This contains the configuration of the Shepherd application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class ShepherdConfig(AppConfig):
    name = "ghostwriter.shepherd"

    def ready(self):
        try:
            import ghostwriter.shepherd.signals  # noqa F401
        except ImportError:
            pass
