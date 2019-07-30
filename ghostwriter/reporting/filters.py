"""This contains all of the model filters for the Ghostwriter application."""

import django_filters
from django import forms

from .models import Finding, Severity, FindingType, Report, Archive


class FindingFilter(django_filters.FilterSet):
    """Filter used to search the `Finding` model."""
    title = django_filters.CharFilter(lookup_expr='icontains')
    severity = django_filters.\
        ModelMultipleChoiceFilter(
            queryset=Severity.objects.all().order_by('weight'),
            widget=forms.CheckboxSelectMultiple)
    finding_type = django_filters.\
        ModelMultipleChoiceFilter(
            queryset=FindingType.objects.all(),
            widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Finding
        fields = ['title', 'severity', 'finding_type']


class ReportFilter(django_filters.FilterSet):
    """Filter used to search the `Report` model."""
    title = django_filters.CharFilter(lookup_expr='icontains')

    STATUS_CHOICES = (
        (0, 'All Reports'),
        (1, 'Completed'),
    )

    complete = django_filters.ChoiceFilter(choices=STATUS_CHOICES,
                                           empty_label=None,
                                           label='Report status')

    class Meta:
        model = Report
        fields = ['title', 'complete']


class ArchiveFilter(django_filters.FilterSet):
    """Filter used to search the `Report` model."""
    client = django_filters.CharFilter(field_name='project__client__name',
                                       label='Client Name',
                                       lookup_expr='icontains')

    class Meta:
        model = Archive
        fields = ['project__client']
