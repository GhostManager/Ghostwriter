"""This contains the configuration of the Home application."""

# Django Imports
from django.apps import AppConfig


class HomeConfig(AppConfig):
    name = "ghostwriter.home"

    def ready(self):
        try:
            import ghostwriter.home.signals  # noqa F401 isort:skip
        except ImportError:
            pass

        # Ghostwriter Libraries
        from ghostwriter.home.django_q_integration import install_django_q_restrictions

        install_django_q_restrictions()
