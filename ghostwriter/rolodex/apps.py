"""This contains the configuration of the Rolodex application."""

# Django Imports
from django.apps import AppConfig


class RolodexConfig(AppConfig):
    name = "ghostwriter.rolodex"
    verbose_name = "Clients & Projects"

    def ready(self):
        try:
            import ghostwriter.rolodex.signals  # noqa F401 isort:skip
        except ImportError:
            pass
