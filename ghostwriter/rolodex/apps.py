"""This contains the configuration of the Rolodex application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class RolodexConfig(AppConfig):
    name = "ghostwriter.rolodex"

    def ready(self):
        try:
            import ghostwriter.rolodex.signals  # noqa F401
        except ImportError:
            pass
