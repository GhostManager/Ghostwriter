"""This contains the configuration of the Singleton application."""

# Django Imports
from django.apps import AppConfig


class SingletonConfig(AppConfig):
    name = "ghostwriter.singleton"

    def ready(self):
        try:
            import ghostwriter.singleton.signals  # noqa F401 isort:skip
        except ImportError:
            pass
