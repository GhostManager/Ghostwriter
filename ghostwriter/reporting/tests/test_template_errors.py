from unittest.mock import Mock

from django.test import SimpleTestCase
from jinja2.exceptions import SecurityError

from ghostwriter.modules.reportwriter.base import ReportExportTemplateError


class ReportTemplateErrorTests(SimpleTestCase):
    def test_error_with_location_and_code_context(self):
        error = ReportExportTemplateError("An expression failed.", "the template", "{{ summary }}")

        self.assertEqual(str(error), "An expression failed. The error occurred in the template, near `{{ summary }}`.")

    def test_error_with_code_context_only(self):
        error = ReportExportTemplateError("Invalid expression", code_context="{{ summary }}")

        self.assertEqual(str(error), "Invalid expression near `{{ summary }}`.")

    def test_rejected_call_hides_callable_details(self):
        error = SecurityError("<function helper at 0x1234> is not safely callable")
        with self.assertRaises(ReportExportTemplateError) as result:
            ReportExportTemplateError.map_errors(Mock(side_effect=error), "the template")

        self.assertIn("unsupported function or method", str(result.exception))
        self.assertIn("The error occurred in the template.", str(result.exception))
        self.assertNotIn("0x1234", str(result.exception))
        self.assertIs(result.exception.__cause__, error)

    def test_unknown_sandbox_error_uses_readable_fallback(self):
        error = SecurityError("Call to <function helper at 0x1234> was rejected")
        with self.assertRaises(ReportExportTemplateError) as result:
            ReportExportTemplateError.map_errors(Mock(side_effect=error), "the template")

        self.assertIn("The template uses an unsupported operation.", str(result.exception))
        self.assertIn("The error occurred in the template.", str(result.exception))
        self.assertNotIn("0x1234", str(result.exception))
        self.assertIs(result.exception.__cause__, error)
