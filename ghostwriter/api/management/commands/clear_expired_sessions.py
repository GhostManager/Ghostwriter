# Django Imports
from django.core.management import call_command
from django.core.management.base import BaseCommand
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.models import UserSession


class Command(BaseCommand):
    help = "Clear expired Django sessions and GraphQL login sessions."

    def handle(self, *args, **options):
        call_command("clearsessions", stdout=self.stdout, stderr=self.stderr)

        expired_sessions = UserSession.objects.filter(expires_at__lt=timezone.now())
        deleted_count, _ = expired_sessions.delete()

        self.stdout.write(
            self.style.SUCCESS(
                f"Cleared {deleted_count} expired GraphQL login session(s)."
            )
        )
