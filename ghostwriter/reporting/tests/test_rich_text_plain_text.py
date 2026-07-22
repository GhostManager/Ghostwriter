"""Tests for HTML conversion used by XLSX rich-text cells."""

# Django Imports
from django.test import SimpleTestCase

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter.richtext.plain_text import html_to_plain_text


class RichTextToPlainTextTests(SimpleTestCase):
    """Tests for report rich text converted to XLSX-compatible text."""

    def test_trailing_empty_paragraph_after_list_is_omitted(self):
        result = html_to_plain_text(
            "<ul><li><p>First</p></li><li><p>Second</p></li></ul><p></p>",
            {},
        )

        self.assertEqual(result, "First\nSecond\n")

    def test_internal_empty_paragraph_is_preserved(self):
        result = html_to_plain_text("<p>Before</p><p></p><p>After</p>", {})

        self.assertEqual(result, "Before\n\nAfter\n")

    def test_trailing_hard_break_is_preserved(self):
        result = html_to_plain_text("<p>Before</p><p><br></p>", {})

        self.assertEqual(result, "Before\n\n\n")
