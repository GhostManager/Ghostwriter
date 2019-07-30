from django.apps import AppConfig


class ReportingConfig(AppConfig):
    name = 'ghostwriter.reporting'

    def ready(self):
        try:
            import ghostwriter.reporting.signals  # noqa F401
        except ImportError:
            pass