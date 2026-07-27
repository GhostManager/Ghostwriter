"""This contains the configuration of the Singleton application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class SingletonConfig(AppConfig):
    name = "ghostwriter.singleton"

    def ready(self):
        try:
            import ghostwriter.singleton.signals  # noqa F401 isort:skip
        except ModuleNotFoundError as exception:
            if exception.name != "ghostwriter.singleton.signals":
                raise
            logger.debug("No Singleton signal handlers are configured.")
