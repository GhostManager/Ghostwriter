"""Regression tests for reporting resource exports."""

# Standard Libraries
import csv
from io import StringIO

# Django Imports
from django.contrib import admin
from django.test import RequestFactory, TestCase

# 3rd Party Libraries
from import_export.formats.base_formats import CSV

# Ghostwriter Libraries
from ghostwriter.factories import AdminFactory, FindingFactory
from ghostwriter.reporting.models import Finding
from ghostwriter.reporting.resources import FindingResource


class FindingAdminExportTests(TestCase):
    """Exercise the admin CSV pipeline with real finding tag managers."""

    @classmethod
    def setUpTestData(cls):
        cls.user = AdminFactory()
        cls.tagged = FindingFactory(tags=["alpha", "beta"])
        cls.untagged = FindingFactory()

    def test_admin_csv_preserves_populated_and_empty_tags(self):
        request = RequestFactory().get("/admin/reporting/finding/export/")
        request.user = self.user
        queryset = Finding.objects.filter(pk__in=[self.tagged.pk, self.untagged.pk]).order_by("pk")

        output = admin.site._registry[Finding].get_export_data(CSV(), request, queryset)

        rows = list(csv.DictReader(StringIO(output)))
        self.assertEqual(len(rows), 2)
        rows_by_id = {int(row["id"]): row for row in rows}
        self.assertEqual(set(rows_by_id[self.tagged.pk]["tags"].split(",")), {"alpha", "beta"})
        self.assertEqual(rows_by_id[self.untagged.pk]["tags"], "")

    def test_export_can_exclude_tags(self):
        dataset = FindingResource().export([self.tagged], export_fields=["id", "title"])

        self.assertEqual(dataset.headers, ["id", "title"])
        self.assertEqual(dataset[0], (str(self.tagged.pk), self.tagged.title))
