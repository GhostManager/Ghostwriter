# Standard Libraries
import logging

# Django Imports
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template import Context, Template
from django.test import TestCase
from django.test.utils import override_settings

# Ghostwriter Libraries
from ghostwriter.singleton.models import get_cache
from ghostwriter.singleton.tests.models import (
    SiteConfiguration,
    SiteConfigurationWithExplicitlyGivenId,
)

logging.disable(logging.CRITICAL)


# Tests are modified versions of tests from the original "Django Solo" project
# https://github.com/lazybird/django-solo/tree/master/solo/tests


# Test Cases


class SingletonTest(TestCase):
    def setUp(self):
        self.template = Template(
            "{% load settings_tags %}"
            '{% get_solo "singleton.SiteConfiguration" as site_config  %}'
            "{{ site_config.site_name }}"
            "{{ site_config.file.url }}"
        )
        self.cache = get_cache("default")
        self.cache_key = SiteConfiguration.get_cache_key()
        self.cache.clear()
        SiteConfiguration.objects.all().delete()

    def test_template_tag_renders_default_site_config(self):
        SiteConfiguration.objects.all().delete()
        # At this point, there is no configuration object and we expect
        # one to be created automatically with the default name value as
        # defined in the test models
        output = self.template.render(Context())
        self.assertIn("Default Config", output)

    def test_template_tag_renders_site_config(self):
        SiteConfiguration.objects.create(site_name="Test Config")
        output = self.template.render(Context())
        self.assertIn("Test Config", output)

    @override_settings(SOLO_CACHE="default")
    def test_template_tag_uses_cache_if_enabled(self):
        SiteConfiguration.objects.create(site_name="Config In Database")
        fake_configuration = {"site_name": "Config In Cache"}
        self.cache.set(self.cache_key, fake_configuration, 10)
        output = self.template.render(Context())
        self.assertNotIn("Config In Database", output)
        self.assertNotIn("Default Config", output)
        self.assertIn("Config In Cache", output)

    @override_settings(SOLO_CACHE=None)
    def test_template_tag_uses_database_if_cache_disabled(self):
        SiteConfiguration.objects.create(site_name="Config In Database")
        fake_configuration = {"site_name": "Config In Cache"}
        self.cache.set(self.cache_key, fake_configuration, 10)
        output = self.template.render(Context())
        self.assertNotIn("Config In Cache", output)
        self.assertNotIn("Default Config", output)
        self.assertIn("Config In Database", output)

    @override_settings(SOLO_CACHE="default")
    def test_delete_if_cache_enabled(self):
        self.assertEqual(SiteConfiguration.objects.count(), 0)
        self.assertIsNone(self.cache.get(self.cache_key))

        one_cfg = SiteConfiguration.get_solo()
        one_cfg.site_name = "TEST SITE PLEASE IGNORE"
        one_cfg.save()
        self.assertEqual(SiteConfiguration.objects.count(), 1)
        self.assertIsNotNone(self.cache.get(self.cache_key))

        one_cfg.delete()
        self.assertEqual(SiteConfiguration.objects.count(), 0)
        self.assertIsNone(self.cache.get(self.cache_key))
        self.assertEqual(SiteConfiguration.get_solo().site_name, "Default Config")

    @override_settings(SOLO_CACHE=None)
    def test_delete_if_cache_disabled(self):
        # As above, but without the cache checks
        self.assertEqual(SiteConfiguration.objects.count(), 0)
        one_cfg = SiteConfiguration.get_solo()
        one_cfg.site_name = "TEST (uncached) SITE PLEASE IGNORE"
        one_cfg.save()
        self.assertEqual(SiteConfiguration.objects.count(), 1)
        one_cfg.delete()
        self.assertEqual(SiteConfiguration.objects.count(), 0)
        self.assertEqual(SiteConfiguration.get_solo().site_name, "Default Config")

    @override_settings(SOLO_CACHE="default")
    def test_file_upload_if_cache_enabled(self):
        cfg = SiteConfiguration.objects.create(site_name="Test Config", file=SimpleUploadedFile("file.pdf", None))
        output = self.template.render(Context())
        self.assertIn(cfg.file.url, output)

    @override_settings(SOLO_CACHE_PREFIX="other")
    def test_cache_prefix_overriding(self):
        key = SiteConfiguration.get_cache_key()
        prefix = key.partition(":")[0]
        self.assertEqual(prefix, "other")


class SingletonWithExplicitIdTest(TestCase):
    def setUp(self):
        SiteConfigurationWithExplicitlyGivenId.objects.all().delete()

    def test_when_singleton_instance_id_is_given_created_item_will_have_given_instance_id(
        self,
    ):
        item = SiteConfigurationWithExplicitlyGivenId.get_solo()
        self.assertEqual(item.pk, SiteConfigurationWithExplicitlyGivenId.singleton_instance_id)
