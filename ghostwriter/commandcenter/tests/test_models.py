# Standard Libraries
import logging
import zoneinfo
from unittest.mock import patch

# Django Imports
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    BannerConfigurationFactory,
    CloudServicesConfigurationFactory,
    CompanyInformationFactory,
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
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

    def test_parse_outline_tags_includes_defaults_and_prefix_rules(self):
        rules = self.ReportConfiguration.parse_outline_tags("cred*, ATT&CK:, report")

        self.assertEqual(rules.exact_tags, ("report", "evidence"))
        self.assertEqual(rules.prefix_tags, ("cred", "att&ck:"))

    def test_parse_outline_tags_without_defaults_preserves_exact_and_prefix_rules(self):
        rules = self.ReportConfiguration.parse_outline_tags("Credential,att&ck:*", include_defaults=False)

        self.assertEqual(rules.exact_tags, ("credential",))
        self.assertEqual(rules.prefix_tags, ("att&ck:",))


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
        self.assertEqual(entry.default_timezone, zoneinfo.ZoneInfo("UTC"))
        self.assertEqual(entry.pk, 1)

        # Update
        entry.default_timezone = "US/Pacific"
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.default_timezone, zoneinfo.ZoneInfo("US/Pacific"))

        # Delete
        entry.delete()
        self.assertFalse(self.GeneralConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.GeneralConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("GeneralConfiguration model `get_solo` method failed unexpectedly!")


class BannerConfigurationTests(TestCase):
    """Collection of tests for :model:`commandcenter.BannerConfiguration`."""

    @classmethod
    def setUpTestData(cls):
        cls.BannerConfiguration = BannerConfigurationFactory._meta.model

    def test_crud_finding(self):
        # Create
        entry = BannerConfigurationFactory(enable_banner=False)

        # Read
        self.assertEqual(entry.enable_banner, False)
        self.assertEqual(entry.pk, 1)

        # Update
        entry.enable_banner = True
        entry.save()
        entry.refresh_from_db()
        self.assertEqual(entry.enable_banner, True)

        # Delete
        entry.delete()
        self.assertFalse(self.BannerConfiguration.objects.all().exists())

    def test_get_solo_method(self):
        try:
            entry = self.BannerConfiguration.get_solo()
            self.assertEqual(entry.pk, 1)
        except Exception:
            self.fail("BannerConfiguration model `get_solo` method failed unexpectedly!")


class ExtraFieldSpecModelTests(TestCase):
    """Collection of tests for :model:`commandcenter.ExtraFieldSpec`."""

    @classmethod
    def setUpTestData(cls):
        cls.model = ExtraFieldModelFactory(
            model_internal_name="rolodex.Client",
            model_display_name="Clients",
        )

    def test_moving_field_to_later_position_shifts_intervening_fields(self):
        first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        second = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=2,
        )
        third = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="third",
            display_name="Third",
            type="single_line_text",
            position=3,
        )

        first.position = 3
        first.save()

        first.refresh_from_db()
        second.refresh_from_db()
        third.refresh_from_db()

        self.assertEqual(
            [
                (first.internal_name, first.position),
                (second.internal_name, second.position),
                (third.internal_name, third.position),
            ],
            [("first", 3), ("second", 1), ("third", 2)],
        )

    def test_inserting_field_at_existing_position_shifts_following_fields(self):
        ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=2,
        )
        inserted = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="inserted",
            display_name="Inserted",
            type="single_line_text",
            position=2,
        )

        self.assertEqual(
            list(
                inserted.__class__.objects.filter(target_model=self.model)
                .values_list("internal_name", "position")
            ),
            [("first", 1), ("inserted", 2), ("second", 3)],
        )

    def test_moving_field_to_earlier_position_shifts_intervening_fields(self):
        first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        second = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=2,
        )
        third = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="third",
            display_name="Third",
            type="single_line_text",
            position=3,
        )

        third.position = 1
        third.save()

        first.refresh_from_db()
        second.refresh_from_db()
        third.refresh_from_db()

        self.assertEqual(
            [
                (first.internal_name, first.position),
                (second.internal_name, second.position),
                (third.internal_name, third.position),
            ],
            [("first", 2), ("second", 3), ("third", 1)],
        )

    def test_deleting_field_closes_position_gap(self):
        first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        second = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=2,
        )
        third = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="third",
            display_name="Third",
            type="single_line_text",
            position=3,
        )

        second.delete()
        first.refresh_from_db()
        third.refresh_from_db()

        self.assertEqual(
            list(
                third.__class__.objects.filter(target_model=self.model)
                .values_list("internal_name", "position")
            ),
            [("first", 1), ("third", 2)],
        )

    def test_blank_position_appends_to_end(self):
        ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        appended = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="appended",
            display_name="Appended",
            type="single_line_text",
            position=None,
        )

        appended.refresh_from_db()
        self.assertEqual(appended.position, 2)

    def test_same_position_is_allowed_on_different_models(self):
        other_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Report",
            model_display_name="Reports",
        )

        first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        second = ExtraFieldSpecFactory(
            target_model=other_model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=1,
        )

        self.assertEqual(first.position, 1)
        self.assertEqual(second.position, 1)

    def test_reordering_with_update_fields_persists_new_position(self):
        first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        second = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="second",
            display_name="Second",
            type="single_line_text",
            position=2,
        )
        third = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="third",
            display_name="Third",
            type="single_line_text",
            position=3,
        )

        first.position = 3
        first.save(update_fields={"display_name"})

        first.refresh_from_db()
        second.refresh_from_db()
        third.refresh_from_db()

        self.assertEqual(
            [
                (first.internal_name, first.position),
                (second.internal_name, second.position),
                (third.internal_name, third.position),
            ],
            [("first", 3), ("second", 1), ("third", 2)],
        )

    def test_moving_models_with_update_fields_persists_target_model_and_position(self):
        other_model = ExtraFieldModelFactory(
            model_internal_name="reporting.Report",
            model_display_name="Reports",
        )
        source_first = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="source_first",
            display_name="Source First",
            type="single_line_text",
            position=1,
        )
        moving = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="moving",
            display_name="Moving",
            type="single_line_text",
            position=2,
        )
        destination = ExtraFieldSpecFactory(
            target_model=other_model,
            internal_name="destination",
            display_name="Destination",
            type="single_line_text",
            position=1,
        )

        moving.target_model = other_model
        moving.position = 1
        moving.save(update_fields={"display_name"})

        source_first.refresh_from_db()
        moving.refresh_from_db()
        destination.refresh_from_db()

        self.assertEqual(source_first.position, 1)
        self.assertEqual(moving.target_model_id, other_model.pk)
        self.assertEqual(moving.position, 1)
        self.assertEqual(destination.position, 2)

    def test_existing_save_locks_row_before_target_models(self):
        field = ExtraFieldSpecFactory(
            target_model=self.model,
            internal_name="first",
            display_name="First",
            type="single_line_text",
            position=1,
        )
        lock_order = []
        manager = type(field).objects
        original_select_for_update = manager.select_for_update

        def tracked_select_for_update(*args, **kwargs):
            lock_order.append("row")
            return original_select_for_update(*args, **kwargs)

        def tracked_model_lock(target_model_id):
            lock_order.append(f"model:{target_model_id}")

        field.position = 1
        with patch.object(manager, "select_for_update", side_effect=tracked_select_for_update):
            with patch.object(type(field), "_lock_target_model", side_effect=tracked_model_lock):
                field.save()

        self.assertEqual(lock_order[0], "row")
        self.assertIn(f"model:{self.model.pk}", lock_order[1:])
