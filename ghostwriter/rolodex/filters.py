"""This contains all of the model filters used by the Rolodex application."""

# Django Imports
from django import forms
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

from .models import Client, Project


class ClientFilter(django_filters.FilterSet):
    """
    Filter :model:`rolodex.Client` model.

    **Fields**

    ``name``
        Case insensitive search of the model's ``name`` field
    ``codename``
        Case insensitive search of the model's ``codename`` field
    """

    name = django_filters.CharFilter(
        lookup_expr="icontains",
        widget=TextInput(
            attrs={
                "placeholder": "Part of Name",
                "autocomplete": "off",
            }
        ),
    )
    codename = django_filters.CharFilter(
        lookup_expr="icontains",
        widget=TextInput(
            attrs={
                "placeholder": "Part of Codename",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Client
        fields = ["name", "codename"]

    def __init__(self, *args, **kwargs):
        super(ClientFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("name", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-6 mb-0",
                    ),
                    Column(
                        PrependedText("codename", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-6 mb-0",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'rolodex:clients' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )


class ProjectFilter(django_filters.FilterSet):
    """
    Filter :model:`rolodex.Project` model.

    **Fields**

    ``start_date``
        Date filter for ``start_date`` values greater than provided value
    ``end_date``
        Date filter for ``end_date`` values less than provided value
    ``start_date_range``
        Date range filter for retrieving entries with matching ``start_date`` values
    ``complete``
        Boolean field for filtering incomplete projects based on the ``complete`` field
    ``codename``
        Case insensitive search of the model's ``codename`` field
    """

    codename = django_filters.CharFilter(
        lookup_expr="icontains",
        widget=TextInput(
            attrs={
                "placeholder": "Part of Codename",
                "autocomplete": "off",
            }
        ),
    )
    start_date = django_filters.DateFilter(
        lookup_expr="gte",
        field_name="start_date",
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "dateinput form-control"}),
    )
    end_date = django_filters.DateFilter(
        lookup_expr="lte",
        field_name="end_date",
        label="End Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "dateinput form-control"}),
    )
    start_date_range = django_filters.DateRangeFilter(
        field_name="start_date", empty_label="-- Relative Start Date --"
    )

    STATUS_CHOICES = (
        (0, "All Projects"),
        (1, "Completed"),
    )

    complete = django_filters.ChoiceFilter(
        choices=STATUS_CHOICES, empty_label=None, label="Project status"
    )

    class Meta:
        model = Project
        fields = [
            "complete",
        ]

    def __init__(self, *args, **kwargs):
        super(ProjectFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("codename", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-4 mb-0",
                    ),
                    Column("complete", css_class="form-group col-md-4 mb-0"),
                    Column("start_date_range", css_class="form-group col-md-4 mb-0"),
                ),
                Row(
                    Column(
                        PrependedText(
                            "start_date", '<i class="fas fa-hourglass-start"></i>'
                        ),
                        css_class="form-group col-md-6 mb-0",
                    ),
                    Column(
                        PrependedText(
                            "end_date",
                            '<i class="fas fa-hourglass-end"></i>',
                        ),
                        css_class="form-group col-md-6 mb-0",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'rolodex:projects' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )
