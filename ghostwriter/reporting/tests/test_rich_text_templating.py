
from django.test import TestCase

from ghostwriter.factories import ExtraFieldModelFactory, ExtraFieldSpecFactory, ReportFactory
from ghostwriter.modules.reportwriter import prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.base.html_rich_text import rich_text_template
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.reporting.models import Report


class RichTextTemplatingTests(TestCase):
    maxDiff = None

    def test_list(self):
        env, _ = prepare_jinja2_env(debug=True)
        template = rich_text_template(env, "<ol><li>{%li for i in thelist %}</li><li>{{i}}</li><li>{%li endfor %}</li></ol>")
        out = template.render({
            "thelist": ["foo", "bar", "baz"]
        })
        self.assertEqual(out, "<ol><li>foo</li><li>bar</li><li>baz</li></ol>")

    def test_table(self):
        env, _ = prepare_jinja2_env(debug=True)
        template = rich_text_template(env, "<table><tr><td>{%tr for row in thelist%}</td><td></td></tr><tr><td>{{row[0]}}</td><td>{{row[1]}}</td></tr><tr><td>{%tr endfor %}</td><td></td></tr></table>")
        out = template.render({
            "thelist": [["foo", 1], ["bar", 2], ["baz", 3]]
        })
        self.assertEqual(out, "<table><tr><td>foo</td><td>1</td></tr><tr><td>bar</td><td>2</td></tr><tr><td>baz</td><td>3</td></tr></table>")

    def test_prefix_not_nested(self):
        env, _ = prepare_jinja2_env(debug=True)
        with self.assertRaisesMessage(ReportExportTemplateError, "Jinja tag prefixed with 'li' was not a descendant of a li tag"):
            rich_text_template(env, "<ol>{%li for i in thelist %}<li>{{i}}</li><li>{%li endfor %}</li></ol>")

    def test_legacy_reference_and_caption_tags_accept_whitespace_after_opening_braces(self):
        env, _ = prepare_jinja2_env(debug=True)
        template = rich_text_template(
            env,
            '<h2 xmlns="http://www.w3.org/1999/xhtml">Some H2</h2>'
            '<p xmlns="http://www.w3.org/1999/xhtml">The following is an example.</p>'
            '<h3 xmlns="http://www.w3.org/1999/xhtml">Some H3</h3>'
            '<p xmlns="http://www.w3.org/1999/xhtml">{{ .ref Payload Hosting and Lateral Movement With Codex }} is a reference with a space after the dot.</p>'
            '<p xmlns="http://www.w3.org/1999/xhtml">{{ .caption Here is a Caption}}</p>',
        )
        out = template.render({})
        self.assertIn('data-gw-ref="Payload Hosting and Lateral Movement With Codex"', out)
        self.assertIn('data-gw-caption="Here is a Caption"', out)

    def test_report_export_handles_report_extra_field_with_spaced_legacy_reference_and_caption_tags(self):
        report_extra_field = ExtraFieldModelFactory(
            model_internal_name=Report._meta.label,
            model_display_name="Reports",
        )
        ExtraFieldSpecFactory(
            internal_name="narrative",
            display_name="Narrative",
            type="rich_text",
            target_model=report_extra_field,
        )
        report = ReportFactory(
            extra_fields={
                "narrative": (
                    '<h2 xmlns="http://www.w3.org/1999/xhtml">Some H2</h2>'
                    '<p xmlns="http://www.w3.org/1999/xhtml">'
                    "The following is an example."
                    "</p>"
                    '<h3 xmlns="http://www.w3.org/1999/xhtml">Some H3</h3>'
                    '<p xmlns="http://www.w3.org/1999/xhtml">'
                    "{{ .ref Payload Hosting and Lateral Movement With Codex }} "
                    "is a reference with a space after the dot."
                    "</p>"
                    '<p xmlns="http://www.w3.org/1999/xhtml">'
                    "{{ .caption Here is a Caption}}"
                    "</p>"
                )
            },
        )

        out = ExportReportDocx(report, report_template=report.docx_template).run()
        self.assertGreater(len(out.getvalue()), 0)
