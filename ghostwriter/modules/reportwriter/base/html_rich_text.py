
from typing import Any, Callable
import jinja2
from markupsafe import Markup
from abc import ABC, abstractmethod

from ghostwriter.modules.reportwriter.base import ReportExportTemplateError

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
