
import io
import logging

from docxtpl import DocxTemplate
from docx.opc.exceptions import PackageNotFoundError
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration

from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.richtext.docx import HtmlToDocxWithEvidence

logger = logging.getLogger(__name__)


class ExportDocxBase(ExportBase):
    """
    Base class for exporting DOCX (Word) documents.

    Subclasses should override `run` to replace rich text objects in `self.data` using the
    `process_rich_text_docx` method, then call this class's `run` method to execute
    and return the `DocxTemplate`.
    """

    word_doc: DocxTemplate
    company_config: CompanyInformation

    def __init__(self, object, template_loc=None):
        super().__init__(object)

        # Create Word document writer using the specified template file
        try:
            self.word_doc = DocxTemplate(template_loc)
        except PackageNotFoundError:
            logger.exception(
                "Failed to load the provided template document because file could not be found: %s",
                template_loc,
            )
            raise
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
        prefix_figure = global_report_config.prefix_figure.strip()
        self.prefix_figure = f" {prefix_figure} "
        label_figure = global_report_config.label_figure.strip()
        self.label_figure = f"{label_figure} "
        self.title_case_captions = global_report_config.title_case_captions
        self.title_case_exceptions = global_report_config.title_case_exceptions.split(",")

    def run(self) -> io.BytesIO:
        self.create_styles()

        self.word_doc.render(self.data, self.jinja_env, autoescape=True)

        out = io.BytesIO()
        self.word_doc.save(out)
        return out

    def create_styles(self):
        """
        Creates default styles
        """
        styles = self.word_doc.styles
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

    def process_rich_text_docx(self, text, template_vars, evidences, p_style=None):
        """
        Converts HTML from the TinyMCE rich text editor to a Word subdoc.
        """
        text = self.preprocess_rich_text(text, template_vars)
        doc = self.word_doc.new_subdoc()
        try:
            HtmlToDocxWithEvidence.run(
                text,
                doc=doc,
                p_style=p_style,
                evidences=evidences,
                figure_label=self.label_figure,
                figure_prefix=self.prefix_figure,
                title_case_captions=self.title_case_captions,
                title_case_exceptions=self.title_case_exceptions,
                border_color_width=(self.border_color, self.border_weight) if self.enable_borders else None,
            )
        except:
            # Log input text to help diagnose errors
            logger.warning("Input text: %r", text)
            raise
        return doc

    def process_extra_fields(self, extra_fields, model, render_rich_text):
        """
        Process the `extra_fields` dict, filling missing extra fields with empty values and rendering
        rich text
        """
        specs = self.extra_field_specs_for(model)
        for field in specs:
            if field.internal_name not in extra_fields:
                extra_fields[field.internal_name] = field.empty_value()
            if field.type == "rich_text":
                extra_fields[field.internal_name] = render_rich_text(str(extra_fields[field.internal_name]))
