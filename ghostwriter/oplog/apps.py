"""This contains the configuration of the Oplog application."""

# Django Imports
from django.apps import AppConfig


class OplogConfig(AppConfig):
    name = "ghostwriter.oplog"
    verbose_name = "Activity Logging"

    def ready(self):
        try:
            import ghostwriter.oplog.signals  # noqa F401 isort:skip
        except ImportError:
            pass
