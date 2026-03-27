"""This contains all the views used by the Oplog application."""

# Standard Libraries
import collections
import csv
from datetime import datetime
import io
import json
import logging
import mimetypes
import os
import tempfile
import zipfile
from itertools import count

# Django Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import transaction
from django.http import FileResponse, Http404, HttpResponse, HttpResponseRedirect, JsonResponse
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
from ghostwriter.oplog.forms import OplogEntryForm, OplogEvidenceForm, OplogForm
from ghostwriter.oplog.models import Oplog, OplogEntry, OplogEntryEvidence, OplogEntryRecording
from ghostwriter.oplog.utils import extract_cast_text
from ghostwriter.reporting.models import Report
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

class OplogSanitize(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Sanitize all :model:`oplog.OplogEntry` objects associated with an individual :model:`oplog.Oplog`.

    Sanitization nullifies the `source_ip`, `dest_ip`, `description`, `output`, `user_context` and `comments` fields.
    It also removes everything after the first space in the `command` field. This action keeps the command while
    removing any arguments or options that may be sensitive (e.g., hashes, keys).
    """

    model = Oplog

    clearable_fields = {
        "identifier",
        "start_date",
        "end_date",
        "source_ip",
        "dest_ip",
        "tool",
        "user_context",
        "description",
        "output",
        "comments",
        "operator_name",
    }

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        data = {"result": "error", "message": "Only a manager or admin can choose to sanitize a log."}
        return JsonResponse(data, status=403)

    def post(self, *args, **kwargs):
        obj = self.get_object()
        data = self.request.POST.get("fields", None)
        try:
            fields_json = json.loads(data)
        except (json.JSONDecodeError, TypeError):
            fields_json = []

        # Extract ``sanitize_recordings`` flag from the posted JSON before the existing field filtering
        sanitize_recordings = any(field["name"] == "recordings" for field in fields_json)

        entry_field_specs = {spec.internal_name: spec for spec in ExtraFieldSpec.for_model(OplogEntry)}
        fields = [
            field["name"]
            for field in fields_json
            if field["name"] == "command"
                or field["name"] == "tags"
                or field["name"] in self.clearable_fields
                or field["name"] in entry_field_specs
        ]

        bulk_update_fields = [
            field["name"]
            for field in fields_json
            if field["name"] == "command"
                or field["name"] == "tags"
                or field["name"] in self.clearable_fields
        ]
        if any(field["name"] in entry_field_specs for field in fields_json):
            bulk_update_fields.append("extra_fields")

        # Allows a recordings-only sanitization that doesn't require any field selections, since recordings are handled separately
        if fields or sanitize_recordings:
            entries = obj.entries.all()
            logger.info(
                "Sanitizing log entries for %s %s by request of %s", obj.__class__.__name__, obj.id, self.request.user
            )
            data = {
                "result": "success",
                "message": "Successfully sanitized log entries.",
            }
            try:
                for entry in entries:
                    # Only process fields if non-recording fields were selected; otherwise skip directly to recording sanitization
                    if fields:
                        extra_fields_data = entry.extra_fields
                        for field in fields:
                            if field == "command":
                                if entry.command:
                                    setattr(entry, field, entry.command.split(" ")[0])
                            elif field == "tags":
                                entry.tags.clear()
                            elif field in self.clearable_fields:
                                setattr(entry, field, "")
                            elif field in entry_field_specs:
                                extra_fields_data[field] = entry_field_specs[field].empty_value()
                        entry.extra_fields = extra_fields_data

                    if sanitize_recordings:
                        try:
                            entry.recording.delete()
                        except OplogEntryRecording.DoesNotExist:
                            pass

                # Only perform a bulk update if there are non-recording fields to update
                if fields:
                    OplogEntry.objects.bulk_update(entries, bulk_update_fields, batch_size=100)
            except Exception as exception:  # pragma: no cover
                template = "An exception of type {0} occurred. Arguments:\n{1!r}"
                log_message = template.format(type(exception).__name__, exception.args)
                logger.exception(log_message)
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
        queryset = (
            Oplog.for_user(self.request.user)
            .select_related("project", "project__client", "project__project_type")
        )
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
        ctx["project_has_reports"] = Report.objects.filter(
            project=self.object.project
        ).exists()
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

    def get_initial(self):
        initial = super().get_initial()
        initial["extra_fields"] = ExtraFieldSpec.initial_json(self.model)
        return initial


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
    valid_include_values = {"recordings", "evidence", "all"}
    attachment_chunk_size = 1024 * 1024
    recoverable_attachment_errors = (OSError, RuntimeError, TypeError, ValueError)
    path_lookup_errors = (AttributeError, NotImplementedError, OSError, TypeError, ValueError)
    close_errors = (AttributeError, OSError, ValueError)

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("oplog:index")

    def _write_file_to_zip(self, zf, field_file, arcname):
        """Write a storage-backed file into the ZIP without reading the whole file into memory."""
        try:
            path = field_file.path
            if os.path.exists(path):
                zf.write(path, arcname)
                return True
        except self.path_lookup_errors:
            pass

        try:
            field_file.open("rb")
            with zf.open(arcname, "w") as zip_member:
                for chunk in field_file.chunks(self.attachment_chunk_size):
                    zip_member.write(chunk)
            return True
        finally:
            try:
                field_file.close()
            except self.close_errors:
                pass

    @staticmethod
    def _next_arcname(directory, entry_id, basename, used_names):
        """Generate a unique archive name for an attachment inside the ZIP."""
        stem, ext = os.path.splitext(basename)
        for index in count():
            suffix = "" if index == 0 else f"_{index}"
            arcname = f"{directory}/{entry_id}_{stem}{suffix}{ext}"
            if arcname not in used_names:
                used_names.add(arcname)
                return arcname

    def get(self, *args, **kwargs):
        obj = self.get_object()

        # Determine whether attachments should be included. Accepted values:
        # - no param / empty: CSV only (existing behavior)
        # - include=recordings
        # - include=evidence
        # - include=all
        include_param = (self.request.GET.get("include") or "").lower()
        include_set = {p.strip() for p in include_param.split(",") if p.strip()}
        invalid_include_values = include_set - self.valid_include_values
        if invalid_include_values:
            invalid_options = ", ".join(sorted(invalid_include_values))
            return HttpResponse(
                f"Invalid include value(s): {invalid_options}",
                status=400,
                content_type="text/plain",
            )

        queryset = obj.entries.select_related("recording").prefetch_related("tags", "evidence_links__evidence")
        opts = queryset.model._meta

        # Prepare CSV data into memory (small) for inclusion in ZIP
        field_names = [field.name for field in opts.fields]
        if "id" in field_names:
            field_names.remove("id")
        # Add the tags field to the list of fields
        if "tags" not in field_names:
            field_names.append("tags")

        # If no attachments requested, return original CSV response for compatibility
        if not include_set:
            response = HttpResponse(content_type="text/csv")
            add_content_disposition_header(response, f"{obj.name}.csv")
            writer = csv.writer(response)
            writer.writerow(field_names)
            for entry in queryset:
                tag_names = ", ".join(tag.name for tag in entry.tags.all())
                values = []
                for field in field_names:
                    if field == "oplog_id":
                        values.append(getattr(entry, field).id)
                    elif field == "tags":
                        values.append(tag_names)
                    else:
                        values.append(getattr(entry, field))
                writer.writerow(values)
            return response

        # Build the ZIP in a spooled temp file so small exports stay in memory and
        # larger ones spill to disk without buffering every attachment in RAM.
        # Do not wrap this in ``with``: FileResponse needs the file handle to remain
        # open after this method returns so Django can stream it to the client.
        tmp = tempfile.SpooledTemporaryFile(max_size=50 * 1024 * 1024, mode="w+b")
        manifest = {"generated_at": datetime.utcnow().isoformat() + "Z", "entries": {}}
        attachments_map = {}
        used_archive_names = set()
        try:
            with zipfile.ZipFile(tmp, "w", compression=zipfile.ZIP_DEFLATED) as zf:
                # First pass: collect and add attachment files, record filenames per entry
                for entry in queryset:
                    attachments_map[str(entry.id)] = {"recordings": [], "evidence": []}
                    # Recordings
                    if "recordings" in include_set or "all" in include_set:
                        try:
                            rec = entry.recording
                            if rec.recording_file:
                                fname = os.path.basename(rec.recording_file.name)
                                arcname = self._next_arcname("recordings", entry.id, fname, used_archive_names)
                                try:
                                    self._write_file_to_zip(zf, rec.recording_file, arcname)
                                except self.recoverable_attachment_errors:
                                    logger.exception("Could not include recording for entry %s", entry.id)
                                    continue
                                attachments_map[str(entry.id)]["recordings"].append(arcname)
                        except OplogEntryRecording.DoesNotExist:
                            pass

                    # Evidence files
                    if "evidence" in include_set or "all" in include_set:
                        links = entry.evidence_links.all()
                        for link in links:
                            ev = link.evidence
                            if ev.document:
                                fname = os.path.basename(ev.document.name)
                                arcname = self._next_arcname("evidence", entry.id, fname, used_archive_names)
                                try:
                                    self._write_file_to_zip(zf, ev.document, arcname)
                                except self.recoverable_attachment_errors:
                                    logger.exception(
                                        "Could not include evidence %s for entry %s",
                                        getattr(ev, "pk", "?"),
                                        entry.id,
                                    )
                                    continue
                                attachments_map[str(entry.id)]["evidence"].append(arcname)

                    if attachments_map[str(entry.id)]["recordings"] or attachments_map[str(entry.id)]["evidence"]:
                        manifest["entries"][str(entry.id)] = {
                            "recordings": attachments_map[str(entry.id)]["recordings"],
                            "evidence": attachments_map[str(entry.id)]["evidence"],
                        }

                # After attachments are added, build CSV text including attachment columns
                # Extend field_names with attachment columns when relevant
                if "recordings" in include_set or "all" in include_set:
                    if "recordings" not in field_names:
                        field_names.append("recordings")
                if "evidence" in include_set or "all" in include_set:
                    if "evidence" not in field_names:
                        field_names.append("evidence")

                csv_buf = io.StringIO()
                csv_writer = csv.writer(csv_buf)
                csv_writer.writerow(field_names)
                for entry in queryset:
                    tag_names = ", ".join(tag.name for tag in entry.tags.all())
                    values = []
                    for field in field_names:
                        if field == "oplog_id":
                            values.append(getattr(entry, field).id)
                        elif field == "tags":
                            values.append(tag_names)
                        elif field == "recordings":
                            values.append(", ".join(attachments_map.get(str(entry.id), {}).get("recordings", [])))
                        elif field == "evidence":
                            values.append(", ".join(attachments_map.get(str(entry.id), {}).get("evidence", [])))
                        else:
                            values.append(getattr(entry, field))
                    csv_writer.writerow(values)
                zf.writestr(f"{obj.name}.csv", csv_buf.getvalue().encode("utf-8"))

                # Add manifest.json for mapping and metadata
                zf.writestr("manifest.json", json.dumps(manifest, indent=2))

            # Rewind temp file and return it as a response body
            tmp.seek(0)
            zip_name = f"{obj.name}_attachments.zip"
            response = FileResponse(tmp, as_attachment=True, filename=zip_name, content_type="application/zip")
            return response
        except Exception:
            logger.exception("Failed while creating ZIP export for oplog %s", obj.id)
            tmp.close()
            raise


class OplogEvidenceCreate(RoleBasedAccessControlMixin, View):
    """
    Upload an :model:`reporting.Evidence` file and link it to an :model:`oplog.OplogEntry`
    via an :model:`oplog.OplogEntryEvidence`.

    Returns form HTML on GET (for AJAX modal), JSON response on POST.
    """

    def get_entry(self):
        return get_object_or_404(OplogEntry, pk=self.kwargs["pk"])

    def test_func(self):
        return self.get_entry().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return JsonResponse({"result": "error", "message": "You do not have permission to access that."}, status=403)

    def get(self, request, *args, **kwargs):
        entry = self.get_entry()
        project = entry.oplog_id.project
        active_report_id = None
        try:
            active = request.session.get("active_report") or {}
            active_report_id = int(active.get("id", 0)) or None
        except (TypeError, ValueError, AttributeError):
            active_report_id = None
        form = OplogEvidenceForm(project=project, active_report_id=active_report_id)
        form.helper.form_action = reverse("oplog:oplog_entry_evidence_upload", kwargs={"pk": entry.pk})
        return render(request, "oplog/snippets/oplog_evidence_form_inner.html", {"form": form})

    def post(self, request, *args, **kwargs):
        entry = self.get_entry()
        project = entry.oplog_id.project
        form = OplogEvidenceForm(request.POST, request.FILES, project=project)
        if form.is_valid():
            with transaction.atomic():
                evidence = form.save(commit=False)
                evidence.uploaded_by = request.user
                evidence.save()
                form.save_m2m()
                OplogEntryEvidence.objects.create(oplog_entry=entry, evidence=evidence)
            return JsonResponse({
                "result": "success",
                "evidence_id": evidence.pk,
                "friendly_name": evidence.friendly_name,
            })
        # Return the form with errors for re-rendering in the modal
        form.helper.form_action = reverse("oplog:oplog_entry_evidence_upload", kwargs={"pk": entry.pk})
        return render(request, "oplog/snippets/oplog_evidence_form_inner.html", {"form": form})


class OplogEntryEvidenceList(RoleBasedAccessControlMixin, View):
    """Return a JSON list of :model:`reporting.Evidence` linked to an :model:`oplog.OplogEntry`."""

    def get_entry(self):
        return get_object_or_404(OplogEntry, pk=self.kwargs["pk"])

    def test_func(self):
        return self.get_entry().user_can_view(self.request.user)

    def handle_no_permission(self):
        return JsonResponse({"result": "error", "message": "You do not have permission to access that."}, status=403)

    def get(self, request, *args, **kwargs):
        entry = self.get_entry()
        links = entry.evidence_links.select_related("evidence", "evidence__uploaded_by").all()
        evidence_list = []
        for link in links:
            ev = link.evidence
            evidence_list.append({
                "id": ev.pk,
                "friendly_name": ev.friendly_name,
                "caption": ev.caption,
                "document_url": reverse("reporting:evidence_download", kwargs={"pk": ev.pk}) + "?view=1" if ev.document else "",
                "filename": ev.document.name.split("/")[-1] if ev.document else "",
                "link_id": link.pk,
                "uploaded_by_user": ev.uploaded_by_user,
            })
        return JsonResponse({"result": "success", "evidence": evidence_list})


class OplogRecordingUpload(RoleBasedAccessControlMixin, View):
    """
    Upload or replace the Asciinema terminal recording for an :model:`oplog.OplogEntry`.

    Returns a JSON response.
    """

    def get_entry(self):
        return get_object_or_404(OplogEntry, pk=self.kwargs["pk"])

    def test_func(self):
        return self.get_entry().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return JsonResponse({"result": "error", "message": "You do not have permission to access that."}, status=403)

    def post(self, request, *args, **kwargs):
        entry = self.get_entry()
        recording_file = request.FILES.get("recording_file")
        if not recording_file:
            return JsonResponse({"result": "error", "message": "No file provided."}, status=400)
        filename_lower = recording_file.name.lower()
        if not (filename_lower.endswith(".cast") or filename_lower.endswith(".cast.gz")):
            return JsonResponse({"result": "error", "message": "Only .cast and .cast.gz files are accepted."}, status=400)
        # Replace any existing recording
        try:
            entry.recording.delete()
        except OplogEntryRecording.DoesNotExist:
            pass

        # Extract searchable text from the cast file before saving
        file_content = recording_file.read()
        recording_file.seek(0)
        recording_text, text_warning = extract_cast_text(file_content)

        recording = OplogEntryRecording(oplog_entry=entry, uploaded_by=request.user)
        recording.recording_file = recording_file
        recording.recording_text = recording_text
        recording.save()
        response = {
            "result": "success",
            "recording_url": reverse("oplog:oplog_entry_recording_download", kwargs={"pk": recording.pk}),
        }
        if text_warning:
            response["warning"] = text_warning
        return JsonResponse(response)


class OplogRecordingDelete(RoleBasedAccessControlMixin, View):
    """Delete the Asciinema terminal recording for an :model:`oplog.OplogEntry`."""

    def get_entry(self):
        return get_object_or_404(OplogEntry, pk=self.kwargs["pk"])

    def test_func(self):
        return self.get_entry().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return JsonResponse({"result": "error", "message": "You do not have permission to access that."}, status=403)

    def post(self, request, *args, **kwargs):
        entry = self.get_entry()
        try:
            entry.recording.delete()
            logger.info("Deleted recording for %s %s by request of %s", entry.__class__.__name__, entry.id, self.request.user)
            return JsonResponse({"result": "success"})
        except OplogEntryRecording.DoesNotExist:
            return JsonResponse({"result": "error", "message": "No recording found."}, status=404)


class OplogRecordingDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Serve the Asciinema recording file for an :model:`oplog.OplogEntryRecording`."""

    model = OplogEntryRecording

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        return JsonResponse({"result": "error", "message": "You do not have permission to access that."}, status=403)

    def get(self, request, *args, **kwargs):
        recording = self.get_object()
        file_path = recording.recording_file.path
        if os.path.exists(file_path):
            # Detect the content type
            content_type, _ = mimetypes.guess_type(file_path)
            if content_type is None:
                content_type = "application/octet-stream"

            # Check if inline viewing is explicitly requested via query parameter
            # Default to download (as_attachment=True) for security
            inline_view = request.GET.get("view", "").lower() in ("1", "true", "yes")

            # Check if file is gzipped - if so, serve with Content-Encoding: gzip
            # so the browser decompresses it for the Asciinema player
            is_gzipped = file_path.lower().endswith(".gz")

            response = FileResponse(
                open(file_path, "rb"),
                as_attachment=not inline_view,
                filename=recording.filename,
                content_type=content_type,
            )

            # Add security headers to mitigate XSS risks
            response["X-Content-Type-Options"] = "nosniff"
            if inline_view:
                # Additional hardening for inline content
                response["Content-Security-Policy"] = "default-src 'none'; img-src 'self'; style-src 'unsafe-inline'"

            # For gzipped files, add Content-Encoding header so browser decompresses
            if is_gzipped:
                response["Content-Encoding"] = "gzip"

            return response
        raise Http404
