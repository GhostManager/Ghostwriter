"""This contains the configuration of the GraphQL application."""

# Django Imports
from django.apps import AppConfig


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ghostwriter.api"

    def ready(self):
        try:
            import ghostwriter.graphql.signals  # noqa F401 isort:skip
        except ImportError:
            pass
