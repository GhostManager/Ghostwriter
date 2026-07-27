"""This contains the configuration of the Shepherd application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ShepherdConfig(AppConfig):
    name = "ghostwriter.shepherd"
    verbose_name = "Infrastructure Management"

    def ready(self):
        try:
            import ghostwriter.shepherd.signals  # noqa F401 isort:skip
        except ImportError:
            logger.warning("Unable to import Shepherd signal handlers.", exc_info=True)
