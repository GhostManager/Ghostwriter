"""This contains the configuration of the Oplog application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class OplogConfig(AppConfig):
    name = "ghostwriter.oplog"
    verbose_name = "Activity Logging"

    def ready(self):
        try:
            import ghostwriter.oplog.signals  # noqa F401 isort:skip
        except ImportError:
            logger.warning("Unable to import Oplog signal handlers.", exc_info=True)
