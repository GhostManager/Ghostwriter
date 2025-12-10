from django.test import SimpleTestCase

from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter.base.docx import _lint_context_has_variable


class LintContextHasVariableTests(SimpleTestCase):
    """Validate context lookup helper used during DOCX linting."""

    def test_nested_dict_path_is_detected(self):
        context = {"project": {"data_responses": {"general": {"scope_count": 3}}}}
        self.assertTrue(
            _lint_context_has_variable(
                context, "project.data_responses.general.scope_count"
            )
        )

    def test_list_index_path_is_detected(self):
        context = {"findings": [{"title": "Example"}]}
        self.assertTrue(_lint_context_has_variable(context, "findings[0].title"))

    def test_missing_path_returns_false(self):
        context = {}
        self.assertFalse(
            _lint_context_has_variable(context, "project.data_responses.general.scope_count")
        )

    def test_password_policy_rich_text_fields_present_for_linting(self):
        self.assertTrue(
            _lint_context_has_variable(
                LINTER_CONTEXT, "project.workbook_data.password.policies[0].history_rt"
            )
        )
        self.assertTrue(
            _lint_context_has_variable(
                LINTER_CONTEXT,
                "project.workbook_data.password.policies[0].fgpp[1].lockout_threshold_rt",
            )
        )
