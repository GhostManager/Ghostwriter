"""This contains the configuration of the Shepherd application."""

# Django Imports
from django.apps import AppConfig

class ShepherdConfig(AppConfig):
    name = "ghostwriter.shepherd"
    verbose_name = "Infrastructure Management"

    def ready(self):
        import ghostwriter.shepherd.signals  # noqa F401 isort:skip
