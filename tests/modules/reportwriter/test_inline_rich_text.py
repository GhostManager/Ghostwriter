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


def test_render_inline_rich_text_accepts_nested_spans_with_styles():
    html = "<p><span class=\"bold\"><span style=\"color: #00b050;\">Low</span>--><span style=\"color: #ed7d31;\">Medium</span></span></p>"

    result = _render_inline_rich_text(html)

    assert isinstance(result, RichText)
    result_str = str(result)
    assert "Low" in result_str and "Medium" in result_str
