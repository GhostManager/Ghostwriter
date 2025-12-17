"""This contains all the database models used by the Reporting application."""

# Standard Libraries
import json
import logging
import os
from collections import OrderedDict
from decimal import Decimal

# Django Imports
from django.conf import settings
from django.core.files.storage import FileSystemStorage
from django.core.validators import MinValueValidator
from django.db import models
from django.db.models import Q
from django.db.utils import OperationalError, ProgrammingError
from django.urls import reverse

# 3rd Party Libraries
from bs4 import BeautifulSoup
from cvss import CVSS3, CVSS4
from taggit.managers import TaggableManager

# Ghostwriter Libraries
from ghostwriter.reporting.validators import validate_evidence_extension

# Using __name__ resolves to ghostwriter.reporting.models
logger = logging.getLogger(__name__)


class Severity(models.Model):
    """Stores an individual severity rating."""

    def get_default_weight():
        """
        Return the default weight for a new :model:`reporting.Severity` instance.
        """
        return Severity.objects.count() + 1

    severity = models.CharField(
        "Severity",
        max_length=255,
        unique=True,
        help_text="Name for this severity rating (e.g., High, Low)",
    )
    weight = models.IntegerField(
        "Severity Weight",
        default=get_default_weight,
        validators=[MinValueValidator(1)],
        help_text="Weight for sorting severity categories in reports (lower numbers are more severe)",
    )
    color = models.CharField(
        "Severity Color",
        max_length=6,
        default="7A7A7A",
        help_text="Six character hex color code associated with this severity for reports (e.g., FF7E79)",
    )

    def count_findings(self):
        """Return the number of :model:`reporting.Finding` associated with an instance."""
        return Finding.objects.filter(severity=self).count()

    @property
    def color_rgb(self):
        """Return the severity color code as a list of RGB values."""
        return tuple(int(self.color[i : i + 2], 16) for i in (0, 2, 4))

    @property
    def color_hex(self):
        """Return the severity color code as a list of hexadecimal."""
        n = 2
        return tuple(hex(int(self.color[i : i + n], 16)) for i in range(0, len(self.color), n))

    count = property(count_findings)

    class Meta:
        ordering = ["weight", "severity"]
        verbose_name = "Severity rating"
        verbose_name_plural = "Severity ratings"

    def __str__(self):
        return f"{self.severity}"

    def clean(self):
        old_entry = None
        if self.pk:
            try:
                old_entry = self.__class__.objects.get(pk=self.pk)
            except self.__class__.DoesNotExist:
                pass

        # A ``pre_save`` Signal is connected to this model and runs this ``clean()`` method
        # whenever ``save()`` is called

        # The following adjustments use the queryset ``update()`` method (direct SQL statement)
        # instead of calling ``save()`` on the individual model instance
        # This avoids forever looping through position changes

        severity_queryset = self.__class__.objects.all()
        if old_entry:
            old_weight = old_entry.weight
            if old_weight != self.weight:
                self.weight = max(self.weight, 1)
                if self.weight > severity_queryset.count():
                    self.weight = severity_queryset.count()

                counter = 1
                if severity_queryset:
                    for category in severity_queryset:
                        if not self.pk == category.pk:
                            if self.weight == counter:
                                counter += 1
                            severity_queryset.filter(id=category.id).update(weight=counter)
                            counter += 1
                        else:
                            pass
                else:
                    self.weight = 1
        else:
            self.weight = severity_queryset.count() + 1


class FindingType(models.Model):
    """Stores an individual finding type."""

    finding_type = models.CharField("Type", max_length=255, unique=True, help_text="Type of finding (e.g. network)")

    def count_findings(self):
        """Return the number of :model:`reporting.Finding` associated with an instance."""
        return Finding.objects.filter(finding_type=self).count()

    count = property(count_findings)

    class Meta:
        ordering = ["finding_type"]
        verbose_name = "Finding type"
        verbose_name_plural = "Finding types"

    def __str__(self):
        return f"{self.finding_type}"


class Finding(models.Model):
    """Stores an individual finding, related to :model:`reporting.Severity` and :model:`reporting.FindingType`."""

    title = models.TextField(
        "Title",
        blank=True,
        help_text="Enter a title for this finding that will appear in reports",
    )
    description = models.TextField(
        "Description",
        blank=True,
        default="",
        help_text="Provide a description for this finding that introduces it",
    )
    impact = models.TextField(
        "Impact",
        blank=True,
        default="",
        help_text="Describe the impact of this finding on the affected entities",
    )
    mitigation = models.TextField(
        "Mitigation",
        blank=True,
        default="",
        help_text="Describe how this finding can be resolved or addressed",
    )
    replication_steps = models.TextField(
        "Replication Steps",
        blank=True,
        default="",
        help_text="Provide an explanation for how the reader may reproduce this finding",
    )
    host_detection_techniques = models.TextField(
        "Host Detection Techniques",
        blank=True,
        default="",
        help_text="Describe how this finding can be detected on an endpoint - leave blank if this does not apply",
    )
    network_detection_techniques = models.TextField(
        "Network Detection Techniques",
        blank=True,
        default="",
        help_text="Describe how this finding can be detected on a network - leave blank if this does not apply",
    )
    references = models.TextField(
        "References",
        blank=True,
        default="",
        help_text="Provide solid references for this finding, such as links to tools and white papers",
    )
    finding_guidance = models.TextField(
        "Finding Guidance",
        blank=True,
        default="",
        help_text="Provide notes for your team that describes how the finding is intended to be used or edited during editing",
    )
    cvss_score = models.FloatField(
        "CVSS Score",
        blank=True,
        null=True,
        help_text="Set the CVSS score for this finding",
    )
    cvss_vector = models.CharField(
        "CVSS Vector",
        blank=True,
        default="",
        max_length=255,
        help_text="Set the CVSS vector for this finding",
    )
    tags = TaggableManager(blank=True)
    # Foreign Keys
    severity = models.ForeignKey(
        "Severity",
        default=1,
        on_delete=models.PROTECT,
        help_text="Select a severity rating for this finding that reflects its role in a system compromise",
    )
    finding_type = models.ForeignKey(
        "FindingType",
        default=1,
        on_delete=models.PROTECT,
        help_text="Select a finding category that fits",
    )

    extra_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ["severity", "-cvss_score", "finding_type", "title"]
        verbose_name = "Finding"
        verbose_name_plural = "Findings"

    def get_absolute_url(self):
        return reverse("reporting:finding_detail", args=[str(self.id)])

    def get_edit_url(self):
        return reverse("reporting:finding_update", kwargs={"pk": self.pk})

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged or user.enable_finding_create

    def user_can_view(self, user) -> bool:
        return True

    @classmethod
    def user_viewable(cls, user):
        return cls.objects.all()

    def user_can_edit(self, user) -> bool:
        return user.is_privileged or user.enable_finding_edit

    def user_can_delete(self, user) -> bool:
        return user.is_privileged or user.enable_finding_delete

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return "(Untitled Finding)"

    def __str__(self):
        return f"[{self.severity}] {self.title}"


class DocType(models.Model):
    """Stores an individual document type, related to :model:`reporting.ReportTemplate`."""

    doc_type = models.CharField(
        "Document Type",
        max_length=20,
        unique=True,
        help_text="Enter a file extension for a report template filetype",
    )

    extension = models.CharField(
        "Document Extension",
        max_length=10,
    )

    name = models.CharField(
        "Name",
        max_length=255,
    )

    class Meta:
        ordering = [
            "doc_type",
        ]
        verbose_name = "Document type"
        verbose_name_plural = "Document types"

    def __str__(self):
        return f"{self.name}"


class ReportTemplate(models.Model):
    """Stores an individual report template file, related to :model:`reporting.Report`."""

    # Direct template uploads to ``TEMPLATE_LOC`` instead of ``MEDIA``
    template_storage = FileSystemStorage(location=settings.TEMPLATE_LOC)

    document = models.FileField(storage=template_storage, blank=True)
    name = models.CharField(
        "Template Name",
        max_length=255,
        help_text="Provide a name to be used when selecting this template",
    )
    upload_date = models.DateField(
        "Upload Date",
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
    lint_result = models.JSONField(
        "Template Linter Results",
        null=True,
        blank=True,
        help_text="Results returned by the linter for this template in JSON format",
    )
    changelog = models.TextField(
        "Template Change Log",
        default="",
        blank=True,
        help_text="Add a line explaining any file changes",
    )
    landscape = models.BooleanField(
        "Landscape Orientation",
        default=False,
        help_text="Flag this document as landscape orientation",
    )
    filename_override = models.CharField(
        "Filename Template",
        max_length=255,
        default="",
        blank=True,
        help_text="Jinja2 template. All template variables are available, plus {{now}} and {{company_name}}. The file extension is added to this. If blank, the admin-provided default will be used.",
    )
    bloodhound_heading_offset = models.SmallIntegerField(
        "BloodHound Heading Offset",
        default=0,
        blank=True,
        help_text="Headings in BloodHound finding descriptions will have their level offset by this amount"
    )
    contains_bloodhound_data = models.BooleanField(
        "Contains BloodHound Data",
        default=False,
        help_text="Set to true if this template is designed to include data from BloodHound",
    )
    tags = TaggableManager(blank=True)
    # Foreign Keys
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
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
        help_text="Select the file type and target for this template",
    )
    p_style = models.CharField(
        "New Paragraph Style",
        max_length=255,
        default="",
        blank=True,
        help_text="Provide the name of a style in your template to use for new paragraphs (Word only).",
    )
    evidence_image_width = models.FloatField(
        "Evidence Image Width",
        default=6.5,
        blank=True,
        validators=[MinValueValidator(0)],
        help_text="The width of inserted evidence images, in inches (Word only)",
    )

    class Meta:
        ordering = ["doc_type", "client", "name"]
        verbose_name = "Report template"
        verbose_name_plural = "Report templates"

    def get_absolute_url(self):
        return reverse("reporting:template_detail", args=[str(self.id)])

    def __str__(self):
        return f"{self.name}"

    @property
    def filename(self):
        return os.path.basename(self.document.name)

    def get_status(self):
        result_code = "unknown"
        if self.lint_result:
            try:
                result_code = self.lint_result["result"]
            except json.decoder.JSONDecodeError:  # pragma: no cover
                logger.exception("Could not decode data in model as JSON: %r", self.lint_result)
            except Exception:  # pragma: no cover
                logger.exception(
                    "Encountered an exception while trying to decode this as JSON: %r",
                    self.lint_result,
                )
        return result_code

    def exporter(self, object, **kwargs):
        """
        Returns an ExportBase subclass instance based on the template and the passed-in object.
        Call the `run` method to generate the corresponding report.
        """
        # Import in function to avoid circular references
        # Ghostwriter Libraries
        from ghostwriter.rolodex.models import Project

        if self.doc_type.doc_type == "docx":
            assert isinstance(object, Report)
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx

            return ExportReportDocx(
                object,
                template_loc=self.document.path,
                p_style=self.p_style,
                evidence_image_width=self.evidence_image_width,
                **kwargs
            )
        if self.doc_type.doc_type == "project_docx":
            assert isinstance(object, Project)
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.project.docx import ExportProjectDocx

            return ExportProjectDocx(
                object,
                report_template=self,
                **kwargs
            )
        if self.doc_type.doc_type == "pptx" and isinstance(object, Report):
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx

            return ExportReportPptx(object, report_template=self, **kwargs)
        if self.doc_type.doc_type == "pptx" and isinstance(object, Project):
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.project.pptx import ExportProjectPptx

            return ExportProjectPptx(object, report_template=self, **kwargs)
        raise RuntimeError(
            f"Template for doc_type {self.doc_type.doc_type} and object {object} not implemented. Either this is a bug or an admin messed with the database."
        )

    def lint(self):
        """
        Lints a `ReportTemplate`. Sets `self.lint_results` and returns a `results` object
        for the frontend. Be sure to save the template afterwards.
        """

        try:
            warnings, errors = self.lint_raw()
        except Exception:
            logging.exception("Could not lint template %d (%s)", self.pk, self.document.path)
            warnings = []
            errors = ["Unexpected error while linting template"]

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
        self.lint_result = results.copy()

        if results["result"] == "success":
            results["message"] = "Template linter returned results with no errors or warnings."
        else:
            results["message"] = "Template linter returned results with issues that require attention."
        return results

    def lint_raw(self):
        """
        Runs the linter and returns the results. Does not set the template's `lint_results`.
        """
        # Import in function to avoid circular references
        if self.doc_type.doc_type == "docx":
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.report.docx import ExportReportDocx

            return ExportReportDocx.lint(report_template=self)
        if self.doc_type.doc_type == "project_docx":
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.project.docx import ExportProjectDocx

            return ExportProjectDocx.lint(report_template=self)
        if self.doc_type.doc_type == "pptx":
            # Report PPTX exporter exports more content, so use it to lint
            # Ghostwriter Libraries
            from ghostwriter.modules.reportwriter.report.pptx import ExportReportPptx

            return ExportReportPptx.lint(template_loc=self.document.path)
        raise RuntimeError(
            f"Lint for doc_type {self.doc_type.doc_type} not implemented. Either this is a bug or an admin messed with the database."
        )


class Report(models.Model):
    """Stores an individual report, related to :model:`rolodex.Project` and :model:`users.User`."""

    title = models.CharField(
        "Title",
        max_length=255,
        default="New Report",
        help_text="Provide a meaningful title for this report - this is only seen in Ghostwriter",
    )
    creation = models.DateField("Creation Date", auto_now_add=True, help_text="Date the report was created")
    last_update = models.DateField("Last Update", auto_now=True, help_text="Date the report was last touched")
    complete = models.BooleanField("Completed", default=False, help_text="Mark the report as complete")
    archived = models.BooleanField("Archived", default=False, help_text="Mark the report as archived")
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)
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
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)
    delivered = models.BooleanField("Delivered", default=False, help_text="Delivery status of the report")
    include_bloodhound_data = models.BooleanField(default=False, help_text="Include data from BloodHound in the report context")

    class Meta:
        ordering = ["-creation", "-last_update", "project"]
        verbose_name = "Report"
        verbose_name_plural = "Reports"

    def get_absolute_url(self):
        return reverse("reporting:report_detail", args=[str(self.id)])

    @classmethod
    def clear_incorrect_template_defaults(cls, updated_template: ReportTemplate):
        """
        Find ReportTemplates that use the specified updated_template improperly and clears it.

        Specifically, if the template is for an incorrect document type that its used in, or if
        the template's client does not match the report's project's client, it will be cleared.
        """
        if updated_template.doc_type.doc_type == "docx":
            filter_docx = Q(pk__in=[])  # Always false
            filter_pptx = Q(pptx_template=updated_template)
        elif updated_template.doc_type.doc_type == "pptx":
            filter_docx = Q(docx_template=updated_template)
            filter_pptx = Q(pk__in=[])  # Always false
        else:
            filter_docx = Q(docx_template=updated_template)
            filter_pptx = Q(pptx_template=updated_template)

        if updated_template.client is not None:
            q_mismatched = ~Q(project__client__id=updated_template.client.id)
            filter_docx = filter_docx | (Q(docx_template__id=updated_template.id) & q_mismatched)
            filter_pptx = filter_pptx | (Q(pptx_template__id=updated_template.id) & q_mismatched)

        cls.objects.filter(filter_docx).update(docx_template=None)
        cls.objects.filter(filter_pptx).update(pptx_template=None)

    def all_evidences(self):
        """
        Returns a queryset of all evidences attached to the report - both directly attached and through the findings.
        """
        return Evidence.objects.filter(Q(report__id=self.pk) | Q(finding__report__id=self.pk))

    def __str__(self):
        return f"{self.title}"

    @classmethod
    def user_can_create(cls, user, project) -> bool:
        return project.user_can_edit(user)

    def user_can_view(self, user) -> bool:
        return self.project.user_can_view(user)

    @classmethod
    def user_viewable(cls, user):
        from ghostwriter.rolodex.models import Project
        if user.is_privileged:
            return cls.objects.all()
        return cls.objects.filter(project__in=Project.user_viewable(user))

    def user_can_edit(self, user) -> bool:
        return self.project.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.project.user_can_edit(user)


class ReportFindingLink(models.Model):
    """
    Stores an individual copy of a finding added to a :model:`reporting.Report` with
    :model:`reporting.Severity`, :model:`reporting.FindingType`, and :model:`users.User`.
    """

    title = models.TextField(
        "Title",
        blank=True,
        help_text="Enter a title for this finding that will appear in the reports",
    )
    position = models.IntegerField(
        "Report Position",
        default=1,
        validators=[MinValueValidator(1)],
    )
    affected_entities = models.TextField(
        "Affected Entities",
        default="",
        blank=True,
        help_text="Provide a list of the affected entities (e.g. domains, hostnames, IP addresses)",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a description for this finding that introduces it",
    )
    impact = models.TextField(
        "Impact",
        default="",
        blank=True,
        help_text="Describe the impact of this finding on the affected entities",
    )
    mitigation = models.TextField(
        "Mitigation",
        default="",
        blank=True,
        help_text="Describe how this finding can be resolved or addressed",
    )
    replication_steps = models.TextField(
        "Replication Steps",
        default="",
        blank=True,
        help_text="Provide an explanation for how the reader may reproduce this finding",
    )
    host_detection_techniques = models.TextField(
        "Host Detection Techniques",
        default="",
        blank=True,
        help_text="Describe how this finding can be detected on an endpoint - leave blank if this does not apply",
    )
    network_detection_techniques = models.TextField(
        "Network Detection Techniques",
        default="",
        blank=True,
        help_text="Describe how this finding can be detected on a network - leave blank if this does not apply",
    )
    references = models.TextField(
        "References",
        default="",
        blank=True,
        help_text="Provide solid references for this finding, such as links to reference materials, tooling, and white papers",
    )
    finding_guidance = models.TextField(
        "Finding Guidance",
        default="",
        blank=True,
        help_text="Provide notes for your team that describes this finding within this report",
    )
    complete = models.BooleanField(
        "Completed",
        default=False,
        help_text="Mark the finding as ready for a QA review",
    )
    added_as_blank = models.BooleanField(
        "Added as Blank",
        default=False,
        help_text="Identify a finding that was created for this report instead of copied from the library",
    )
    tags = TaggableManager(blank=True)
    # Foreign Keys
    severity = models.ForeignKey(
        "Severity",
        default=1,
        on_delete=models.PROTECT,
        help_text="Select a severity rating for this finding that reflects its role in a system compromise",
    )
    finding_type = models.ForeignKey(
        "FindingType",
        default=1,
        on_delete=models.PROTECT,
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
    cvss_score = models.FloatField(
        "CVSS Score",
        blank=True,
        null=True,
        help_text="Set the CVSS score for this finding",
    )
    cvss_vector = models.CharField(
        "CVSS Vector",
        blank=True,
        default="",
        max_length=255,
        help_text="Set the CVSS vector for this finding",
    )
    extra_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ["report", "severity__weight", "position"]
        verbose_name = "Report finding"
        verbose_name_plural = "Report findings"
        _extra_fields_model = Finding

    def __str__(self):
        return f"{self.display_title} on {self.report}"

    def get_absolute_url(self):
        return reverse("reporting:report_detail", kwargs={"pk": self.report.pk}) + "#findings"

    def get_edit_url(self):
        return reverse("reporting:local_edit", kwargs={"pk": self.pk})

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return "(Untitled Finding)"

    @classmethod
    def user_can_create(cls, user, report) -> bool:
        return report.user_can_edit(user)

    def user_can_view(self, user) -> bool:
        return self.report.user_can_view(user)

    @classmethod
    def user_viewable(cls, user):
        return cls.objects.filter(report__in=Report.user_viewable(user))

    def user_can_edit(self, user) -> bool:
        return self.report.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.report.user_can_edit(user)


    @property
    def cvss_data(self):
        if "3.1" in self.cvss_vector:
            cvss_version = "3.1"
            cvss_obj = CVSS3(self.cvss_vector)
            cvss_scores = cvss_obj.scores()
            cvss_severities = cvss_obj.severities()
        elif "4.0" in self.cvss_vector:
            cvss_version = "4.0"
            cvss_obj = CVSS4(self.cvss_vector)
            cvss_scores = cvss_obj.base_score
            cvss_severities = cvss_obj.severity
        else:
            cvss_version = "Unknown"
            cvss_scores = ""
            cvss_severities = ""

        cvss_severity_colors = ""
        if cvss_severities:
            if cvss_version == "3.1":
                cvss_severity_colors = []
                for sev in cvss_severities:
                    obj = Severity.objects.filter(severity__iexact=sev)
                    if obj.exists():
                        obj = obj.first()
                        cvss_severity_colors.append(obj.color)
                    else:
                        cvss_severity_colors.append("7A7A7A")
            elif cvss_version == "4.0":
                obj = Severity.objects.filter(severity__iexact=cvss_severities)
                if obj.exists():
                    obj = obj.first()
                    cvss_severity_colors = obj.color
                else:
                    cvss_severity_colors = "7A7A7A"

        return cvss_version, cvss_scores, cvss_severities, cvss_severity_colors

    @property
    def exists_in_finding_library(self):
        """
        Returns True if the finding exists in the finding library. If a finding was not added as a blank finding,
        it is assumed to exist in the library.
        """
        if not self.added_as_blank:
            return True
        return Finding.objects.filter(title=self.title).exists()



def set_evidence_upload_destination(this, filename):
    """Sets the `upload_to` destination to the evidence folder for the associated report ID."""
    return os.path.join("evidence", str(this.associated_report.id), filename)


class Evidence(models.Model):
    """
    Stores an individual evidence file, related to :model:`reporting.ReportFindingLink`
    and :model:`users.User`.
    """

    document = models.FileField(
        upload_to=set_evidence_upload_destination,
        validators=[validate_evidence_extension],
        blank=True,
        max_length=255,
    )
    friendly_name = models.CharField(
        "Friendly Name",
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
    tags = TaggableManager(blank=True)
    # Foreign Keys
    finding = models.ForeignKey("ReportFindingLink", on_delete=models.CASCADE, null=True, blank=True)
    report = models.ForeignKey("Report", on_delete=models.CASCADE, null=True, blank=True)
    uploaded_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["finding", "report", "document"]
        verbose_name = "Evidence"
        verbose_name_plural = "Evidence"

        constraints = [
            models.CheckConstraint(
                name="%(app_label)s_%(class)s_finding_or_report",
                check=(
                    models.Q(finding__isnull=True, report__isnull=False)
                    | models.Q(finding__isnull=False, report__isnull=True)
                ),
            )
        ]

    def get_absolute_url(self):
        return reverse("reporting:evidence_detail", args=[str(self.id)])

    @property
    def associated_report(self):
        """
        The report associated with this evidence, either directly through `self.report` or indirectly through
        `self.finding.report`.
        """
        if self.finding:
            return self.finding.report
        return self.report

    def __str__(self):
        return f"{self.friendly_name} @ {self.document.name}"

    @property
    def filename(self):
        return os.path.basename(self.document.name)


class Archive(models.Model):
    """Stores an individual archived report, related to :model:`rolodex.Project."""

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
        return f"{self.report_archive.name}"


class FindingNote(models.Model):
    """Stores an individual finding note, related to :model:`reporting.Finding`."""

    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        blank=True,
        default="",
        help_text="Provide additional information about the finding",
    )
    # Foreign Keys
    finding = models.ForeignKey("Finding", on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["finding", "-timestamp"]
        verbose_name = "Finding note"
        verbose_name_plural = "Finding notes"

    def __str__(self):
        return f"{self.finding} {self.timestamp}: {self.note}"


class LocalFindingNote(models.Model):
    """Stores an individual finding note in a report, related to :model:`reporting.ReportFindingLink`."""

    timestamp = models.DateField("Timestamp", auto_now_add=True, help_text="Creation timestamp")
    note = models.TextField(
        "Notes",
        default="",
        blank=True,
        help_text="Provide additional information about the finding",
    )
    # Foreign Keys
    finding = models.ForeignKey("ReportFindingLink", on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        ordering = ["finding", "-timestamp"]
        verbose_name = "Local finding note"
        verbose_name_plural = "Local finding notes"

    def __str__(self):
        return f"{self.finding} {self.timestamp}: {self.note}"


class Observation(models.Model):
    """
    An observation.

    Similar to a finding, but more generic. Can be used for positive observations or other things.
    """

    title = models.TextField(
        "Title",
        default="",
        blank=True,
        help_text="Enter a title for this finding that will appear in reports",
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a description for this observation that introduces it",
    )
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)

    class Meta:
        ordering = ["title"]
        verbose_name = "Observation"
        verbose_name_plural = "Observations"

    def __str__(self):
        return self.display_title

    def get_absolute_url(self):
        return reverse("reporting:observation_detail", args=[str(self.id)])

    @property
    def display_title(self) -> str:
        if self.title:
            return self.title
        return "(Untitled Observation)"

    @classmethod
    def user_can_create(cls, user) -> bool:
        return user.is_privileged or user.enable_observation_create

    def user_can_view(self, user) -> bool:
        return True

    @classmethod
    def user_viewable(cls, user):
        return cls.objects.all()

    def user_can_edit(self, user) -> bool:
        return user.is_privileged or user.enable_observation_edit

    def user_can_delete(self, user) -> bool:
        return user.is_privileged or user.enable_observation_delete


class ReportObservationLink(models.Model):
    title = models.CharField(
        "Title",
        max_length=255,
        help_text="Enter a title for this observation that will appear in the reports",
    )
    position = models.IntegerField(
        "Report Position",
        default=1,
        validators=[MinValueValidator(1)],
    )
    description = models.TextField(
        "Description",
        default="",
        blank=True,
        help_text="Provide a description for this observation that introduces it",
    )
    added_as_blank = models.BooleanField(
        "Added as Blank",
        default=False,
        help_text="Identify an observation that was created for this report instead of copied from the library",
    )
    tags = TaggableManager(blank=True)
    extra_fields = models.JSONField(default=dict)

    # Foreign Keys
    report = models.ForeignKey("Report", on_delete=models.CASCADE, null=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text="Assign the task of editing this observation to a specific operator - defaults to the operator that added it to the report",
    )

    class Meta:
        ordering = ["report", "position"]
        verbose_name = "Report observation"
        verbose_name_plural = "Report observations"
        _extra_fields_model = Observation

    def __str__(self):
        return str(self.title)

    @classmethod
    def user_can_create(cls, user, report: Report) -> bool:
        return Observation.user_can_create(user) and report.user_can_edit(user)

    def user_can_view(self, user) -> bool:
        return self.report.user_can_view(user)

    @classmethod
    def user_viewable(cls, user):
        return cls.objects.filter(report__in=Report.user_viewable(user))

    def user_can_edit(self, user) -> bool:
        return self.report.user_can_edit(user)

    def user_can_delete(self, user) -> bool:
        return self.report.user_can_edit(user)


class PasswordComplianceMapping(models.Model):
    """Store workbook password policy compliance rules."""

    DATA_TYPE_NUMERIC = "numeric"
    DATA_TYPE_STRING = "string"

    DATA_TYPE_CHOICES = (
        (DATA_TYPE_NUMERIC, "Numeric"),
        (DATA_TYPE_STRING, "String"),
    )

    setting = models.CharField(
        "Password setting",
        max_length=64,
        unique=True,
        help_text="Name of the password policy setting captured from workbook data.",
    )
    data_type = models.CharField(
        "Value type",
        max_length=16,
        choices=DATA_TYPE_CHOICES,
        default=DATA_TYPE_NUMERIC,
        help_text="How the policy value should be interpreted when evaluating compliance.",
    )
    rule = models.JSONField(
        "Non-compliance rule",
        default=dict,
        help_text=(
            "Definition describing when the password setting is considered out of compliance. "
            "Rules may include logical groupings (any/all) and comparison operators."
        ),
    )

    class Meta:
        ordering = ["setting"]
        verbose_name = "Password setting compliance rule"
        verbose_name_plural = "Password Setting Compliance matrix"

    def __str__(self):
        return self.setting

    @property
    def serialized_rule(self):
        """Return the stored rule with a guaranteed dictionary shape."""

        return self.rule if isinstance(self.rule, dict) else {}


class ScopingWeightCategory(models.Model):
    """Store configurable weights for each project scoping category."""

    DEFAULT_SCOPING_WEIGHTS = OrderedDict(
        (
            (
                "external",
                OrderedDict(
                    (
                        ("nexpose", Decimal("0.5")),
                        ("web", Decimal("0.4")),
                        ("dns", Decimal("0.05")),
                        ("osint", Decimal("0.05")),
                    )
                ),
            ),
            (
                "internal",
                OrderedDict(
                    (
                        ("nexpose", Decimal("0.5")),
                        ("endpoint", Decimal("0.27")),
                        ("snmp", Decimal("0.12")),
                        ("sql", Decimal("0.11")),
                    )
                ),
            ),
            (
                "iam",
                OrderedDict((("ad", Decimal("0.6")), ("password", Decimal("0.4")))),
            ),
            (
                "wireless",
                OrderedDict((("walkthru", Decimal("0.5")), ("segmentation", Decimal("0.5")))),
            ),
            (
                "firewall",
                OrderedDict((("configuration", Decimal("0.6")), ("os", Decimal("0.4")))),
            ),
            (
                "cloud",
                OrderedDict(
                    (
                        ("iam_management", Decimal("0.4")),
                        ("cloud_management", Decimal("0.4")),
                        ("system_configuration", Decimal("0.2")),
                    )
                ),
            ),
        )
    )

    key = models.SlugField(
        "Category Key",
        max_length=32,
        unique=True,
        help_text="Identifier that matches keys in the project scoping payload (e.g., external)",
    )
    label = models.CharField("Display Label", max_length=255, help_text="Human-friendly category name")
    position = models.PositiveIntegerField(
        "Display Order",
        default=0,
        help_text="Control how categories and their weights are displayed in the admin",
    )

    class Meta:
        ordering = ["position", "label"]
        verbose_name = "Scoping weight category"
        verbose_name_plural = "Scoping weight categories"

    def __str__(self):
        return self.label

    @classmethod
    def get_weight_map(cls):
        """Return configured scoping weights, falling back to defaults when needed."""

        try:
            categories = cls.objects.prefetch_related("options").order_by("position", "pk")
        except (ProgrammingError, OperationalError):  # pragma: no cover - table not ready
            return OrderedDict(
                (key, OrderedDict(value)) for key, value in cls.DEFAULT_SCOPING_WEIGHTS.items()
            )

        mapping: "OrderedDict[str, OrderedDict[str, Decimal]]" = OrderedDict()
        for category in categories:
            option_map: "OrderedDict[str, Decimal]" = OrderedDict(
                (option.key, option.weight)
                for option in category.options.all().order_by("position", "pk")
            )
            if option_map:
                mapping[category.key] = option_map

        if not mapping:
            return OrderedDict(
                (key, OrderedDict(value)) for key, value in cls.DEFAULT_SCOPING_WEIGHTS.items()
            )
        return mapping


class ScopingWeightOption(models.Model):
    """Represent an individual scoping option weight within a category."""

    category = models.ForeignKey(
        ScopingWeightCategory,
        on_delete=models.CASCADE,
        related_name="options",
    )
    key = models.SlugField(
        "Option Key",
        max_length=32,
        help_text="Identifier that matches a specific scoping option (e.g., nexpose)",
    )
    label = models.CharField("Display Label", max_length=255, help_text="Human-friendly option name")
    weight = models.DecimalField(
        "Base Weight",
        max_digits=5,
        decimal_places=4,
        validators=[MinValueValidator(Decimal("0"))],
        help_text="Relative weight to use when this option is in scope (values are normalized per category)",
    )
    position = models.PositiveIntegerField(
        "Display Order",
        default=0,
        help_text="Control how options are listed under their category",
    )

    class Meta:
        unique_together = ("category", "key")
        ordering = ["category", "position", "label"]
        verbose_name = "Scoping weight option"
        verbose_name_plural = "Scoping weight options"

    def __str__(self):
        return f"{self.category}: {self.label}"


class GradeRiskMapping(models.Model):
    """Map a workbook letter grade to a report risk level."""

    GRADE_CHOICES = (
        ("A", "A"),
        ("A-", "A-"),
        ("B+", "B+"),
        ("B", "B"),
        ("B-", "B-"),
        ("C+", "C+"),
        ("C", "C"),
        ("C-", "C-"),
        ("D+", "D+"),
        ("D", "D"),
        ("D-", "D-"),
        ("F", "F"),
    )

    RISK_CHOICES = (
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    )

    DEFAULT_GRADE_RISK_MAP = OrderedDict(
        (
            ("A", "low"),
            ("A-", "low"),
            ("B+", "low"),
            ("B", "medium"),
            ("B-", "medium"),
            ("C+", "medium"),
            ("C", "medium"),
            ("C-", "high"),
            ("D+", "high"),
            ("D", "high"),
            ("D-", "high"),
            ("F", "high"),
        )
    )

    grade = models.CharField(
        "Letter Grade",
        max_length=2,
        unique=True,
        choices=GRADE_CHOICES,
        help_text="Letter grade value from uploaded workbooks (e.g., B+ or C-)",
    )
    risk = models.CharField(
        "Mapped Risk",
        max_length=6,
        choices=RISK_CHOICES,
        default="medium",
        help_text="Risk level that should be associated with this letter grade",
    )

    class Meta:
        ordering = ["grade"]
        verbose_name = "Grade to risk mapping"
        verbose_name_plural = "Grade to risk mappings"

    def __str__(self):
        return f"{self.grade} → {self.get_risk_display()}"

    @classmethod
    def get_grade_map(cls):
        """Return the configured grade to risk mapping with defaults as a fallback."""

        try:
            records = cls.objects.all()
        except (ProgrammingError, OperationalError):  # pragma: no cover - table not ready
            return dict(cls.DEFAULT_GRADE_RISK_MAP)

        mapping = {record.grade.upper(): record.risk for record in records}
        if not mapping:
            mapping = dict(cls.DEFAULT_GRADE_RISK_MAP)
        return mapping

    @classmethod
    def risk_for_grade(cls, grade):
        """Return the configured risk slug (low/medium/high) for ``grade``."""

        if not grade:
            return None
        normalized = str(grade).strip().upper()
        if not normalized:
            return None
        return cls.get_grade_map().get(normalized)


class RiskScoreRangeMapping(models.Model):
    """Map a report risk label to the inclusive numeric score range it represents."""

    DEFAULT_RISK_SCORE_MAP = OrderedDict(
        (
            ("Low", (Decimal("1.0"), Decimal("1.9"))),
            ("Low-->Medium", (Decimal("2.0"), Decimal("2.4"))),
            ("Medium-->Low", (Decimal("2.5"), Decimal("2.9"))),
            ("Medium", (Decimal("3.0"), Decimal("3.9"))),
            ("Medium-->High", (Decimal("4.0"), Decimal("4.4"))),
            ("High-->Medium", (Decimal("4.5"), Decimal("4.9"))),
            ("High", (Decimal("5.0"), Decimal("6.0"))),
        )
    )

    risk = models.CharField(
        "Risk label",
        max_length=32,
        unique=True,
        help_text="Risk bucket label (e.g., Low or Medium-->High)",
    )
    risk_rich_text = models.TextField(
        "Risk label rich text",
        default="",
        blank=True,
        help_text="Rich Text version of the risk bucket label.",
    )
    min_score = models.DecimalField(
        "Minimum score",
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text="Lowest inclusive score for this risk bucket.",
    )
    max_score = models.DecimalField(
        "Maximum score",
        max_digits=4,
        decimal_places=1,
        validators=[MinValueValidator(Decimal("0.0"))],
        help_text="Highest inclusive score for this risk bucket.",
    )

    class Meta:
        ordering = ["min_score", "risk"]
        verbose_name = "Risk to score range mapping"
        verbose_name_plural = "Risk to score range mappings"

    def __str__(self):
        return f"{self.risk} = {self.min_score}–{self.max_score}"

    @classmethod
    def get_risk_score_map(cls):
        """Return configured score ranges keyed by risk label, falling back to defaults."""

        try:
            records = cls.objects.all()
        except (ProgrammingError, OperationalError):  # pragma: no cover - table not ready
            return OrderedDict(cls.DEFAULT_RISK_SCORE_MAP)

        mapping = OrderedDict(
            (record.risk, (record.min_score, record.max_score)) for record in records
        )
        if not mapping:
            mapping = OrderedDict(cls.DEFAULT_RISK_SCORE_MAP)
        return mapping

    @classmethod
    def get_risk_rich_text_map(cls):
        """Return configured rich text labels keyed by risk label."""

        try:
            records = cls.objects.all()
        except (ProgrammingError, OperationalError):  # pragma: no cover - table not ready
            return OrderedDict(
                (risk, cls._wrap_inline_rich_text(risk))
                for risk in cls.DEFAULT_RISK_SCORE_MAP
            )

        mapping = OrderedDict(
            (
                record.risk,
                cls._wrap_inline_rich_text(
                    record.risk_rich_text if record.risk_rich_text.strip() else record.risk
                ),
            )
            for record in records
        )
        if not mapping:
            mapping = OrderedDict(
                (risk, cls._wrap_inline_rich_text(risk))
                for risk in cls.DEFAULT_RISK_SCORE_MAP
            )
        return mapping

    @staticmethod
    def _wrap_inline_rich_text(html: str) -> str:
        """
        Ensure inline-only rich text content is wrapped in a block container.

        The DOCX renderer requires text nodes to be nested inside block-level elements
        (e.g., ``<p>``). Inline-only values such as ``"<b>High</b>"`` are wrapped to
        prevent export failures.
        """

        if html is None:
            return html

        text = str(html)
        stripped = text.strip()
        if not stripped:
            return text

        if "<" not in stripped and ">" not in stripped:
            return f"<p>{stripped}</p>"

        soup = BeautifulSoup(text, "html.parser")
        block_tags = ("p", "div", "ul", "ol", "table", "blockquote", "pre")
        if any(soup.find(tag) for tag in block_tags):
            return text

        return f"<p>{stripped}</p>"

    @classmethod
    def score_range_for_risk(cls, risk_label):
        """Return the configured inclusive score range tuple for ``risk_label``."""

        if not risk_label:
            return None
        normalized = str(risk_label).strip()
        if not normalized:
            return None
        return cls.get_risk_score_map().get(normalized)
