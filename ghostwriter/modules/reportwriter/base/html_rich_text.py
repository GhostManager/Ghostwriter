# Standard Libraries
import re
import secrets
from abc import ABC, abstractmethod
from typing import Any, Callable

# 3rd Party Libraries
import bs4
import jinja2
from markupsafe import Markup

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter import ReportSandboxedEnvironment, jinja_funcs
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError

_H = [f"h{n}" for n in range(1, 7)]
JINJA_LITERAL_ATTRIBUTE = "data-gw-jinja-literal"


def _require_report_sandbox(template_or_environment):
    """Reject templates that were not created by Ghostwriter's report sandbox."""
    environment = (
        template_or_environment.environment
        if isinstance(template_or_environment, jinja2.Template)
        else template_or_environment
    )
    if not isinstance(environment, ReportSandboxedEnvironment):
        raise TypeError("Rich-text templates must use ReportSandboxedEnvironment")


class CompiledRichTextTemplate:
    """
    A compiled rich-text template with HTML fragments excluded from Jinja parsing.

    Literal fragments are represented by unpredictable inert placeholders while
    Jinja compiles and renders the rest of the rich text. They are restored only
    after the single template-rendering pass has completed.
    """

    _jinja_block_all_attributes = True

    def __init__(self, template: jinja2.Template, literal_fragments: dict[str, str]):
        _require_report_sandbox(template)
        self._template = template
        self._literal_fragments = literal_fragments

    def render(self, *args, **kwargs):
        rendered = self._template.render(*args, **kwargs)
        for placeholder, literal_html in self._literal_fragments.items():
            rendered = rendered.replace(placeholder, literal_html)
        return rendered


def _extract_jinja_literal_fragments(text: str) -> tuple[str, dict[str, str]]:
    """
    Replace marked HTML containers with inert placeholders before Jinja parsing.

    The marker container itself is intentionally omitted from the rendered output;
    only its contents are restored. Nested markers are handled by their outermost
    marked ancestor.
    """
    soup = bs4.BeautifulSoup(text, "html.parser")
    literal_fragments = {}
    for node in soup.find_all(attrs={JINJA_LITERAL_ATTRIBUTE: True}):
        if node.find_parent(attrs={JINJA_LITERAL_ATTRIBUTE: True}) is not None:
            continue

        placeholder = f"GWJINJALITERAL{secrets.token_hex(24)}"
        literal_fragments[placeholder] = node.decode_contents()
        node.replace_with(placeholder)
    return str(soup), literal_fragments


def remove_trailing_empty_paragraphs(body):
    """Remove editor-only trailing paragraphs from parsed rich text."""
    for child in reversed(list(body.children)):
        if isinstance(child, bs4.NavigableString):
            if child.strip():
                break
            continue
        if (
            child.name == "p"
            and not child.get_text(strip=True)
            and child.find(True) is None
        ):
            child.extract()
            continue
        break


def rich_text_template(
    env: jinja2.Environment,
    text: str,
) -> CompiledRichTextTemplate:
    """
    Converts rich text `text` to a Jinja template. This does some additional Ghostwriter-specific
    processing.
    """
    _require_report_sandbox(env)

    # Remove generated literal data from the source before any normalization can
    # assemble or interpret Jinja delimiters.
    text, literal_fragments = _extract_jinja_literal_fragments(text)

    # Replace old `{{.item}}`` syntax with jinja templates or elements to replace
    def replace_old_tag(match: re.Match):
        contents = match.group(1).strip()
        # These will be swapped out when parsing the HTML
        if contents.startswith("ref "):
            return jinja_funcs.ref(contents[4:].strip())
        elif contents == "caption":
            return jinja_funcs.caption("")
        elif contents.startswith("caption "):
            return jinja_funcs.caption(contents[8:].strip())
        return "{{ _old_dot_vars[" + repr(contents.strip()) + "]}}"

    # Replace items with old dot syntax
    # Detect `{{.item}}` and other old dot-style forms with optional whitespace after `{{`,
    # after `.`, and before `}}` to be forgiving of formatting inconsistencies
    text = re.sub(r"\{\{\s*\.([^\{\}]*?)\s*\}\}", replace_old_tag, text)

    # Replace TinyMCE page breaks with something that the parser can easily pick up
    text = text.replace("<p><!-- pagebreak --></p>", '<br data-gw-pagebreak="true" />')

    # Replace `{%li foreach %}`-esque prefixes. This is similar to what python-docx-template does.
    soup = bs4.BeautifulSoup(text, "html.parser")
    _process_prefix(text, soup, "li")
    _process_prefix(text, soup, "p")
    _process_prefix(text, soup, "tr")
    _process_prefix(text, soup, "td")
    text = str(soup)

    # Compile
    try:
        return CompiledRichTextTemplate(
            env.from_string(text),
            literal_fragments,
        )
    except jinja2.TemplateSyntaxError as err:
        line = text.splitlines()[err.lineno - 1]
        raise ReportExportTemplateError(str(err), code_context=line) from err


def _process_prefix(input_str: str, soup: bs4.BeautifulSoup, prefix: str):
    """
    Converts text nodes of the form `{%prefix someop %}` and replaces its parent `prefix` tag with `{% someop %}`
    in the passed-in soup.
    """

    regex = re.compile(
        r"^\s*(\{%|\{\{)\s*" + re.escape(prefix) + r"\b(.*)(%\}|\}\})\s*$"
    )
    # Store in list since we mutate the nodes
    matching_strings = list(soup.find_all(string=regex))
    for node in matching_strings:
        # Find parent to strip out
        parent_tag = None
        for parent in node.parents:
            if parent.name == prefix:
                parent_tag = parent
                break
        if parent_tag is None:
            line = input_str.splitlines()[node.parent.sourceline - 1]
            raise ReportExportTemplateError(
                f"Jinja tag prefixed with '{prefix}' was not a descendant of a {prefix} tag",
                code_context=line,
            )

        capture = regex.search(node)
        parent_tag.replace_with(capture.group(1) + capture.group(2) + capture.group(3))


class RichTextBase(ABC):
    """
    Base class for a value that can produce some rich text, represented as HTML.
    """

    # Templates only need the rendered value. Public attributes and methods are
    # implementation details and must not expose application or Jinja objects.
    _jinja_block_all_attributes = True

    # User-friendly descriptor of where the rich text was produced
    location: str | None

    @abstractmethod
    def __html__(self) -> Markup | str:
        """
        Gets/renders the HTML rich text.
        """

    @staticmethod
    def deep_copy_process_html(
        value: Any, process_html: Callable[["RichTextBase"], Any]
    ):
        """
        Deep copies a value, mapping any `RichTextBase` subclasses through `process_html`.
        """
        if isinstance(value, RichTextBase):
            return process_html(value)
        if isinstance(value, dict):
            return {
                k: RichTextBase.deep_copy_process_html(v, process_html)
                for k, v in value.items()
            }
        if isinstance(value, list):
            return [RichTextBase.deep_copy_process_html(v, process_html) for v in value]
        return value


class HtmlRichText(RichTextBase):
    """
    An HTML string, with no templating.
    """

    html: str

    def __init__(self, html: str, location: str | None = None):
        super().__init__()
        self.html = html
        self.location = location

    def __html__(self):
        return self.html


class LazilyRenderedTemplate(RichTextBase):
    """
    Renders a Jinja template lazily
    """

    location: str | None

    def __init__(
        self,
        template: CompiledRichTextTemplate,
        location: str | None,
        context: dict,
    ):
        super().__init__()
        if not isinstance(template, CompiledRichTextTemplate):
            raise TypeError(
                "LazilyRenderedTemplate requires a CompiledRichTextTemplate"
            )
        self._template = template
        self._context = context
        self.location = location
        self._rendered = None
        self._rendering = False

    def render_html(self):
        """
        Will throw a `ReportExportTemplateError` if the template attempted to render itself while it was
        rendering (i.e. infinite recursion).
        """
        if self._rendered is None:
            if self._rendering:
                raise ReportExportTemplateError(
                    f"Circular reference to {self.location} (ensure rich text fields are not referencing each other)"
                )
            self._rendering = True
            try:
                self._rendered = Markup(
                    ReportExportTemplateError.map_errors(
                        lambda: self._template.render(self._context),
                        self.location,
                    )
                )
            finally:
                self._rendering = False
        return self._rendered

    def __html__(self):
        return self.render_html()


class HtmlAndObject(RichTextBase):
    """
    HTML rich text and an exporter-specific object (ex. a docx `RichText`).

    The object isn't used by this class at all - exporters will need to use it themselves.
    """

    html: str

    def __init__(self, html: str, obj, location: str | None = None):
        super().__init__()
        self.html = html
        self._obj = obj
        self.location = location

    @property
    def exporter_object(self):
        """Return the exporter-specific object to trusted exporter code."""
        return self._obj

    def __html__(self):
        return self.html


class LazySubdocRender:
    """
    Renders a subdocument via a render function lazily
    """

    _jinja_block_all_attributes = True

    def __init__(self, render):
        self._render = render
        self._rendered = None

    def __str__(self):
        if not self._rendered:
            self._rendered = self._render()
        return self._rendered.__str__()

    def __html__(self):
        if not self._rendered:
            self._rendered = self._render()
        return self._rendered.__html__()


def offset_headings(html: str, heading_offset: int):
    """
    Increases the level of `h1-6` tags in the `html`.
    """
    if heading_offset == 0:
        return html
    soup = bs4.BeautifulSoup(html, "html.parser")
    for el in soup.find_all(_H):
        level = int(el.name[1:])
        level = min(level + heading_offset, 6)
        el.name = f"h{level}"
    out = str(soup)
    return out
