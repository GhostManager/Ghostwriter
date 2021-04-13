"""This contains all of the database models used by the Reporting application."""

# Standard Libraries
import json
import logging
import os

# Django Imports
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.storage import FileSystemStorage
from django.db import models
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

from .validators import validate_evidence_extension

# Using __name__ resolves to ghostwriter.reporting.models
logger = logging.getLogger(__name__)


class Severity(models.Model):
    """
    Stores an individual severity rating.
    """

    severity = models.CharField(
        "Severity",
        max_length=255,
        unique=True,
        help_text="Name for this severity rating (e.g. High, Low)",
    )
    weight = models.IntegerField(
        "Severity Weight",
        default=1,
        help_text="Weight for sorting severity categories in reports (lower numbers are more severe)",
    )
    color = models.CharField(
        "Severity Color",
        max_length=6,
        default="7A7A7A",
        help_text="Six character hex color code associated with this severity for reports (e.g., FF7E79)",
    )

    def count_findings(self):
        """
        Return the number of :model:`reporting.Finding` associated with an instance.
        """
        return Finding.objects.filter(severity=self).count()

    @property
    def color_rgb(self):
        """
        Return the severity color code as a list of RGB values.
        """
        return tuple(int(self.color[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def color_hex(self):
        """
        Return the severity color code as a list of hexadecimal.
        """
        n = 2
        return tuple(
            hex(int(self.color[i : i + n], 16)) for i in range(0, len(self.color), n)
        )

    count = property(count_findings)

    class Meta:
        ordering = ["weight", "severity"]
        verbose_name = "Severity rating"
        verbose_name_plural = "Severity ratings"

    def __str__(self):
        return f"{self.severity}"


class FindingType(models.Model):
    """
    Stores an individual finding type.
    """

    finding_type = models.CharField(
        "Type", max_length=255, unique=True, help_text="Type of finding (e.g. network)"
    )

    def count_findings(self):
        """
        Return the number of :model:`reporting.Finding` associated with an instance.
        """
        return Finding.objects.filter(finding_type=self).count()

    count = property(count_findings)

    class Meta:
        ordering = ["finding_type"]
        verbose_name = "Finding type"
        verbose_name_plural = "Finding types"

    def __str__(self):
        return f"{self.finding_type}"


class Finding(models.Model):
    """
    Stores an individual finding, related to :model:`reporting.Severity` and :model:`reporting.FindingType`.
    """

    title = models.CharField(
        "Title",
        max_length=255,
        unique=True,
        help_text="Enter a title for this finding that will appear in reports",
    )
    description = models.TextField(
        "Description",
        null=True,
        blank=True,
        help_text="Provide a description for this finding that introduces it",
    )
    impact = models.TextField(
        "Impact",
        help_text="Describe the impact of this finding on the affected entities",
        null=True,
        blank=True,
    )
    mitigation = models.TextField(
        "Mitigation",
        null=True,
        blank=True,
        help_text="Describe how this finding can be resolved or addressed",
    )
    replication_steps = models.TextField(
        "Replication Steps",
        null=True,
        blank=True,
        help_text="Provide an explanation for how the reader may reproduce this finding",
    )
    host_detection_techniques = models.TextField(
        "Host Detection Techniques",
        null=True,
        blank=True,
        help_text="Describe how this finding can be detected on an endpoint - leave blank if this does not apply",
    )
    network_detection_techniques = models.TextField(
        "Network Detection Techniques",
        null=True,
        blank=True,
        help_text="Describe how this finding can be detected on a network - leave blank if this does not apply",
    )
    references = models.TextField(
        "References",
        null=True,
        blank=True,
        help_text="Provide solid references for this finding, such as links to tools and white papers",
    )
    finding_guidance = models.TextField(
        "Finding Guidance",
        null=True,
        blank=True,
        help_text="Provide notes for your team that describes how the finding is intended to be used or edited during editing",
    )
    # Foreign Keys
    severity = models.ForeignKey(
        "Severity",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a severity rating for this finding that reflects its role in a system compromise",
    )
    finding_type = models.ForeignKey(
        "FindingType",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a finding category that fits",
    )

    class Meta:
        ordering = ["severity", "finding_type", "title"]
        verbose_name = "Finding"
        verbose_name_plural = "Findings"

    def get_absolute_url(self):
        return reverse("reporting:finding_detail", args=[str(self.id)])

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class DocType(models.Model):
    """
    Stores an individual document type, related to :model:`reporting.ReportTemplate`.
    """

    doc_type = models.CharField(
        "Document Type",
        max_length=5,
        unique=True,
        help_text="Enter a file extension for a report template filetype",
    )

    class Meta:
        ordering = [
            "doc_type",
        ]
        verbose_name = "Document type"
        verbose_name_plural = "Document types"

    def __str__(self):
        return f"{self.doc_type}"


class ReportTemplate(models.Model):
    """
    Stores an individual report template file, related to :model:`reporting.Report`.
    """

    # Direct template uploads to ``TEMPLATE_LOC`` instead of ``MEDIA``
    template_storage = FileSystemStorage(location=settings.TEMPLATE_LOC)

    document = models.FileField(storage=template_storage, blank=True)
    name = models.CharField(
        "Template Name",
        null=True,
        max_length=255,
        help_text="Provide a name to be used when selecting this template",
    )
    upload_date = models.DateField(
        "Upload Date",
        auto_now=True,
        help_text="Date and time the template was first uploaded",
    )
    last_update = models.DateField(
        "Last Modified",
        auto_now=True,
        help_text="Date and time the report was last modified",
    )
    description = models.TextField(
        "Description",
        blank=True,
        help_text="Provide a description of this template",
    )
    protected = models.BooleanField(
        "Protected",
        default=False,
        help_text="Only administrators can edit this template",
    )
    lint_result = models.TextField(
        "Template Linter Results",
        null=True,
        blank=True,
        help_text="Results returned by the linter for this template",
    )
    changelog = models.TextField(
        "Template Change Log",
        null=True,
        blank=True,
        help_text="Add a line explaining any file changes",
    )
    # Foreign Keys
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    client = models.ForeignKey(
        "rolodex.Client",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        help_text="Template will only be displayed for this client",
    )
    doc_type = models.ForeignKey(
        "reporting.DocType",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Select the filetype for this template",
    )

    class Meta:
        ordering = ["doc_type", "client", "name"]
        verbose_name = "Report template"
        verbose_name_plural = "Report templates"

    def get_absolute_url(self):
        return reverse("reporting:template_file", args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"

    def clean(self, *args, **kwargs):
        super(ReportTemplate, self).clean(*args, **kwargs)
        # Validate here in the model so there is always a file asociated with the entry
        if not self.document:
            raise ValidationError(_("You must provide a template file"), "incomplete")

    @property
    def filename(self):
        return os.path.basename(self.document.name)

    def get_status(self):
        result_code = "unknown"
        if self.lint_result:
            try:
                lint_result = json.loads(self.lint_result)
                result_code = lint_result["result"]
            except json.decoder.JSONDecodeError:
                logger.exception(
                    "Could not decode data in model as JSON: %s", self.lint_result
                )
            except Exception:
                logger.exception(
                    "Encountered an exceptio while trying to decode this as JSON: %s",
                    self.lint_result,
                )
        return result_code


class Report(models.Model):
    """
    Stores an individual report, related to :model:`rolodex.Project` and :model:`users.User`.
    """

    title = models.CharField(
        "Title",
        max_length=255,
        default="New Report",
        help_text="Provide a meaningful title for this report - this is only seen in Ghostwriter",
    )
    creation = models.DateField(
        "Creation Date", auto_now_add=True, help_text="Date the report was created"
    )
    last_update = models.DateField(
        "Last Update", auto_now=True, help_text="Date the report was last touched"
    )
    complete = models.BooleanField(
        "Completed", default=False, help_text="Mark the report as complete"
    )
    archived = models.BooleanField(
        "Archived", default=False, help_text="Mark the report as archived"
    )
    # Foreign Keys
    project = models.ForeignKey(
        "rolodex.Project",
        on_delete=models.CASCADE,
        null=True,
        help_text="Select the project tied to this report",
    )
    docx_template = models.ForeignKey(
        "ReportTemplate",
        related_name="reporttemplate_docx_set",
        on_delete=models.SET_NULL,
        limit_choices_to={
            "doc_type__doc_type__iexact": "docx",
        },
        null=True,
        help_text="Select the Word template to use for this report",
    )
    pptx_template = models.ForeignKey(
        "ReportTemplate",
        related_name="reporttemplate_pptx_set",
        on_delete=models.SET_NULL,
        limit_choices_to={"doc_type__doc_type__iexact": "pptx"},
        null=True,
        help_text="Select the PowerPoint template to use for this report",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )
    delivered = models.BooleanField(
        "Delivered", default=False, help_text="Delivery status of the report"
    )

    class Meta:
        ordering = ["-creation", "-last_update", "project"]
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def get_absolute_url(self):
        return reverse("reporting:report_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.title}"


class ReportFindingLink(models.Model):
    """
    Stores an individual copy of a finding added to a :model:`reporting.Report` with
    :model:`reporting.Severity`, :model:`reporting.FindingType`, and :model:`users.User`.
    """

    title = models.CharField(
        "Title",
        max_length=255,
        help_text="Enter a title for this finding that will appear in the reports",
    )
    position = models.IntegerField(
        "Report Position",
        default=1,
    )
    affected_entities = models.TextField(
        "Affected Entities",
        null=True,
        blank=True,
        help_text="Provide a list of the affected entities (e.g. domains, hostnames, IP addresses)",
    )
    description = models.TextField(
        "Description",
        null=True,
        blank=True,
        help_text="Provide a description for this finding that introduces it",
    )
    impact = models.TextField(
        "Impact",
        null=True,
        blank=True,
        help_text="Describe the impact of this finding on the affected entities",
    )
    mitigation = models.TextField(
        "Mitigation",
        null=True,
        blank=True,
        help_text="Describe how this finding can be resolved or addressed",
    )
    replication_steps = models.TextField(
        "Replication Steps",
        null=True,
        blank=True,
        help_text="Provide an explanation for how the reader may reproduce this finding",
    )
    host_detection_techniques = models.TextField(
        "Host Detection Techniques",
        null=True,
        blank=True,
        help_text="Describe how this finding can be detected on an endpoint - leave blank if this does not apply",
    )
    network_detection_techniques = models.TextField(
        "Network Detection Techniques",
        null=True,
        blank=True,
        help_text="Describe how this finding can be detected on a network - leave blank if this does not apply",
    )
    references = models.TextField(
        "References",
        null=True,
        blank=True,
        help_text="Provide solid references for this finding, such as links to reference materials, tooling, and white papers",
    )
    finding_guidance = models.TextField(
        "Finding Guidance",
        null=True,
        blank=True,
        help_text="Provide notes for your team that describes this finding within this report",
    )
    complete = models.BooleanField(
        "Completed",
        default=False,
        help_text="Mark the finding as ready for a QA review",
    )
    # Foreign Keys
    severity = models.ForeignKey(
        "Severity",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a severity rating for this finding that reflects its role in a system compromise",
    )
    finding_type = models.ForeignKey(
        "FindingType",
        on_delete=models.PROTECT,
        null=True,
        help_text="Select a finding category that fits",
    )
    report = models.ForeignKey("Report", on_delete=models.CASCADE, null=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Assign the task of editing this finding to a specific operator - defaults to the operator that added it to the report",
    )

    class Meta:
        ordering = ["report", "severity__weight", "position"]
        verbose_name = "Report finding"
        verbose_name_plural = "Report findings"

    def __str__(self):
        return self.title

    def get_evidence_list(self):
        upload_path = os.path.join(
            settings.MEDIA_ROOT, str(self.report.id), str(self.title)
        )
        evidence_files = []
        if not os.path.exists(upload_path):
            return evidence_files
        else:
            for root, dirs, files in os.walk(upload_path):
                for filename in files:
                    if not filename == ".DS_Store":
                        evidence_files.append(filename)
            return evidence_files


class Evidence(models.Model):
    """
    Stores an individual evidence file, related to :model:`reporting.ReportFindingLink`
    and :model:`users.User`.
    """

    def set_upload_destination(instance, filename):
        """
        Sets the `upload_to` destination to the evidence folder for the associated report ID.
        """
        return os.path.join("evidence", str(instance.finding.report.id), filename)

    document = models.FileField(
        upload_to=set_upload_destination,
        validators=[validate_evidence_extension],
        blank=True,
    )
    friendly_name = models.CharField(
        "Friendly Name",
        null=True,
        max_length=255,
        help_text="Provide a simple name to be used to reference this evidence",
    )
    upload_date = models.DateField(
        "Upload Date",
        auto_now=True,
        help_text="Date and time the evidence was uploaded",
    )
    caption = models.CharField(
        "Caption",
        max_length=255,
        blank=True,
        help_text="Provide a one line caption to be used in the report - keep it brief",
    )
    description = models.TextField(
        "Description",
        blank=True,
        help_text="Describe this evidence to your team",
    )
    # Foreign Keys
    finding = models.ForeignKey("ReportFindingLink", on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["finding", "document"]
        verbose_name = "Evidence"
        verbose_name_plural = "Evidence"

    def get_absolute_url(self):
        return reverse("reporting:evidence_file", args=[str(self.id)])

    def __str__(self):
        return self.document.name

    def clean(self, *args, **kwargs):
        super(Evidence, self).clean(*args, **kwargs)
        # Validate here in the model so there is always a file asociated with the entry
        if not self.document:
            raise ValidationError(_("You must provide an evidence file"), "incomplete")

    @property
    def filename(self):
        return os.path.basename(self.document.name)


class Archive(models.Model):
    """
    Stores an individual archived report, related to :model:`rolodex.Project.
    """

    report_archive = models.FileField()
    project = models.ForeignKey("rolodex.Project", on_delete=models.CASCADE, null=True)

    @property
    def filename(self):
        return os.path.basename(self.report_archive.name)

    class Meta:
        ordering = ["project"]
        verbose_name = "Archived report"
        verbose_name_plural = "Archived reports"

    def __str__(self):
        return self.report_archive.name


class FindingNote(models.Model):
    """
    Stores an individual finding note, related to :model:`reporting.Finding`.
    """

    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Provide additional information about the finding",
    )
    # Foreign Keys
    finding = models.ForeignKey("Finding", on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["finding", "-timestamp"]
        verbose_name = "Finding note"
        verbose_name_plural = "Finding notes"

    def __str__(self):
        return f"{self.finding} {self.timestamp}: {self.note}"


class LocalFindingNote(models.Model):
    """
    Stores an individual finding note in a report, related to :model:`reporting.ReportFindingLink`.
    """

    timestamp = models.DateField(
        "Timestamp", auto_now_add=True, help_text="Creation timestamp"
    )
    note = models.TextField(
        "Notes",
        null=True,
        blank=True,
        help_text="Provide additional information about the finding",
    )
    # Foreign Keys
    finding = models.ForeignKey("ReportFindingLink", on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True
    )

    class Meta:
        ordering = ["finding", "-timestamp"]
        verbose_name = "Local finding note"
        verbose_name_plural = "Local finding notes"

    def __str__(self):
        return f"{self.finding} {self.timestamp}: {self.note}"
