"""This contains the configuration of the Home application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig

logger = logging.getLogger(__name__)


class HomeConfig(AppConfig):
    name = "ghostwriter.home"

    def ready(self):
        try:
            import ghostwriter.home.signals  # noqa F401 isort:skip
        except ImportError:
            logger.warning("Unable to import Home signal handlers.", exc_info=True)

        # Ghostwriter Libraries
        from ghostwriter.home.django_q_integration import install_django_q_restrictions

        install_django_q_restrictions()
