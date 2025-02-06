"""This contains all the model filters used by the Reporting application."""

# Django Imports
from django import forms
from django.forms.widgets import TextInput

# 3rd Party Libraries
import django_filters
from crispy_forms.bootstrap import InlineCheckboxes, PrependedText
from crispy_forms.helper import FormHelper
from crispy_forms.layout import HTML, ButtonHolder, Column, Div, Layout, Row, Submit

# Ghostwriter Libraries
from ghostwriter.modules.shared import search_tags
from ghostwriter.reporting.models import (
    Archive,
    Finding,
    FindingType,
    Observation,
    Report,
    ReportTemplate,
    Severity,
)


class FindingFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Finding` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    ``severity``
        Checkbox choice filter using :model:`reporting.Severity`.
    ``finding_type``
        Multiple choice filter using :model:`reporting.FindingType`.
    ``tags``
        Search of the tags field contents.
    """

    title = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Finding Title Contains",
        widget=TextInput(attrs={"placeholder": "Partial Finding Title", "autocomplete": "off"}),
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
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Finding Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Finding Tag",
                "autocomplete": "off",
            }
        ),
    )

    # Dummy filter to add a checkbox onto the form, which the view uses to select Findings vs
    # ReportFindingLinks
    on_reports = django_filters.BooleanFilter(
        method="filter_on_reports",
        label="Search findings on reports",
        widget=forms.CheckboxInput,
    )

    def filter_on_reports(self, queryset, *args, **kwargs):
        return queryset

    class Meta:
        model = Finding
        fields = ["title", "severity", "finding_type"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("title", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-4 offset-md-2 mb-0",
                    ),
                    Column(
                        PrependedText("tags", '<i class="fas fa-tag"></i>'),
                        css_class="col-md-4 mb-0",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        InlineCheckboxes("severity"),
                        css_class="col-md-12 m-1",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        InlineCheckboxes("finding_type"),
                        css_class="col-md-12 m-1",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        "on_reports",
                        css_class="col-md-12 m-1",
                        data_toggle="tooltip",
                        data_placement="top",
                        title="Return results from reports instead of the library",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    HTML(
                        """
                        <a class="btn btn-info col-md-2" role="button" href="{%  url 'reporting:finding_create' %}">Create</a>
                        """
                    ),
                    Submit("submit_btn", "Filter", css_class="col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'reporting:findings' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )

    def search_tags(self, queryset, name, value):
        """Filter findings by tags."""
        return search_tags(queryset, value)


class ObservationFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Observation` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    """

    title = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Observation Title Contains",
        widget=TextInput(attrs={"placeholder": "Observation Title Contains", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Observation Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Observation Tag",
                "autocomplete": "off",
            }
        ),
    )

    class Meta:
        model = Observation
        fields = ["title"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        self.helper.form_id = "observations-filter-form"
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("title", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-4 offset-md-2 mb-0",
                    ),
                    Column(
                        PrependedText("tags", '<i class="fas fa-tag"></i>'),
                        css_class="col-md-4 mb-0",
                    ),
                    css_class="form-row",
                ),
                css_class="justify-content-center",
            ),
        )

    def search_tags(self, queryset, name, value):
        """Filter observation by tags."""
        return search_tags(queryset, value)


class ReportFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``title``
        Case insensitive search of the title field contents.
    ``tags``
        Search of the tags field contents.
    ``complete``
        Boolean field to filter completed reports.
    """

    title = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Report Title Contains",
        widget=TextInput(attrs={"placeholder": "Partial Report Title", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Report Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Report Tag",
                "autocomplete": "off",
            }
        ),
    )

    STATUS_CHOICES = (
        (0, "All Reports"),
        (1, "Completed"),
    )

    complete = django_filters.ChoiceFilter(choices=STATUS_CHOICES, empty_label=None, label="Report Status")

    class Meta:
        model = Report
        fields = ["title", "complete"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("title", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-4",
                    ),
                    Column(
                        PrependedText("tags", '<i class="fas fa-tag"></i>'),
                        css_class="col-md-4 mb-0",
                    ),
                    Column(
                        PrependedText(
                            "complete",
                            '<i class="fas fa-toggle-on"></i>',
                        ),
                        css_class="col-md-4 mb-0",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    HTML(
                        """
                        <a class="btn btn-info col-md-2" role="button" href="{%  url 'reporting:report_create_no_project' %}">Create</a>
                        """
                    ),
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

    def search_tags(self, queryset, name, value):
        """Filter reports by tags."""
        return search_tags(queryset, value)


class ArchiveFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.Report` model for searching.

    **Fields**

    ``client``
        Case insensitive search of the client field and associated :model:`rolodex.Client`.
    """

    client = django_filters.CharFilter(
        field_name="project__client__name",
        label="Client Name Contains",
        lookup_expr="icontains",
        widget=TextInput(attrs={"placeholder": "Partial Client Name", "autocomplete": "off"}),
    )

    class Meta:
        model = Archive
        fields = ["project__client"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("client", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-6 offset-md-3 mb-0",
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


class ReportTemplateFilter(django_filters.FilterSet):
    """
    Filter :model:`reporting.ReportTemplate` model for searching.

    **Fields**

    ``name``
        Case insensitive search of the name field contents.
    ``doc_type``
        Multiple choice filter using :model:`reporting.DocType`.
    ``tags``
        Search of the tags field contents.
    ``protected``
        Boolean field to filter protected report templates.
    """

    name = django_filters.CharFilter(
        lookup_expr="icontains",
        label="Report Title Contains",
        widget=TextInput(attrs={"placeholder": "Partial Report Title", "autocomplete": "off"}),
    )
    client = django_filters.CharFilter(
        field_name="client__name",
        label="Client Name Contains",
        lookup_expr="icontains",
        widget=TextInput(attrs={"placeholder": "Partial Client Name", "autocomplete": "off"}),
    )
    tags = django_filters.CharFilter(
        method="search_tags",
        label="Template Tags Contain",
        widget=TextInput(
            attrs={
                "placeholder": "Report Tag",
                "autocomplete": "off",
            }
        ),
    )

    DOC_TYPE_CHOICES = (
        (1, "DOCX"),
        (2, "PPTX"),
    )

    doc_type = django_filters.ChoiceFilter(choices=DOC_TYPE_CHOICES, empty_label="All Templates", label="Document Type")

    PROTECTED_CHOICES = (
        (0, "Not Protected"),
        (1, "Protected"),
    )

    protected = django_filters.ChoiceFilter(
        choices=PROTECTED_CHOICES, empty_label="All Projects", label="Project Status"
    )

    class Meta:
        model = ReportTemplate
        fields = ["name", "doc_type", "protected"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.helper = FormHelper()
        self.helper.form_method = "get"
        # Layout the form for Bootstrap
        self.helper.layout = Layout(
            Div(
                Row(
                    Column(
                        PrependedText("name", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-6",
                    ),
                    Column(
                        PrependedText(
                            "doc_type",
                            '<i class="fas fa-file-alt"></i>',
                        ),
                        css_class="col-md-6 mb-0",
                    ),
                    css_class="form-row",
                ),
                Row(
                    Column(
                        PrependedText("client", '<i class="fas fa-filter"></i>'),
                        css_class="col-md-6",
                    ),
                    Column(
                        PrependedText("tags", '<i class="fas fa-tag"></i>'),
                        css_class="col-md-6 mb-0",
                    ),
                    css_class="form-row",
                ),
                ButtonHolder(
                    HTML(
                        """
                        <a class="btn btn-info" href="{% url 'reporting:template_create' %}">Upload a Report Template</a>
                        """
                    ),
                    Submit("submit_btn", "Filter", css_class="btn btn-primary col-md-2"),
                    HTML(
                        """
                        <a class="btn btn-outline-secondary col-md-2" role="button" href="{%  url 'reporting:templates' %}">Reset</a>
                        """
                    ),
                ),
                css_class="justify-content-center",
            ),
        )

    def search_tags(self, queryset, name, value):
        """Filter report templates by tags."""
        return search_tags(queryset, value)
