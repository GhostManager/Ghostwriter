"""This contains all of the model filters for the Shepherd application."""

import django_filters
from django import forms

from .models import Domain, HealthStatus, DomainStatus, ServerStatus


class DomainFilter(django_filters.FilterSet):
    """Filter used to search the `Domain` model."""
    name = django_filters.CharFilter(lookup_expr='icontains')
    all_cat = django_filters.CharFilter(lookup_expr='icontains')
    health_status = django_filters.ModelMultipleChoiceFilter(
        queryset=HealthStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple)
    domain_status = django_filters.ModelMultipleChoiceFilter(
        queryset=DomainStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple)

    STATUS_CHOICES = (
        (0, 'Active'),
        (1, 'Expired'),
    )
    expiration_status = django_filters.ChoiceFilter(field_name='expired', choices=STATUS_CHOICES)

    class Meta:
        model = Domain
        fields = ['name', 'all_cat', 'health_status', 'domain_status']


class ServerFilter(django_filters.FilterSet):
    """Filter used to search the `StaticServer` model."""
    ip_address = django_filters.CharFilter(lookup_expr='icontains')
    name = django_filters.CharFilter(lookup_expr='icontains')
    server_status = django_filters.ModelMultipleChoiceFilter(
        queryset=ServerStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple)

    class Meta:
        model = Domain
        fields = ['ip_address', 'name', 'server_status']
