
import logging

from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx
from ghostwriter.reporting.models import ReportTemplate

logger = logging.getLogger(__name__)


def lint_template(template: ReportTemplate):
    """
    Lints a `ReportTemplate`. Sets `template.lint_results` and returns a `results` object
    for the frontend. Be sure to save the template afterwards.
    """
    if template.doc_type.doc_type == "docx":
        warnings, errors = ExportReportDocx.lint(
            template.document.path,
            p_style=template.p_style,
        )
    elif template.doc_type.doc_type == "pptx":
        warnings, errors = ExportReportPptx.lint(
            template.document.path
        )
    else:
        logger.warning(
            "Template %d had an unknown filetype not supported by the linter: %s",
            template.id,
            template.doc_type,
        )
        warnings = []
        errors = ["Template had an unknown filetype not supported by linter"]

    results = {
        "warnings": warnings,
        "errors": errors,
    }
    if errors:
        results["result"] = "failed"
    elif warnings:
        results["result"] = "warning"
    else:
        results["result"] = "success"
    template.lint_result = results.copy()

    if results["result"] == "success":
        results["message"] = "Template linter returned results with no errors or warnings."
    else:
        results["message"] = "Template linter returned results with issues that require attention."
    return results
