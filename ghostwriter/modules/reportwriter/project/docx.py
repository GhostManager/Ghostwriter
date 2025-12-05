
from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase


class ExportProjectDocx(ExportDocxBase, ExportProjectBase):
    def __init__(self, object, **kwargs):
        image_replacements = kwargs.get("image_replacements", {})
        if not kwargs.get("is_raw"):
            if object.client.logo:
                image_replacements["CLIENT_LOGO"] = object.client.logo.path
        super().__init__(object, image_replacements=image_replacements, **kwargs)
