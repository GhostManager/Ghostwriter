"""This contains the configuration of the Users application."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    name = "ghostwriter.users"
    verbose_name = _("Users")

    def ready(self):
        try:
            import ghostwriter.users.signals  # noqa F401
        except ImportError:
            pass
