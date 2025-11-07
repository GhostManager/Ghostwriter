"""This contains all the model filters used by the Rolodex application."""

# Django Imports
from django import forms
from django.db.models import Q
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import Accordion, AccordionGroup, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.modules.shared import search_tags
from ghostwriter.rolodex.models import Client, Project, ProjectType


class ClientFilter(django_filters.FilterSet):
    """
    Filter :model:`rolodex.Client` model.

    **Fields**

    ``name``
        Case insensitive search of the model's ``name`` field
    ``codename``
        Case insensitive search of the model's ``codename`` field
    ``tags``
        Search of the `tags` field
    """

    name = django_filters.CharFilter(
        method="search_all_names",
        label="Client Name Contains",
        widget=TextInput(attrs={"placeholder": "Partial Name, Short Name, or Codename", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Client Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Client Tag",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Client
        fields = ["name", "codename"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"

        # Determine active state from session (default to False if not available)
        is_active = False
        if self.request and hasattr(self.request, "session"):
            filter_data = self.request.session.get("filter", {})
            is_active = filter_data.get("sticky", False)

        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Accordion(
                AccordionGroup(
                    "Client Filters",
                    Div(
                        Row(
                            Column(
                                PrependedText("name", '<i class="fas fa-filter"></i>'),
                                css_class="form-group col-md-6 mb-0",
                            ),
                            Column(
                                PrependedText("tags", '<i class="fas fa-tag"></i>'),
                                css_class="form-group col-md-6 mb-0",
                            ),
                            css_class="form-row",
                        ),
                        ButtonHolder(
                            Submit("submit_btn", "Filter", css_class="btn btn-primary col-1"),
                            HTML(
                                """
                                <a class="btn btn-outline-secondary col-1" role="button" href="{%  url 'rolodex:clients' %}">Reset</a>
                                """
                            ),
                            css_class="mt-3",
                        ),
                    ),
                    active=is_active,
                    template="accordion_group.html",
                    css_class="library-filter"
                ),
                css_class="justify-content-center",
            ),
        )

    def search_all_names(self, queryset, name, value):
        """
        Search for a value that appears in the :model:`rolodex.Client`
        `name`, `short_name`, or `codename` fields.
        """
        return queryset.filter(Q(name__icontains=value) | Q(short_name__icontains=value) | Q(codename__icontains=value))

    def search_tags(self, queryset, name, value):
        """Filter clients by tags."""
        return search_tags(queryset, value)


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
    ``client``
        Case insensitive search of the model's ``client`` field
    ``tags``
        Search of the `tags` field
    """

    client = django_filters.CharFilter(
        label="Client Name Contains",
        method="search_all_client_names",
        widget=TextInput(
            attrs={
                "placeholder": "Partial Client Name",
                "autocomplete": "off",
            }
        ),
    )
    codename = django_filters.CharFilter(
        label="Project Codename Contains",
        lookup_expr="icontains",
        widget=TextInput(
            attrs={
                "placeholder": "Partial Project Codename",
                "autocomplete": "off",
            }
        ),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Project Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Project Tag",
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
        label="Relative Start Date", field_name="start_date", empty_label="-- Relative Start Date --"
    )

    STATUS_CHOICES = (
        (0, "Active"),
        (1, "Completed"),
    )

    complete = django_filters.ChoiceFilter(choices=STATUS_CHOICES, empty_label="All Projects", label="Project Status")

    project_type = django_filters.ModelChoiceFilter(
        queryset=lambda _: ProjectType.objects.all(),
        label="Project Type",
        field_name="project_type",
        empty_label="-- Project Type --",
    )

    class Meta:
        model = Project
        fields = [
            "complete",
        ]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"

        # Determine active state from session (default to False if not available)
        is_active = False
        if self.request and hasattr(self.request, "session"):
            filter_data = self.request.session.get("filter", {})
            is_active = filter_data.get("sticky", False)

        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Accordion(
                AccordionGroup(
                    "Project Filters",
                    Div(
                        Row(
                            Column(
                                PrependedText("client", '<i class="fas fa-filter"></i>'),
                                css_class="form-group col-md-6 mb-0",
                            ),
                            Column(
                                PrependedText("codename", '<i class="fas fa-filter"></i>'),
                                css_class="form-group col-md-6 mb-0",
                            ),
                        ),
                        Row(
                            Column(
                                PrependedText(
                                    "project_type",
                                    '<i class="fas fa-filter"></i>',
                                ),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            Column(
                                PrependedText(
                                    "complete",
                                    '<i class="fas fa-toggle-on"></i>',
                                ),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            Column(
                                PrependedText("tags", '<i class="fas fa-tag"></i>'),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            css_class="form-row",
                        ),
                        Row(
                            Column(
                                PrependedText(
                                    "start_date_range",
                                    '<i class="far fa-calendar"></i>',
                                ),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            Column(
                                PrependedText("start_date", '<i class="fas fa-hourglass-start"></i>'),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            Column(
                                PrependedText(
                                    "end_date",
                                    '<i class="fas fa-hourglass-end"></i>',
                                ),
                                css_class="form-group col-md-4 mb-0",
                            ),
                            css_class="form-row",
                        ),
                        ButtonHolder(
                            Submit("submit_btn", "Filter", css_class="btn btn-primary col-1"),
                            HTML(
                                """
                                <a class="btn btn-outline-secondary col-1" role="button"
                                href="{%  url 'rolodex:projects' %}">Reset</a>
                                """
                            ),
                            css_class="mt-3",
                        ),
                    ),
                    active=is_active,
                    template="accordion_group.html",
                ),
                css_class="justify-content-center",
            ),
        )

    def search_all_client_names(self, queryset, name, value):
        """
        Search for a value that appears in the :model:`rolodex.Client`
        `name`, `short_name`, or `codename` fields.
        """
        return queryset.filter(
            Q(client__name__icontains=value)
            | Q(client__short_name__icontains=value)
            | Q(client__codename__icontains=value)
        )

    def search_tags(self, queryset, name, value):
        """Filter projects by tags."""
        return search_tags(queryset, value)
