"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import datetime
import io
import logging
import os
import zipfile
from datetime import date

# Django Imports
from django.conf import settings
from django.core.files import File
from django.db.models import Q

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter.report.json import ExportReportJson
from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx
from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx
from ghostwriter.modules.reportwriter.report.xlsx import ExportReportXlsx

from .models import Archive, Report

# Using __name__ resolves to ghostwriter.reporting.tasks
logger = logging.getLogger(__name__)


def zip_directory(path, zip_handler):
    """
    Zip the target directory and all of its contents to create a project archive.

    **Parameters**

    ``path``
        File path to archive
    ``zip_handler``
        A ``zipfile.ZipFile()`` object to create the archive
    """
    # Walk the target directory
    abs_src = os.path.abspath(path)
    for root, _, files in os.walk(path):
        # Add each file to the zip file handler
        for file in files:
            absname = os.path.abspath(os.path.join(root, file))
            arcname = absname[len(abs_src) + 1 :]
            zip_handler.write(os.path.join(root, file), "evidence/" + arcname)


def archive_projects():
    """
    Collect all completed :model:`rolodex.Project` that have not yet been archived and
    archive the associated reports. The archived reports are deleted and the new archive
    file is logged in the :model:`rolodex.Archive`.
    """
    # Get the non-archived reports for all projects marked as complete
    report_queryset = Report.objects.select_related("project").filter(Q(project__complete=False) & Q(archived=False))
    for report in report_queryset:
        if date.today() >= report.project.end_date - datetime.timedelta(days=90):
            archive_loc = os.path.join(settings.MEDIA_ROOT, "archives")
            evidence_loc = os.path.join(settings.MEDIA_ROOT, "evidence", str(report.project.id))
            docx_template_loc = os.path.join(settings.MEDIA_ROOT, "templates", "template.docx")
            pptx_template_loc = os.path.join(settings.MEDIA_ROOT, "templates", "template.pptx")

            word_doc = ExportReportDocx(report, template_loc=docx_template_loc).run()
            ppt_doc = ExportReportPptx(report, template_loc=pptx_template_loc).run()
            excel_doc = ExportReportXlsx(report).run()
            json_doc = ExportReportJson(report).run()

            # Create a zip file in memory and add the reports to it
            zip_buffer = io.BytesIO()
            with zipfile.ZipFile(zip_buffer, "a") as zf:
                zf.writestr("report.json", json_doc.getvalue())
                zf.writestr("report.docx", word_doc.getvalue())
                zf.writestr("report.xlsx", excel_doc.getvalue())
                zf.writestr("report.pptx", ppt_doc.getvalue())
                zip_directory(evidence_loc, zf)
            zip_buffer.seek(0)
            with open(os.path.join(archive_loc, report.title + ".zip"), "wb") as archive_file:
                archive_file.write(zip_buffer.getvalue())
            new_archive = Archive(
                project=report.project,
                report_archive=File(zip_buffer),
            )
            new_archive.save()
            report.archived = True
            report.complete = True
            report.save()
        else:
            pass
