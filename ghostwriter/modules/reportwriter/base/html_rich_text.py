
from typing import Any
import jinja2
from markupsafe import Markup

from ghostwriter.modules.reportwriter.base import ReportExportTemplateError


def deep_copy_with_copiers(value, typ_copiers):
    """
    Deep copies a value with custom handlers.

    `class_copiers` is a dict with class keys and
    """
    typ = type(value)
    if typ in typ_copiers:
        # A more advanced implementation would respect subclasses, but that's not needed (yet)
        return typ_copiers[typ](value)
    if isinstance(value, dict):
        return {k: deep_copy_with_copiers(v, typ_copiers) for k, v in value.items()}
    if isinstance(value, list):
        return [deep_copy_with_copiers(v, typ_copiers) for v in value]
    return value


class LazilyRenderedTemplate:
    """
    Renders a template lazily
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


class HtmlAndRich:
    """
    Object containing some rich-text HTML and an exporter-specific rich-text object.
    """
    html: Markup
    rich: Any

    def __init__(self, html: Markup, rich: Any):
        self.html = html
        self.rich = rich

    def __html__(self):
        return self.html


class LazySubdocRender:
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
