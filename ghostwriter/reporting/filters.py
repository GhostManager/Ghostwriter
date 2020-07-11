"""This contains all of the model filters used by the Reporting application."""

import django_filters
from django import forms

from .models import Archive, Finding, FindingType, Report, Severity


class FindingFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Finding` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    ``severity``
        Checkbox choice filter using :model:`reporting.Severty`.
    ``finding_type``
        Multiple choice filter using :model:`reporting.FindingType`.
    """

    title = django_filters.CharFilter(lookup_expr="icontains", label="Title Contains")
    severity = django_filters.ModelMultipleChoiceFilter(
        queryset=Severity.objects.all().order_by("weight"),
        widget=forms.CheckboxSelectMultiple,
    )
    finding_type = django_filters.ModelMultipleChoiceFilter(
        queryset=FindingType.objects.all(), widget=forms.CheckboxSelectMultiple
    )

    class Meta:
        model = Finding
        fields = ["title", "severity", "finding_type"]


class ReportFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    ``complete``
        Boolean field to filter completed reports.
    """

    title = django_filters.CharFilter(lookup_expr="icontains", label="Title Contains")

    STATUS_CHOICES = (
        (0, "All Reports"),
        (1, "Completed"),
    )

    complete = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES, empty_label=None, label="Report Status"
    )

    class Meta:
        model = Report
        fields = ["title", "complete"]


class ArchiveFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``client``
        Case insensitive search of the client field and associated :model:`rolodex.Client`.
    """

    client = django_filters.CharFilter(
        field_name="project__client__name", label="Client Name", lookup_expr="icontains"
    )

    class Meta:
        model = Archive
        fields = ["project__client"]
