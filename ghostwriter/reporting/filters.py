"""This contains all of the model filters used by the Reporting application."""

# Django Imports
from django import forms
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import InlineCheckboxes, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

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

    title = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Title Contains",
        widget=TextInput(attrs={"placeholder": "Part of Title", "autocomplete": "off"}),
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
        model = Finding
        fields = ["title", "severity", "finding_type"]

    def __init__(self, *args, **kwargs):
        super(FindingFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("title", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-6 offset-md-3 mb-0",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        InlineCheckboxes("severity"),
                        css_class="form-group col-md-12",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        InlineCheckboxes("finding_type"),
                        css_class="form-group col-md-12",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'reporting:findings' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )


class ReportFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    ``complete``
        Boolean field to filter completed reports.
    """

    title = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Title Contains",
        widget=TextInput(attrs={"placeholder": "Part of Title", "autocomplete": "off"}),
    )

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

    def __init__(self, *args, **kwargs):
        super(ReportFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("title", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-6",
                    ),
                    Column(
                        "complete",
                        css_class="form-group col-md-6",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'reporting:reports' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )


class ArchiveFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``client``
        Case insensitive search of the client field and associated :model:`rolodex.Client`.
    """

    client = django_filters.CharFilter(
        field_name="project__client__name",
        label="Client Name",
        lookup_expr="icontains",
        widget=TextInput(attrs={"placeholder": "Part of Name", "autocomplete": "off"}),
    )

    class Meta:
        model = Archive
        fields = ["project__client"]

    def __init__(self, *args, **kwargs):
        super(ArchiveFilter, self).__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_class = "newitem"
        self.helper.form_show_labels = False
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("client", '<i class="fas fa-filter"></i>'),
                        css_class="form-group col-md-6 offset-md-3 mb-0",
                    ),
                ),
                ButtonHolder(
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'reporting:archived_reports' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )
