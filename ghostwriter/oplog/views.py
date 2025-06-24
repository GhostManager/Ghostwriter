"""This contains all the views used by the Oplog application."""

# Standard Libraries
import collections
import csv
import json
import logging

# Django Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import FieldDoesNotExist
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.views.generic import ListView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View

# 3rd Party Libraries
from tablib import Dataset

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    RoleBasedAccessControlMixin,
    verify_user_is_privileged,
)
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import ExtraFieldsSpecSerializer
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.oplog.admin import OplogEntryResource
from ghostwriter.oplog.forms import OplogEntryForm, OplogForm
from ghostwriter.oplog.models import Oplog, OplogEntry
from ghostwriter.rolodex.models import Project

# Using __name__ resolves to ghostwriter.oplog.views
logger = logging.getLogger(__name__)


def escape_message(message):
    """
    Escape single quotes, double quotes, newlines and other characters
    that may break JavaScript.
    """
    # Replace single quotes
    message = message.replace("'", "")
    # Replace double quotes
    message = message.replace('"', "")
    # Replace newlines
    message = message.replace("\n", "\\n")
    # Replace carriage return
    message = message.replace("\r", "\\r")
    # Replace horizontal tab
    message = message.replace("\t", "\\t")
    # Replace backspace
    message = message.replace("\b", "\\b")
    # Replace form feed
    message = message.replace("\f", "\\f")
    return message


##################
#   AJAX Views   #
##################


class OplogMuteToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the ``mute_notifications`` field of an individual :model:`oplog.Oplog`."""

    model = Oplog

    def test_func(self):
        # Only allow managers and admins to mute notifications
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        data = {"result": "error", "message": "Only a manager or admin can mute notifications."}
        return JsonResponse(data, status=403)

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            if obj.mute_notifications:
                obj.mute_notifications = False
                data = {
                    "result": "success",
                    "message": "Log monitor notifications have been unmuted.",
                    "toggle": 0,
                }
            else:
                obj.mute_notifications = True
                data = {
                    "result": "success",
                    "message": "Log monitor notifications have been muted.",
                    "toggle": 1,
                }
            obj.save()
            logger.info(
                "Toggled notifications for %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update mute status for log monitor notifications."}

        return JsonResponse(data)


def parse_fields(data: dict, entry_field_specs: dict) -> tuple:
    """
    Parse a dictionary of fields and return a list of fields and extra fields.

    **Parameters**

    ``data`` (dict)
        Dictionary of fields
    ``entry_field_specs`` (dict)
        Dictionary of field specifications
    """
    fields = [field["name"] for field in data]
    extra_fields = []
    # Remove any extra fields from the list of fields
    for field_spec in entry_field_specs:
        if field_spec["internal_name"] in fields:
            fields.pop(fields.index(field_spec["internal_name"]))
            extra_fields.append(field_spec["internal_name"])
    if extra_fields:
        fields.append("extra_fields")
    return fields, extra_fields


class OplogSanitize(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Sanitize all :model:`oplog.OplogEntry` objects associated with an individual :model:`oplog.Oplog`.

    Sanitization nullifies the `source_ip`, `dest_ip`, `description`, `output`, `user_context` and `comments` fields.
    It also removes everything after the first space in the `command` field. This action keeps the command while
    removing any arguments or options that may be sensitive (e.g., hashes, keys).
    """

    model = Oplog

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        data = {"result": "error", "message": "Only a manager or admin can choose to sanitize a log."}
        return JsonResponse(data, status=403)

    def post(self, *args, **kwargs):
        obj = self.get_object()
        data = self.request.POST.get("fields", None)
        try:
            json_data = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            json_data = None

        if json_data and len(json_data) > 0:
            entries = obj.entries.all()
            entry_field_specs = ExtraFieldsSpecSerializer(
                ExtraFieldSpec.objects.filter(target_model=OplogEntry._meta.label), many=True
            ).data
            fields, _ = parse_fields(json_data, entry_field_specs)

            logger.info(
                "Sanitizing log entries for %s %s by request of %s", obj.__class__.__name__, obj.id, self.request.user
            )
            data = {
                "result": "success",
                "message": "Successfully sanitized log entries.",
            }
            try:
                for entry in entries:
                    extra_fields_data = entry.extra_fields
                    for field in json_data:
                        for field_spec in entry_field_specs:
                            if field_spec["internal_name"] == field["name"]:
                                extra_fields_data[field["name"]] = None
                            else:
                                if field["name"] == "command":
                                    if entry.command:
                                        setattr(entry, field["name"], entry.command.split(" ")[0])
                                else:
                                    setattr(entry, field["name"], None)
                    entry.extra_fields = extra_fields_data
                try:
                    OplogEntry.objects.bulk_update(entries, fields)
                except FieldDoesNotExist as exception:
                    logger.error("One of the fields submitted for sanitization does not exist: %s", exception)
                    data = {
                        "result": "failed",
                        "message": "One of the fields submitted for sanitization does not exist.",
                    }
            except Exception as exception:  # pragma: no cover
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                log_message = template.format(type(exception).__name__, exception.args)
                logger.error(log_message)
                data = {
                    "result": "failed",
                    "message": "An error occurred while sanitizing log entries.",
                }
        else:
            data = {
                "result": "failed",
                "message": "No fields selected for sanitization.",
            }
        return JsonResponse(data)


##################
# View Functions #
##################


def validate_headers(imported_data):
    """Validate the headers of the CSV file for an activity log import."""
    expected_header_count = collections.Counter([
        "entry_identifier",
        "start_date",
        "end_date",
        "source_ip",
        "dest_ip",
        "tool",
        "user_context",
        "command",
        "description",
        "output",
        "comments",
        "operator_name",
        "tags",
    ])
    actual_header_count = collections.Counter(imported_data.headers)
    num_extra_fields = actual_header_count.pop("extra_fields", 0)
    return expected_header_count == actual_header_count and num_extra_fields in (0,1)


def validate_log_selection(user, oplog_id):
    """Validate the log selection for an activity log import."""
    bad_selection = False
    if isinstance(oplog_id, str):
        if oplog_id.isdigit():
            oplog_id = int(oplog_id)
    if oplog_id and isinstance(oplog_id, int):
        try:
            oplog = Oplog.objects.get(id=oplog_id)
            if not oplog.user_can_view(user):
                bad_selection = True
        except Oplog.DoesNotExist:
            bad_selection = True
    else:
        bad_selection = True
    return not bad_selection


def import_data(request, oplog_id, new_entries, dry_run=False):
    """Import the data into a dataset for validation and import."""
    logger.info("Importing log data for log ID %s", oplog_id)
    dataset = Dataset()
    oplog_entry_resource = OplogEntryResource()
    try:
        imported_data = dataset.load(new_entries, format="csv")
    except csv.Error:  # pragma: no cover
        logger.exception("An error occurred while loading the CSV file for log import")
        messages.error(
            request,
            "Your log file could not be loaded. There may be cells that exceed the 128KB text size limit for CSVs.",
            extra_tags="alert-error",
        )
        return None

    if "oplog_id" in imported_data.headers:
        del imported_data["oplog_id"]

    if validate_headers(imported_data):
        imported_data.append_col([oplog_id] * len(imported_data), header="oplog_id")
        result = oplog_entry_resource.import_data(imported_data, dry_run=dry_run)
        return result

    messages.error(
        request,
        "Your log file needs the required header row and at least one entry.",
        extra_tags="alert-error",
    )
    return None


def handle_errors(request, result):
    """Handle errors from a dry run of an activity log import."""
    row_errors = result.row_errors()
    for (row, errors) in row_errors:
        error_message = escape_message(f"There was an error in row {row}: {errors[0].error}")
        for err in errors:
            logger.error("Could not import row %d", row, exc_info=err.error)
        messages.error(
            request,
            error_message,
            extra_tags="alert-danger",
        )
    for invalid_row in result.invalid_rows:
        error = str(invalid_row.error).replace("'", "")
        error_message = escape_message(
            f"There was a validation error in row {invalid_row.number} with these errors: {error}"
        )
        logger.error(error_message)
        messages.error(
            request,
            error_message,
            extra_tags="alert-danger",
        )


@login_required
def oplog_entries_import(request):
    """
    Import a collection of :model:`oplog.OplogEntry` entries for an individual
    :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_import.html`
    """

    logs = Oplog.for_user(request.user)
    if request.method == "POST":
        oplog_id = request.POST.get("oplog_id")
        new_entries = request.FILES["csv_file"].read().decode("iso-8859-1")

        if not new_entries or not validate_log_selection(request.user, oplog_id):
            messages.error(
                request, "Your log file needs the required header row and at least one entry.", extra_tags="alert-error"
            )
            return HttpResponseRedirect(reverse("oplog:oplog_import"))

        imported_data = import_data(request, oplog_id, new_entries, dry_run=True)

        if imported_data is None:
            return HttpResponseRedirect(reverse("oplog:oplog_import"))

        if imported_data.has_errors() or imported_data.has_validation_errors():
            handle_errors(request, imported_data)
            return HttpResponseRedirect(reverse("oplog:oplog_import"))

        import_data(request, oplog_id, new_entries)
        messages.success(request, "Successfully imported log data.", extra_tags="alert-success")
        return HttpResponseRedirect(reverse("oplog:oplog_entries", kwargs={"pk": oplog_id}))

    log_id = request.GET.get("log", None)
    initial_log = None
    if log_id:
        for log in logs:
            if log_id == str(log.id):
                initial_log = log
    return render(request, "oplog/oplog_import.html", context={"logs": logs, "initial_log": initial_log})


################
# View Classes #
################


class OplogListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of :model:`oplog.Oplog`. Only show logs associated with :model:`rolodex.Project`
    to which the user has access.

    **Template**

    :template:`oplog/oplog_list.html`
    """

    model = Oplog
    template_name = "oplog/oplog_list.html"

    def get_queryset(self):
        queryset = Oplog.for_user(self.request.user)
        return queryset


class OplogListEntries(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`oplog.Oplog`.

    **Context**

    ``entries``
        :model:`oplog:OplogEntry` entries associated with the :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_detail.html`
    """

    model = Oplog

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["oplog_entry_extra_fields_spec_ser"] = ExtraFieldsSpecSerializer(
            ExtraFieldSpec.objects.filter(target_model=OplogEntry._meta.label), many=True
        ).data
        return ctx


class OplogCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual instance of :model:`oplog.Oplog`.

    **Context**

    ``project``
        Instance of :model:`rolodex.Project` associated with this log
    ``cancel_link``
        Link for the form's Cancel button to return to oplog list or details page

    **Template**

    :template:`oplog/oplog_form.html`
    """

    model = Oplog
    form_class = OplogForm

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Check if this request is for a specific project or not
        self.project = ""
        # Determine if ``pk`` is in the kwargs
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk")
            # Try to get the project from :model:`rolodex.Project`
            if pk:
                try:
                    project = get_object_or_404(Project, pk=self.kwargs.get("pk"))
                    if project.user_can_edit(self.request.user):
                        self.project = project
                except Project.DoesNotExist:
                    logger.info(
                        "Received log create request for project ID %s, but that project does not exist",
                        pk,
                    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"project": self.project, "user": self.request.user})
        return kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project
        if self.project:
            ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.project.pk})
        else:
            ctx["cancel_link"] = reverse("oplog:index")
        return ctx

    def get_form(self, form_class=None):
        form = super().get_form(form_class)
        if not form.fields["project"].queryset:
            messages.error(
                self.request,
                "There are no active projects for a new activity log.",
                extra_tags="alert-error",
            )
        return form

    def get_initial(self):
        if self.project:
            name = f"{self.project.client} {self.project.project_type} Log"
            return {"name": name, "project": self.project.id}
        return {}

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully created new operation log",
            extra_tags="alert-success",
        )
        return reverse("oplog:index")


class OplogUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_form.html`
    """

    model = Oplog
    form_class = OplogForm

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.id,))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("oplog:oplog_entries", kwargs={"pk": self.object.pk})
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class AjaxTemplateMixin:
    def __init__(self):
        pass

    def dispatch(self, request, *args, **kwargs):
        if not hasattr(self, "ajax_template_name"):
            split = self.template_name.split(".html")
            split[-1] = "_inner"
            split.append(".html")
            self.ajax_template_name = "".join(split)
        # NOTE: this is JQuery specific
        if request.META.get("HTTP_X_REQUESTED_WITH") == "XMLHttpRequest":
            self.template_name = self.ajax_template_name
        return super().dispatch(request, *args, **kwargs)


class OplogEntryCreate(RoleBasedAccessControlMixin, AjaxTemplateMixin, CreateView):
    """
    Create an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplog_modal.html`
    """

    model = OplogEntry
    form_class = OplogEntryForm
    template_name = "oplog/oplogentry_form.html"
    ajax_template_name = "oplog/snippets/oplogentry_form_inner.html"

    def test_func(self):
        return OplogEntry.user_can_create(self.request.user, self.get_object())

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))

    def form_valid(self, form):
        # Add defaults for extra fields
        form.instance.extra_fields = ExtraFieldSpec.initial_json(self.model)
        return super().form_valid(self, form)


class OplogEntryUpdate(RoleBasedAccessControlMixin, AjaxTemplateMixin, UpdateView):
    """
    Update an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplog_modal.html`
    """

    model = OplogEntry
    form_class = OplogEntryForm
    template_name = "oplog/oplogentry_form.html"
    ajax_template_name = "oplog/snippets/oplogentry_form_inner.html"

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogEntryDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual :model:`oplog.OplogEntry`.
    """

    model = OplogEntry
    fields = "__all__"

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogExport(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Export the :oplog:`oplog.Entries` for an individual :model:`oplog.Oplog` in a csv format."""

    model = Oplog

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def get(self, *args, **kwargs):
        obj = self.get_object()

        queryset = obj.entries.all()
        opts = queryset.model._meta

        response = HttpResponse(content_type="text/csv")
        add_content_disposition_header(response, f"{obj.name}.csv")

        writer = csv.writer(response)
        field_names = [field.name for field in opts.fields]
        field_names.remove("id")

        # Add the tags field to the list of fields
        field_names.append("tags")

        # Write the headers to the csv file
        writer.writerow(field_names)

        for obj in queryset:
            values = []
            for field in field_names:
                # Special case for oplog_id to write the ID of the oplog instead of the object
                if field == "oplog_id":
                    values.append(getattr(obj, field).id)
                # Special case for tags to write a comma-separated list of tag names
                elif field == "tags":
                    values.append(", ".join([tag.name for tag in obj.tags.all()]))
                else:
                    values.append(getattr(obj, field))
            writer.writerow(values)

        return response
