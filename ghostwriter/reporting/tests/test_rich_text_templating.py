# Standard Libraries
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory

# Django Imports
from django.test import SimpleTestCase, TestCase

# 3rd Party Libraries
import jinja2
from docxtpl import RichText as DocxRichText
from jinja2.exceptions import SecurityError

# Ghostwriter Libraries
from ghostwriter.factories import (
    ExtraFieldModelFactory,
    ExtraFieldSpecFactory,
    OplogEntryFactory,
    ReportFactory,
)
from ghostwriter.modules.reportwriter import jinja_funcs, prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.base.html_rich_text import (
    CompiledRichTextTemplate,
    HtmlRichText,
    LazilyRenderedTemplate,
    rich_text_template,
)
from ghostwriter.modules.reportwriter.forms import JinjaRichTextField
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Report


class RichTextTemplatingTests(SimpleTestCase):
    maxDiff = None

    @staticmethod
    def render_with_project_description(source):
        """Render source with the rich-text object used by the reported escapes."""
        env = prepare_jinja2_env()
        context = {}
        context["project"] = {
            "description_rt": LazilyRenderedTemplate(
                rich_text_template(env, ""),
                "the project description",
                context,
            )
        }
        return LazilyRenderedTemplate(
            rich_text_template(env, source),
            "test rich text",
            context,
        ).render_html()

    def test_debug_extension_is_not_enabled(self):
        env, undefined_variables = prepare_jinja2_env(debug=True)

        self.assertNotIn("jinja2.ext.DebugExtension", env.extensions)
        with self.assertRaises(jinja2.TemplateSyntaxError):
            env.from_string("{% debug %}")

        env.from_string("{{ missing_variable }}").render()
        self.assertEqual(undefined_variables, {"missing_variable"})

    def test_sandbox_does_not_expose_rich_text_attributes(self):
        env = prepare_jinja2_env()
        rich_text = LazilyRenderedTemplate(
            rich_text_template(env, "<p>Safe content</p>"),
            "sensitive location",
            {},
        )

        rendered = env.from_string(
            "{{ rich_text }}|{{ rich_text.location }}|" "{{ rich_text.render_html }}"
        ).render(rich_text=rich_text)

        self.assertEqual(rendered, "<p>Safe content</p>||")

    def test_lazy_template_rejects_raw_jinja_template(self):
        template = jinja2.Template("{{ cycler.__init__.__globals__.os.name }}")

        with self.assertRaisesMessage(
            TypeError,
            "LazilyRenderedTemplate requires a CompiledRichTextTemplate",
        ):
            LazilyRenderedTemplate(template, "test", {})

    def test_rich_text_template_rejects_unsandboxed_environment(self):
        env = jinja2.Environment()

        with self.assertRaisesMessage(
            TypeError,
            "Rich-text templates must use ReportSandboxedEnvironment",
        ):
            rich_text_template(env, "safe")

        with self.assertRaisesMessage(
            TypeError,
            "Rich-text templates must use ReportSandboxedEnvironment",
        ):
            CompiledRichTextTemplate(env.from_string("safe"), {})

    def test_sandbox_is_immutable(self):
        env = prepare_jinja2_env()

        with self.assertRaises(SecurityError):
            env.from_string("{{ values.clear() }}").render(values=["safe"])

    def test_documented_jinja_features_remain_available(self):
        env = prepare_jinja2_env()
        template = env.from_string(
            "{% set totals=namespace(value=0) %}"
            '{% for item in items|sort(attribute="name") %}'
            "{{ loop.index }}:{{ item.name|upper }};"
            "{% set totals.value=totals.value + item.value %}"
            "{% endfor %}"
            'match={{ "Ghostwriter 42"|regex_search("[0-9]+") }};'
            "total={{ totals.value }}"
        )

        rendered = template.render(
            items=[
                {"name": "beta", "value": 2},
                {"name": "alpha", "value": 3},
            ]
        )

        self.assertEqual(rendered, "1:ALPHA;2:BETA;match=42;total=5")

    def test_standard_jinja_globals_remain_available(self):
        env = prepare_jinja2_env()

        self.assertLessEqual(
            {"cycler", "dict", "joiner", "lipsum", "namespace", "range"},
            env.globals.keys(),
        )

    def test_registered_globals_and_template_macros_remain_callable(self):
        env = prepare_jinja2_env()
        template = env.from_string(
            "{% macro render_value(value) %}[{{ value }}]{% endmacro %}"
            "{% for number in range(3) %}"
            "{{ render_value(dict(value=number).value) }}"
            "{% endfor %}"
            '{% set rows=cycler("odd", "even") %}'
            "{{ rows.next() }}-{{ rows.next() }}|"
            '{% set comma=joiner(",") %}'
            "{{ comma() }}a{{ comma() }}b"
        )

        self.assertEqual(template.render(), "[0][1][2]odd-even|a,b")

    def test_data_only_builtin_methods_remain_callable(self):
        env = prepare_jinja2_env()
        template = env.from_string(
            '{{ values.get("name").upper() }}|'
            "{% for key, value in values.items()|sort %}"
            "{{ key }}={{ value }};"
            "{% endfor %}"
        )

        self.assertEqual(
            template.render(values={"name": "ghostwriter", "count": 2}),
            "GHOSTWRITER|count=2;name=ghostwriter;",
        )

    def test_jinja_loop_and_block_helpers_remain_callable(self):
        env = prepare_jinja2_env()
        template = env.from_string(
            "{% block content %}content{% endblock %}|"
            "{{ self.content() }}|"
            "{% for number in range(2) %}{{ loop.cycle('a', 'b') }}{% endfor %}"
        )

        self.assertEqual(template.render(), "content|content|ab")

    def test_unregistered_python_callable_is_blocked(self):
        env = prepare_jinja2_env()

        def unregistered(value):
            return value

        with self.assertRaises(SecurityError):
            env.from_string("{{ unregistered('unsafe') }}").render(
                unregistered=unregistered
            )

        rendered = env.from_string('{{ mk_ref("Example") }}').render(
            mk_ref=jinja_funcs.ref
        )
        self.assertIn('data-gw-ref="Example"', rendered)

    def test_unregistered_bound_method_and_callable_object_are_blocked(self):
        env = prepare_jinja2_env()

        class Capability:
            def execute(self):
                return "executed"

            def __call__(self):
                return "called"

        capability = Capability()
        for payload in ("{{ capability.execute() }}", "{{ capability() }}"):
            with self.subTest(payload=payload), self.assertRaises(SecurityError):
                env.from_string(payload).render(capability=capability)

        sink = StringIO()
        with self.assertRaises(SecurityError):
            env.from_string("{{ sink.write('executed') }}").render(sink=sink)
        self.assertEqual(sink.getvalue(), "")

        with self.assertRaises(SecurityError):
            env.from_string("{{ operation(values) }}").render(
                operation=len,
                values=[],
            )

    def test_data_type_subclass_cannot_introduce_callable_methods(self):
        env = prepare_jinja2_env()

        class ExecutableDict(dict):
            def execute(self):
                return "executed"

        with self.assertRaises(SecurityError):
            env.from_string("{{ values.execute() }}").render(values=ExecutableDict())

    def test_python_callable_attributes_are_blocked(self):
        env = prepare_jinja2_env()

        rendered = env.from_string(
            "{{ mk_ref.__name__ }}|{{ mk_ref.jinja_pass_arg }}"
        ).render(mk_ref=jinja_funcs.ref)

        self.assertEqual(rendered, "|")

    def test_docx_exporter_objects_expose_no_template_attributes(self):
        env = prepare_jinja2_env()
        rich_text = DocxRichText("Safe")

        rendered = env.from_string("{{ value.xml }}|{{ value.add }}").render(
            value=rich_text
        )

        self.assertEqual(rendered, "|")

    def test_common_generic_sandbox_escape_families_are_blocked(self):
        env = prepare_jinja2_env()
        payloads = [
            '{{ cycler.__init__.__globals__["os"] }}',
            '{{ lipsum.__globals__["os"] }}',
            '{{ namespace.__init__.__globals__["os"] }}',
            "{{ dict.__base__ }}",
            '{{ "".__class__.__mro__ }}',
            '{{ (namespace|attr("__init__"))|attr("__globals__") }}',
            '{{ "{0.__class__}".format("x") }}',
            '{{ "{x.__class__}".format_map({"x": "y"}) }}',
        ]

        for payload in payloads:
            with self.subTest(payload=payload):
                try:
                    rendered = env.from_string(payload).render()
                except SecurityError:
                    continue
                self.assertEqual(rendered, "")

    def test_rich_text_form_accepts_user_authored_jinja(self):
        source = (
            '<p>{% for value in ["one", "two"] %}'
            "{{ loop.index }}={{ value }} "
            "{% endfor %}</p>"
        )

        self.assertEqual(JinjaRichTextField().clean(source), source)

    def test_nested_rich_text_still_renders_as_template_data(self):
        env = prepare_jinja2_env()
        context = {"client": {"name": "Example Client"}}
        context["project"] = {
            "description_rt": LazilyRenderedTemplate(
                rich_text_template(
                    env,
                    "<strong>{{ client.name }}</strong>",
                ),
                "the project description",
                context,
            )
        }
        outer = LazilyRenderedTemplate(
            rich_text_template(
                env,
                "<section>{{ project.description_rt }}</section>",
            ),
            "outer rich text",
            context,
        )

        self.assertEqual(
            outer.render_html(),
            "<section><strong>Example Client</strong></section>",
        )

    def test_marked_oplog_content_is_restored_only_after_jinja_rendering(self):
        env = prepare_jinja2_env()
        payload = (
            "{% set e=project.description_rt.template.environment %}"
            "{{ e.template_class("
            "\"{{ cycler.__init__.__globals__.os.popen('id').read() }}\""
            ").render() }}"
        )
        source = (
            "<p>Authored template: {{ client.name }}</p>"
            '<div data-gw-jinja-literal="true">'
            f"<p>{payload}</p>"
            "<pre><code>{{ client.name }} {% endraw %} {#</code></pre>"
            "</div>"
            "<p>Still authored: {{ client.name|upper }}</p>"
        )

        rendered = rich_text_template(env, source).render(
            client={"name": "Example Client"},
            project={},
        )

        self.assertIn("Authored template: Example Client", rendered)
        self.assertIn("Still authored: EXAMPLE CLIENT", rendered)
        self.assertIn(payload, rendered)
        self.assertIn("{{ client.name }} {% endraw %} {#", rendered)
        self.assertNotIn("data-gw-jinja-literal", rendered)

    def test_marked_oplog_content_survives_html_entity_normalization(self):
        env = prepare_jinja2_env()
        source = (
            '<div data-gw-jinja-literal="true">'
            "<p>&lcub;&lcub; client.name &rcub;&rcub;</p>"
            '<p><span data-gw-ref="safe}}CLIENT={{ client.name }}{{.ref safe">'
            "{{.ref safe}}CLIENT={{ client.name }}{{.ref safe}}"
            "</span></p>"
            "</div>"
        )

        rendered = rich_text_template(env, source).render(
            client={"name": "Rendered Client"}
        )

        self.assertIn("{{ client.name }}", rendered)
        self.assertIn("safe}}CLIENT={{ client.name }}{{.ref safe", rendered)
        self.assertNotIn("Rendered Client", rendered)

    def test_encoded_reference_is_decoded_only_after_jinja_rendering(self):
        env = prepare_jinja2_env()
        ref_name = "safe}}CLIENT={{ client.name }}{{.ref safe"
        encoded_ref = "-".join(f"{ord(character):x}" for character in ref_name)
        encoded_node = f'<p><span data-gw-ref-encoded="{encoded_ref}"></span></p>'

        for source in (
            encoded_node + "<p>{{ client.name }}</p>",
            f'<div data-gw-jinja-literal="true">{encoded_node}</div>'
            "<p>{{ client.name }}</p>",
        ):
            with self.subTest(source=source):
                rendered = rich_text_template(env, source).render(
                    client={"name": "Rendered Client"}
                )

                self.assertIn(
                    'data-gw-ref="safe}}CLIENT={{ client.name }}{{.ref safe"',
                    rendered,
                )
                self.assertNotIn("data-gw-ref-encoded", rendered)
                self.assertEqual(rendered.count("Rendered Client"), 1)

    def test_legacy_reference_node_is_always_literal_data(self):
        env = prepare_jinja2_env()
        source = (
            '<p><span data-gw-ref="safe}}CLIENT={{ client.name }}{{.ref safe">'
            "{{ client.name }}"
            "</span></p>"
            "<p>{{ client.name }}</p>"
        )

        rendered = rich_text_template(env, source).render(
            client={"name": "Rendered Client"}
        )

        self.assertIn("{{ client.name }}", rendered)
        self.assertEqual(rendered.count("Rendered Client"), 1)

    def test_structural_marker_values_are_always_literal_data(self):
        env = prepare_jinja2_env()
        marker_value = "safe}}CLIENT={{ client.name }}{{.ref safe"

        for attribute in (
            "data-evidence-id",
            "data-gw-caption",
            "data-gw-evidence",
            "data-gw-image",
        ):
            with self.subTest(attribute=attribute):
                source = (
                    f'<div {attribute}="{marker_value}">'
                    "Caption for {{ client.name }}"
                    "</div>"
                )

                rendered = rich_text_template(env, source).render(
                    client={"name": "Rendered Client"}
                )

                self.assertIn(f'{attribute}="{marker_value}"', rendered)
                self.assertIn("Caption for Rendered Client", rendered)
                self.assertEqual(rendered.count("Rendered Client"), 1)

    def test_invalid_encoded_reference_remains_inert(self):
        env = prepare_jinja2_env()
        source = '<span data-gw-ref-encoded="110000"></span>'

        rendered = rich_text_template(env, source).render()

        self.assertIn('data-gw-ref-encoded="110000"', rendered)

    def test_debug_extension_ast_escape_is_blocked(self):
        payload = """
            {% set e=project.description_rt.template.environment %}
            {% set a=e.parse('{{ 0 }}') %}
            {% set x=a.body[0].nodes.clear() %}
            {% set x=a.body[0].nodes.append(e.extensions['jinja2.ext.DebugExtension'].call_method('__init__.__globals__["__builtins__"]["__import__"]("os").popen("id").read')) %}
            {{ e.from_string(a).render() }}
        """

        with self.assertRaises(ReportExportTemplateError):
            self.render_with_project_description(payload)

    def test_unsandboxed_template_constructor_escape_is_blocked(self):
        payload = """
            {{ project.description_rt.template.environment.template_class(
                "{{ cycler.__init__.__globals__.os.popen('id').read() }}"
            ).render() }}
        """

        with self.assertRaises(ReportExportTemplateError):
            self.render_with_project_description(payload)

    def test_environment_capabilities_are_blocked_if_directly_exposed(self):
        env = prepare_jinja2_env()
        payload = '{{ exposed.template_class("{{ 7 * 7 }}").render() }}'

        with self.assertRaises(SecurityError):
            env.from_string(payload).render(exposed=env)

        direct_template_payload = '{{ exposed("{{ 7 * 7 }}").render() }}'
        with self.assertRaises(SecurityError):
            env.from_string(direct_template_payload).render(
                exposed=jinja2.environment.Template
            )

        extension = jinja2.ext.DebugExtension(env)
        with self.assertRaises(SecurityError):
            env.from_string('{{ exposed.call_method("anything") }}').render(
                exposed=extension
            )

        parsed_ast = env.parse("{{ 0 }}")
        with self.assertRaises(SecurityError):
            env.from_string('{{ exposed.set_ctx("load") }}').render(exposed=parsed_ast)

    def test_template_stream_file_write_is_blocked_if_template_is_exposed(self):
        env = prepare_jinja2_env()
        exposed_template = env.from_string("attacker-controlled")

        with TemporaryDirectory() as temp_dir:
            destination = Path(temp_dir) / "written.py"
            payload = "{{ exposed.stream().dump(destination) }}"

            with self.assertRaises(SecurityError):
                env.from_string(payload).render(
                    exposed=exposed_template,
                    destination=str(destination),
                )

            self.assertFalse(destination.exists())

    def test_list(self):
        env, _ = prepare_jinja2_env(debug=True)
        template = rich_text_template(
            env,
            "<ol><li>{%li for i in thelist %}</li><li>{{i}}</li><li>{%li endfor %}</li></ol>",
        )
        out = template.render({"thelist": ["foo", "bar", "baz"]})
        self.assertEqual(out, "<ol><li>foo</li><li>bar</li><li>baz</li></ol>")

    def test_table(self):
        env, _ = prepare_jinja2_env(debug=True)
        template = rich_text_template(
            env,
            "<table><tr><td>{%tr for row in thelist%}</td><td></td></tr><tr><td>{{row[0]}}</td><td>{{row[1]}}</td></tr><tr><td>{%tr endfor %}</td><td></td></tr></table>",
        )
        out = template.render({"thelist": [["foo", 1], ["bar", 2], ["baz", 3]]})
        self.assertEqual(
            out,
            "<table><tr><td>foo</td><td>1</td></tr><tr><td>bar</td><td>2</td></tr><tr><td>baz</td><td>3</td></tr></table>",
        )

    def test_prefix_not_nested(self):
        env, _ = prepare_jinja2_env(debug=True)
        with self.assertRaisesMessage(
            ReportExportTemplateError,
            "Jinja tag prefixed with 'li' was not a descendant of a li tag",
        ):
            rich_text_template(
                env,
                "<ol>{%li for i in thelist %}<li>{{i}}</li><li>{%li endfor %}</li></ol>",
            )

    def test_legacy_reference_and_caption_tags_accept_whitespace_after_opening_braces(
        self,
    ):
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
        self.assertIn(
            'data-gw-ref="Payload Hosting and Lateral Movement With Codex"', out
        )
        self.assertIn('data-gw-caption="Here is a Caption"', out)


class RichTextTemplatingExportTests(TestCase):
    def test_create_lazy_template_normalizes_none_to_empty_rich_text(self):
        class DummyExport(ExportBase):
            @classmethod
            def generate_lint_data(cls):
                return {}

            def map_rich_texts(self):
                return {}

            def run(self):
                return None

            @classmethod
            def mime_type(cls) -> str:
                return "text/plain"

            @classmethod
            def extension(cls) -> str:
                return "txt"

        lazy_template = DummyExport({}, is_raw=True).create_lazy_template(
            "test rich text", None, {}
        )

        self.assertEqual(lazy_template.render_html(), "")

    def test_report_export_handles_report_extra_field_with_spaced_legacy_reference_and_caption_tags(
        self,
    ):
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

    def test_oplog_rich_text_extra_field_is_literal_report_data(self):
        oplog_extra_field = ExtraFieldModelFactory(
            model_internal_name=OplogEntry._meta.label,
            model_display_name="Oplog Entries",
        )
        ExtraFieldSpecFactory(
            internal_name="analyst_notes",
            display_name="Analyst Notes",
            type="rich_text",
            target_model=oplog_extra_field,
        )
        report = ReportFactory()
        payload = (
            "<p>{{ client.name }}</p>"
            "<p>{% set e=project.description_rt.template.environment %}</p>"
        )
        OplogEntryFactory(
            oplog_id__project=report.project,
            oplog_id__name="Literal log",
            extra_fields={"analyst_notes": payload},
        )

        exporter = ExportReportJson(report)
        context = exporter.map_rich_texts()
        log = next(log for log in context["logs"] if log["name"] == "Literal log")
        literal_value = log["entries"][0]["extra_fields"]["analyst_notes"]

        self.assertIsInstance(literal_value, HtmlRichText)
        self.assertEqual(literal_value.__html__(), payload)

        rendered = exporter.create_lazy_template(
            "test oplog reference",
            "{{ logs[0].entries[0].extra_fields.analyst_notes }}",
            {**context, "logs": [log]},
        ).render_html()
        self.assertEqual(str(rendered), payload)
        self.assertNotIn(report.project.client.name, rendered)
