
from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase


class ExportProjectDocx(ExportDocxBase, ExportProjectBase):
    def __init__(self, object, **kwargs):
        if kwargs.get("p_style") is None and not kwargs.get("is_raw"):
            kwargs["p_style"] = object.docx_template.p_style
        super().__init__(object, **kwargs)
