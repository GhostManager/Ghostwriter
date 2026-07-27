"""This contains the configuration of the Reporting application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class ReportingConfig(AppConfig):
    name = "ghostwriter.reporting"

    def ready(self):
        try:
            import ghostwriter.reporting.signals  # noqa F401 isort:skip
        except ImportError:
            logger.warning("Unable to import Reporting signal handlers.", exc_info=True)
