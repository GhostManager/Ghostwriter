from typing import Tuple, List
import io
import logging
import os
import re

from docx import Document
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.image.exceptions import UnrecognizedImageError
from docx.opc.exceptions import PackageNotFoundError
from docx.oxml.ns import qn
from docx.shared import Inches, Pt
from docxtpl import DocxTemplate, RichText as DocxRichText

from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.base.html_rich_text import (
    HtmlAndObject,
    RichTextBase,
    LazySubdocRender,
)
from ghostwriter.modules.reportwriter.richtext.docx import HtmlToDocxWithEvidence
from ghostwriter.reporting.models import ReportTemplate

logger = logging.getLogger(__name__)

EXPECTED_STYLES = [
    "Bullet List",
    "Number List",
    "CodeBlock",
    "CodeInline",
    "Caption",
    "List Paragraph",
    "Blockquote",
] + [f"Heading {i}" for i in range(1, 7)]

_img_desc_replace_re = re.compile(r"^\s*\[\s*([a-zA-Z0-9_]+)\s*\]\s*(.*)$")

class ExportDocxBase(ExportBase):
    """
    Base class for exporting DOCX (Word) documents.

    The basic flow for this exporter is:

    1. Serialize the object into a plain JSON-compatible representation. This is optional - the plain data may be provided directly.
    2. Add/replace rich text objects in the data with a `RichTextBase` subclass instance.
       The context used for those templates is usually the serialized data augmented with a few jinja functions and variables.
    3. Copy the context. In the copy, render each template, and replace it with the template render, converting the HTML to
       a format appropriate for export. The jinja templates will access the old context without the converted templates, and
       may include other rich texts as raw strings.
    4. Run the main docx template over the converted rich text objects.

    Subclasses should implement `map_rich_texts` to do step 2.
    """

    word_doc: DocxTemplate
    report_template: ReportTemplate
    global_report_config: ReportConfiguration
    company_config: CompanyInformation
    linting: bool
    image_replacements: dict[str, str]

    @classmethod
    def mime_type(cls) -> str:
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"

    @classmethod
    def extension(cls) -> str:
        return "docx"

    def __init__(
        self,
        object,
        *,
        report_template: ReportTemplate,
        linting: bool = False,
        image_replacements: dict[str, str] | None,
        **kwargs,
    ):
        if "jinja_debug" not in kwargs:
            kwargs["jinja_debug"] = linting
        super().__init__(object, **kwargs)
        self.linting = linting
        self.report_template = report_template
        self.image_replacements = image_replacements or {}

        # Create Word document writer using the specified template file
        try:
            self.word_doc = DocxTemplate(report_template.document.path)
        except PackageNotFoundError as err:
            logger.exception("Failed to load the provided template document: %s", report_template.document.path)
            raise ReportExportTemplateError("Template document file could not be found - try re-uploading it") from err
        except Exception:
            logger.exception("Failed to load the provided template document: %s", report_template.document.path)
            raise

        self.global_report_config = ReportConfiguration.get_solo()
        self.company_config = CompanyInformation.get_solo()

    def run(self) -> io.BytesIO:
        try:
            self.create_styles()
            self.replace_images()

            rich_text_context = self.map_rich_texts()
            docx_context = RichTextBase.deep_copy_process_html(
                rich_text_context,
                self.render_rich_text_docx,
            )

            ReportExportTemplateError.map_errors(
                lambda: self.word_doc.render(docx_context, self.jinja_env, autoescape=True), "the DOCX template"
            )
            ReportExportTemplateError.map_errors(
                lambda: self.render_properties(docx_context), "the DOCX properties"
            )
        except UnrecognizedImageError as err:
            raise ReportExportTemplateError(f"Could not load an image: {err}", "the DOCX template") from err
        except PackageNotFoundError as err:
            raise ReportExportTemplateError(
                "The word template could not be found on the server – try uploading it again.", "the DOCX template"
            ) from err
        except FileNotFoundError as err:
            logger.exception("Missing file")
            raise ReportExportTemplateError(
                "An evidence file was missing – try uploading it again.", "the DOCX template"
            ) from err

        out = io.BytesIO()
        self.word_doc.save(out)

        # Post-process to clean up separator footnotes (remove extra empty paragraphs)
        out = self._cleanup_footnote_separators(out)

        return out

    def _cleanup_footnote_separators(self, docx_bytes: io.BytesIO) -> io.BytesIO:
        """
        Remove extra empty paragraphs from separator footnotes.

        Some Word templates have extra empty paragraphs in the separator and
        continuationSeparator footnotes, which causes unwanted spacing between
        the footnote separator line and the actual footnotes.

        This post-processes the saved DOCX to avoid interfering with docxtpl's
        template rendering.
        """
        try:
            docx_bytes.seek(0)
            doc = Document(docx_bytes)

            # Access the footnotes part (requires accessing internal python-docx members)
            # pylint: disable=protected-access
            if not hasattr(doc._part, '_footnotes_part') or doc._part._footnotes_part is None:
                docx_bytes.seek(0)
                return docx_bytes

            footnotes_part = doc._part._footnotes_part
            footnotes_element = footnotes_part._element
            # pylint: enable=protected-access

            modified = False
            for footnote in footnotes_element:
                # Only clean separator footnotes (id=-1 or id=0)
                footnote_id = footnote.get(qn("w:id"))
                if footnote_id in ("-1", "0"):
                    # Find all paragraph elements
                    paragraphs = list(footnote.iterchildren(qn("w:p")))
                    # Keep only the first paragraph (which contains the separator)
                    for para in paragraphs[1:]:
                        footnote.remove(para)
                        modified = True

            if modified:
                # Save the modified document
                out = io.BytesIO()
                doc.save(out)
                out.seek(0)
                return out

            docx_bytes.seek(0)
            return docx_bytes

        except Exception as e:  # pylint: disable=broad-exception-caught
            # Log but don't fail the report generation
            logger.warning("Failed to cleanup footnote separators: %s", e)
            docx_bytes.seek(0)
            return docx_bytes

    def create_styles(self):
        """
        Creates default styles
        """
        styles = self.word_doc.get_docx().styles
        if "CodeBlock" not in styles:
            codeblock_style = styles.add_style("CodeBlock", WD_STYLE_TYPE.PARAGRAPH)
            codeblock_style.base_style = styles["Normal"]
            codeblock_style.hidden = False
            codeblock_style.quick_style = True
            codeblock_style.priority = 2
            # Set font and size
            codeblock_font = codeblock_style.font
            codeblock_font.name = "Courier New"
            codeblock_font.size = Pt(11)
            # Set alignment
            codeblock_par = codeblock_style.paragraph_format
            codeblock_par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            codeblock_par.line_spacing = 1
            codeblock_par.left_indent = Inches(0.2)
            codeblock_par.right_indent = Inches(0.2)

        if "CodeInline" not in styles:
            codeinline_style = styles.add_style("CodeInline", WD_STYLE_TYPE.CHARACTER)
            codeinline_style.hidden = False
            codeinline_style.quick_style = True
            codeinline_style.priority = 3
            # Set font and size
            codeinline_font = codeinline_style.font
            codeinline_font.name = "Courier New"
            codeinline_font.size = Pt(11)

        if "Caption" not in styles:
            caption_style = styles.add_style("Caption", WD_STYLE_TYPE.PARAGRAPH)
            caption_style.hidden = False
            caption_style.quick_style = True
            caption_style.priority = 4
            # Set font and size
            caption_font = caption_style.font
            caption_font.name = "Calibri"
            caption_font.size = Pt(9)
            caption_font.italic = True

        if "Blockquote" not in styles:
            block_style = styles.add_style("Blockquote", WD_STYLE_TYPE.PARAGRAPH)
            block_style.base_style = styles["Normal"]
            block_style.hidden = False
            block_style.quick_style = True
            block_style.priority = 5
            # Set font and size
            block_font = block_style.font
            block_font.name = "Calibri"
            block_font.size = Pt(12)
            block_font.italic = True
            # Set alignment
            block_par = block_style.paragraph_format
            block_par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
            block_par.left_indent = Inches(0.2)
            block_par.right_indent = Inches(0.2)
            # Keep first and last lines together after repagination
            block_par.widow_control = True

    def render_properties(self, context: dict):
        """
        Renders templates inside of the word doc properties
        """
        attrs = [
            "author",
            "category",
            "comments",
            "content_status",
            "identifier",
            "keywords",
            "language",
            "subject",
            "title",
            "version",
        ]
        for attr in attrs:
            template_src = getattr(self.word_doc.core_properties, attr)
            if not template_src:
                continue

            out = ReportExportTemplateError.map_errors(
                lambda: self.jinja_env.from_string(template_src).render(context), f"DOCX property {attr}"
            )
            setattr(self.word_doc.core_properties, attr, out)

    def render_rich_text_docx(self, rich_text: RichTextBase) -> LazySubdocRender | DocxRichText:
        """
        Renders a `RichTextBase`, converting the HTML from the rich text editor, to a Word subdoc.
        """
        if isinstance(rich_text, HtmlAndObject):
            return rich_text.obj

        def render():
            doc = self.word_doc.new_subdoc()
            ReportExportTemplateError.map_errors(
                lambda: HtmlToDocxWithEvidence.run(
                    rich_text.__html__(),
                    doc=doc,
                    evidences=self.evidences_by_id,
                    report_template=self.report_template,
                    global_report_config=self.global_report_config,
                    images=self.image_replacements,
                ),
                getattr(rich_text, "location", None),
            )
            return doc
        return LazySubdocRender(render)

    def replace_images(self):
        """
        Replaces images whose alt text contains an item from `self.image_replacements`.
        """
        if not self.image_replacements:
            return

        # Collect elements to search in, including the main body and any defined headers/footers
        toplevels = [(self.word_doc.docx.part, self.word_doc.docx._element)]
        for section in self.word_doc.docx.sections:
            headers_and_footers = [
                section.header,
                section.footer,
                section.first_page_header,
                section.first_page_footer,
                section.even_page_header,
                section.even_page_footer,
            ]

            for hp in headers_and_footers:
                if not hp._has_definition:
                    continue
                toplevels.append((
                    hp.part,
                    hp.part._element,
                ))

        # Go through each part and replace matcing drawings
        image_rids_and_objs = {}
        for (part, element) in toplevels:
            for drawing in element.xpath(".//w:drawing"):
                docpr = next(iter(drawing.xpath(".//wp:docPr")), None)
                if docpr is None:
                    continue

                blip = next(iter(drawing.xpath(".//pic:pic//a:blip")), None)
                if blip is None:
                    continue
                if "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed" not in blip.attrib:
                    continue

                # Get image name from alt text
                descr = docpr.attrib.get("descr")
                if not descr:
                    continue
                match = _img_desc_replace_re.search(descr)
                if match is None:
                    continue
                img_name = match[1]
                if img_name not in self.image_replacements:
                    continue
                docpr.attrib["descr"] = match[2]

                # Add image to oc
                key = (id(part), img_name)
                if key in image_rids_and_objs:
                    rid = image_rids_and_objs[key]
                else:
                    rid, _ = part.get_or_add_image(self.image_replacements[img_name])
                    image_rids_and_objs[key] = rid

                # Replace image
                blip.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}embed"] = rid


    @classmethod
    def lint(cls, report_template: ReportTemplate) -> Tuple[List[str], List[str]]:
        """
        Checks a Word template to help ensure that it will export properly.

        Returns two lists: a list of warnings and a list of errors.
        Linting passes if the errors list is empty.
        """
        warnings = []
        errors = []

        logger.info("Linting docx file %r", report_template.document.path)
        try:
            if not os.path.exists(report_template.document.path):
                logger.error("Template file path did not exist: %r", report_template.document.path)
                errors.append("Template file does not exist – upload it again")
                return warnings, errors

            lint_data = cls.generate_lint_data()
            exporter = cls(
                lint_data,
                is_raw=True,
                linting=True,
                report_template=report_template,
            )
            logger.info("Template loaded for linting")

            undeclared_variables = ReportExportTemplateError.map_errors(
                lambda: exporter.word_doc.get_undeclared_template_variables(exporter.jinja_env), "the DOCX template"
            )
            for variable in undeclared_variables:
                if variable not in lint_data:
                    warnings.append("Potential undefined variable: {!r}".format(variable))

            document_styles = exporter.word_doc.styles
            for style in EXPECTED_STYLES:
                if style not in document_styles:
                    warnings.append("Template is missing a recommended style (see documentation): " + style)
                else:
                    if style == "CodeInline":
                        if document_styles[style].type != WD_STYLE_TYPE.CHARACTER:
                            warnings.append("CodeInline style is not a character style (see documentation)")
                    if style == "CodeBlock":
                        if document_styles[style].type != WD_STYLE_TYPE.PARAGRAPH:
                            warnings.append("CodeBlock style is not a paragraph style (see documentation)")
                    if style == "Bullet List":
                        if document_styles[style].type != WD_STYLE_TYPE.PARAGRAPH:
                            warnings.append("Bullet List style is not a paragraph style (see documentation)")
                    if style == "Number List":
                        if document_styles[style].type != WD_STYLE_TYPE.PARAGRAPH:
                            warnings.append("Number List style is not a paragraph style (see documentation)")
                    if style == "List Paragraph":
                        if document_styles[style].type != WD_STYLE_TYPE.PARAGRAPH:
                            warnings.append("List Paragraph style is not a paragraph style (see documentation)")
            if "Table Grid" not in document_styles:
                errors.append("Template is missing a required style (see documentation): Table Grid")
            if report_template.p_style and report_template.p_style not in document_styles:
                warnings.append("Template is missing your configured default paragraph style: " + report_template.p_style)

            exporter.run()

            for var in exporter.jinja_undefined_variables:
                warnings.append("Undefined variable: {!r}".format(var))
        except ReportExportTemplateError as error:
            logger.exception("Template failed linting: %s", error)
            errors.append(f"Linting failed: {error}")
        except Exception:
            logger.exception("Template failed linting")
            errors.append("Template rendering failed unexpectedly")

        logger.info("Linting finished: %d warnings, %d errors", len(warnings), len(errors))
        return warnings, errors

    def bloodhound_heading_offset(self) -> int:
        return self.report_template.bloodhound_heading_offset
