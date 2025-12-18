
from docxtpl import RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase


class ExportReportDocx(ExportDocxBase, ExportReportBase):
    def __init__(self, object, **kwargs):
        image_replacements = kwargs.get("image_replacements", {})
        if not kwargs.get("is_raw"):
            if object.project.client.logo:
                image_replacements["CLIENT_LOGO"] = object.project.client.logo.path
        super().__init__(object, image_replacements=image_replacements, **kwargs)

    def severity_rich_text(self, text, severity_color):
        return RichText(text, color=severity_color)
