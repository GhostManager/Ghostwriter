# Standard Libraries
import json
import os

# Django Imports
from django.apps import apps
from django.core.management.commands import loaddata

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportTemplate, Severity


def should_add_record(record):
    """
    Determine if a record should be inserted into the database. Some records are
    customizable and should not be overwritten during a build. If the ``pk`` already
    exists, err on the side of skipping the insert.
    """
    return not apps.get_model(record["model"]).objects.filter(pk=record["pk"]).exists()


class Command(loaddata.Command):
    def handle(self, *args, **options):
        """
        Altered ``handle`` method to skip records that already exist.

        Based on this StackOverflow answer: https://stackoverflow.com/a/68894033
        """
        args = list(args)

        # Read the original JSON file
        file_name = args[0]
        with open(file_name) as json_file:
            json_list = json.load(json_file)

        # Filter out records that already exists
        json_list_filtered = list(filter(should_add_record, json_list))
        if not json_list_filtered:
            print("All required records are present; no new data to load.")
            return
        else:
            print(f"Found {len(json_list) - len(json_list_filtered)} new records to insert into the database.")

        # Write the updated JSON file
        file_dir_and_name, file_ext = os.path.splitext(file_name)
        file_name_temp = f"{file_dir_and_name}_temp{file_ext}"
        with open(file_name_temp, "w") as json_file_temp:
            json.dump(json_list_filtered, json_file_temp)

        # Pass the request to the actual loaddata (parent functionality)
        args[0] = file_name_temp
        super().handle(*args, **options)

        # You can choose to not delete the file so that you can see what was added to your records
        os.remove(file_name_temp)
