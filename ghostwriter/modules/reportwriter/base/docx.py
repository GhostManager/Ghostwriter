from typing import Tuple, List
import io
import logging
import os

from docxtpl import DocxTemplate
from docx.opc.exceptions import PackageNotFoundError
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docx.image.exceptions import UnrecognizedImageError

from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.base.html_rich_text import (
    HtmlAndRich,
    LazilyRenderedTemplate,
    LazySubdocRender,
    deep_copy_with_copiers,
)
from ghostwriter.modules.reportwriter.richtext.docx import HtmlToDocxWithEvidence

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


class ExportDocxBase(ExportBase):
    """
    Base class for exporting DOCX (Word) documents.

    The basic flow for this exporter is:

    1. Serialize the object into a plain JSON-compatible representation. This is optional - the plain data may be provided directly.
    2. Add/replace rich text objects in the data with a `LazilyRenderedTemplate` instance containing the compiled template or `HtmlAndRich` objects.
       The context used for those templates is usually the serialized data augmented with a few jinja functions and variables.
    3. Copy the context. In the copy, render each template, and replace it with the template render, converting the HTML to
       a format appropriate for export. The jinja templates will access the old context without the converted templates, and
       may include other rich texts as raw strings.
    4. Run the main docx template over the converted rich text objects.

    Subclasses should implement `map_rich_texts` to do step 2.
    """

    word_doc: DocxTemplate
    company_config: CompanyInformation
    linting: bool
    p_style: str | None
    evidence_image_width: float | None

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
        template_loc: str,
        p_style: str | None,
        linting: bool = False,
        evidence_image_width: float | None,
        **kwargs,
    ):
        if "jinja_debug" not in kwargs:
            kwargs["jinja_debug"] = linting
        super().__init__(object, **kwargs)
        self.linting = linting
        self.p_style = p_style
        self.evidence_image_width = evidence_image_width

        # Create Word document writer using the specified template file
        try:
            self.word_doc = DocxTemplate(template_loc)
        except PackageNotFoundError as err:
            logger.exception("Failed to load the provided template document: %s", template_loc)
            raise ReportExportTemplateError("Template document file could not be found - try re-uploading it") from err
        except Exception:
            logger.exception("Failed to load the provided template document: %s", template_loc)
            raise

        global_report_config = ReportConfiguration.get_solo()
        self.company_config = CompanyInformation.get_solo()

        # Picture border settings for Word
        self.enable_borders = global_report_config.enable_borders
        self.border_color = global_report_config.border_color
        self.border_weight = global_report_config.border_weight

        # Caption options
        prefix_figure = global_report_config.prefix_figure
        self.prefix_figure = f"{prefix_figure}"
        label_figure = global_report_config.label_figure
        self.label_figure = f"{label_figure}"
        prefix_table = global_report_config.prefix_table
        self.prefix_table = f"{prefix_table}"
        self.figure_caption_location = global_report_config.figure_caption_location
        label_table = global_report_config.label_table
        self.label_table = f"{label_table}"
        self.table_caption_location = global_report_config.table_caption_location
        self.title_case_captions = global_report_config.title_case_captions
        self.title_case_exceptions = global_report_config.title_case_exceptions.split(",")

    def run(self) -> io.BytesIO:
        try:
            self.create_styles()

            rich_text_context = self.map_rich_texts()
            docx_context = deep_copy_with_copiers(
                rich_text_context,
                {
                    LazilyRenderedTemplate: self.render_rich_text_docx,
                    HtmlAndRich: lambda v: v.rich,
                },
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
            raise ReportExportTemplateError(
                "An evidence file was missing – try uploading it again.", "the DOCX template"
            ) from err

        out = io.BytesIO()
        self.word_doc.save(out)
        return out

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

    def render_rich_text_docx(self, rich_text: LazilyRenderedTemplate):
        """
        Renders a `LazilyRenderedTemplate`, converting the HTML from the TinyMCE rich text editor to a Word subdoc.
        """
        def render():
            doc = self.word_doc.new_subdoc()
            ReportExportTemplateError.map_errors(
                lambda: HtmlToDocxWithEvidence.run(
                    rich_text.render_html(),
                    doc=doc,
                    p_style=self.p_style,
                    evidence_image_width=self.evidence_image_width,
                    evidences=self.evidences_by_id,
                    figure_label=self.label_figure,
                    figure_prefix=self.prefix_figure,
                    figure_caption_location=self.figure_caption_location,
                    table_label=self.label_table,
                    table_prefix=self.prefix_table,
                    table_caption_location=self.table_caption_location,
                    title_case_captions=self.title_case_captions,
                    title_case_exceptions=self.title_case_exceptions,
                    border_color_width=(self.border_color, self.border_weight) if self.enable_borders else None,
                ),
                getattr(rich_text, "location", None),
            )
            return doc
        return LazySubdocRender(render)

    @classmethod
    def lint(cls, template_loc: str, p_style: str | None) -> Tuple[List[str], List[str]]:
        """
        Checks a Word template to help ensure that it will export properly.

        Returns two lists: a list of warnings and a list of errors.
        Linting passes if the errors list is empty.
        """
        warnings = []
        errors = []

        logger.info("Linting docx file %r", template_loc)
        try:
            if not os.path.exists(template_loc):
                logger.error("Template file path did not exist: %r", template_loc)
                errors.append("Template file does not exist – upload it again")
                return warnings, errors

            lint_data = cls.generate_lint_data()
            exporter = cls(
                lint_data,
                is_raw=True,
                linting=True,
                template_loc=template_loc,
                p_style=p_style,
                evidence_image_width=6.5,  # Value doesn't matter for linting
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
            if p_style and p_style not in document_styles:
                warnings.append("Template is missing your configured default paragraph style: " + p_style)

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
