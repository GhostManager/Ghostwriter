
from functools import partial

from docxtpl import DocxTemplate, RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.log_dependencies import LOG_KEYS, template_variables
from ghostwriter.modules.reportwriter.report.base import ExportReportBase


class ExportReportDocx(ExportDocxBase, ExportReportBase):
    def __init__(self, object, *, filename_template=None, **kwargs):
        if filename_template is not None:
            kwargs["inspect_templates"] = partial(
                _word_template_variables,
                kwargs["report_template"].document.path,
                filename_template,
            )
        image_replacements = kwargs.get("image_replacements", {})
        if not kwargs.get("is_raw"):
            if object.project.client.logo:
                image_replacements["CLIENT_LOGO"] = object.project.client.logo.path
        super().__init__(object, image_replacements=image_replacements, **kwargs)

    def severity_rich_text(self, text, severity_color):
        return RichText(text, color=severity_color)


def _word_template_variables(path, filename_template, env):
    """Inspect each independently rendered Word part and the export filename."""
    template = DocxTemplate(path)
    document = template.get_docx()
    sources = [template.patch_xml(template.xml_to_string(document._element.body))]
    for rel in document.part.rels.values():
        if rel.reltype in (template.HEADER_URI, template.FOOTER_URI):
            sources.append(template.patch_xml(template.get_part_xml(rel.target_part)))
    for part in document.part.package.parts:
        if part.content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.footnotes+xml":
            sources.append(template.patch_xml(part.blob.decode("utf-8")))
    sources.append(filename_template)
    variables = set().union(*(template_variables(env, source) for source in sources))

    # docxtpl and Ghostwriter both render properties. Even a constant
    # expression in the first pass can produce Jinja for the second pass.
    for element in document.core_properties._element:
        source = element.text or ""
        if any(delimiter in source for delimiter in ("{{", "{%", "{#")):
            variables.update(LOG_KEYS)
            break
    return variables
