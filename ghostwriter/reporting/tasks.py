"""This contains tasks to be run using Django Q and Redis."""

# Standard Libraries
import datetime
import logging
from datetime import date


# Ghostwriter Libraries
from ghostwriter.modules.reportwriter import report_generation_queryset
from ghostwriter.reporting.archive import archive_report

# Using __name__ resolves to ghostwriter.reporting.tasks
logger = logging.getLogger(__name__)

def archive_projects():
    """
    Collect all completed :model:`rolodex.Project` that have not yet been archived and
    archive the associated reports. The archived reports are deleted and the new archive
    file is logged in the :model:`rolodex.Archive`.
    """
    # Get the non-archived reports for all projects marked as complete
    report_queryset = report_generation_queryset().filter(project__complete=True, archived=False, project__end_date__lte=date.today() - datetime.timedelta(days=90))
    for report in report_queryset:
        try:
            logger.info("Archiving report %s", report.pk)
            archive_report(report)
        except Exception: # pylint: disable=broad-exception-caught
            logger.exception("Error while archiving report %s", report.pk)
