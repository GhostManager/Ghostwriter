# Standard Libraries
import logging

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import CompanyInformationFactory
from ghostwriter.singleton.templatetags import settings_tags

logging.disable(logging.CRITICAL)

PASSWORD = "SuperNaturalReporting!"


# Tests related to custom template tags and filters


class TemplateTagTests(TestCase):
    """Collection of tests for custom template tags."""

    @classmethod
    def setUpTestData(cls):
        cls.company = CompanyInformationFactory(company_name="SpecterOps")

    def setUp(self):
        pass

    def test_tags(self):
        result = settings_tags.get_solo("commandcenter.CompanyInformation")
        self.assertEqual(result.company_name, "SpecterOps")
