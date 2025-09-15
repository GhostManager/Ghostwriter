
from django.test import TestCase

from ghostwriter.modules.reportwriter import prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError, rich_text_template


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
