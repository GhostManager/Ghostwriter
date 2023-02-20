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
from ghostwriter.shepherd.models import Domain, DomainStatus, HealthStatus, ServerStatus


class DomainFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.Domain` model for searching.

    **Fields**

    ``name``
        Case insensitive search of the name field contents
    ``categorization``
        Case insensitive search of the categorization field
    ``health_status``
        Checkbox choice filter using :model:`shepherd.HealthStatus`
    ``domain_status``
        Checkbox choice filter using :model:`shepherd.DomainStatus`
    ``exclude_expired``
        Checkbox to exclude expired domains from search results
    """

    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Domain Name Contains",
        widget=TextInput(attrs={"placeholder": "Domain Name", "autocomplete": "off"}),
    )
    categorization = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Categories Contain",
        widget=TextInput(attrs={"placeholder": "Category", "autocomplete": "off"}),
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
        fields = ["name", "categorization", "health_status", "domain_status"]

    def filter_expired(self, queryset, name, value):
        """
        Choose to include or exclude expired domains in search results.
        """
        if value:
            # return queryset.filter(Q(expiration__lt=date.today()) & Q(auto_renew=False))
            return queryset.filter(Q(expiration__gte=date.today()) | Q(auto_renew=True))
        return queryset

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = True
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("name", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-6",
                ),
                Column(
                    PrependedText("categorization", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-6",
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
            ),
        )


class ServerFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.StaticServer` model for searching.

    **Fields**

    ``io_address``
        Case insensitive search of the ip_address field contents
    ``name``
        Case insensitive search of the name field contents
    ``server_status``
        Checkbox choice filter using :model:`shepherd.ServerStatus`
    """

    ip_address = django_filters.CharFilter(
        lookup_expr="icontains",
        label="IP Address Contains",
        widget=TextInput(attrs={"placeholder": "IP Address", "autocomplete": "off"}),
    )
    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Server Name Contains",
        widget=TextInput(attrs={"placeholder": "Hostname", "autocomplete": "off"}),
    )
    server_status = django_filters.ModelMultipleChoiceFilter(
        queryset=ServerStatus.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    class Meta:
        model = Domain
        fields = ["ip_address", "name", "server_status"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("ip_address", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-6",
                ),
                Column(
                    PrependedText("name", '<i class="fas fa-filter"></i>'),
                    css_class=" col-md-6",
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
            ),
        )
