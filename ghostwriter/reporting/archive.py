
import os
import zipfile
import tempfile
from shutil import copyfileobj

from django.core.files import File
from django.db.transaction import atomic

from ghostwriter.commandcenter.models import ReportConfiguration
from ghostwriter.modules.exceptions import MissingTemplate
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.modules.reportwriter.report.xlsx import ExportReportXlsx
from ghostwriter.reporting.models import Archive, Report

def archive_report(report: Report):
    """
    Archives a report, generating the report and storing it and other info into a zip file
    """
    report_config = ReportConfiguration.get_solo()
    docx_template = report.docx_template or report_config.default_docx_template
    pptx_template = report.pptx_template or report_config.default_pptx_template
    if not docx_template:
        raise MissingTemplate()
    if not pptx_template:
        raise MissingTemplate()
    filename = "archives/" + "".join(c for c in report.title if c.isalpha() or c.isdigit() or c == ' ') + ".zip"
    evidences = report.all_evidences()

    with tempfile.TemporaryFile("w+b") as arcfile:
        with zipfile.ZipFile(arcfile, mode="w", compression=zipfile.ZIP_DEFLATED) as zf:
            zf.writestr("report.json", ExportReportJson(report).run().getvalue())
            zf.writestr("report.xlsx", ExportReportXlsx(report).run().getvalue())
            zf.writestr("report.docx", docx_template.exporter(report).run().getvalue())
            zf.writestr("report.pptx", pptx_template.exporter(report).run().getvalue())

            for evi in evidences:
                evi_file = evi.document
                with zf.open("evidence/"+os.path.basename(evi_file.name), "w") as out_file:
                    copyfileobj(evi_file, out_file)
        arcfile.seek(0)

        with atomic():
            new_archive = Archive(
                project=report.project,
                report_archive=File(arcfile, name=filename)
            )
            new_archive.save()
            report.archived = True
            report.complete = True
            report.delivered = True
            report.save()
            evidences.delete()
