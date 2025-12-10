import copy
from unittest.mock import patch

from django.test import SimpleTestCase

from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
from ghostwriter.modules.reportwriter.base.html_rich_text import LazilyRenderedTemplate


class WorkbookPasswordRichTextTests(SimpleTestCase):
    def test_password_policy_fields_render_as_rich_text(self):
        context = copy.deepcopy(LINTER_CONTEXT)
        policy = context["project"]["workbook_data"]["password"]["policies"][0]
        policy["max_age_rt"] = '<p><span class="bold" style="color: #ee0000;">60</span></p>'
        policy["fgpp"][1][
            "lockout_threshold_rt"
        ] = '<p><span class="bold" style="color: #ee0000;">0</span></p>'

        with patch(
            "ghostwriter.modules.reportwriter.project.base.ExtraFieldSpec.objects.filter",
            return_value=[],
        ):
            renderer = ExportProjectBase(context, is_raw=True)
            rendered_context = renderer.map_rich_texts()

        rendered_policy = rendered_context["project"]["workbook_data"]["password"]["policies"][0]
        max_age_rt = rendered_policy["max_age_rt"]
        lockout_threshold_rt = rendered_policy["fgpp"][1]["lockout_threshold_rt"]

        self.assertIsInstance(max_age_rt, LazilyRenderedTemplate)
        self.assertEqual(
            str(max_age_rt.render_html()), '<p><span class="bold" style="color: #ee0000;">60</span></p>'
        )

        self.assertIsInstance(lockout_threshold_rt, LazilyRenderedTemplate)
        self.assertEqual(
            str(lockout_threshold_rt.render_html()),
            '<p><span class="bold" style="color: #ee0000;">0</span></p>',
        )
