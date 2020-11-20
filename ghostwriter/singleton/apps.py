"""This contains the configuration of the Singleton application."""

# Django & Other 3rd Party Libraries
from django.apps import AppConfig


class SingletonConfig(AppConfig):
    name = "ghostwriter.singleton"

    def ready(self):
        try:
            import ghostwriter.singleton.signals  # noqa F401
        except ImportError:
            pass
