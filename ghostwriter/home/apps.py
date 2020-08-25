"""This contains the configuration of the Home application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = "ghostwriter.home"

    def ready(self):
        try:
            import ghostwriter.home.signals  # noqa F401
        except ImportError:
            pass
