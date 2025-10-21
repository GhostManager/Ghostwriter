
from docxtpl import RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase


class ExportReportDocx(ExportDocxBase, ExportReportBase):
    def severity_rich_text(self, text, severity_color):
        return RichText(text, color=severity_color)
