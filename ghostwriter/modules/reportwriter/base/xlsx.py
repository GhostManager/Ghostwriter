
import io

from xlsxwriter.workbook import Workbook

from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.base.html_rich_text import LazilyRenderedTemplate
from ghostwriter.modules.reportwriter.richtext.plain_text import html_to_plain_text


class ExportXlsxBase(ExportBase):
    """
    Base class for Xlsx (Excel) export

    Subclasses should override `run` to add data to the `workbook` field, using `process_rich_text_xlsx`
    to template and convert rich text fields, then return `super().run()` to save and return the workbook.
    """
    output_file: io.BytesIO
    workbook: Workbook

    def __init__(self, object):
        super().__init__(object)
        self.output = io.BytesIO()
        self.workbook = Workbook(self.output, {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        })

    @classmethod
    def mime_type(cls) -> str:
        return "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

    @classmethod
    def extension(cls) -> str:
        return "xlsx"

    def render_rich_text_xlsx(self, rich_text: LazilyRenderedTemplate) -> str:
        """
        Renders a `LazilyRenderedTemplate`, converting the HTML from the TinyMCE rich text editor to a plain text string
        for use in XLSX cells
        """
        return ReportExportTemplateError.map_errors(
            lambda: html_to_plain_text(
                rich_text.render_html(),
                self.evidences_by_id,
            ),
            getattr(rich_text, "location", None),
        )

    def run(self) -> io.BytesIO:
        self.workbook.close()
        return self.output
