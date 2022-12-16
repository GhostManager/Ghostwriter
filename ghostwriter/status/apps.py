"""This contains all the views used by the Status application."""

# Django Imports
from django.apps import AppConfig

# 3rd Party Libraries
from health_check.plugins import plugin_dir

# Ghostwriter Libraries
from ghostwriter.modules.health_utils import HasuraBackend


class StatusConfig(AppConfig):
    name = "ghostwriter.status"

    def ready(self):
        try:
            import ghostwriter.status.signals  # noqa F401 isort:skip

            plugin_dir.register(HasuraBackend)
        except ImportError:
            pass
