"""Audit Django Q schedules against Ghostwriter's server-side policy."""

# Django Imports
from django.core.management.base import BaseCommand, CommandError

# 3rd Party Libraries
from django_q.models import Schedule

# Ghostwriter Libraries
from ghostwriter.home.django_q_policy import TaskPolicyError, validate_schedule


class Command(BaseCommand):
    help = "Audit Django Q schedules against the server task allowlist"

    def add_arguments(self, parser):
        parser.add_argument(
            "--check",
            action="store_true",
            help="Exit with an error when a disallowed schedule is found",
        )
        parser.add_argument(
            "--pause-disallowed",
            action="store_true",
            help="Set repeats=0 on every disallowed schedule",
        )

    def handle(self, *args, **options):
        disallowed = []
        for schedule in Schedule.objects.order_by("pk"):
            try:
                validate_schedule(schedule)
            except TaskPolicyError as error:
                disallowed.append((schedule, error))
                self.stdout.write(
                    self.style.WARNING(
                        f"DISALLOWED schedule={schedule.pk} func={schedule.func}: {error}"
                    )
                )
                if options["pause_disallowed"] and schedule.repeats != 0:
                    Schedule.objects.filter(pk=schedule.pk).update(repeats=0)

        if not disallowed:
            self.stdout.write(
                self.style.SUCCESS("All Django Q schedules satisfy server policy.")
            )
            return

        if options["pause_disallowed"]:
            self.stdout.write(
                self.style.SUCCESS(f"Paused {len(disallowed)} disallowed schedule(s).")
            )
        if options["check"]:
            raise CommandError(
                f"Found {len(disallowed)} disallowed Django Q schedule(s)."
            )
