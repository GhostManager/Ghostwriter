"""Tests for custom Shepherd template tags."""

# Django Imports
from django.test import SimpleTestCase

# Ghostwriter Libraries
from ghostwriter.shepherd.templatetags.shepherd_tags import category_value


class CategoryValueTests(SimpleTestCase):
    def test_dict_values_render_keys_and_nonempty_nested_values(self):
        value = {
            "source": "business",
            "categories": ["technology", "security"],
            "empty": None,
        }

        self.assertEqual(
            category_value(value),
            "source: business, categories: technology, security",
        )

    def test_set_values_are_rendered_in_deterministic_order(self):
        self.assertEqual(
            category_value({"technology", "business"}),
            "business, technology",
        )

    def test_list_values_preserve_their_order(self):
        self.assertEqual(
            category_value(["technology", "business"]),
            "technology, business",
        )
