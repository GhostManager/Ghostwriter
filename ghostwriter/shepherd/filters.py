"""This contains all the model filters used by the Shepherd application."""

# Standard Libraries
from datetime import date

# Django Imports
from django import forms
from django.db.models import Q
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import (
    Accordion,
    AccordionGroup,
    InlineCheckboxes,
    PrependedText,
)
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.modules.custom_layout_object import SwitchToggle
from ghostwriter.modules.shared import search_tags
from ghostwriter.shepherd.models import Domain, DomainStatus, HealthStatus, ServerStatus


class DomainFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.Domain` model for searching.

    **Fields**

    ``domain``
        Case insensitive search of the `name` and `categorization` fields contents
    ``health_status``
        Checkbox choice filter using :model:`shepherd.HealthStatus`
    ``domain_status``
        Checkbox choice filter using :model:`shepherd.DomainStatus`
    ``exclude_expired``
        Checkbox to exclude expired domains from search results
    ``tags``
        Search of the `tags` field
    """

    domain = django_filters.CharFilter(
        method="search_name_and_category",
        label="Domain Name or Category Contains",
        widget=TextInput(attrs={"placeholder": "Partial Domain Name or Category", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Domain Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Domain Tag",
                "autocomplete": "off",
            }
        ),
    )
    health_status = django_filters.ModelMultipleChoiceFilter(
        queryset=HealthStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )
    domain_status = django_filters.ModelMultipleChoiceFilter(
        queryset=DomainStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    exclude_expired = django_filters.BooleanFilter(
        label="Filter Expired",
        method="filter_expired",
        widget=forms.CheckboxInput,
    )

    class Meta:
        model = Domain
        fields = ["health_status", "domain_status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("domain", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-6",
                ),
                Column(
                    PrependedText("tags", '<i class="fas fa-tag"></i>'),
                    css_class="form-group col-md-6 mb-0",
                ),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup("Domain Status", InlineCheckboxes("domain_status"), SwitchToggle("exclude_expired")),
                AccordionGroup("Health Status", InlineCheckboxes("health_status")),
            ),
            ButtonHolder(
                HTML(
                    """
                    <a class="btn btn-info col-md-2" role="button" href="{%  url 'shepherd:domain_create' %}">Create</a>
                    """
                ),
                Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                HTML(
                    """
                    <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'shepherd:domains' %}">Reset</a>
                    """
                ),
                css_class="mt-3",
            ),
        )

    def search_tags(self, queryset, name, value):
        """Filter domains by tags."""
        return search_tags(queryset, value)

    def filter_expired(self, queryset, name, value):
        """
        Choose to include or exclude expired domains in search results.
        """
        if value:
            return queryset.filter(Q(expiration__gte=date.today()) | Q(auto_renew=True))
        return queryset

    def search_name_and_category(self, queryset, name, value):
        """
        Search for a value that appears in either the :model:`shepherd.Domain` `name` and `categorization` fields.
        """
        return queryset.filter(Q(name__icontains=value) | Q(categorization__icontains=value))


class ServerFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.StaticServer` model for searching.

    **Fields**

    ``server``
        Case insensitive search of the `ip_address` and `name` fields tied to
        :model:`shepherd.StaticServer` and :model:`shepherd.AuxServerAddress`
    ``server_status``
        Checkbox choice filter using :model:`shepherd.ServerStatus`
    ``tags``
        Search of the `tags` field
    """

    server = django_filters.CharFilter(
        method="search_name_and_address",
        label="IP Address or Hostname Contains",
        widget=TextInput(attrs={"placeholder": "Partial IP Address or Hostname", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Server Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Server Tag",
                "autocomplete": "off",
            }
        ),
    )
    server_status = django_filters.ModelMultipleChoiceFilter(
        queryset=ServerStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    class Meta:
        model = Domain
        fields = ["server_status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("server", '<i class="fas fa-filter"></i>'),
                    css_class="form-group col-md-6 mb-0",
                ),
                Column(
                    PrependedText("tags", '<i class="fas fa-tag"></i>'),
                    css_class="form-group col-md-6 mb-0",
                ),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup("Server Status", InlineCheckboxes("server_status")),
            ),
            ButtonHolder(
                HTML(
                    """
                    <a class="btn btn-info col-md-2" role="button" href="{%  url 'shepherd:server_create' %}">Create</a>
                    """
                ),
                Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                HTML(
                    """
                    <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'shepherd:servers' %}">Reset</a>
                    """
                ),
                css_class="mt-3",
            ),
        )

    def search_tags(self, queryset, name, value):
        """Filter servers by tags."""
        return search_tags(queryset, value)

    def search_name_and_address(self, queryset, name, value):
        """
        Search for a value that appears in either the :model:`shepherd.StaticServer` `name` and `ip_address` fields
        or the :model:`shepherd.AuxServerAddress` `ip_address` field.
        """
        return queryset.filter(
            Q(ip_address__icontains=value) | Q(name__icontains=value) | Q(auxserveraddress__ip_address__icontains=value)
        )
