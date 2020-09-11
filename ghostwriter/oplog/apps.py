"""This contains the configuration of the Oplog application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class OplogConfig(AppConfig):
    name = "ghostwriter.oplog"

    def ready(self):
        try:
            import ghostwriter.oplog.signals  # noqa F401
        except ImportError:
            pass
