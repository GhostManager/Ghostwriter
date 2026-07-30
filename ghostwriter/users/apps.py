"""This contains the configuration of the Users application."""

# Standard Libraries
import logging

# Django Imports
from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _

logger = logging.getLogger(__name__)


class UsersConfig(AppConfig):
    name = "ghostwriter.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import ghostwriter.users.signals  # noqa F401 isort:skip
        except ModuleNotFoundError as exception:
            if exception.name != "ghostwriter.users.signals":
                raise
            logger.debug("No Users signal handlers are configured.")
