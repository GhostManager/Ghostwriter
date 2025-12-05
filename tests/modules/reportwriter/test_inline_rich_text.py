import pytest

from ghostwriter.modules.reportwriter.base.docx import _render_inline_rich_text
from docxtpl import RichText


def test_render_inline_rich_text_returns_richtext_for_simple_html():
    html = "<p><span style='color: #ff0000'>High</span></p>"

    result = _render_inline_rich_text(html)

    assert isinstance(result, RichText)
    assert "High" in str(result)


def test_render_inline_rich_text_rejects_block_content():
    html = "<div><p>Nested</p></div>"

    result = _render_inline_rich_text(html)

    assert result is None
