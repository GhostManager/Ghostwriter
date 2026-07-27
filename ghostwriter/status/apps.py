"""This contains all the views used by the Status application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class StatusConfig(AppConfig):
    name = "ghostwriter.status"

    def ready(self):
        try:
            import ghostwriter.status.signals  # noqa F401 isort:skip
        except ModuleNotFoundError as exception:
            if exception.name != "ghostwriter.status.signals":
                raise
            logger.debug("No Status signal handlers are configured.")
