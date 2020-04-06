"""This contains all of the database models for the Ghostwriter application."""

import os

from django.db import models
from django.urls import reverse
from django.conf import settings
# from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

# Import for Tiny MCE fields
from tinymce.models import HTMLField


class Severity(models.Model):
    """Model representing the various severity ratings for findings."""
    severity = models.CharField(
        'Severity',
        max_length=100,
        unique=True,
        help_text='Severity rating (e.g. High, Low)')
    weight = models.IntegerField(
        'Severity Weight',
        default=1,
        help_text='Used for custom sorting in reports. Lower numbers are '
        'more severe.')

    def count_findings(self):
        """Count and return the number of findings using the severity entry in
        the `Finding` model.
        """
        return Finding.objects.filter(severity=self).count()

    count = property(count_findings)

    class Meta:
        """Metadata for the model."""
        ordering = ['severity']
        verbose_name = 'Severity rating'
        verbose_name_plural = 'Severity ratings'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.severity


class FindingType(models.Model):
    """Model representing the types of findings available."""
    finding_type = models.CharField(
        'Type',
        max_length=100,
        unique=True,
        help_text='Type of finding (e.g. network)')

    def count_findings(self):
        """Count and return the number of findings using the finding_type
        entry in the `Finding` model.
        """
        return Finding.objects.filter(finding_type=self).count()

    count = property(count_findings)

    class Meta:
        """Metadata for the model."""
        ordering = ['finding_type']
        verbose_name = 'Finding type'
        verbose_name_plural = 'Finding types'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.finding_type


class Finding(models.Model):
    """Model representing the findings. This is the primary model for the
    Ghostwriter application. This model keeps a record of the finding names,
    descriptions, severities, and other related data.

    There are foreign keys for the `Severity` and `FindingType` models.
    """
    title = models.CharField(
        'Title',
        max_length=200,
        unique=True,
        help_text='Enter a title for this finding that will appear in the '
        'reports')
    description = HTMLField(
        'Description',
        null=True,
        blank=True,
        help_text='Provide a description for this finding that introduces it')
    impact = HTMLField(
        'Impact',
        help_text='Describe the impact of this finding on the affected '
        'entities',
        null=True,
        blank=True)
    mitigation = HTMLField(
        'Mitigation',
        null=True,
        blank=True,
        help_text='Describe how this finding can be resolved or addressed')
    replication_steps = HTMLField(
        'Replication Steps',
        null=True,
        blank=True,
        help_text='Provide an explanation for how the reader may reproduce '
        'this finding')
    host_detection_techniques = HTMLField(
        'Host Detection Techniques',
        null=True,
        blank=True,
        help_text='Describe how this finding can be detected on an endpoint '
        '- leave blank if this does not apply')
    network_detection_techniques = HTMLField(
        'Network Detection Techniques',
        null=True,
        blank=True,
        help_text='Describe how this finding can be detected on a network '
        '- leave blank if this does not apply')
    references = HTMLField(
        'References',
        null=True,
        blank=True,
        help_text='Provide solid references for this finding, such as links '
        'to reference materials, tooling, and white papers')
    finding_guidance = models.TextField(
        'Finding Guidance',
        null=True,
        blank=True,
        help_text='Provide notes for your team that describes how the finding '
        'is intended to be used and any details that should be provided '
        'during editing')
    # Foreign Keys
    severity = models.ForeignKey(
        'Severity',
        on_delete=models.PROTECT,
        null=True,
        help_text='Select a severity rating for this finding that reflects '
        'its role in a system compromise')
    finding_type = models.ForeignKey(
        'FindingType',
        on_delete=models.PROTECT,
        null=True,
        help_text='Select a finding category that fits')

    class Meta:
        """Metadata for the model."""
        ordering = ['severity', 'finding_type', 'title']
        verbose_name = 'Finding'
        verbose_name_plural = 'Findings'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('reporting:finding_detail', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.title} ({self.severity})'


class Report(models.Model):
    """Model representing the reports for projects.

    There are foreign keys for the `Project` and `User` models.
    """
    title = models.CharField(
        'Title',
        max_length=200,
        default='New Report',
        help_text='Provide a meaningful title for this report '
        '- this is only seen in Ghostwriter')
    creation = models.DateField(
        'Creation Date',
        auto_now_add=True,
        help_text='Date the report was created')
    last_update = models.DateField(
        'Creation Date',
        auto_now=True,
        help_text='Date the report was last touched')
    complete = models.BooleanField(
        'Completed',
        default=False,
        help_text='Mark the report as complete')
    archived = models.BooleanField(
        'Archived',
        default=False,
        help_text='Mark the report as archived')
    # Foreign Keys
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True,
        help_text='Select the project tied to this report')
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)
    delivered = models.BooleanField(
        'Delivered',
        default=False,
        help_text='Delivery status of the report')

    class Meta:
        """Metadata for the model."""
        ordering = ['-creation', '-last_update', 'project']
        verbose_name = 'Report'
        verbose_name_plural = 'Reports'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('reporting:report_detail', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.title}'


class ReportFindingLink(models.Model):
    """Model representing findings linked to active reports. This also stores
    any local edits made to the findings for the report and to which operator
    the edits are assigned.

    There are foreign keys for the `Severity`, `FindingType`, `Report`, and
    `User` models.
    """
    title = models.CharField(
        'Title',
        max_length=200,
        help_text='Enter a title for this finding that will appear in the '
        'reports')
    position = models.IntegerField(
        'Report Position',
        default=1,
        help_text='Set this findings weight to adjust where it appears in the '
        'report compared to other findings with the same Severity rating')
    affected_entities = models.TextField(
        'Affected Entities',
        null=True,
        blank=True,
        help_text='Provide a list of the affected entities (e.g. domains, '
        'hostnames, IP addresses)')
    description = models.TextField(
        'Description',
        null=True,
        blank=True,
        help_text='Provide a description for this finding that introduces it')
    impact = models.TextField(
        'Impact',
        null=True,
        blank=True,
        help_text='Describe the impact of this finding on the affected '
        'entities')
    mitigation = models.TextField(
        'Mitigation',
        null=True,
        blank=True,
        help_text='Describe how this finding can be resolved or addressed')
    replication_steps = models.TextField(
        'Replication Steps',
        null=True,
        blank=True,
        help_text='Provide an explanation for how the reader may reproduce '
        'this finding')
    host_detection_techniques = models.TextField(
        'Host Detection Techniques',
        null=True,
        blank=True,
        help_text='Describe how this finding can be detected on an endpoint '
        '- leave blank if this does not apply')
    network_detection_techniques = models.TextField(
        'Network Detection Techniques',
        null=True,
        blank=True,
        help_text='Describe how this finding can be detected on a network '
        '- leave blank if this does not apply')
    references = HTMLField(
        'References',
        null=True,
        blank=True,
        help_text='Provide solid references for this finding, such as links '
        'to reference materials, tooling, and white papers')
    finding_guidance = models.TextField(
        'Finding Guidance',
        null=True,
        blank=True,
        help_text='Provide notes for your team that describes how the finding '
        'is intended to be used and any details that should be provided '
        'during editing')
    complete = models.BooleanField(
        'Completed',
        default=False,
        help_text='Is the finding ready for review')
    # Foreign Keys
    severity = models.ForeignKey(
        'Severity',
        on_delete=models.PROTECT,
        null=True,
        help_text='Select a severity rating for this finding that reflects '
        'its role in a system compromise')
    finding_type = models.ForeignKey(
        'FindingType',
        on_delete=models.PROTECT,
        null=True,
        help_text='Select a finding category that fits')
    report = models.ForeignKey(
        'Report',
        on_delete=models.CASCADE,
        null=True)
    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        help_text='Assign the task of editing this finding to a specific '
        'operator - defaults to the operator that added it to the report')

    class Meta:
        """Metadata for the model."""
        ordering = ['report', 'severity__weight', 'position']
        verbose_name = 'Report link'
        verbose_name_plural = 'Report links'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.title

    def get_evidence_list(self):
        upload_path = os.path.join(settings.MEDIA_ROOT,
                                   str(self.report.id),
                                   str(self.title))
        evidence_files = []
        if not os.path.exists(upload_path):
            return evidence_files
        else:
            for root, dirs, files in os.walk(upload_path):
                for filename in files:
                    if not filename == '.DS_Store':
                        evidence_files.append(filename)
            return evidence_files


class Evidence(models.Model):
    """Model representing metadata for uploaded evidence files linked to
    findings in reports.

    There are foreign keys for the `ReportFindingLink` and `User` models.
    """
    def set_upload_destination(instance, filename):
        """Sets the `upload_to` destination to the evidence folder for the
        associated report ID.
        """
        return os.path.join('evidence', str(instance.finding.report.id), filename)

    document = models.FileField(
        upload_to=set_upload_destination,
        blank=True)
    friendly_name = models.CharField(
        'Friendly Name',
        null=True,
        max_length=100,
        help_text='Provide a simple name to be used for displaying this '
        'file in the interface and for use as a keyword for placing the '
        'file within the report')
    upload_date = models.DateField(
        'Upload Date',
        auto_now=True,
        help_text='Date and time the evidence was uploaded')
    caption = models.CharField(
        'Caption',
        max_length=200,
        blank=True,
        help_text='Provide a caption to be used in the report output '
        '- keep it brief')
    description = models.TextField(
        'Description',
        max_length=500,
        blank=True,
        help_text='Provide a description/explanation of the evidence that '
        'other users can see to help them understand the purpose of this '
        'evidence')
    # Foreign Keys
    finding = models.ForeignKey(
        'ReportFindingLink', on_delete=models.CASCADE)
    uploaded_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['finding', 'document']
        verbose_name = 'Evidence'
        verbose_name_plural = 'Evidence'

    def get_absolute_url(self):
        """Returns the URL to access a particular instance of the model."""
        return reverse('reporting:evidence_file', args=[str(self.id)])

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.document.name

    def clean(self, *args, **kwargs):
        super(Evidence, self).clean(*args, **kwargs)
        if not self.document:
            raise ValidationError('Please provide an evidence file.')


class Archive(models.Model):
    """Model representing all of the archived reports linked to clients and
    projects.

    There is a foreign key for the `Project` model.
    """
    report_archive = models.FileField()
    project = models.ForeignKey(
        'rolodex.Project',
        on_delete=models.CASCADE,
        null=True)

    @property
    def filename(self):
        return os.path.basename(self.report_archive.name)

    class Meta:
        """Metadata for the model."""
        ordering = ['project']
        verbose_name = 'Archived report'
        verbose_name_plural = 'Archived reports'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return self.report_archive.name


class FindingNote(models.Model):
    """Model representing notes for findings added to a report.

    There are foreign keys for the `Finding` and `User` models.
    """
    # This field is automatically filled with the current date
    timestamp = models.DateField(
        'Timestamp',
        auto_now_add=True,
        max_length=100,
        help_text='Creation timestamp')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to add a note to this finding - it can be '
                  'anything you want others to see/know about the finding')
    # Foreign Keys
    finding = models.ForeignKey(
        'Finding', on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['finding', '-timestamp']
        verbose_name = 'Local finding note'
        verbose_name_plural = 'Local finding notes'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.finding} {self.timestamp}: {self.note}'


class LocalFindingNote(models.Model):
    """Model representing notes for findings added to a report.

    There are foreign keys for the `ReportFindingLink` and `User` models.
    """
    # This field is automatically filled with the current date
    timestamp = models.DateField(
        'Timestamp',
        auto_now_add=True,
        max_length=100,
        help_text='Creation timestamp')
    note = models.TextField(
        'Notes',
        null=True,
        blank=True,
        help_text='Use this area to add a note to this finding - it can be '
                  'anything you want others to see/know about the finding')
    # Foreign Keys
    finding = models.ForeignKey(
        'ReportFindingLink', on_delete=models.CASCADE, null=False)
    operator = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True)

    class Meta:
        """Metadata for the model."""
        ordering = ['finding', '-timestamp']
        verbose_name = 'Local finding note'
        verbose_name_plural = 'Local finding notes'

    def __str__(self):
        """String for representing the model object (in Admin site etc.)."""
        return f'{self.finding} {self.timestamp}: {self.note}'
