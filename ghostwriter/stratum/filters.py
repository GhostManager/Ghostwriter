# Django Imports
from django import forms
from django.db.models import Q
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import InlineCheckboxes, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.reporting.models import FindingType, ReportFindingLink, Severity
from ghostwriter.users.models import User


class ReportFindingFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.ReportFinding` model for searching.
    **Fields**
    ``q``
        Case insensitive search of the title or finding evidence field contents.
    ``start_date``
        Date range search for findings.
    ``end_date``
        Date range search for findings.
    ``start_date_range``
        Date range search for findings.
    ``tester``
        Find findings by tester.
    ``severity``
        Checkbox choice filter using :model:`reporting.Severity`.
    ``finding_type``
        Multiple choice filter using :model:`reporting.FindingType`.
    """

    q = django_filters.CharFilter(
        method="_text_search_filter",
        label="Search",
        widget=TextInput(
            attrs={"placeholder": "Part of Title or Evidence", "autocomplete": "off"}
        ),
    )

    def _text_search_filter(self, queryset, name, value):
        return queryset.filter(
            Q(title__icontains=value) | Q(affected_entities__icontains=value)
        )

    start_date = django_filters.DateFilter(
        lookup_expr="gte",
        field_name="report__creation",
        label="Start Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "dateinput form-control"}),
    )
    end_date = django_filters.DateFilter(
        lookup_expr="lte",
        field_name="report__creation",
        label="End Date",
        widget=forms.DateInput(attrs={"type": "date", "class": "dateinput form-control"}),
    )
    start_date_range = django_filters.DateRangeFilter(
        field_name="report__creation", empty_label="-- Relative Start Date --"
    )

    tester = django_filters.ModelChoiceFilter(
        queryset=User.objects.all().order_by("username"),
        field_name="report__created_by",
        empty_label="All Users",
        widget=forms.Select(attrs={"class": "form-control"}),
        label="User",
    )

    severity = django_filters.ModelMultipleChoiceFilter(
        queryset=Severity.objects.all().order_by("weight"),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )
    finding_type = django_filters.ModelMultipleChoiceFilter(
        queryset=FindingType.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        label="",
    )

    class Meta:
        model = ReportFindingLink
        fields = ["q", "finding_type", "severity"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("q", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-4 mb-0",
                    ),
                    Column("tester", css_class="form-group col-md-4 mb-0"),
                    css_class="form-row",
                ),
                Row(
                    Column("start_date_range", css_class="form-group col-md-4 mb-0"),
                    Column(
                        PrependedText(
                            "start_date", '<i class="fas fa-hourglass-start"></i>'
                        ),
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
                Row(
                    Column(
                        InlineCheckboxes("severity"),
                        css_class="form-group col-md-12 m-1",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        InlineCheckboxes("finding_type"),
                        css_class="form-group col-md-12 m-1",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="col-md-2"),
                    HTML(
                        """
                        <a class="btn col-md-2 btn-info download" role="button" onclick="tableToCSV()">Export</a>
                        """
                    ),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'stratum:report_findings' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )
