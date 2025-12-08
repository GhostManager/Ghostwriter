"""Views for managing the vulnerability and web issue matrices."""

from __future__ import annotations

# Standard Libraries
import logging
from typing import Sequence, Tuple

# Django Imports
from django.contrib import messages
from django.contrib.messages.views import SuccessMessageMixin
from django.core.exceptions import ImproperlyConfigured
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views import View
from django.views.generic import CreateView, ListView, UpdateView

# 3rd Party Libraries
from tablib import Dataset

# Ghostwriter Libraries
from ghostwriter.api.utils import RoleBasedAccessControlMixin, verify_user_is_privileged
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.rolodex.forms_matrix import (
    MatrixUploadForm,
    VulnerabilityMatrixEntryForm,
    WebIssueMatrixEntryForm,
)
from ghostwriter.rolodex.models import VulnerabilityMatrixEntry, WebIssueMatrixEntry
from ghostwriter.rolodex.resources import (
    VulnerabilityMatrixEntryResource,
    WebIssueMatrixEntryResource,
)

logger = logging.getLogger(__name__)


class MatrixPermissionRequiredMixin(RoleBasedAccessControlMixin):
    """Ensure that only privileged users can manage the matrices."""

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")


class MatrixContextMixin(MatrixPermissionRequiredMixin):
    """Common helpers shared by all matrix management views."""

    matrix_slug: str = ""
    matrix_title: str = ""
    table_columns: Sequence[Tuple[str, str]] = ()
    list_url_name: str = ""
    create_url_name: str | None = None
    export_url_name: str | None = None
    import_url_name: str | None = None
    edit_url_name: str | None = None
    resource_class = None

    def get_success_url(self):
        if not self.list_url_name:
            raise ImproperlyConfigured("The list_url_name attribute must be set.")
        return reverse(self.list_url_name)

    def get_matrix_context(self):
        context = {
            "matrix_slug": self.matrix_slug,
            "matrix_title": self.matrix_title,
            "table_columns": self.table_columns,
            "list_url": reverse(self.list_url_name) if self.list_url_name else None,
            "create_url": reverse(self.create_url_name) if self.create_url_name else None,
            "export_url": reverse(self.export_url_name) if self.export_url_name else None,
            "import_url": reverse(self.import_url_name) if self.import_url_name else None,
            "edit_url_name": self.edit_url_name,
        }
        resource_fields = self.get_resource_fields()
        context["csv_field_names"] = [field for field in resource_fields if field != "id"]
        return context

    def get_resource_fields(self):
        meta = getattr(self.resource_class, "Meta", None)
        if meta and getattr(meta, "fields", None):
            return meta.fields
        return []

    def get_resource(self):
        if self.resource_class is None:
            raise ImproperlyConfigured("The resource_class attribute must be set.")
        return self.resource_class()


class BaseMatrixListView(MatrixContextMixin, ListView):
    template_name = "rolodex/matrix_list.html"
    context_object_name = "entries"
    paginate_by = 100
    search_fields: Sequence[str] = ()

    def get_search_query(self) -> str:
        return (self.request.GET.get("q") or "").strip()

    def get_queryset(self):
        queryset = super().get_queryset()
        search_query = self.get_search_query()
        if search_query and self.search_fields:
            terms = [term for term in search_query.split(" ") if term]
            for term in terms:
                term_filters = Q()
                for field in self.search_fields:
                    term_filters |= Q(**{f"{field}__icontains": term})
                queryset = queryset.filter(term_filters)
        return queryset

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_matrix_context())
        context["upload_form"] = MatrixUploadForm()
        context["search_query"] = self.get_search_query()
        return context


class BaseMatrixEntryFormView(MatrixContextMixin, SuccessMessageMixin):
    template_name = "rolodex/matrix_form.html"
    success_message: str = ""
    form_heading: str = ""

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context.update(self.get_matrix_context())
        context["form_heading"] = self.form_heading
        return context


class MatrixImportView(MatrixContextMixin, View):
    form_class = MatrixUploadForm

    def validate_dataset(self, dataset: Dataset, resource):
        """Validate and optionally modify the dataset prior to import."""

        return dataset

    def post(self, request, *args, **kwargs):
        form = self.form_class(request.POST, request.FILES)
        if not form.is_valid():
            for error in form.errors.get("csv_file", []):
                messages.error(self.request, error)
            return redirect(self.get_success_url())

        uploaded_file = form.cleaned_data["csv_file"]
        uploaded_file.seek(0)
        file_bytes = uploaded_file.read()
        if not file_bytes:
            messages.error(self.request, "The uploaded file was empty.")
            return redirect(self.get_success_url())

        csv_text = None
        for encoding in ("utf-8-sig", "utf-8"):
            try:
                csv_text = file_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue
        if csv_text is None:
            messages.error(self.request, "Unable to decode the uploaded CSV file. Please use UTF-8 encoding.")
            return redirect(self.get_success_url())

        dataset = Dataset()
        try:
            dataset.load(csv_text, format="csv")
        except Exception as exc:  # pragma: no cover - exercised in integration
            logger.exception("Failed to parse matrix CSV upload")
            messages.error(self.request, f"Unable to read the CSV file: {exc}")
            return redirect(self.get_success_url())

        resource = self.get_resource()
        try:
            dataset = self.validate_dataset(dataset, resource)
        except ValueError as exc:
            messages.error(self.request, str(exc))
            return redirect(self.get_success_url())
        try:
            resource.import_data(dataset, dry_run=True, raise_errors=True)
            resource.import_data(dataset, dry_run=False, raise_errors=True)
        except Exception as exc:  # pragma: no cover - exercised in integration
            logger.exception("Matrix import failed")
            messages.error(self.request, f"Could not import the CSV file: {exc}")
            return redirect(self.get_success_url())

        messages.success(self.request, f"Successfully imported {dataset.height} entries.")
        return redirect(self.get_success_url())


class MatrixExportView(MatrixContextMixin, View):
    def get(self, request, *args, **kwargs):
        resource = self.get_resource()
        dataset = resource.export()
        response = HttpResponse(dataset.csv, content_type="text/csv; charset=utf-8")
        filename = f"{self.matrix_slug}-matrix.csv"
        add_content_disposition_header(response, filename=filename)
        return response


class VulnerabilityMatrixListView(BaseMatrixListView):
    model = VulnerabilityMatrixEntry
    matrix_slug = "vulnerability"
    matrix_title = "Vulnerability matrix"
    table_columns = (
        ("vulnerability", "Vulnerability"),
        ("category", "Category"),
        ("vulnerability_threat", "Vulnerability Threat"),
        ("action_required", "Action Required"),
        ("remediation_impact", "Remediation Impact"),
    )
    list_url_name = "rolodex:vulnerability_matrix"
    create_url_name = "rolodex:vulnerability_matrix_add"
    export_url_name = "rolodex:vulnerability_matrix_export"
    import_url_name = "rolodex:vulnerability_matrix_import"
    resource_class = VulnerabilityMatrixEntryResource
    edit_url_name = "rolodex:vulnerability_matrix_edit"
    ordering = ["vulnerability"]
    search_fields = (
        "vulnerability",
        "category",
        "vulnerability_threat",
        "action_required",
        "remediation_impact",
    )


class VulnerabilityMatrixCreateView(BaseMatrixEntryFormView, CreateView):
    model = VulnerabilityMatrixEntry
    form_class = VulnerabilityMatrixEntryForm
    matrix_slug = "vulnerability"
    matrix_title = "Vulnerability matrix"
    form_heading = "Add vulnerability matrix entry"
    success_message = "Vulnerability matrix entry added."
    list_url_name = "rolodex:vulnerability_matrix"
    create_url_name = "rolodex:vulnerability_matrix_add"
    export_url_name = "rolodex:vulnerability_matrix_export"
    import_url_name = "rolodex:vulnerability_matrix_import"
    resource_class = VulnerabilityMatrixEntryResource


class VulnerabilityMatrixUpdateView(BaseMatrixEntryFormView, UpdateView):
    model = VulnerabilityMatrixEntry
    form_class = VulnerabilityMatrixEntryForm
    matrix_slug = "vulnerability"
    matrix_title = "Vulnerability matrix"
    form_heading = "Edit vulnerability matrix entry"
    success_message = "Vulnerability matrix entry updated."
    list_url_name = "rolodex:vulnerability_matrix"
    create_url_name = "rolodex:vulnerability_matrix_add"
    export_url_name = "rolodex:vulnerability_matrix_export"
    import_url_name = "rolodex:vulnerability_matrix_import"
    resource_class = VulnerabilityMatrixEntryResource


class VulnerabilityMatrixImportView(MatrixImportView):
    matrix_slug = "vulnerability"
    matrix_title = "Vulnerability matrix"
    list_url_name = "rolodex:vulnerability_matrix"
    resource_class = VulnerabilityMatrixEntryResource

    def validate_dataset(self, dataset: Dataset, resource):
        """Ensure uploaded CSV rows meet vulnerability matrix requirements."""

        required_fields = [
            "vulnerability",
            "action_required",
            "remediation_impact",
            "vulnerability_threat",
            "category",
        ]
        headers = dataset.headers or []
        missing_headers = [field for field in required_fields if field not in headers]
        if missing_headers:
            missing_list = ", ".join(missing_headers)
            raise ValueError(f"Missing required columns: {missing_list}.")

        allowed_categories = {"OOD", "ISC", "IWC"}
        cleaned_dataset = Dataset(headers=required_fields)

        for row_index, row in enumerate(dataset.dict, start=2):
            values = {}
            for field in required_fields:
                value = row.get(field, "")
                value_str = str(value).strip() if value is not None else ""
                if not value_str:
                    raise ValueError(
                        f"Row {row_index}: '{field}' is required and cannot be empty."
                    )
                if "UPDATE ME" in value_str.upper():
                    raise ValueError(
                        f"Row {row_index}: '{field}' cannot contain placeholder text."
                    )
                values[field] = value_str

            for extra_field, raw_value in row.items():
                extra_value_str = str(raw_value).strip() if raw_value is not None else ""
                if "UPDATE ME" in extra_value_str.upper():
                    raise ValueError(
                        f"Row {row_index}: '{extra_field}' cannot contain placeholder text."
                    )

            category_value = values["category"].upper()
            if category_value not in allowed_categories:
                allowed_list = ", ".join(sorted(allowed_categories))
                raise ValueError(
                    f"Row {row_index}: category must be one of {allowed_list}."
                )

            if "<EC>" not in values["vulnerability_threat"]:
                raise ValueError(
                    f"Row {row_index}: vulnerability_threat must include '<EC>'."
                )

            values["category"] = category_value
            cleaned_dataset.append([values[field] for field in required_fields])

        return cleaned_dataset


class VulnerabilityMatrixExportView(MatrixExportView):
    matrix_slug = "vulnerability"
    matrix_title = "Vulnerability matrix"
    list_url_name = "rolodex:vulnerability_matrix"
    resource_class = VulnerabilityMatrixEntryResource


class WebIssueMatrixListView(BaseMatrixListView):
    model = WebIssueMatrixEntry
    matrix_slug = "web-issue"
    matrix_title = "Web issue matrix"
    table_columns = (
        ("title", "Title"),
        ("impact", "Impact"),
        ("fix", "Fix"),
    )
    list_url_name = "rolodex:web_issue_matrix"
    create_url_name = "rolodex:web_issue_matrix_add"
    export_url_name = "rolodex:web_issue_matrix_export"
    import_url_name = "rolodex:web_issue_matrix_import"
    resource_class = WebIssueMatrixEntryResource
    edit_url_name = "rolodex:web_issue_matrix_edit"
    ordering = ["title"]
    search_fields = (
        "title",
        "impact",
        "fix",
    )


class WebIssueMatrixCreateView(BaseMatrixEntryFormView, CreateView):
    model = WebIssueMatrixEntry
    form_class = WebIssueMatrixEntryForm
    matrix_slug = "web-issue"
    matrix_title = "Web issue matrix"
    form_heading = "Add web issue matrix entry"
    success_message = "Web issue matrix entry added."
    list_url_name = "rolodex:web_issue_matrix"
    create_url_name = "rolodex:web_issue_matrix_add"
    export_url_name = "rolodex:web_issue_matrix_export"
    import_url_name = "rolodex:web_issue_matrix_import"
    resource_class = WebIssueMatrixEntryResource


class WebIssueMatrixUpdateView(BaseMatrixEntryFormView, UpdateView):
    model = WebIssueMatrixEntry
    form_class = WebIssueMatrixEntryForm
    matrix_slug = "web-issue"
    matrix_title = "Web issue matrix"
    form_heading = "Edit web issue matrix entry"
    success_message = "Web issue matrix entry updated."
    list_url_name = "rolodex:web_issue_matrix"
    create_url_name = "rolodex:web_issue_matrix_add"
    export_url_name = "rolodex:web_issue_matrix_export"
    import_url_name = "rolodex:web_issue_matrix_import"
    resource_class = WebIssueMatrixEntryResource


class WebIssueMatrixImportView(MatrixImportView):
    matrix_slug = "web-issue"
    matrix_title = "Web issue matrix"
    list_url_name = "rolodex:web_issue_matrix"
    resource_class = WebIssueMatrixEntryResource


class WebIssueMatrixExportView(MatrixExportView):
    matrix_slug = "web-issue"
    matrix_title = "Web issue matrix"
    list_url_name = "rolodex:web_issue_matrix"
    resource_class = WebIssueMatrixEntryResource
