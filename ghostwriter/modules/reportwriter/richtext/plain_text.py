import bs4
from io import StringIO

from ghostwriter.modules.reportwriter.richtext.ooxml import strip_text_whitespace


def html_to_plain_text(text: str, evidences) -> str:
    soup = bs4.BeautifulSoup(text, "lxml")
    tag = soup.find("body")
    if tag is None:
        return ""
    out = StringIO()
    _build_html_str(tag, evidences, out)

    out = out.getvalue()
    # Escape computational prefixes
    for bad_char in ["=", "+", "-", "@", "\t", "\r", "{"]:
        if out.startswith(bad_char):
            out = "'" + out[0] + "'" + out[1:]
            break
    return out


def _build_html_str(node, evidences, out: StringIO):
    if node.name is None:
        text = strip_text_whitespace(node)
        out.write(text)
        return

    if node.name == "span" and "data-gw-evidence" in node.attrs:
        try:
            evidence = evidences[int(node.attrs["data-gw-evidence"])]
        except (KeyError, ValueError):
            return
        out.write(
            f"\n<See Report for Evidence File: {evidence['friendly_name']}>\nCaption \u2013 {evidence['caption']}"
        )
        return
    elif node.name == "span" and "data-gw-caption" in node.attrs:
        ref_name = node.attrs["data-gw-caption"]
        if ref_name:
            out.write(f"See {ref_name}")
            return
    elif node.name == "span" and "data-gw-ref" in node.attrs:
        ref_name = node.attrs["data-gw-ref"]
        if ref_name:
            out.write(f"See {ref_name}")
            return

    if node.name == "br":
        out.write("\n")

    for child in node.children:
        _build_html_str(child, evidences, out)

    if node.name == "p":
        out.write("\n")
