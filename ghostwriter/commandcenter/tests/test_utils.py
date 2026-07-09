import logging

from django.test import SimpleTestCase

from ghostwriter.commandcenter.utils import render_rich_text_value
from ghostwriter.modules.reportwriter.base import ReportExportError


class BrokenRichTextValue:
    def __html__(self):
        raise ReportExportError("database details should stay out of the response")


class RenderRichTextValueTests(SimpleTestCase):
    def test_report_export_error_logs_exception_and_returns_generic_preview_error(self):
        previous_disable_level = logging.root.manager.disable
        logging.disable(logging.NOTSET)
        try:
            with self.assertLogs("ghostwriter.commandcenter.utils", level="ERROR") as logs:
                rendered = render_rich_text_value(BrokenRichTextValue())
        finally:
            logging.disable(previous_disable_level)

        self.assertIn("Preview Error", rendered)
        self.assertIn("An unexpected error occurred while rendering this preview.", rendered)
        self.assertNotIn("database details", rendered)
        self.assertIn("Export error rendering rich-text preview value", logs.output[0])
