# Standard Libraries
import logging

# 3rd Party Libraries
import pytz

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    CloudServicesConfigurationFactory,
    CompanyInformationFactory,
    GeneralConfigurationFactory,
    NamecheapConfigurationFactory,
    ReportConfigurationFactory,
    SlackConfigurationFactory,
    VirusTotalConfigurationFactory,
)

logging.disable(logging.CRITICAL)


class NamecheapConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.NamecheapConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.NamecheapConfiguration = NamecheapConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = NamecheapConfigurationFactory(enable=False)

        # Read
        self.assertEqual(entry.enable, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable, True)

        # Delete
        entry.delete()
        self.assertFalse(self.NamecheapConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.NamecheapConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("NamecheapConfiguration model `get_solo` method failed unexpectedly!")

    def test_sanitized_api_key_property(self):
        entry = self.NamecheapConfiguration.get_solo()
        length = len(entry.api_key)
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_api_key
        self.assertNotEqual(entry.api_key, sanitized)
        self.assertIn(replacement, sanitized)


class ReportConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.ReportConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.ReportConfiguration = ReportConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = ReportConfigurationFactory(enable_borders=False)

        # Read
        self.assertEqual(entry.enable_borders, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable_borders = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable_borders, True)

        # Delete
        entry.delete()
        self.assertFalse(self.ReportConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.ReportConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("ReportConfiguration model `get_solo` method failed unexpectedly!")


class SlackConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.SlackConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.SlackConfiguration = SlackConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = SlackConfigurationFactory(enable=False)

        # Read
        self.assertEqual(entry.enable, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable, True)

        # Delete
        entry.delete()
        self.assertFalse(self.SlackConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.SlackConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("SlackConfiguration model `get_solo` method failed unexpectedly!")

    def test_sanitized_webhook_property(self):
        entry = self.SlackConfiguration.get_solo()
        length = len(entry.webhook_url.split("/")[-1])
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_webhook
        self.assertNotEqual(entry.webhook_url, sanitized)
        self.assertIn(replacement, sanitized)


class CompanyInformationTests(TestCase):
    """Collection of tests for :model:`commandcenter.CompanyInformation`."""

    @classmethod
    def setUpTestData(cls):
        cls.CompanyInformation = CompanyInformationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = CompanyInformationFactory(company_name="SpecterOps")

        # Read
        self.assertEqual(entry.company_name, "SpecterOps")
        self.assertEqual(entry.pk, 1)

        # Update
        entry.company_name = "SpecterOps, Inc."
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.company_name, "SpecterOps, Inc.")

        # Delete
        entry.delete()
        self.assertFalse(self.CompanyInformation.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.CompanyInformation.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("CompanyInformation model `get_solo` method failed unexpectedly!")


class CloudServicesConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.CloudServicesConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.CloudServicesConfiguration = CloudServicesConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = CloudServicesConfigurationFactory(enable=False)

        # Read
        self.assertEqual(entry.enable, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable, True)

        # Delete
        entry.delete()
        self.assertFalse(self.CloudServicesConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.CloudServicesConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("CloudServicesConfiguration model `get_solo` method failed unexpectedly!")

    def test_sanitized_aws_key_property(self):
        entry = self.CloudServicesConfiguration.get_solo()
        length = len(entry.aws_key)
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_aws_key
        self.assertNotEqual(entry.aws_key, sanitized)
        self.assertIn(replacement, sanitized)

    def test_sanitized_aws_secret_property(self):
        entry = self.CloudServicesConfiguration.get_solo()
        length = len(entry.aws_secret)
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_aws_secret
        self.assertNotEqual(entry.aws_secret, sanitized)
        self.assertIn(replacement, sanitized)

    def test_sanitized_do_api_key_property(self):
        entry = self.CloudServicesConfiguration.get_solo()
        length = len(entry.do_api_key)
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_do_api_key
        self.assertNotEqual(entry.do_api_key, sanitized)
        self.assertIn(replacement, sanitized)


class VirusTotalConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.VirusTotalConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.VirusTotalConfiguration = VirusTotalConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = VirusTotalConfigurationFactory(enable=False)

        # Read
        self.assertEqual(entry.enable, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable, True)

        # Delete
        entry.delete()
        self.assertFalse(self.VirusTotalConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.VirusTotalConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("VirusTotalConfiguration model `get_solo` method failed unexpectedly!")

    def test_sanitized_api_key_property(self):
        entry = self.VirusTotalConfiguration.get_solo()
        length = len(entry.api_key)
        replacement = "\u2717" * (length - 8)
        sanitized = entry.sanitized_api_key
        self.assertNotEqual(entry.api_key, sanitized)
        self.assertIn(replacement, sanitized)


class GeneralConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.GeneralConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.GeneralConfiguration = GeneralConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = GeneralConfigurationFactory(default_timezone="UTC")

        # Read
        self.assertEqual(entry.default_timezone, "UTC")
        self.assertEqual(entry.pk, 1)

        # Update
        entry.default_timezone = "US/Pacific"
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.default_timezone, pytz.timezone("US/Pacific"))

        # Delete
        entry.delete()
        self.assertFalse(self.GeneralConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.GeneralConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("GeneralConfiguration model `get_solo` method failed unexpectedly!")
