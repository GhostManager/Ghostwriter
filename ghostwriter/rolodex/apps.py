"""This contains the configuration of the Rolodex application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class RolodexConfig(AppConfig):
    name = "ghostwriter.rolodex"
    verbose_name = "Clients & Projects"

    def ready(self):
        try:
            import ghostwriter.rolodex.signals  # noqa F401 isort:skip
        except ImportError:
            logger.warning("Unable to import Rolodex signal handlers.", exc_info=True)
