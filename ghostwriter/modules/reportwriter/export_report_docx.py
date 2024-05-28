# Standard Libraries
import io
import logging
from copy import deepcopy
from importlib.metadata import PackageNotFoundError

# 3rd Party Libraries
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Inches, Pt
from docxtpl import DocxTemplate, RichText

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration
from ghostwriter.modules.reportwriter.export_report_base import ExportReportBase
from ghostwriter.modules.reportwriter.html_to_docx import HtmlToDocxWithEvidence
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer

logger = logging.getLogger(__name__)


class ExportReportDocx(ExportReportBase):
    word_doc: DocxTemplate

    def __init__(self, report, template_loc=None):
        super().__init__(report)

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
            logger.exception(
                "Failed to load the provided template document: %s", template_loc
            )
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
        self.title_case_exceptions = global_report_config.title_case_exceptions.split(
            ","
        )

    def process_extra_fields(self, extra_fields, model, render_rich_text):
        specs = self.extra_field_specs_for(model)
        for field in specs:
            if field.internal_name not in extra_fields:
                extra_fields[field.internal_name] = field.initial_value()
            if field.type == "rich_text":
                extra_fields[field.internal_name] = render_rich_text(
                    str(extra_fields[field.internal_name])
                )

    def _process_rich_text_docx(self, text, template_vars, evidences, p_style=None):
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
                border_color_width=(
                    (self.border_color, self.border_weight)
                    if self.enable_borders
                    else None
                ),
            )
        except:
            # Log input text to help diagnose errors
            logger.warning("Input text: %r", text)
            raise
        return doc

    def _process_extra_fields(self, extra_fields, model, render_rich_text):
        specs = self.extra_field_specs_for(model)
        for field in specs:
            if field.internal_name not in extra_fields:
                extra_fields[field.internal_name] = field.initial_value()
            if field.type == "rich_text":
                extra_fields[field.internal_name] = render_rich_text(
                    str(extra_fields[field.internal_name])
                )

    def _process_richtext(self, context: dict) -> dict:
        """
        Update the document context with ``RichText`` and ``Subdocument`` objects for
        each finding and any other values editable with a WYSIWYG editor.

        **Parameters**

        ``context``
            Pre-defined template context
        """

        p_style = self.report.docx_template.p_style

        base_context = self.jinja_richtext_base_context()
        base_evidences = {e["friendly_name"]: e for e in context["evidence"]}

        def base_render(text):
            return self._process_rich_text_docx(
                text, base_context, base_evidences, p_style
            )

        self._process_extra_fields(context["extra_fields"], Report, base_render)

        # Findings
        for finding in context["findings"]:
            logger.info("Processing %s", finding["title"])

            finding_context = self.jinja_richtext_finding_context(base_context, finding)
            finding_evidences = base_evidences | {
                e["friendly_name"]: e for e in finding["evidence"]
            }

            def finding_render(text):
                return self._process_rich_text_docx(
                    text, finding_context, finding_evidences, p_style
                )

            self._process_extra_fields(finding["extra_fields"], Finding, finding_render)

            # Create ``RichText()`` object for a colored severity category
            finding["severity_rt"] = RichText(
                finding["severity"], color=finding["severity_color"]
            )
            finding["cvss_score_rt"] = RichText(
                finding["cvss_score"], color=finding["severity_color"]
            )
            finding["cvss_vector_rt"] = RichText(
                finding["cvss_vector"], color=finding["severity_color"]
            )
            # Create subdocuments for each finding section
            finding["affected_entities_rt"] = finding_render(
                finding["affected_entities"]
            )
            finding["description_rt"] = finding_render(finding["description"])
            finding["impact_rt"] = finding_render(finding["impact"])

            # Include a copy of ``mitigation`` as ``recommendation`` to match legacy context
            mitigation_section = finding_render(finding["mitigation"])
            finding["mitigation_rt"] = mitigation_section
            finding["recommendation_rt"] = mitigation_section

            finding["replication_steps_rt"] = finding_render(
                finding["replication_steps"]
            )
            finding["host_detection_techniques_rt"] = finding_render(
                finding["host_detection_techniques"]
            )
            finding["network_detection_techniques_rt"] = finding_render(
                finding["network_detection_techniques"]
            )
            finding["references_rt"] = finding_render(finding["references"])

        # Client
        context["client"]["note_rt"] = base_render(context["client"]["note"])
        context["client"]["address_rt"] = base_render(context["client"]["address"])
        self._process_extra_fields(
            context["client"]["extra_fields"], Client, base_render
        )

        # Project
        context["project"]["note_rt"] = base_render(context["project"]["note"])
        self._process_extra_fields(
            context["project"]["extra_fields"], Project, base_render
        )

        # Assignments
        for assignment in context["team"]:
            if isinstance(assignment, dict):
                if assignment["note"]:
                    assignment["note_rt"] = base_render(assignment["note"])

        # Contacts
        for contact in context["client"]["contacts"]:
            if isinstance(contact, dict):
                if contact["note"]:
                    contact["note_rt"] = base_render(contact["note"])

        # Objectives
        for objective in context["objectives"]:
            if isinstance(objective, dict):
                if objective["description"]:
                    objective["description_rt"] = base_render(objective["description"])

        # Scope Lists
        for scope_list in context["scope"]:
            if isinstance(scope_list, dict):
                if scope_list["description"]:
                    scope_list["description_rt"] = base_render(
                        scope_list["description"]
                    )

        # Targets
        for target in context["targets"]:
            if isinstance(target, dict):
                if target["note"]:
                    target["note_rt"] = base_render(target["note"])

        # Deconfliction Events
        for event in context["deconflictions"]:
            if isinstance(event, dict):
                if event["description"]:
                    event["description_rt"] = base_render(event["description"])

        # White Cards
        for card in context["whitecards"]:
            if isinstance(card, dict):
                if card["description"]:
                    card["description_rt"] = base_render(card["description"])

        # Infrastructure
        for asset_type in context["infrastructure"]:
            for asset in context["infrastructure"][asset_type]:
                if isinstance(asset, dict):
                    if asset["note"]:
                        asset["note_rt"] = base_render(asset["note"])
        for asset in context["infrastructure"]["domains"]:
            self._process_extra_fields(asset["extra_fields"], Domain, base_render)
        for asset in context["infrastructure"]["servers"]:
            self._process_extra_fields(asset["extra_fields"], StaticServer, base_render)

        # Logs
        for log in context["logs"]:
            for entry in log["entries"]:
                self._process_extra_fields(
                    entry["extra_fields"], OplogEntry, base_render
                )

        # Observations
        for observation in context["observations"]:
            if observation["description"]:
                observation["description_rt"] = base_render(observation["description"])
            self._process_extra_fields(
                observation["extra_fields"], Observation, base_render
            )

        # Report Evidence
        # for evidence in context["evidence"]:
        #    self._process_extra_fields(evidence["extra_fields"], Report, base_render)

        return context

    def run(self) -> io.BytesIO:
        # Check for styles
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

        # Process template context, converting HTML elements to XML as needed
        context = deepcopy(self.data)
        context = self._process_richtext(context)

        # Render the Word document + auto-escape any unsafe XML/HTML
        self.word_doc.render(context, self.jinja_env, autoescape=True)

        # Return the final rendered document
        out = io.BytesIO()
        self.word_doc.save(out)
        return out
