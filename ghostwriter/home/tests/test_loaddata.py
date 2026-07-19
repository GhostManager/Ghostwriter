# Standard Libraries
import json
import tempfile
from io import StringIO

# Django Imports
from django.core.management import call_command
from django.core.management.base import CommandError
from django.test import SimpleTestCase


class LoadDataCommandTests(SimpleTestCase):
    """Tests for rejecting JSON data that is not a Django fixture."""

    def call_command(self, fixture):
        call_command(
            "loaddata",
            fixture,
            stdout=StringIO(),
            stderr=StringIO(),
        )

    def test_rejects_non_fixture_json(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as non_fixture:
            json.dump({"domains": []}, non_fixture)
            non_fixture.flush()

            with self.assertRaisesMessage(
                CommandError,
                "is not a Django fixture: expected a top-level JSON array of records.",
            ):
                self.call_command(non_fixture.name)

    def test_rejects_non_object_records(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json") as non_fixture:
            json.dump(["not-a-record"], non_fixture)
            non_fixture.flush()

            with self.assertRaisesMessage(
                CommandError,
                "is not a Django fixture: every record must be a JSON object.",
            ):
                self.call_command(non_fixture.name)
