
from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase


class ExportProjectDocx(ExportDocxBase, ExportProjectBase):
    def __init__(self, object, **kwargs):
        if kwargs.get("p_style") is None and not kwargs.get("is_raw"):
            kwargs["p_style"] = object.docx_template.p_style
        if kwargs.get("evidence_image_width") is None and not kwargs.get("is_raw"):
            kwargs["evidence_image_width"] = object.docx_template.evidence_image_width
        super().__init__(object, **kwargs)
