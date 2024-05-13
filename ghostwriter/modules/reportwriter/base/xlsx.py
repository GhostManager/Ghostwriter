
import io

from xlsxwriter.workbook import Workbook

from ghostwriter.modules.reportwriter.base import ReportExportError
from ghostwriter.modules.reportwriter.base.base import ExportBase
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

    def process_rich_text_xlsx(self, name, html, template_vars, evidences) -> str:
        """
        Converts HTML from the TinyMCE rich text editor and returns a plain string
        for use in XLSX cells
        """
        return ReportExportError.map_jinja2_render_errors(
            lambda: html_to_plain_text(self.preprocess_rich_text(html, template_vars), evidences),
            name,
        )

    def run(self) -> io.BytesIO:
        self.workbook.close()
        return self.output
