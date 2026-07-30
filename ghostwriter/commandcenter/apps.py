"""This contains the configuration of the CommandCenter application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class CommandCenterConfig(AppConfig):
    name = "ghostwriter.commandcenter"

    def ready(self):
        try:
            import ghostwriter.commandcenter.signals  # noqa F401 isort:skip
        except ModuleNotFoundError as exception:
            if exception.name != "ghostwriter.commandcenter.signals":
                raise
            logger.debug("No CommandCenter signal handlers are configured.")
