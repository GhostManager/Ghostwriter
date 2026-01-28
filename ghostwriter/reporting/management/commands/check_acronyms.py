"""Management command to check loaded acronyms."""

from django.core.management.base import BaseCommand

from ghostwriter.reporting.models import Acronym


class Command(BaseCommand):
    help = "Display acronyms loaded in the database"

    def handle(self, *args, **options):
        count = Acronym.objects.count()
        self.stdout.write(f"Total acronyms: {count}\n")
        
        if count > 0:
            self.stdout.write("\nFirst 10 acronyms:")
            for acronym in Acronym.objects.all()[:10]:
                expansion = acronym.expansion[:50] + "..." if len(acronym.expansion) > 50 else acronym.expansion
                self.stdout.write(f"  {acronym.acronym}: {expansion}")
        else:
            self.stdout.write("No acronyms found in database")
