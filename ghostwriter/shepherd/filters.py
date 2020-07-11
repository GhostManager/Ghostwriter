"""This contains all of the model filters used by the Shepherd application."""

import django_filters
from django import forms

from .models import Domain, DomainStatus, HealthStatus, ServerStatus


class DomainFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.Domain` model for searching.

    **Fields**

    ``name``
        Case insensitive search of the name field contents.
    ``all_cat``
        Case insensitive search of the all_cat field.
    ``health_status``
        Checkbox choice filter using :model:`shepherd.HealthStatus`.
    ``domain_status``
        Checkbox choice filter using :model:`shepherd.DomainStatus`.
    ``expiration_status``
        Boolean field to filter expired domains.
    """

    name = django_filters.CharFilter(
        lookup_expr="icontains", label="Domain Name Contains"
    )
    all_cat = django_filters.CharFilter(
        lookup_expr="icontains", label="Categories Contain"
    )
    health_status = django_filters.ModelMultipleChoiceFilter(
        queryset=HealthStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Health Status",
    )
    domain_status = django_filters.ModelMultipleChoiceFilter(
        queryset=DomainStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Domain Status",
    )

    STATUS_CHOICES = (
        (0, "Active"),
        (1, "Expired"),
    )
    expiration_status = django_filters.ChoiceFilter(
        field_name="expired", choices=STATUS_CHOICES, label="Expiration Status"
    )

    class Meta:
        model = Domain
        fields = ["name", "all_cat", "health_status", "domain_status"]


class ServerFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.StaticServer` model for searching.

    **Fields**

    ``io_address``
        Case insensitive search of the ip_address field contents.
    ``name``
        Case insensitive search of the name field contents.
    ``server_status``
        Checkbox choice filter using :model:`shepherd.ServerStatus`.
    """

    ip_address = django_filters.CharFilter(
        lookup_expr="icontains", label="IP Address Contains"
    )
    name = django_filters.CharFilter(
        lookup_expr="icontains", label="Server Name Contains"
    )
    server_status = django_filters.ModelMultipleChoiceFilter(
        queryset=ServerStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="Server Status",
    )

    class Meta:
        model = Domain
        fields = ["ip_address", "name", "server_status"]
