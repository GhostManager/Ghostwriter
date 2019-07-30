"""This defines the available applications."""

from django.apps import AppConfig


class ShepherdConfig(AppConfig):
    name = 'ghostwriter.shepherd'

    def ready(self):
        try:
            import ghostwriter.shepherd.signals  # noqa F401
        except ImportError:
            pass