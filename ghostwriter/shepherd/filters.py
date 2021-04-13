"""This contains all of the model filters used by the Shepherd application."""

# Django Imports
from django import forms
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

from .models import Domain, DomainStatus, HealthStatus, ServerStatus


class DomainFilter(django_filters.FilterSet):
    """
    Filter :model:`shepherd.Domain` model for searching.

    **Fields**

    ``name``
        Case insensitive search of the name field contents
    ``all_cat``
        Case insensitive search of the all_cat field
    ``health_status``
        Checkbox choice filter using :model:`shepherd.HealthStatus`
    ``domain_status``
        Checkbox choice filter using :model:`shepherd.DomainStatus`
    ``expiration_status``
        Boolean field to filter expired domains
    """

    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Domain Name Contains",
        widget=TextInput(attrs={"placeholder": "Domain Name", "autocomplete": "off"}),
    )
    all_cat = django_filters.CharFilter(
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

    def __init__(self, *args, **kwargs):
        super(DomainFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("name", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-4 offset-md-2",
                ),
                Column(
                    PrependedText("all_cat", '<i class="fas fa-filter"></i>'),
                    css_class=" col-md-4",
                ),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup("Domain Status", InlineCheckboxes("domain_status")),
                AccordionGroup("Health Status", InlineCheckboxes("health_status")),
            ),
            ButtonHolder(
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
        super(ServerFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Row(
                Column(
                    PrependedText("ip_address", '<i class="fas fa-filter"></i>'),
                    css_class="col-md-4 offset-md-2",
                ),
                Column(
                    PrependedText("name", '<i class="fas fa-filter"></i>'),
                    css_class=" col-md-4",
                ),
                css_class="form-row",
            ),
            Accordion(
                AccordionGroup("Server Status", InlineCheckboxes("server_status")),
            ),
            ButtonHolder(
                Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                HTML(
                    """
                    <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'shepherd:servers' %}">Reset</a>
                    """
                ),
            ),
        )
