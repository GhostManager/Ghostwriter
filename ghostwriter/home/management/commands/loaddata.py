# Standard Libraries
import json
import os

# Django Imports
from django.apps import apps
from django.core.management.commands import loaddata


def should_add_record(record):
    """
    Determine if a record should be inserted into the database. Some records are
    customizable and should not be overwritten during a build. If the ``pk`` already
    exists, err on the side of skipping the insert. Certain models are always seeded.
    """
    models_to_seed = [
        "reporting.doctype",
    ]
    if (
        record["model"] not in models_to_seed
        and apps.get_model(record["model"]).objects.filter(pk=record["pk"]).exists()
    ):
        return False
    return True


class Command(loaddata.Command):
    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            dest="force",
            help="Apply all fixtures even if they already exist.",
        )
        super().add_arguments(parser)

    def handle(self, *args, **options):
        """
        Altered ``handle`` method to skip records that already exist.

        Based on this StackOverflow answer: https://stackoverflow.com/a/68894033
        """
        self.force_apply = options["force"]
        args = list(args)

        # Read the original JSON file
        file_name = args[0]
        with open(file_name, "r", encoding="utf-8") as json_file:
            json_list = json.load(json_file)

        # Filter out records that already exists
        if not self.force_apply:
            json_list_filtered = list(filter(should_add_record, json_list))
        else:
            self.stdout.write(self.style.WARNING("Applying all fixtures."))
            json_list_filtered = json_list
        if not json_list_filtered:
            self.stdout.write(self.style.SUCCESS("All required records are present; no new data to load."))
            return
        self.stdout.write(
            self.style.WARNING(f"Found {len(json_list_filtered)} new records to insert into the database.")
        )

        # Write the updated JSON file
        file_dir_and_name, file_ext = os.path.splitext(file_name)
        file_name_temp = f"{file_dir_and_name}_temp{file_ext}"
        with open(file_name_temp, "w", encoding="utf-8") as json_file_temp:
            json.dump(json_list_filtered, json_file_temp)

        # Pass the request to the actual loaddata (parent functionality)
        args[0] = file_name_temp
        super().handle(*args, **options)

        # You can choose to not delete the file so that you can see what was added to your records
        os.remove(file_name_temp)
