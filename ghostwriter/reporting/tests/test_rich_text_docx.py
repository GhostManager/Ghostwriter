# Standard Libraries
from io import BytesIO
from zipfile import ZipFile

# Django Imports
from django.test import TestCase

# 3rd Party Libraries
import docx
from lxml import etree

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter.richtext.docx import HtmlToDocx

WORD_PREFIX = """<?xml version='1.0' encoding='UTF-8' standalone='yes'?>
<w:document xmlns:wpc="http://schemas.microsoft.com/office/word/2010/wordprocessingCanvas" xmlns:mo="http://schemas.microsoft.com/office/mac/office/2008/main" xmlns:mc="http://schemas.openxmlformats.org/markup-compatibility/2006" xmlns:mv="urn:schemas-microsoft-com:mac:vml" xmlns:o="urn:schemas-microsoft-com:office:office" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" xmlns:v="urn:schemas-microsoft-com:vml" xmlns:wp14="http://schemas.microsoft.com/office/word/2010/wordprocessingDrawing" xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" xmlns:w10="urn:schemas-microsoft-com:office:word" xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml" xmlns:wpg="http://schemas.microsoft.com/office/word/2010/wordprocessingGroup" xmlns:wpi="http://schemas.microsoft.com/office/word/2010/wordprocessingInk" xmlns:wne="http://schemas.microsoft.com/office/word/2006/wordml" xmlns:wps="http://schemas.microsoft.com/office/word/2010/wordprocessingShape" mc:Ignorable="w14 wp14"><w:body>"""  # noqa: E501
WORD_SUFFIX = """<w:sectPr w:rsidR="00FC693F" w:rsidRPr="0006063C" w:rsidSect="00034616"><w:pgSz w:w="12240" w:h="15840"/><w:pgMar w:top="1440" w:right="1800" w:bottom="1440" w:left="1800" w:header="720" w:footer="720" w:gutter="0"/><w:cols w:space="720"/><w:docGrid w:linePitch="360"/></w:sectPr></w:body></w:document>"""  # noqa: E501


def clean_xml(xml):
    """
    Pretty-formats XML, for comparison and better diffs in case of test failures.
    """
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    parser = etree.XMLParser(
        no_network=True,
        collect_ids=False,
        remove_blank_text=True,
        remove_comments=True,
    )
    v = etree.fromstring(xml, parser=parser)
    v = etree.tostring(
        v,
        pretty_print=True,
    ).decode("utf-8")
    return v


def mk_test_docx(name, input, expected_output, p_style=None):
    """
    Creates a test function, that compares the output of running the `HtmlToDocx` converter
    over `input` to the `expected_output`.

    The converted result XML and expected output XML are both cleaned before comparison, so differences in
    whitespace will not affect comparison.
    """
    expected_output = clean_xml(WORD_PREFIX + expected_output + WORD_SUFFIX)

    def test_func(self):
        doc = docx.Document()
        HtmlToDocx.run(input, doc, p_style)
        out = BytesIO()
        doc.part.save(out)

        # Uncomment to write generates docx files for manual inspection
        # with open(name + ".docx", "wb") as f:
        #     f.write(out.getvalue())

        with ZipFile(out) as zip:
            with zip.open("word/document.xml") as file:
                contents = file.read()
        contents = clean_xml(contents)
        self.assertEqual(contents, expected_output)

    test_func.__name__ = name
    return test_func


class RichTextToDocxTests(TestCase):
    maxDiff = None

    test_paragraphs = mk_test_docx(
        "test_paragraphs",
        "<p>Hello World!</p><p>This is a test!</p>",
        """<w:p><w:pPr/><w:r><w:t>Hello World!</w:t></w:r></w:p><w:p><w:pPr/><w:r><w:t>This is a test!</w:t></w:r></w:p>""",
    )

    test_bold = mk_test_docx(
        "test_bold",
        "<p>Hello <b>World</b>!</p>",
        """
            <w:p>
                <w:pPr/>
                <w:r><w:t xml:space="preserve">Hello </w:t></w:r>
                <w:r><w:rPr><w:b/></w:rPr><w:t>World</w:t></w:r>
                <w:r><w:t>!</w:t></w:r>
            </w:p>
        """,
    )

    test_headers = mk_test_docx(
        "test_headers",
        "<h1>Hello World!</h1><h2>Heading two</h2><h3>Heading three</h3><p>Paragraph</p>",
        """
            <w:p>
                <w:pPr><w:pStyle w:val="Heading1"/></w:pPr>
                <w:r><w:t>Hello World!</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr><w:pStyle w:val="Heading2"/></w:pPr>
                <w:r><w:t>Heading two</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr><w:pStyle w:val="Heading3"/></w:pPr>
                <w:r><w:t>Heading three</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr/>
                <w:r><w:t>Paragraph</w:t></w:r>
            </w:p>
        """,
    )

    test_colors = mk_test_docx(
        "test_colors",
        """<p><span style="color: #ff0000;">Red</span>Text</p>""",
        """
            <w:p>
                <w:pPr/>
                <w:r><w:rPr><w:color w:val="FF0000"/></w:rPr><w:t>Red</w:t></w:r>
                <w:r><w:t>Text</w:t></w:r>
            </w:p>
        """,
    )

    test_formatting = mk_test_docx(
        "test_formatting",
        """
            <p>
                <b>Bold</b>
                <strong>Strong</strong>
                <span class="bold">Bold class</span>
                <i>Italic</i>
                <em>Emphasis</em>
                <span class="italic">Italic class</span>
                <u>Underline</u>
                <span class="underline">Underline class</span>
                <sub>Subscript</sub>
                <sup>Superscript</sup>
                <del>Strikethrough</del>
                <span class="highlight">Highlight class</span>
            </p>
        """,
        """
            <w:p>
                <w:pPr/>
                <w:r/>
                <w:r><w:rPr><w:b/></w:rPr><w:t>Bold</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:b/></w:rPr><w:t>Strong</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:b/></w:rPr><w:t>Bold class</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:i/></w:rPr><w:t>Italic</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:i/></w:rPr><w:t>Emphasis</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:i/></w:rPr><w:t>Italic class</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>Underline</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:u w:val="single"/></w:rPr><w:t>Underline class</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:vertAlign w:val="subscript"/></w:rPr><w:t>Subscript</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:vertAlign w:val="superscript"/></w:rPr><w:t>Superscript</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:strike/></w:rPr><w:t>Strikethrough</w:t></w:r>
                <w:r><w:t xml:space="preserve"> </w:t></w:r>
                <w:r><w:rPr><w:highlight w:val="yellow"/></w:rPr><w:t>Highlight class</w:t></w:r>
                <w:r/>
            </w:p>
        """,
    )

    test_unordered_list = mk_test_docx(
        "test_unordered_list",
        """
            <p>List test one:</p>
            <ul>
                <li>Item one</li>
                <li>Item two</li>
                <li>Item three:<ul>
                    <li>Subitem one</li>
                    <li>Subitem two</li>
                </ul></li>
            </ul>
            <p>List test two:</p>
            <ul>
                <li>Item one</li>
                <li>Item two</li>
            </ul>
        """,
        """
            <w:p><w:pPr/><w:r><w:t>List test one:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item three:</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem two</w:t></w:r>
            </w:p>
            <w:p><w:pPr/><w:r><w:t>List test two:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
        """,
    )

    test_ordered_list = mk_test_docx(
        "test_ordered_list",
        """
            <p>List test one:</p>
            <ol>
                <li>Item one</li>
                <li>Item two</li>
                <li>Item three:<ol>
                    <li>Subitem one</li>
                    <li>Subitem two</li>
                </ol></li>
            </ol>
            <p>List test two:</p>
            <ol>
                <li>Item one</li>
                <li>Item two</li>
            </ol>
        """,
        """
            <w:p><w:pPr/><w:r><w:t>List test one:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item three:</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem two</w:t></w:r>
            </w:p>
            <w:p><w:pPr/><w:r><w:t>List test two:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
        """,
    )

    test_mixed_list = mk_test_docx(
        "test_mixed_list",
        """
            <p>List test one:</p>
            <ul>
                <li>Item one</li>
                <li>Item two</li>
                <li>Item three:<ol>
                    <li>Subitem one</li>
                    <li>Subitem two</li>
                </ol></li>
            </ul>
            <p>List test two:</p>
            <ol>
                <li>Item one</li>
                <li>Item two</li>
                <li>Item three:<ul>
                    <li>Subitem one</li>
                    <li>Subitem two</li>
                </ul></li>
            </ol>
        """,
        """
            <w:p><w:pPr/><w:r><w:t>List test one:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item three:</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="10"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem two</w:t></w:r>
            </w:p>
            <w:p><w:pPr/><w:r><w:t>List test two:</w:t></w:r></w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item two</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="0"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Item three:</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem one</w:t></w:r>
            </w:p>
            <w:p>
                <w:pPr>
                    <w:pStyle w:val="ListParagraph"/>
                    <w:numPr><w:ilvl w:val="1"/><w:numId w:val="11"/></w:numPr>
                </w:pPr>
                <w:r><w:t>Subitem two</w:t></w:r>
            </w:p>
        """,
    )

    test_blockquote = mk_test_docx(
        "test_blockquote",
        """
        <p>A quote:</p>
        <blockquote>Alas poor <b>Yorik</b>, I knew him well</blockquote>
        """,
        """
            <w:p><w:pPr/><w:r><w:t>A quote:</w:t></w:r></w:p>
            <w:p>
                <w:r><w:t xml:space="preserve">Alas poor </w:t></w:r>
                <w:r><w:rPr><w:b/></w:rPr><w:t>Yorik</w:t></w:r>
                <w:r><w:t>, I knew him well</w:t></w:r>
            </w:p>
        """,
    )

    test_pre = mk_test_docx(
        "test_pre",
        """
        <p>Some code:</p>
        <pre>int main() {
    printf("hello world!\\n");
}</pre>
        """,
        """
            <w:p><w:pPr/><w:r><w:t>Some code:</w:t></w:r></w:p>
            <w:p>
                <w:pPr><w:jc w:val="left"/></w:pPr>
                <w:r>
                    <w:rPr>
                        <w:rFonts w:ascii="Courier New" w:hAnsi="Courier New"/>
                        <w:noProof/>
                    </w:rPr>
                    <w:t>int main() {</w:t>
                    <w:br/>
                    <w:t xml:space="preserve">    printf("hello world!\\n");</w:t>
                    <w:br/>
                    <w:t>}</w:t>
                </w:r>
            </w:p>
        """,
    )

    test_table = mk_test_docx(
        "test_table",
        """
        <table>
            <tbody>
                <tr>
                    <td>Cell one</td>
                    <td>Cell two</td>
                    <td>Cell three</td>
                </tr>
                <tr>
                    <td>Cell four</td>
                    <td>Cell five</td>
                    <td>Cell six</td>
                </tr>
            </tbody>
        </table>
        """,
        """
            <w:tbl>
                <w:tblPr>
                    <w:tblStyle w:val="TableGrid"/>
                    <w:tblW w:type="auto" w:w="0"/>
                    <w:tblLayout w:type="autofit"/>
                    <w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/>
                </w:tblPr>
                <w:tblGrid>
                    <w:gridCol w:w="2880"/>
                    <w:gridCol w:w="2880"/>
                    <w:gridCol w:w="2880"/>
                </w:tblGrid>
                <w:tr>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell one</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell two</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell three</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
                <w:tr>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell four</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell five</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell six</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
            </w:tbl>
        """,
    )

    test_table_spans = mk_test_docx(
        "test_table_spans",
        """
        <table>
            <tbody>
                <tr>
                    <td>Cell one</td>
                    <td colspan="2">Wide cell</td>
                </tr>
                <tr>
                    <td rowspan="2" colspan = "2">Big cell</td>
                    <td>Cell two</td>
                </tr>
                <tr>
                    <td>Cell three</td>
                </tr>
            </tbody>
        </table>
        """,
        """
            <w:tbl>
                <w:tblPr>
                    <w:tblStyle w:val="TableGrid"/>
                    <w:tblW w:type="auto" w:w="0"/>
                    <w:tblLayout w:type="autofit"/>
                    <w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/>
                </w:tblPr>
                <w:tblGrid>
                    <w:gridCol w:w="2880"/>
                    <w:gridCol w:w="2880"/>
                    <w:gridCol w:w="2880"/>
                </w:tblGrid>
                <w:tr>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell one</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/><w:gridSpan w:val="2"/></w:tcPr>
                        <w:p><w:r><w:t>Wide cell</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
                <w:tr>
                    <w:tc>
                        <w:tcPr>
                            <w:tcW w:type="auto" w:w="0"/>
                            <w:gridSpan w:val="2"/>
                            <w:vMerge w:val="restart"/>
                        </w:tcPr>
                        <w:p><w:r><w:t>Big cell</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell two</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
                <w:tr>
                    <w:tc>
                        <w:tcPr>
                            <w:tcW w:type="auto" w:w="0"/>
                            <w:gridSpan w:val="2"/>
                            <w:vMerge/>
                        </w:tcPr>
                        <w:p/>
                    </w:tc>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>Cell three</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
            </w:tbl>
        """,
    )

    test_table_spans_2 = mk_test_docx(
        "test_table_spans_2",
        """
        <table>
            <tbody>
                <tr>
                    <td>a</td>
                    <td rowspan="2">bcd</td>
                </tr>
                <tr>
                    <td>e</td>
                </tr>
            </tbody>
        </table>
        """,
        """
            <w:tbl>
                <w:tblPr>
                    <w:tblStyle w:val="TableGrid"/>
                    <w:tblW w:type="auto" w:w="0"/>
                    <w:tblLayout w:type="autofit"/>
                    <w:tblLook w:firstColumn="1" w:firstRow="1" w:lastColumn="0" w:lastRow="0" w:noHBand="0" w:noVBand="1" w:val="04A0"/>
                </w:tblPr>
                <w:tblGrid>
                    <w:gridCol w:w="4320"/>
                    <w:gridCol w:w="4320"/>
                </w:tblGrid>
                <w:tr>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>a</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr>
                            <w:tcW w:type="auto" w:w="0"/>
                            <w:vMerge w:val="restart"/>
                        </w:tcPr>
                        <w:p><w:r><w:t>bcd</w:t></w:r></w:p>
                    </w:tc>
                </w:tr>
                <w:tr>
                    <w:tc>
                        <w:tcPr><w:tcW w:type="auto" w:w="0"/></w:tcPr>
                        <w:p><w:r><w:t>e</w:t></w:r></w:p>
                    </w:tc>
                    <w:tc>
                        <w:tcPr>
                            <w:tcW w:type="auto" w:w="0"/>
                            <w:vMerge/>
                        </w:tcPr>
                        <w:p/>
                    </w:tc>
                </w:tr>
            </w:tbl>
        """,
    )

    test_paragraph_class = mk_test_docx(
        "test_paragraph_class",
        """
        <p class="left">Paragraph with a class</p>
        """,
        """
        <w:p>
            <w:pPr><w:jc w:val="left"/></w:pPr>
            <w:r><w:t>Paragraph with a class</w:t></w:r>
        </w:p>
        """,
    )

    test_paragraphs_with_invalid_chars = mk_test_docx(
        "test_paragraphs_with_invalid_chars",
        "<p>Hello&#20; World!</p><p>This is a test!</p>",
        """<w:p><w:pPr/><w:r><w:t>Hello World!</w:t></w:r></w:p><w:p><w:pPr/><w:r><w:t>This is a test!</w:t></w:r></w:p>""",
    )
