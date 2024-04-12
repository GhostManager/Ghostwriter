
from typing import Tuple, List
import io
import logging
import os

from docxtpl import DocxTemplate
from docx.opc.exceptions import PackageNotFoundError
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from jinja2.exceptions import TemplateRuntimeError, TemplateSyntaxError, UndefinedError

from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration
from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter.base.base import ExportBase
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

    Subclasses should override `run` to replace rich text objects in `self.data` using the
    `process_rich_text_docx` method, then call this class's `run` method to execute
    and return the `DocxTemplate`.
    """

    word_doc: DocxTemplate
    company_config: CompanyInformation
    linting: bool
    p_style: str | None

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
        **kwargs
    ):
        if "jinja_debug" not in kwargs:
            kwargs["jinja_debug"] = linting
        super().__init__(object, **kwargs)
        self.linting = linting
        self.p_style = p_style

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
        self.render_properties()

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

    def render_properties(self):
        """
        Renders templates inside of the word doc properties
        """
        attrs = ["author", "category", "comments", "content_status", "identifier", "keywords", "language", "subject", "title", "version"]
        for attr in attrs:
            template_src = getattr(self.word_doc.core_properties, attr)
            if not template_src:
                continue
            template = self.jinja_env.from_string(template_src)
            out = template.render(self.data)
            setattr(self.word_doc.core_properties, attr, out)

    def process_rich_text_docx(self, text, template_vars, evidences):
        """
        Converts HTML from the TinyMCE rich text editor to a Word subdoc.
        """
        text = self.preprocess_rich_text(text, template_vars)
        doc = self.word_doc.new_subdoc()
        try:
            HtmlToDocxWithEvidence.run(
                text,
                doc=doc,
                p_style=self.p_style,
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

    @classmethod
    def generate_lint_data(cls):
        raise NotImplementedError()

    @classmethod
    def lint(cls, template_loc: str, p_style: str | None) -> Tuple[List[str], List[str]]:
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
            )
            logger.info("Template loaded for linting")

            for variable in exporter.word_doc.get_undeclared_template_variables(exporter.jinja_env):
                if variable not in lint_data:
                    warnings.append("Potential undefined variable: {!r}".format(variable))

            document_styles = exporter.word_doc.styles
            for style in EXPECTED_STYLES:
                if style not in document_styles:
                    warnings.append("Template is missing a recommended style (see documentation): " + style)
            if "Table Grid" not in document_styles:
                errors.append("Template is missing a required style (see documentation): Table Grid")
            if p_style and p_style not in document_styles:
                warnings.append("Template is missing your configured default paragraph style: " + p_style)

            exporter.run()

            for var in exporter.jinja_undefined_variables:
                warnings.append("Undefined variable: {!r}".format(var))
        except TemplateSyntaxError as error:
            logger.error("Template syntax error: %s", error)
            errors.append(f"Template syntax error: {error}")
        except UndefinedError as error:
            logger.exception("Template undefined variable error: %s", error)
            errors.append(f"Template syntax error: {error}")
        except InvalidFilterValue as error:
            logger.error("Invalid value provided to filter: %s", error)
            errors.append(f"Invalid filter value: {error.message}")
        except TypeError as error:
            logger.exception("TypeError during template linting")
            errors.append(f": {error}")
        except TemplateRuntimeError as error:
            logger.error("Invalid filter or expression: %s", error)
            errors.append(f"Invalid filter or expression: {error}")
        except Exception:
            logger.exception("Template failed linting")
            errors.append("Template rendering failed unexpectedly")

        logger.info("Linting finished: %d warnings, %d errors", len(warnings), len(errors))
        return warnings, errors
