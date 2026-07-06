import bs4
from django.utils.html import escape


def render_rich_text_value(value):
    """
    Render a lazily-evaluated rich-text value to an HTML string.

    Catches ``ReportExportTemplateError`` and returns an inline alert
    so the preview can still display remaining fields.
    """
    from ghostwriter.modules.reportwriter.base import ReportExportTemplateError

    if value is None:
        return ""
    try:
        return str(value.__html__()) if hasattr(value, "__html__") else str(value)
    except ReportExportTemplateError as error:
        return (
            f'<div class="alert alert-danger">'
            f"<strong>Template Error</strong><br>{escape(str(error))}"
            f"</div>"
        )


def has_rich_text_content(html_str):
    """Return ``True`` if *html_str* contains visible text or marker elements."""
    if not html_str or not html_str.strip():
        return False
    soup = bs4.BeautifulSoup(html_str, "html.parser")
    if soup.get_text(strip=True):
        return True
    return bool(soup.select(
        "[data-gw-evidence], [data-evidence-id], [data-gw-image], [data-gw-ref], [data-gw-caption], img"
    ))


def wrap_plain_value(value, html_str):
    """Wrap non-HTML or boolean values in appropriate HTML for preview display."""
    if isinstance(value, bool):
        icon = "fa-check" if value else "fa-times"
        css = "healthy" if value else "burned"
        return f'<p><span class="{css}"><i class="fas {icon}"></i></span></p>'
    if not hasattr(value, "__html__") and "<" not in html_str:
        return f"<p>{escape(html_str)}</p>"
    return html_str
