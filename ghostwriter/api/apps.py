"""This contains the configuration of the GraphQL application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ApiConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "ghostwriter.api"

    def ready(self):
        try:
            import ghostwriter.graphql.signals  # noqa F401 isort:skip
        except ImportError:
            logger.debug("No GraphQL signal handlers are configured.")
