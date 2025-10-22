
import re
from typing import Any, Callable
import bs4
import jinja2
from markupsafe import Markup
from abc import ABC, abstractmethod

from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError

_H = [f"h{n}" for n in range(1, 7)]

def rich_text_template(
    env: jinja2.Environment,
    text: str,
) -> jinja2.Template:
    """
    Converts rich text `text` to a Jinja template. This does some additional Ghostwriter-specific
    processing.
    """
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

    text = re.sub(r"\{\{\.([^\{\}]*)\}\}", replace_old_tag, text)

    # Replace TinyMCE page breaks with something that the parser can easily pick up
    text = text.replace(
        "<p><!-- pagebreak --></p>", '<br data-gw-pagebreak="true" />'
    )

    # Replace `{%li foreach %}`-esque prefixes. This is similar to what python-docx-template does.
    soup = bs4.BeautifulSoup(text, "html.parser")
    _process_prefix(text, soup, "li")
    _process_prefix(text, soup, "p")
    _process_prefix(text, soup, "tr")
    _process_prefix(text, soup, "td")
    text = str(soup)

    # Compile
    try:
        return env.from_string(text)
    except jinja2.TemplateSyntaxError as err:
        line = text.splitlines()[err.lineno - 1]
        raise ReportExportTemplateError(str(err), code_context=line) from err


def _process_prefix(input_str: str, soup: bs4.BeautifulSoup, prefix: str):
    """
    Converts text nodes of the form `{%prefix someop %}` and replaces its parent `prefix` tag with `{% someop %}`
    in the passed-in soup.
    """

    regex = re.compile(r"^\s*(\{%|\{\{)\s*" + re.escape(prefix) + r"\b(.*)(%\}|\}\})\s*$")
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
            raise ReportExportTemplateError(f"Jinja tag prefixed with '{prefix}' was not a descendant of a {prefix} tag", code_context=line)

        capture = regex.search(node)
        parent_tag.replace_with(capture.group(1) + capture.group(2) + capture.group(3))


class RichTextBase(ABC):
    """
    Base class for a value that can produce some rich text, represented as HTML.
    """

    # User-friendly descriptor of where the rich text was produced
    location: str | None

    @abstractmethod
    def __html__(self) -> Markup | str:
        """
        Gets/renders the HTML rich text.
        """
        pass

    @staticmethod
    def deep_copy_process_html(value: Any, process_html: Callable[["RichTextBase"], Any]):
        """
        Deep copies a value, mapping any `RichTextBase` subclasses through `process_html`.
        """
        if isinstance(value, RichTextBase):
            return process_html(value)
        if isinstance(value, dict):
            return {k: RichTextBase.deep_copy_process_html(v, process_html) for k,v in value.items()}
        if isinstance(value, list):
            return [RichTextBase.deep_copy_process_html(v, process_html) for v in value]
        return value

class HtmlRichText(RichTextBase):
    """
    An HTML string, with no templating.
    """
    html: str

    def __init__(self, html: str, location: str | None=None):
        super().__init__()
        self.html = html
        self.location = location

    def __html__(self):
        return self.html

class LazilyRenderedTemplate(RichTextBase):
    """
    Renders a Jinja template lazily
    """
    template: jinja2.Template
    context: dict
    location: str | None
    rendered: str | None
    rendering: bool

    def __init__(self, template: jinja2.Template, location: str | None, context: dict):
        self.template = template
        self.context = context
        self.location = location
        self.rendered = None
        self.rendering = False

    def render_html(self):
        """
        Will throw a `ReportExportTemplateError` if the template attempted to render itself while it was
        rendering (i.e. infinite recursion).
        """
        if self.rendered is None:
            if self.rendering:
                raise ReportExportTemplateError(f"Circular reference to {self.location} (ensure rich text fields are not referencing each other)")
            self.rendering = True
            self.rendered = Markup(
                ReportExportTemplateError.map_errors(
                    lambda: self.template.render(self.context),
                    self.location,
                )
            )
            self.rendering = False
        return self.rendered

    def __html__(self):
        return self.render_html()

class HtmlAndObject(RichTextBase):
    """
    HTML rich text and an exporter-specific object (ex. a docx `RichText`).

    The object isn't used by this class at all - exporters will need to use it themselves.
    """

    html: str
    obj: Any

    def __init__(self, html: str, obj, location: str | None = None):
        self.html = html
        self.obj = obj
        self.location = location

    def __html__(self):
        return self.html

class LazySubdocRender:
    """
    Renders a subdocument via a render function lazily
    """
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
