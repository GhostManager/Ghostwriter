
from docxtpl import RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase


class ExportReportDocx(ExportDocxBase, ExportReportBase):
    def __init__(self, object, **kwargs):
        if kwargs.get("p_style") is None and not kwargs.get("is_raw"):
            kwargs["p_style"] = object.docx_template.p_style
        if kwargs.get("evidence_image_width") is None:
            kwargs["evidence_image_width"] = object.docx_template.evidence_image_width
        super().__init__(object, **kwargs)

    def severity_rich_text(self, text, severity_color):
        return RichText(text, color=severity_color)
