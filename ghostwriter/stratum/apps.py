"""This contains the configuration of the Stratum application."""

# Django Imports
from django.apps import AppConfig


class StratumConfig(AppConfig):
    name = "ghostwriter.stratum"

    def ready(self):
        pass