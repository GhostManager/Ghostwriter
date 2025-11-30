"""This contains all the views used by the Rolodex application."""

# Standard Libraries
import base64
import binascii
import copy
import csv
import datetime
import io
import json
import logging
import re
from typing import Any, Dict, List, Optional, Set
from xml.etree import ElementTree

# Django Imports
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
from django.core.files.base import ContentFile
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import ListView
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View

# 3rd Party Libraries
from taggit.models import Tag

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    ForbiddenJsonResponse,
    RoleBasedAccessControlMixin,
    get_client_list,
    get_project_list,
    verify_user_is_privileged,
)
from ghostwriter.commandcenter.models import ExtraFieldSpec, ReportConfiguration
from ghostwriter.modules import codenames
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.modules.reportwriter.base import ReportExportTemplateError
from ghostwriter.modules.reportwriter.project.json import ExportProjectJson
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.reporting.models import ReportTemplate
from ghostwriter.rolodex.filters import ClientFilter, ProjectFilter
from ghostwriter.rolodex.forms_client import (
    ClientContactFormSet,
    ClientForm,
    ClientInviteFormSet,
    ClientNoteForm,
)
from ghostwriter.rolodex.forms_project import (
    DeconflictionForm,
    ProjectAssignmentFormSet,
    ProjectComponentForm,
    ProjectContactFormSet,
    ProjectForm,
    ProjectNoteForm,
    ProjectObjectiveFormSet,
    ProjectScopeFormSet,
    ProjectTargetFormSet,
    WhiteCardFormSet,
)
from ghostwriter.rolodex.forms_workbook import (
    ProjectDataFileForm,
    ProjectDataResponsesForm,
    ProjectIPArtifactForm,
    ProjectWorkbookForm,
)
from ghostwriter.rolodex.models import (
    PROJECT_SCOPING_CONFIGURATION,
    Client,
    ClientContact,
    ClientInvite,
    ClientNote,
    Deconfliction,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectDataFile,
    ProjectAssignment,
    ProjectContact,
    ProjectInvite,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
    normalize_project_scoping,
)
from ghostwriter.rolodex.ip_artifacts import IP_ARTIFACT_DEFINITIONS, IP_ARTIFACT_ORDER
from ghostwriter.rolodex.data_parsers import (
    NEXPOSE_METRICS_KEY_MAP,
    NEXPOSE_METRICS_LABELS,
    normalize_nexpose_artifacts_map,
    resolve_nexpose_requirement_artifact_key,
    summarize_nexpose_matrix_gaps,
    summarize_web_issue_matrix_gaps,
)
from ghostwriter.rolodex.workbook import (
    SECTION_ENTRY_FIELD_MAP,
    build_data_configuration,
    build_scope_summary,
    build_workbook_sections,
    normalize_scope_selection,
    prepare_data_responses_initial,
)
from ghostwriter.rolodex.workbook_defaults import (
    WORKBOOK_DEFAULTS,
    ensure_data_responses_defaults,
    normalize_workbook_payload,
)
from ghostwriter.rolodex.workbook import _slugify_identifier
from ghostwriter.rolodex.workbook_entry import OSINT_FIELDS, build_workbook_entry_payload
from ghostwriter.shepherd.models import History, ServerHistory, TransientServer
from ghostwriter.reporting.models import RiskScoreRangeMapping

# Using __name__ resolves to ghostwriter.rolodex.views
logger = logging.getLogger(__name__)

AD_CSV_HEADER_MAP: dict[str, dict[str, str]] = {
    "domain_admins": {"account": "Account", "password last set": "Password Last Set"},
    "ent_admins": {"account": "Account", "password last set": "Password Last Set"},
    "exp_passwords": {"account": "Account", "password last set": "Password Last Set"},
    "passwords_never_exp": {"account": "Account", "password last set": "Password Last Set"},
    "inactive_accounts": {
        "account": "Account",
        "last login": "Last Login",
        "creation date": "Creation Date",
        "days past": "Days Past",
    },
    "generic_accounts": {
        "account": "Account",
        "creation date": "Creation Date",
    },
    "old_passwords": {
        "account": "Account",
        "password last set date": "Password Last Set Date",
        "days past due": "Days Past Due",
    },
    "generic_logins": {"computer": "Computer", "username": "Username"},
}


def _is_empty_response(value: Any) -> bool:
    if value in (None, "", (), []):
        return True
    if isinstance(value, dict):
        return not value
    return False


def _build_grouped_data_responses(
    responses: Dict[str, Any],
    question_definitions: List[Dict[str, Any]],
    existing_grouped: Optional[Dict[str, Any]] = None,
    workbook_data: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    normalized = dict(responses or {})
    wireless_values = normalized.pop("wireless", None)
    scope_count = normalized.pop("scope_count", None)
    scope_string = normalized.pop("scope_string", None)

    definition_map = {definition["key"]: definition for definition in question_definitions}
    grouped: Dict[str, Any] = copy.deepcopy(existing_grouped or {})

    for key, value in normalized.items():
        definition = definition_map.get(key)
        if not definition:
            if not _is_empty_response(value):
                grouped[key] = value
            continue

        section_key = definition.get("section_key") or key
        subheading = definition.get("subheading")
        if _is_empty_response(value):
            section = grouped.get(section_key)
            if isinstance(section, dict):
                if subheading:
                    entry_slug = definition.get("entry_slug") or key
                    field_key = definition.get("entry_field_key") or key
                    identifier_field = SECTION_ENTRY_FIELD_MAP.get(section_key, "name")
                    entries = section.get("entries")
                    if isinstance(entries, list):
                        to_remove = None
                        for item in entries:
                            if not isinstance(item, dict):
                                continue
                            slug_value = item.get("slug") or item.get("_slug")
                            if slug_value == entry_slug or item.get(identifier_field) == subheading:
                                item.pop(field_key, None)
                                significant_keys = {
                                    key_name
                                    for key_name in item.keys()
                                    if key_name not in {identifier_field, "_slug", "slug"}
                                }
                                if not significant_keys:
                                    to_remove = item
                                break
                        if to_remove is not None:
                            entries.remove(to_remove)
                            if not entries:
                                section.pop("entries", None)
                else:
                    storage_key = definition.get("storage_key") or key
                    if section_key == "overall_risk" and storage_key == "overall_risk_major_issues":
                        storage_key = "major_issues"
                    section.pop(storage_key, None)
                    if not section:
                        grouped.pop(section_key, None)
            continue

        if subheading:
            section = grouped.setdefault(section_key, {})
            entries = section.setdefault("entries", [])
            entry_slug = definition.get("entry_slug") or key
            field_key = definition.get("entry_field_key") or key
            identifier_field = SECTION_ENTRY_FIELD_MAP.get(section_key, "name")
            identifier_value = subheading

            existing = None
            for item in entries:
                if not isinstance(item, dict):
                    continue
                slug_value = item.get("slug") or item.get("_slug")
                if slug_value == entry_slug or item.get(identifier_field) == identifier_value:
                    existing = item
                    break
            if existing is None:
                existing = {"slug": entry_slug}
                existing[identifier_field] = identifier_value
                entries.append(existing)
            existing[field_key] = value
        else:
            section = grouped.setdefault(section_key, {})
            storage_key = definition.get("storage_key") or key
            if section_key == "overall_risk" and storage_key == "overall_risk_major_issues":
                storage_key = "major_issues"
            section[storage_key] = value

    if isinstance(wireless_values, dict) and wireless_values:
        grouped["wireless"] = wireless_values

    if scope_count is not None or scope_string is not None:
        general_section = grouped.setdefault("general", {})
        if scope_count is not None:
            general_section["scope_count"] = scope_count
        if scope_string is not None and not _is_empty_response(scope_string):
            general_section["scope_string"] = scope_string

    # Remove slug metadata before returning while preserving ability to rehydrate during form initialisation.
    for section_key, section_value in list(grouped.items()):
        if not isinstance(section_value, dict):
            continue
        entries = section_value.get("entries")
        if not isinstance(entries, list):
            continue
        cleaned_entries = []
        for item in entries:
            if not isinstance(item, dict):
                continue
            cleaned = dict(item)
            slug_value = cleaned.pop("slug", None)
            # Preserve slug metadata internally for form hydration
            if slug_value:
                cleaned["_slug"] = slug_value
            cleaned_entries.append(cleaned)
        if cleaned_entries:
            section_value["entries"] = cleaned_entries
        else:
            section_value.pop("entries", None)

    if isinstance(workbook_data, dict):
        endpoint_section = grouped.get("endpoint")
        if isinstance(endpoint_section, dict):
            _merge_endpoint_summary(endpoint_section, workbook_data)

    return grouped


def _coerce_firewall_summary(summary: Dict[str, Any]) -> Dict[str, Any]:
    """Ensure firewall summaries include legacy aliases and default counters."""

    if not isinstance(summary, dict):
        return {}

    hydrated = dict(summary)

    hydrated.setdefault("unique", hydrated.get("total", 0))
    hydrated.setdefault("unique_high", hydrated.get("total_high", 0))
    hydrated.setdefault("unique_med", hydrated.get("total_med", 0))
    hydrated.setdefault("unique_low", hydrated.get("total_low", 0))

    hydrated.setdefault("total", hydrated.get("unique", 0))
    hydrated.setdefault("total_high", hydrated.get("unique_high", 0))
    hydrated.setdefault("total_med", hydrated.get("unique_med", 0))
    hydrated.setdefault("total_low", hydrated.get("unique_low", 0))

    hydrated.setdefault("rule_count", 0)
    hydrated.setdefault("config_count", 0)
    hydrated.setdefault("complexity_count", 0)
    hydrated.setdefault("vuln_count", 0)

    hydrated.setdefault("majority_type", "Even")
    hydrated.setdefault("minority_type", "Even")
    hydrated.setdefault("majority_count", 0)
    hydrated.setdefault("minority_count", 0)

    return hydrated


def _merge_endpoint_summary(section: Dict[str, Any], workbook_data: Dict[str, Any]) -> None:
    summary_keys = {
        "domains_str",
        "ood_count_str",
        "wifi_count_str",
        "ood_risk_string",
        "wifi_risk_string",
    }

    entries = section.get("entries")
    if not isinstance(entries, list) or not entries:
        for key in summary_keys:
            section.pop(key, None)
        return

    endpoint_data = workbook_data.get("endpoint", {})
    domain_records = endpoint_data.get("domains") if isinstance(endpoint_data, dict) else None
    domain_lookup: Dict[str, Dict[str, Any]] = {}

    if isinstance(domain_records, list):
        for record in domain_records:
            if not isinstance(record, dict):
                continue
            domain_value = record.get("domain") or record.get("name")
            domain_text = str(domain_value).strip() if domain_value else ""
            if domain_text:
                domain_lookup[domain_text] = record

    domains: List[str] = []
    ood_counts: List[str] = []
    wifi_counts: List[str] = []
    ood_risks: List[str] = []
    wifi_risks: List[str] = []
    cleaned_entries: List[Dict[str, Any]] = []

    def _format_count(value: Any) -> str:
        if value in (None, ""):
            return "0"
        return str(value)

    def _format_risk(value: Any) -> str:
        if value is None:
            return ""
        text = str(value).strip()
        return text.capitalize() if text else ""

    for raw_entry in entries:
        if not isinstance(raw_entry, dict):
            continue
        domain_value = raw_entry.get("domain") or raw_entry.get("name")
        domain_text = str(domain_value).strip() if domain_value else ""
        if not domain_text:
            continue
        entry = dict(raw_entry)
        entry["domain"] = domain_text
        cleaned_entries.append(entry)

        domains.append(domain_text)
        details = domain_lookup.get(domain_text, {})

        if isinstance(details, dict):
            systems_ood = details.get("systems_ood")
            open_wifi = details.get("open_wifi")
        else:
            systems_ood = None
            open_wifi = None

        ood_counts.append(_format_count(systems_ood))
        wifi_counts.append(_format_count(open_wifi))
        ood_risks.append(_format_risk(entry.get("av_gap")))
        wifi_risks.append(_format_risk(entry.get("open_wifi")))

    if not cleaned_entries:
        for key in summary_keys:
            section.pop(key, None)
        section.pop("entries", None)
        return

    section["entries"] = cleaned_entries
    section["domains_str"] = "/".join(domains)
    section["ood_count_str"] = "/".join(ood_counts)
    section["wifi_count_str"] = "/".join(wifi_counts)
    section["ood_risk_string"] = "/".join(ood_risks)
    section["wifi_risk_string"] = "/".join(wifi_risks)


##################
#   AJAX Views   #
##################


@login_required
def update_project_badges(request, pk):
    """
    Return an updated version of the template following a delete action related to
    an individual :model:`rolodex.Project`.

    **Template**

    :template:`snippets/project_nav_tabs.html`
    """
    project_instance = get_object_or_404(Project, pk=pk)

    if not project_instance.user_can_edit(request.user):
        return ForbiddenJsonResponse()

    html = render_to_string(
        "snippets/project_nav_tabs.html",
        {"project": project_instance},
    )
    return HttpResponse(html)


@login_required
def update_client_badges(request, pk):
    """
    Return an updated version of the template following a delete action related to
    an individual :model:`rolodex.Client`.

    **Template**

    :template:`snippets/client_nav_tabs.html`
    """
    client_instance = get_object_or_404(Client, pk=pk)

    if not client_instance.user_can_edit(request.user):
        return ForbiddenJsonResponse()

    html = render_to_string(
        "snippets/client_nav_tabs.html",
        {"client": client_instance, "request": request},
    )
    return HttpResponse(html)


@login_required
def update_project_contacts(request, pk):
    """
    Return an updated version of the template following the addition of a new
    :model:`rolodex.ProjectContact` entry.

    **Template**

    :template:`snippets/project_contacts_table.html`
    """
    project_instance = get_object_or_404(Project, pk=pk)

    if not project_instance.user_can_edit(request.user):
        return ForbiddenJsonResponse()

    contacts = ClientContact.objects.filter(client=project_instance.client)
    for contact in contacts:
        if (
            ProjectContact.objects.filter(
                name=contact.name,
                email=contact.email,
                phone=contact.phone,
                project=project_instance,
            ).count()
            > 0
        ):
            contacts = contacts.exclude(id=contact.id)

    html = render_to_string(
        "snippets/project_contacts_table.html",
        {"project": project_instance, "client_contacts": contacts},
    )
    return HttpResponse(html)


@login_required
def roll_codename(request):
    """Fetch a unique codename for use with a model."""
    try:
        codename_verified = False
        new_codename = None
        while not codename_verified:
            new_codename = codenames.codename(uppercase=True)
            if (
                not Project.objects.filter(codename__iexact=new_codename).exists()
                and not Client.objects.filter(codename__iexact=new_codename).exists()
            ):
                codename_verified = True
        data = {
            "result": "success",
            "message": "Codename successfully generated",
            "codename": new_codename,
        }
        logger.info(
            "Generated new codename at request of %s",
            request.user,
        )
    except Exception as exception:  # pragma: no cover
        template = "An exception of type {0} occurred. Arguments:\n{1!r}"
        log_message = template.format(type(exception).__name__, exception.args)
        logger.error(log_message)
        data = {"result": "error", "message": "Could not generate a codename"}

    return JsonResponse(data)


@login_required
def ajax_update_project_objectives(request):
    """
    Update the ``position`` and ``status`` fields of all :model:`rolodex.ProjectObjective`
    entries attached to an individual :model:`rolodex.Project`.
    """
    if request.method == "POST":
        data = request.POST.get("positions")
        project_id = request.POST.get("project")
        priority_class = request.POST.get("priority").replace("_priority", "")
        order = json.loads(data)

        project_instance = get_object_or_404(Project, id=project_id)
        if not project_instance.user_can_edit(request.user):
            return ForbiddenJsonResponse()

        logger.info(
            "Received AJAX POST to update project %s's %s objectives in this order: %s",
            project_id,
            priority_class,
            ", ".join(order),
        )

        try:
            priority = ObjectivePriority.objects.get(priority__iexact=priority_class)
        except ObjectivePriority.DoesNotExist:
            priority = None

        data = {"result": "success"}

        if priority:
            ignore = ["placeholder", "ignore"]
            counter = 1
            for objective_id in order:
                if not any(name in objective_id for name in ignore):
                    obj_instance = ProjectObjective.objects.get(id=objective_id)
                    if obj_instance:
                        obj_instance.priority = priority
                        obj_instance.position = counter
                        obj_instance.save()
                        counter += 1
                    else:
                        logger.error(
                            "Received an objective ID, %s, that did not match an existing objective",
                            objective_id,
                        )
                else:
                    logger.info("Ignored data-id value %s", objective_id)
        else:
            data = {"result": "specified priority, {}, is invalid".format(priority_class)}
    else:
        data = {"result": "error"}
    return JsonResponse(data)


class GenerateProjectReport(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Generates a project report"""

    model = Project

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def get(self, *args, **kwargs):
        project = self.get_object()

        type_or_template_id = self.kwargs["type_or_template_id"]
        try:
            type_or_template_id = int(type_or_template_id)
        except ValueError:
            pass

        report_config = ReportConfiguration.get_solo()

        try:
            if type_or_template_id == "json":
                exporter = ExportProjectJson(project)
                filename = exporter.render_filename(report_config.project_filename)
                out = exporter.run()
                mime = exporter.mime_type()
            else:
                template = (
                    ReportTemplate.objects.filter(
                        Q(doc_type__doc_type__iexact="project_docx") | Q(doc_type__doc_type__iexact="pptx")
                    )
                    .filter(Q(client=project.client) | Q(client__isnull=True))
                    .select_related("doc_type")
                    .get(pk=type_or_template_id)
                )
                exporter = template.exporter(project)
                filename = exporter.render_filename(template.filename_override or report_config.project_filename)
                out = exporter.run()
                mime = exporter.mime_type()
        except ReportExportTemplateError as error:
            logger.error("Project report failed for project %s and user %s: %s", project.id, self.request.user, error)
            messages.error(
                self.request,
                f"Error: {error}",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("rolodex:project_detail", kwargs={"pk": project.id}) + "#documents")
        response = HttpResponse(out.getvalue(), content_type=mime)
        add_content_disposition_header(response, filename)
        return response


class ProjectObjectiveStatusUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Update the ``status`` field of an individual :model:`rolodex.ProjectObjective`."""

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        objective = self.get_object()
        try:
            success = False
            # Save the old status
            old_status = objective.status
            # Get all available status
            all_status = ObjectiveStatus.objects.all()
            new_status = all_status[0]
            total_status = all_status.count()
            for i, status in enumerate(all_status):
                if status == old_status:
                    # Check if we're at the last status
                    next_index = i + 1
                    if total_status - 1 >= next_index:
                        new_status = all_status[next_index]
                    # If at end, roll-over to the first status
                    else:
                        new_status = all_status[0]

                    objective.status = new_status
                    logger.info("Switching to %s", new_status)
                    objective.save()
                    success = True

            if not success:
                logger.warning("Failed to match old status, %s, with any existing status, so set status to ``0``")
                objective.status = new_status
                objective.save()

            # Prepare the JSON response data
            data = {
                "result": "success",
                "status": new_status.objective_status,
            }
            logger.info(
                "Updated status of %s %s from %s to %s by request of %s",
                objective.__class__.__name__,
                objective.id,
                old_status,
                new_status,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update objective status"}

        return JsonResponse(data)


class ProjectStatusToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the ``complete`` field of an individual :model:`rolodex.Project`."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            if obj.complete:
                obj.complete = False
                data = {
                    "result": "success",
                    "message": "Project successfully marked as incomplete.",
                    "status": "In Progress",
                    "toggle": 0,
                }
            else:
                obj.complete = True
                data = {
                    "result": "success",
                    "message": "Project successfully marked as complete.",
                    "status": "Complete",
                    "toggle": 1,
                }
            obj.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update project status."}

        return JsonResponse(data)


class ProjectObjectiveDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ProjectObjective`."""

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Objective successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectAssignmentDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ProjectAssignment`."""

    model = ProjectAssignment

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Assignment successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ProjectNote`."""

    model = ProjectNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("rolodex:project_detail", kwargs={"pk": self.get_object().project.pk}) + "#notes")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ClientNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ClientNote`."""

    model = ClientNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("rolodex:client_detail", kwargs={"pk": self.get_object().client.pk}) + "#notes")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ClientContactDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ClientContact`."""

    model = ClientContact

    def test_func(self):
        return self.get_object().client.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Contact successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ClientInviteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ClientInvite`."""

    model = ClientInvite

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Invite successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectInviteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ProjectInvite`."""

    model = ProjectInvite

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Invite successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTargetDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`rolodex.ProjectTarget`."""

    model = ProjectTarget

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Target successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTargetToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the ``compromised`` field of an individual :model:`rolodex.ProjectTarget`."""

    model = ProjectTarget

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            if obj.compromised:
                obj.compromised = False
                data = {
                    "result": "success",
                    "message": "Target successfully marked as NOT compromised.",
                    "toggle": 0,
                }
            else:
                obj.compromised = True
                data = {
                    "result": "success",
                    "message": "Target successfully marked as compromised.",
                    "toggle": 1,
                }
            obj.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update target status."}

        return JsonResponse(data)


class ProjectScopeDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectScope`.
    """

    model = ProjectScope

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Scope list successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTaskCreate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Create a new :model:`rolodex.ProjectSubTask` for an individual :model:`ProjectObjective`.
    """

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        task = self.request.POST.get("task", None)
        deadline = self.request.POST.get("deadline", None)
        try:
            if task and deadline:
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d")

                if deadline.date() <= obj.deadline:
                    new_task = ProjectSubTask(
                        parent=obj,
                        task=task,
                        deadline=deadline.date(),
                    )
                    new_task.save()
                    data = {
                        "result": "success",
                        "message": "Task successfully saved.",
                    }
                    logger.info(
                        "Created new %s %s under %s %s by request of %s",
                        new_task.__class__.__name__,
                        new_task.id,
                        obj.__class__.__name__,
                        obj.id,
                        self.request.user,
                    )
                else:
                    data = {
                        "result": "error",
                        "message": "Your new due date must be before (or the same) as the objective due date.",
                    }
            else:
                data = {
                    "result": "error",
                    "message": "Your new task must have a valid task and due date.",
                }
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not create new task with provided values.",
            }

        return JsonResponse(data)


class ProjectTaskToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def test_func(self):
        return self.get_object().parent.project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            if obj.complete:
                obj.complete = False
                data = {
                    "result": "success",
                    "message": "Task successfully marked as incomplete.",
                    "toggle": 0,
                }
            else:
                obj.complete = True
                data = {
                    "result": "success",
                    "message": "Task successfully marked as complete.",
                    "toggle": 1,
                }
            obj.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update task status."}

        return JsonResponse(data)


class ProjectObjectiveToggle(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.ProjectObjective`.
    """

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        try:
            if obj.complete:
                obj.complete = False
                data = {
                    "result": "success",
                    "message": "Objective successfully marked as incomplete.",
                    "toggle": 0,
                }
            else:
                obj.complete = True
                data = {
                    "result": "success",
                    "message": "Objective successfully marked as complete.",
                    "toggle": 1,
                }
            obj.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                obj.__class__.__name__,
                obj.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update objective status."}

        return JsonResponse(data)


class ProjectTaskDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def test_func(self):
        return self.get_object().parent.project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Task successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTaskUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Update an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def test_func(self):
        return self.get_object().parent.project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        task = self.request.POST.get("task", None)
        deadline = self.request.POST.get("deadline", None)
        try:
            if task and deadline:
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d")
                logger.info(deadline.date())
                logger.info(obj.deadline)
                if deadline.date() <= obj.parent.deadline:
                    obj.task = task
                    obj.deadline = deadline.date()
                    obj.save()
                    data = {
                        "result": "success",
                        "message": "Task successfully updated.",
                    }
                    logger.info(
                        "Updated %s %s by request of %s",
                        obj.__class__.__name__,
                        obj.id,
                        self.request.user,
                    )
                else:
                    data = {
                        "result": "error",
                        "message": "Your task due date must be before (or the same) as the objective due date.",
                    }
            else:
                data = {
                    "result": "error",
                    "message": "Task cannot be updated without a valid task and due date.",
                }
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not update the task with provided values.",
            }

        return JsonResponse(data)


class ProjectTaskRefresh(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following an update or delete action related
    to an individual :model:`rolodex.ProjectSubTask.

    **Template**

    :template:`snippets/project_objective_subtasks.html`
    """

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_view(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def get(self, *args, **kwargs):
        obj = self.get_object()
        html = render_to_string(
            "snippets/project_objective_subtasks.html",
            {"objective": obj},
            request=self.request,
        )
        return HttpResponse(html)


class ProjectObjectiveRefresh(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following an update action related
    to an individual :model:`rolodex.ProjectObjective`.

    **Template**

    :template:`snippets/project_objective_row.html`
    """

    model = ProjectObjective

    def test_func(self):
        return self.get_object().project.user_can_view(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def get(self, *args, **kwargs):
        obj = self.get_object()
        html = render_to_string(
            "snippets/project_objective_row.html",
            {"objective": obj},
            request=self.request,
        )
        return HttpResponse(html)


class ProjectScopeExport(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Export scope list from an individual :model:`rolodex.ProjectScope` as a file."""

    model = ProjectScope

    def test_func(self):
        return self.get_object().project.user_can_view(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def get(self, *args, **kwargs):
        lines = []
        obj = self.get_object()
        for row in obj.scope.split("\n"):
            lines.append(row)
        response = HttpResponse(lines, content_type="text/plain")
        add_content_disposition_header(response, f"{obj.name}_scope.txt")
        return response


class DeconflictionDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.Deconfliction`.
    """

    model = Deconfliction

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj_id = obj.id
        obj.delete()
        data = {"result": "success", "message": "Deconfliction event successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class AssignProjectContact(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Copy an individual :model:`rolodex.ClientContact` to create a new :model:`rolodex.ProjectContact`"""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        data = {"result": "success", "message": ""}
        contact_id = self.request.POST.get("contact", None)
        logger.info("Received AJAX POST to assign contact %s to project", contact_id)
        try:
            contact_id = int(contact_id)
            if contact_id:
                if contact_id < 0:
                    return JsonResponse({"result": "error", "message": "You must choose a contact."})
                contact_instance = get_object_or_404(ClientContact, id=contact_id)
                if not contact_instance.client.user_can_edit(self.request.user):
                    return ForbiddenJsonResponse()
                contact_dict = to_dict(contact_instance, resolve_fk=True)
                del contact_dict["client"]
                del contact_dict["note"]

                # Check if this contact already exists in the project
                if ProjectContact.objects.filter(**contact_dict, project=self.get_object()).count() > 0:
                    message = "{} already exists in your project.".format(contact_instance.name)
                    data = {"result": "error", "message": message}
                else:
                    project_contact = ProjectContact(
                        project=self.get_object(), **contact_dict, note=contact_instance.note
                    )
                    project_contact.save()

                    message = "{} successfully added to your project.".format(contact_instance.name)
                    data = {"result": "success", "message": message}
                    logger.info(
                        "Assigned %s %s to %s %s by request of %s",
                        contact_instance.__class__.__name__,
                        contact_instance.id,
                        self.get_object().__class__.__name__,
                        self.get_object().id,
                        self.request.user,
                    )
        except ValueError:
            data = {
                "result": "error",
                "message": "Submitted contact ID was not an integer.",
            }
            logger.error(
                "Received an invalid (non-integer) contact IDs (%s) from a request submitted by %s",
                contact_id,
                self.request.user,
            )
        except Exception:  # pragma: no cover
            data = {
                "result": "error",
                "message": "An exception prevented contact assignment.",
            }
            logger.exception(
                "Encountered an error trying to create a project contact with contact ID %s from a request submitted by %s",
                contact_id,
                self.request.user,
            )
        return JsonResponse(data)


##################
# View Functions #
##################


@login_required
def index(request):
    """Display the main homepage."""
    return HttpResponseRedirect(reverse("home:dashboard"))


################
# View Classes #
################

# CBVs related to :model:`rolodex.Client`


class ClientListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`rolodex.Client`.

    **Context**

    ``filter``
        Instance of :filter:`rolodex.ClientFilter`

    **Template**

    :template:`rolodex/client_list.html`
    """

    model = Client
    template_name = "rolodex/client_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []

    def get_queryset(self):
        user = self.request.user
        queryset = get_client_list(user)

        self.autocomplete = queryset

        # Check if a search parameter is in the request
        try:
            search_term = self.request.GET.get("client_search").strip()
        except AttributeError:
            search_term = ""

        if search_term:
            messages.success(
                self.request,
                "Displaying search results for: {}".format(search_term),
                extra_tags="alert-success",
            )
            queryset = queryset.filter(name__icontains=search_term)
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["filter"] = ClientFilter(self.request.GET, queryset=self.get_queryset(), request=self.request)
        ctx["autocomplete"] = self.autocomplete
        ctx["tags"] = Tag.objects.all()
        return ctx


class ClientDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`rolodex.Client`.

    **Context**

    ``domains``
        List of :model:`shepherd.Domain` associated with :model:`rolodex.Client`
    ``servers``
        List of :model:`shepherd.StaticServer` associated with :model:`rolodex.Client`
    ``vps``
        List of :model:`shepherd.TransientServer` associated with :model:`rolodex.Client`

    **Template**

    :template:`rolodex/client_detail.html`
    """

    model = Client

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        client_instance = self.get_object()
        domain_history = History.objects.select_related("domain").filter(client=client_instance)
        server_history = ServerHistory.objects.select_related("server").filter(client=client_instance)
        projects = Project.objects.filter(client=client_instance)

        client_vps = TransientServer.objects.filter(project__in=projects)
        ctx["domains"] = domain_history
        ctx["servers"] = server_history
        ctx["vps"] = client_vps
        ctx["projects"] = projects
        ctx["client_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=Client._meta.label)

        return ctx


class ClientCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.Client`.

    **Context**

    ``contacts``
        Instance of the `ClientContactFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to clients list page

    **Template**

    :template:`rolodex/client_form.html`
    """

    model = Client
    form_class = ClientForm
    template_name = "rolodex/client_form.html"

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Client successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("rolodex:clients")
        ctx["contacts"] = self.contacts
        ctx["invites"] = self.invites
        return ctx

    def get(self, request, *args, **kwargs):
        self.contacts = ClientContactFormSet(prefix="poc")
        self.contacts.extra = 1
        self.invites = ClientInviteFormSet(prefix="invite")
        self.invites.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        form = self.get_form()
        self.contacts = ClientContactFormSet(request.POST, prefix="poc")
        self.invites = ClientInviteFormSet(request.POST, prefix="invite")
        if form.is_valid() and self.contacts.is_valid() and self.invites.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                obj = form.save(commit=False)
                self.object = obj
                obj.save()
                try:
                    for i in self.contacts.save(commit=False):
                        i.client = obj
                        i.save()
                    for i in self.invites.save(commit=False):
                        i.client = obj
                        i.save()
                    self.contacts.save_m2m()
                    self.invites.save_m2m()
                    form.save_m2m()
                except IntegrityError:  # pragma: no cover
                    form.add_error(None, "You cannot have duplicate contacts or invites for a client.")
                    return self.form_invalid(form)
                return HttpResponseRedirect(self.get_success_url())
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.exception(message)
            return super().form_invalid(form)


    def get_initial(self):
        # Generate and assign a unique codename to the project
        codename_verified = False
        codename = ""
        while not codename_verified:
            codename = codenames.codename(uppercase=True)
            clients = Client.objects.filter(codename__iexact="foo")
            if not clients:
                codename_verified = True
        return {
            "codename": codename,
            "extra_fields": ExtraFieldSpec.initial_json(self.model),
        }


class ClientUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Client`.

    **Context**

    ``contacts``
        Instance of the ``ClientContactFormSet()`` formset
    ``cancel_link``
        Link for the form's Cancel button to return to client detail page

    **Template**

    :template:`rolodex/client_form.html`
    """

    model = Client
    form_class = ClientForm
    template_name = "rolodex/client_form.html"

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Client successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("rolodex:client_detail", kwargs={"pk": self.object.id})
        if self.request.POST:
            ctx["contacts"] = ClientContactFormSet(self.request.POST, prefix="poc", instance=self.object)
            ctx["invites"] = ClientInviteFormSet(self.request.POST, prefix="invite", instance=self.object)
        else:
            contacts = ClientContactFormSet(prefix="poc", instance=self.object)
            if self.object.clientcontact_set.all().count() < 1:
                contacts.extra = 1
            ctx["contacts"] = contacts
            invites = ClientInviteFormSet(prefix="invite", instance=self.object)
            if self.object.clientinvite_set.all().count() < 1:
                invites.extra = 1
            ctx["invites"] = invites
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        contacts = ctx["contacts"]
        invites = ctx["invites"]

        # Now validate inline formsets
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                obj = form.save(commit=False)

                formsets_valid = contacts.is_valid() and invites.is_valid()
                if formsets_valid:
                    contacts.instance = obj
                    invites.instance = obj
                    try:
                        contacts.save()
                        invites.save()
                    except IntegrityError:  # pragma: no cover
                        form.add_error(None, "You cannot have duplicate contacts or invites for a client.")

                if form.is_valid() and formsets_valid:
                    obj.save()
                    form.save_m2m()
                    return HttpResponseRedirect(self.get_success_url())
                # Raise an error to rollback transactions
                raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return ``form_invalid`` and display errors
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super().form_invalid(form)


class ClientDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.Client`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`rolodex.Client`
    ``cancel_link``
        Link for the form's Cancel button to return to client detail page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = Client
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("rolodex:clients")

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "client and all associated data"
        ctx["object_to_be_deleted"] = queryset.name
        ctx["cancel_link"] = reverse("rolodex:client_detail", kwargs={"pk": self.object.id})
        return ctx


class ClientNoteCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.ClientNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Client` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to client detail page

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ClientNote
    form_class = ClientNoteForm
    template_name = "note_form.html"

    def test_func(self):
        self.client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        return self.client_instance.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this client.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id}))

    def get_initial(self):
        return {"client": self.client_instance, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.client_instance
        ctx["cancel_link"] = "{}#notes".format(reverse("rolodex:client_detail", kwargs={"pk": self.client_instance.id}))
        return ctx

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.operator = self.request.user
        obj.client_id = self.kwargs.get("pk")
        obj.save()
        return super().form_valid(form)


class ClientNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ClientNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Client` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to client detail page

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ClientNote
    form_class = ClientNoteForm
    template_name = "note_form.html"

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("rolodex:client_detail", kwargs={"pk": self.get_object().client.pk}) + "#notes")

    def get_success_url(self):
        messages.success(self.request, "Note successfully updated.", extra_tags="alert-success")
        return "{}#notes".format(reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.object.client
        ctx["cancel_link"] = "{}#notes".format(reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id}))
        return ctx


# CBVs related to :model:`rolodex.Project`


class ProjectListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`rolodex.Project`.

    **Context**

    ``filter``
        Instance of :filter:`rolodex.ProjectFilter`

    **Template**

    :template:`rolodex/project_list.html`
    """

    model = Project
    template_name = "rolodex/project_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []

    def get_queryset(self):
        user = self.request.user
        queryset = get_project_list(user).defer("extra_fields")
        self.autocomplete = queryset
        return queryset

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        # Copy the GET request data
        data = self.request.GET.copy()
        # If user has not submitted their own filter, default to showing only active projects
        if len(data) == 0:
            data["complete"] = 0
        ctx["filter"] = ProjectFilter(data, queryset=self.get_queryset(), request=self.request)
        ctx["autocomplete"] = self.autocomplete
        ctx["tags"] = Tag.objects.all()
        return ctx


class ProjectDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`rolodex.Project`.

    **Template**

    :template:`rolodex/project_detail.html`
    """

    model = Project

    def test_func(self):
        return self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, object, **kwargs):
        ctx = super().get_context_data(object=object, **kwargs)
        ctx["project_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=Project._meta.label)
        ctx["export_templates"] = ReportTemplate.objects.filter(
            Q(doc_type__doc_type__iexact="project_docx") | Q(doc_type__doc_type__iexact="pptx")
        ).filter(Q(client=object.client) | Q(client__isnull=True))
        project_type_name = getattr(getattr(object, "project_type", None), "project_type", None)
        questions, required_files = build_data_configuration(
            object.workbook_data,
            project_type_name,
            data_artifacts=object.data_artifacts,
            project_risks=object.risks,
        )
        ctx["workbook_form"] = ProjectWorkbookForm()
        normalized_workbook = normalize_workbook_payload(object.workbook_data)
        ctx["workbook_sections"] = build_workbook_sections(normalized_workbook)
        ctx["data_file_form"] = ProjectDataFileForm()
        ctx["data_questions"] = questions
        normalized_responses = prepare_data_responses_initial(
            object.data_responses,
            project_type_name,
        )
        data_responses_form = ProjectDataResponsesForm(
            question_definitions=questions,
            initial=normalized_responses,
        )
        ctx["data_responses_form"] = data_responses_form
        ctx["project_scoping_json"] = normalize_project_scoping(object.scoping)
        ctx["project_scoping_weights_json"] = {
            category: {option: float(weight) for option, weight in weights.items()}
            for category, weights in object.scoping_weights.items()
        }
        ctx["project_scoping_config_json"] = {
            key: {"label": value.get("label"), "options": value.get("options", {})}
            for key, value in PROJECT_SCOPING_CONFIGURATION.items()
        }
        ctx["risk_score_map_json"] = {
            risk: {"min": float(bounds[0]), "max": float(bounds[1])}
            for risk, bounds in RiskScoreRangeMapping.get_risk_score_map().items()
        }
        ctx["workbook_data_json"] = normalized_workbook
        ctx["data_responses_fields"] = {
            definition["key"]: data_responses_form[definition["key"]]
            for definition in questions
            if definition["key"] in data_responses_form.fields
        }
        data_files = object.data_files.all()
        ctx["data_files"] = data_files
        required_file_lookup = {
            data_file.requirement_slug: data_file
            for data_file in data_files
            if data_file.requirement_slug
        }
        dns_issue_counts: Dict[str, int] = {}
        artifacts = normalize_nexpose_artifacts_map(object.data_artifacts or {})
        object.data_artifacts = artifacts
        ctx["project_data_artifacts_json"] = artifacts
        matrix_gap_summary = summarize_nexpose_matrix_gaps(artifacts)
        ctx["nexpose_matrix_gap_summary"] = matrix_gap_summary
        ctx["has_nexpose_matrix_gaps"] = bool(matrix_gap_summary)
        web_issue_gap_summary = summarize_web_issue_matrix_gaps(artifacts)
        ctx["web_issue_matrix_gap_summary"] = web_issue_gap_summary
        ctx["has_web_issue_matrix_gaps"] = bool(web_issue_gap_summary)
        processed_cards = []
        for metrics_key, label in NEXPOSE_METRICS_LABELS.items():
            payload = artifacts.get(metrics_key)
            if not isinstance(payload, dict):
                continue
            summary = payload.get("summary") if isinstance(payload.get("summary"), dict) else {}
            processed_cards.append(
                {
                    "label": label,
                    "metrics_key": metrics_key,
                    "summary": summary,
                    "has_file": bool(payload.get("xlsx_base64")),
                    "type": "nexpose",
                }
            )
        web_metrics = artifacts.get("web_metrics")
        if isinstance(web_metrics, dict):
            summary = (
                web_metrics.get("summary") if isinstance(web_metrics.get("summary"), dict) else {}
            )
            processed_cards.append(
                {
                    "label": "Web Findings",
                    "metrics_key": "web_metrics",
                    "summary": summary,
                    "has_file": bool(web_metrics.get("xlsx_base64")),
                    "type": "web",
                }
            )
        firewall_metrics = artifacts.get("firewall_metrics")
        if isinstance(firewall_metrics, dict):
            summary = _coerce_firewall_summary(
                firewall_metrics.get("summary")
                if isinstance(firewall_metrics.get("summary"), dict)
                else {}
            )
            processed_cards.append(
                {
                    "label": "Firewall Findings",
                    "metrics_key": "firewall_metrics",
                    "summary": summary,
                    "devices": firewall_metrics.get("devices", []),
                    "has_file": bool(firewall_metrics.get("xlsx_base64")),
                    "type": "firewall",
                }
            )
        ctx["processed_data_cards"] = processed_cards
        cap_payload = object.cap if isinstance(object.cap, dict) else {}
        nexpose_section = cap_payload.get("nexpose") if isinstance(cap_payload, dict) else None
        if not isinstance(nexpose_section, dict):
            nexpose_section = {}
        ctx["nexpose_distilled"] = bool(nexpose_section.get("distilled"))
        for dns_entry in artifacts.get("dns_issues", []) or []:
            domain = (dns_entry.get("domain") or "").strip()
            if domain:
                dns_issue_counts[domain.lower()] = len(dns_entry.get("issues") or [])

        ip_cards = []
        for artifact_type in IP_ARTIFACT_ORDER:
            definition = IP_ARTIFACT_DEFINITIONS[artifact_type]
            existing = required_file_lookup.get(definition.slug)
            card_entry = {
                "type": artifact_type,
                "label": definition.label,
                "slug": definition.slug,
                "artifact_key": definition.artifact_key,
                "existing": existing,
                "ip_count": len(artifacts.get(definition.artifact_key) or []),
            }
            ip_cards.append(card_entry)

        nexpose_requirement_labels = {
            "external_nexpose_xml.xml",
            "internal_nexpose_xml.xml",
            "iot_nexpose_xml.xml",
        }
        burp_requirement_labels = {"burp_xml.xml"}
        reordered_requirements = []
        nexpose_requirements = []
        burp_insert_index = None
        for requirement in required_files:
            label = (requirement.get("label") or "").strip().lower()
            if label in nexpose_requirement_labels:
                nexpose_requirements.append(requirement)
                continue
            reordered_requirements.append(requirement)
            if label in burp_requirement_labels:
                burp_insert_index = len(reordered_requirements)
        if nexpose_requirements:
            if burp_insert_index is None:
                reordered_requirements.extend(nexpose_requirements)
            else:
                reordered_requirements[burp_insert_index:burp_insert_index] = nexpose_requirements
        required_files = reordered_requirements

        supplemental_cards = []
        inserted_ip_cards = False
        pending_ip_cards_after_burp = False
        for requirement in required_files:
            label = (requirement.get("label") or "").strip().lower()
            slug = requirement.get("slug")
            existing = required_file_lookup.get(slug) if slug else None
            if slug:
                requirement["existing"] = existing
            artifact_key = resolve_nexpose_requirement_artifact_key(requirement)
            requirement["artifact_key"] = artifact_key
            requirement["missing_matrix_entries"] = (
                matrix_gap_summary.get(artifact_key, []) if artifact_key else []
            )
            requirement["missing_web_matrix_entries"] = (
                web_issue_gap_summary if label == "burp_xml.xml" else []
            )
            if existing and label == "dns_report.csv":
                candidate_values = [
                    existing.requirement_context,
                    existing.description,
                    existing.filename,
                ]
                fail_count = None
                seen_candidates: Set[str] = set()
                for candidate in candidate_values:
                    key = (candidate or "").strip().lower()
                    if not key or key in seen_candidates:
                        continue
                    seen_candidates.add(key)
                    if key in dns_issue_counts:
                        fail_count = dns_issue_counts[key]
                        break
                if fail_count is None:
                    fail_count = 0
                requirement["parsed_fail_count"] = fail_count
                setattr(existing, "parsed_fail_count", fail_count)
            if label in burp_requirement_labels:
                supplemental_cards.append({"card_type": "required", "data": requirement})
                pending_ip_cards_after_burp = True
                continue

            if (
                pending_ip_cards_after_burp
                and not inserted_ip_cards
                and label not in nexpose_requirement_labels
            ):
                supplemental_cards.extend({"card_type": "ip", "data": card} for card in ip_cards)
                inserted_ip_cards = True
                pending_ip_cards_after_burp = False

            if label in nexpose_requirement_labels:
                supplemental_cards.append({"card_type": "required", "data": requirement})
                continue
            supplemental_cards.append({"card_type": "required", "data": requirement})

        if pending_ip_cards_after_burp and not inserted_ip_cards:
            supplemental_cards.extend({"card_type": "ip", "data": card} for card in ip_cards)
            inserted_ip_cards = True
            pending_ip_cards_after_burp = False

        if not inserted_ip_cards:
            supplemental_cards.extend({"card_type": "ip", "data": card} for card in ip_cards)

        ctx["required_data_files"] = required_files
        ctx["supplemental_cards"] = supplemental_cards
        ctx["ip_artifact_cards"] = ip_cards
        return ctx


class ProjectWorkbookUpload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Handle workbook uploads and removals for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self):
        return reverse("rolodex:project_detail", kwargs={"pk": self.get_object().pk}) + "#workbook"

    def post(self, request, *args, **kwargs):
        project = self.get_object()

        if request.POST.get("clear_workbook"):
            if project.workbook_file:
                project.workbook_file.delete(save=False)
            for data_file in list(project.data_files.all()):
                if data_file.file:
                    data_file.file.delete(save=False)
                data_file.delete()
            project.workbook_file = None
            project.workbook_data = {}
            project.data_responses = {}
            project.save(
                update_fields=[
                    "workbook_file",
                    "workbook_data",
                    "data_responses",
                ]
            )
            project.rebuild_data_artifacts()
            messages.success(request, "Workbook removed for this project.")
            return redirect(self.get_success_url())

        form = ProjectWorkbookForm(request.POST, request.FILES)
        if form.is_valid():
            workbook_file = form.cleaned_data["workbook_file"]
            parsed = form.cleaned_data.get("parsed_workbook", {})
            if hasattr(workbook_file, "seek"):
                workbook_file.seek(0)
            if project.workbook_file:
                project.workbook_file.delete(save=False)
            project.workbook_file = workbook_file
            project.workbook_data = parsed
            project.data_responses = ensure_data_responses_defaults({})
            project.save()
            messages.success(request, "Workbook uploaded successfully.")
        else:
            error_message = form.errors.as_text()
            if error_message:
                messages.error(request, error_message)
            else:
                messages.error(
                    request,
                    "Unable to upload workbook. Please ensure you selected a valid JSON file.",
                )
        return redirect(self.get_success_url())


class ProjectWorkbookDataUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Handle inline workbook data updates for a project."""

    model = Project

    @staticmethod
    def _parse_osint_csv(upload) -> tuple[Optional[list[dict[str, str]]], Optional[dict[str, int]], Optional[str]]:
        required_headers = {
            "domain": "Domain",
            "hostname": "Hostname",
            "altnames": "altNames",
            "ip": "IP",
            "port": "Port",
            "info": "Info",
            "tools": "tools",
        }
        try:
            content = upload.read().decode("utf-8-sig")
        except Exception:
            return None, None, "Unable to read the uploaded CSV file."

        reader = csv.DictReader(io.StringIO(content))
        header_lookup = {header.lower(): header for header in (reader.fieldnames or [])}
        missing_headers = [
            label for key, label in required_headers.items() if key not in header_lookup
        ]
        if missing_headers:
            return None, None, f"Missing required OSINT headers: {', '.join(missing_headers)}"

        rows: list[dict[str, str]] = []
        domain_set: set[str] = set()
        hostname_set: set[str] = set()
        ip_set: set[str] = set()
        for row in reader:
            normalized_row: dict[str, str] = {}
            for key, label in required_headers.items():
                source_header = header_lookup.get(key) or label
                normalized_row[label] = (row.get(source_header) or "").strip()
            rows.append(normalized_row)
            domain_value = normalized_row.get("Domain", "").strip().lower()
            hostname_value = normalized_row.get("Hostname", "").strip().lower()
            ip_value = normalized_row.get("IP", "").strip().lower()
            if domain_value:
                domain_set.add(domain_value)
            if hostname_value:
                hostname_set.add(hostname_value)
            if ip_value:
                ip_set.add(ip_value)

        metrics = {
            "total_domains": len(domain_set),
            "total_hostnames": len(hostname_set),
            "total_ips": len(ip_set),
        }
        return rows, metrics, None

    @staticmethod
    def _parse_dns_csv(upload) -> tuple[
        Optional[list[dict[str, str]]],
        Optional[int],
        Optional[set[str]],
        Optional[bytes],
        Optional[str],
    ]:
        try:
            raw_bytes = upload.read()
            content = raw_bytes.decode("utf-8-sig")
        except Exception:
            return None, None, None, None, "Unable to read the uploaded CSV file."

        reader = csv.DictReader(io.StringIO(content))
        rows: list[dict[str, str]] = []
        fail_count = 0
        unique_tests: set[str] = set()

        for row in reader:
            normalized_row: dict[str, str] = {
                header.strip(): (row.get(header) or "").strip()
                for header in (reader.fieldnames or [])
            }
            rows.append(normalized_row)
            status_value = (normalized_row.get("Status") or normalized_row.get("status") or "").strip()
            if status_value.upper() == "FAIL":
                fail_count += 1
                test_value = (normalized_row.get("Test") or normalized_row.get("test") or "").strip()
                if test_value:
                    unique_tests.add(test_value)

        return rows, fail_count, unique_tests, raw_bytes, None

    @staticmethod
    def _parse_dns_xml(upload) -> tuple[
        Optional[list[dict[str, str]]], Optional[str], Optional[str], Optional[bytes], Optional[str]
    ]:
        try:
            raw_bytes = upload.read()
            content = raw_bytes.decode("utf-8-sig")
        except Exception:
            return None, None, None, None, "Unable to read the uploaded XML file."

        try:
            root = ElementTree.fromstring(content)
        except ElementTree.ParseError:
            return None, None, None, None, "Unable to parse the uploaded XML file."

        records: list[dict[str, str]] = []
        domain_name: Optional[str] = None
        zone_transfer: Optional[str] = None

        for element in root.findall("record"):
            record_entry: dict[str, str] = {key: (value or "").strip() for key, value in element.attrib.items()}
            if record_entry:
                records.append(record_entry)
            if zone_transfer is None:
                transfer_state = record_entry.get("zone_transfer")
                if transfer_state and transfer_state.strip().lower() != "failed":
                    zone_transfer = "yes"

        domain_node = root.find("domain")
        if domain_node is not None:
            domain_name = (domain_node.attrib.get("domain_name") or "").strip() or None

        if zone_transfer is None:
            zone_transfer = "no"

        return records, domain_name, zone_transfer, raw_bytes, None

    @staticmethod
    def _extract_dns_domains(payload: Optional[dict[str, Any]]) -> set[str]:
        domains: set[str] = set()
        if not isinstance(payload, dict):
            return domains
        records = payload.get("records") if isinstance(payload.get("records"), list) else []
        for record in records:
            if not isinstance(record, dict):
                continue
            domain = (record.get("domain") or "").strip()
            if domain:
                domains.add(domain.lower())
        return domains

    @staticmethod
    def _compute_dns_unique_total(records: Optional[list[dict[str, Any]]], findings: Any) -> Optional[int]:
        if not isinstance(records, list):
            return None
        if not isinstance(findings, dict):
            return None

        normalized_findings: dict[str, list[dict[str, Any]]] = {}
        for domain, rows in findings.items():
            if not isinstance(domain, str) or not isinstance(rows, list):
                continue
            normalized_findings[domain.lower()] = rows

        required_domains: list[str] = []
        for record in records:
            if not isinstance(record, dict):
                continue
            domain_value = (record.get("domain") or "").strip()
            if domain_value:
                required_domains.append(domain_value.lower())

        if not required_domains:
            return None

        if any(domain not in normalized_findings for domain in required_domains):
            return None

        unique_tests: set[str] = set()
        for domain in required_domains:
            for row in normalized_findings.get(domain, []):
                if not isinstance(row, dict):
                    continue
                status_value = (row.get("Status") or row.get("status") or "").strip().upper()
                if status_value != "FAIL":
                    continue
                test_value = (row.get("Test") or row.get("test") or "").strip()
                if test_value:
                    unique_tests.add(test_value)

        return len(unique_tests)

    @staticmethod
    def _parse_ad_csv(upload, required_headers: dict[str, str]) -> tuple[
        Optional[list[dict[str, str]]], Optional[str]
    ]:
        raw_bytes = upload.read()
        content = None
        for encoding in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be"):
            try:
                content = raw_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            try:
                content = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                return None, "Unable to read the uploaded CSV file."

        sample = content[:2048]
        candidate_delimiters = ["\t", ",", ";", "|"]
        delimiter = ","
        best_match_count = -1

        for candidate in candidate_delimiters:
            reader = csv.DictReader(io.StringIO(content), delimiter=candidate)
            header_lookup = {
                (header or "").lower().strip(): header for header in (reader.fieldnames or [])
            }
            match_count = sum(1 for key in required_headers if key in header_lookup)
            if match_count == len(required_headers):
                delimiter = candidate
                best_match_count = match_count
                break
            if match_count > best_match_count:
                best_match_count = match_count
                delimiter = candidate

        try:
            sniffed = csv.Sniffer().sniff(sample, delimiters="".join(candidate_delimiters))
            sniff_match_count = 0
            reader = csv.DictReader(io.StringIO(content), delimiter=sniffed.delimiter)
            sniff_header_lookup = {
                (header or "").lower().strip(): header
                for header in (reader.fieldnames or [])
            }
            sniff_match_count = sum(1 for key in required_headers if key in sniff_header_lookup)
            if sniff_match_count > best_match_count:
                delimiter = sniffed.delimiter
        except csv.Error:
            pass

        reader = csv.DictReader(io.StringIO(content), delimiter=delimiter)
        header_lookup = {
            (header or "").lower().strip(): header for header in (reader.fieldnames or [])
        }
        missing_headers = [
            label for key, label in required_headers.items() if key not in header_lookup
        ]
        if missing_headers:
            return None, f"Missing required headers: {', '.join(missing_headers)}"

        rows: list[dict[str, str]] = []
        for row in reader:
            normalized_row: dict[str, str] = {}
            for key, label in required_headers.items():
                source_header = header_lookup.get(key) or label
                normalized_row[label] = (row.get(source_header) or "").strip()
            rows.append(normalized_row)

        return rows, None

    @staticmethod
    def _parse_ad_log(upload) -> tuple[Optional[dict[str, Any]], Optional[str], Optional[str]]:
        raw_bytes = upload.read()
        content = None

        for encoding in ("utf-8-sig", "utf-16", "utf-16le", "utf-16be"):
            try:
                content = raw_bytes.decode(encoding)
                break
            except UnicodeDecodeError:
                continue

        if content is None:
            try:
                content = raw_bytes.decode("utf-8", errors="replace")
            except Exception:
                return None, None, "Unable to read the uploaded AD log file."

        lines = content.splitlines()

        def _parse_first_int(value: str) -> Optional[int]:
            match = re.search(r"(-?[0-9,]+)", value)
            if not match:
                return None
            try:
                return int(match.group(1).replace(",", ""))
            except ValueError:
                return None

        enabled_accounts = None
        total_accounts = None
        for line in lines:
            lowered = line.lower()
            if enabled_accounts is None and "enabled users" in lowered:
                enabled_accounts = _parse_first_int(line)
            if total_accounts is None and "total users" in lowered:
                total_accounts = _parse_first_int(line)
            if enabled_accounts is not None and total_accounts is not None:
                break

        functionality_level = None
        if len(lines) >= 8:
            functionality_level = lines[7].strip() or None

        def _parse_section(
            label: str, mapping: dict[str, str], *, stop_at_blank: bool
        ) -> dict[str, Optional[int]]:
            results: dict[str, Optional[int]] = {}
            start_idx = None
            for idx, line in enumerate(lines):
                if line.strip().lower().startswith(label.lower()):
                    start_idx = idx
                    break

            if start_idx is None:
                return results

            for line in lines[start_idx + 1 :]:
                if stop_at_blank and not line.strip():
                    break
                if not line.strip():
                    continue
                if ":" not in line:
                    continue
                key_text, value_text = line.split(":", 1)
                mapped_key = mapping.get(key_text.strip().lower())
                if not mapped_key:
                    continue
                results[mapped_key] = _parse_first_int(value_text)

            return results

        old_password_counts = _parse_section(
            "Old Password Counts:",
            {
                "compliant accounts": "compliant",
                "30+ days": "30_days",
                "90+ days": "90_days",
                "180+ days": "180_days",
                "1+ year": "1_year",
                "2+ years": "2_year",
                "3+ years": "3_year",
                "never": "never",
            },
            stop_at_blank=True,
        )

        inactive_account_counts = _parse_section(
            "Inactive Account Counts:",
            {
                "active accounts": "active",
                "30+ days": "30_days",
                "90+ days": "90_days",
                "180+ days": "180_days",
                "1+ year": "1_year",
                "2+ years": "2_year",
                "3+ years": "3_year",
                "never": "never",
            },
            stop_at_blank=False,
        )

        return (
            {
                "enabled_accounts": enabled_accounts,
                "total_accounts": total_accounts,
                "functionality_level": functionality_level,
                "old_password_counts": old_password_counts,
                "inactive_account_counts": inactive_account_counts,
            },
            content,
            None,
        )

    @staticmethod
    def _extract_ad_domains(payload: Optional[dict[str, Any]]) -> set[str]:
        domains: set[str] = set()
        if not isinstance(payload, dict):
            return domains
        records = payload.get("domains") if isinstance(payload.get("domains"), list) else []
        for record in records:
            if not isinstance(record, dict):
                continue
            domain_value = (
                record.get("domain") or record.get("name") or ""
            )
            domain = str(domain_value).strip()
            if domain:
                domains.add(domain.lower())
        return domains

    def _handle_dns_csv_upload(self, request, project):
        upload = request.FILES.get("dns_csv")
        if not upload:
            return JsonResponse({"error": "No DNS CSV provided."}, status=400)

        domain = (request.POST.get("domain") or "").strip()
        rows, fail_count, unique_tests, raw_bytes, error_message = self._parse_dns_csv(upload)
        if error_message:
            return JsonResponse({"error": error_message}, status=400)

        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        artifacts = dict(artifacts)

        if rows is not None:
            findings = artifacts.get("dns_findings") if isinstance(artifacts.get("dns_findings"), dict) else {}
            findings = dict(findings)
            findings[domain or upload.name] = rows
            artifacts["dns_findings"] = findings

        slug = _slugify_identifier("required", "dns_report.csv", domain or upload.name)
        project.data_files.filter(requirement_slug=slug).delete()

        data_file = ProjectDataFile(
            project=project,
            requirement_slug=slug,
            requirement_label="dns_report.csv",
            requirement_context=domain,
            description="",
        )
        data_file.file.save(upload.name, ContentFile(raw_bytes or b""))
        data_file.save()

        project.rebuild_data_artifacts()
        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}

        if rows is not None:
            findings = artifacts.get("dns_findings") if isinstance(artifacts.get("dns_findings"), dict) else {}
            findings = dict(findings)
            findings[domain or upload.name] = rows
            artifacts["dns_findings"] = findings

        normalized_workbook = normalize_workbook_payload(project.workbook_data)
        dns_state = normalized_workbook.get("dns") if isinstance(normalized_workbook.get("dns"), dict) else {}
        if not isinstance(dns_state, dict):
            dns_state = {}
        records = dns_state.get("records") if isinstance(dns_state.get("records"), list) else []
        if not isinstance(records, list):
            records = []
        target_domain = (domain or upload.name).strip()

        match = None
        for record in records:
            if not isinstance(record, dict):
                continue
            if (record.get("domain") or "").strip().lower() == target_domain.lower():
                match = record
                break

        if match is None:
            match = {"domain": target_domain, "total": None, "zone_transfer": None}
            records.append(match)

        match["domain"] = target_domain
        if fail_count is not None:
            match["total"] = fail_count

        dns_state["records"] = records

        unique_total = self._compute_dns_unique_total(records, artifacts.get("dns_findings"))
        if unique_total is not None:
            dns_state["unique"] = unique_total
        elif unique_tests is not None and rows is not None and target_domain:
            dns_state["unique"] = len(unique_tests)

        workbook_payload = build_workbook_entry_payload(project=project, dns=dns_state)
        project.workbook_data = workbook_payload
        project.data_artifacts = artifacts
        project.save(update_fields=["workbook_data", "data_artifacts"])
        return JsonResponse(
            {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
        )

    def _handle_dns_xml_upload(self, request, project):
        upload = request.FILES.get("dns_xml")
        if not upload:
            return JsonResponse({"error": "No DNS XML provided."}, status=400)

        records, domain_name, zone_transfer, raw_bytes, error_message = self._parse_dns_xml(upload)
        if error_message:
            return JsonResponse({"error": error_message}, status=400)

        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        artifacts = dict(artifacts)
        if records is not None:
            dns_records = artifacts.get("dns_records") if isinstance(artifacts.get("dns_records"), dict) else {}
            dns_records = dict(dns_records)
            dns_records[domain_name or upload.name] = records
            artifacts["dns_records"] = dns_records

        normalized_workbook = normalize_workbook_payload(project.workbook_data)
        dns_state = normalized_workbook.get("dns") if isinstance(normalized_workbook.get("dns"), dict) else {}
        if not isinstance(dns_state, dict):
            dns_state = {}
        records_state = dns_state.get("records") if isinstance(dns_state.get("records"), list) else []
        if not isinstance(records_state, list):
            records_state = []
        target_domain = (domain_name or "").strip()

        match = None
        for record in records_state:
            if not isinstance(record, dict):
                continue
            if target_domain and (record.get("domain") or "").strip().lower() == target_domain.lower():
                match = record
                break

        if match is None:
            match = {"domain": target_domain or None, "total": None, "zone_transfer": None}
            records_state.append(match)

        if target_domain:
            match["domain"] = target_domain
        if zone_transfer is not None:
            match["zone_transfer"] = zone_transfer

        dns_state["records"] = records_state
        unique_total = self._compute_dns_unique_total(records_state, artifacts.get("dns_findings"))
        if unique_total is not None:
            dns_state["unique"] = unique_total

        workbook_payload = build_workbook_entry_payload(project=project, dns=dns_state)
        project.workbook_data = workbook_payload
        project.data_artifacts = artifacts
        project.save(update_fields=["workbook_data", "data_artifacts"])
        return JsonResponse(
            {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
        )

    def _handle_ad_csv_upload(self, request, project):
        upload = request.FILES.get("ad_csv")
        if not upload:
            return JsonResponse({"error": "No AD CSV provided."}, status=400)

        domain = (request.POST.get("domain") or "").strip()
        if not domain:
            return JsonResponse(
                {"error": "A domain name is required for this upload."}, status=400
            )

        metric = (request.POST.get("ad_metric") or "").strip()

        if metric not in AD_CSV_HEADER_MAP:
            return JsonResponse({"error": "Invalid AD metric provided."}, status=400)

        rows, error_message = self._parse_ad_csv(upload, AD_CSV_HEADER_MAP[metric])
        if error_message:
            return JsonResponse({"error": error_message}, status=400)

        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        artifacts = dict(artifacts)
        ad_artifacts = artifacts.get("ad") if isinstance(artifacts.get("ad"), dict) else {}
        if not isinstance(ad_artifacts, dict):
            ad_artifacts = {}
        domain_key = domain.lower()
        domain_entry = ad_artifacts.get(domain_key, {}) if isinstance(ad_artifacts, dict) else {}
        if not isinstance(domain_entry, dict):
            domain_entry = {}
        domain_entry[metric] = rows or []
        domain_entry[f"{metric}_file_name"] = upload.name
        ad_artifacts[domain_key] = domain_entry
        artifacts["ad"] = ad_artifacts

        normalized_workbook = normalize_workbook_payload(project.workbook_data)
        ad_state = normalized_workbook.get("ad") if isinstance(normalized_workbook.get("ad"), dict) else {}
        if not isinstance(ad_state, dict):
            ad_state = {}
        domain_records = ad_state.get("domains") if isinstance(ad_state.get("domains"), list) else []
        if not isinstance(domain_records, list):
            domain_records = []

        match = None
        for record in domain_records:
            if not isinstance(record, dict):
                continue
            domain_value = (record.get("domain") or record.get("name") or "").strip()
            if domain_value.lower() == domain_key:
                match = record
                break

        if match is None:
            match = {"domain": domain}
            domain_records.append(match)

        match["domain"] = domain
        match[metric] = len(rows or [])

        ad_state["domains"] = domain_records

        workbook_payload = build_workbook_entry_payload(project=project, areas={"ad": ad_state})
        project.workbook_data = workbook_payload
        project.data_artifacts = artifacts
        project.save(update_fields=["workbook_data", "data_artifacts"])
        return JsonResponse(
            {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
        )

    def _handle_ad_log_upload(self, request, project):
        upload = request.FILES.get("ad_log")
        if not upload:
            return JsonResponse({"error": "No AD log provided."}, status=400)

        domain = (request.POST.get("domain") or "").strip()
        if not domain:
            return JsonResponse(
                {"error": "A domain name is required for this upload."}, status=400
            )

        parsed, content, error_message = self._parse_ad_log(upload)
        if error_message:
            return JsonResponse({"error": error_message}, status=400)

        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        artifacts = dict(artifacts)
        ad_artifacts = artifacts.get("ad") if isinstance(artifacts.get("ad"), dict) else {}
        if not isinstance(ad_artifacts, dict):
            ad_artifacts = {}

        domain_key = domain.lower()
        domain_entry = ad_artifacts.get(domain_key, {}) if isinstance(ad_artifacts, dict) else {}
        if not isinstance(domain_entry, dict):
            domain_entry = {}

        domain_entry["ad_log_file_name"] = upload.name
        if content is not None:
            domain_entry["ad_log"] = content
        ad_artifacts[domain_key] = domain_entry
        artifacts["ad"] = ad_artifacts

        normalized_workbook = normalize_workbook_payload(project.workbook_data)
        ad_state = normalized_workbook.get("ad") if isinstance(normalized_workbook.get("ad"), dict) else {}
        if not isinstance(ad_state, dict):
            ad_state = {}
        domain_records = ad_state.get("domains") if isinstance(ad_state.get("domains"), list) else []
        if not isinstance(domain_records, list):
            domain_records = []

        match = None
        for record in domain_records:
            if not isinstance(record, dict):
                continue
            domain_value = (record.get("domain") or record.get("name") or "").strip()
            if domain_value.lower() == domain_key:
                match = record
                break

        if match is None:
            match = {"domain": domain}
            domain_records.append(match)

        match["domain"] = domain

        if parsed:
            if parsed.get("enabled_accounts") is not None:
                match["enabled_accounts"] = parsed.get("enabled_accounts")
            if parsed.get("total_accounts") is not None:
                match["total_accounts"] = parsed.get("total_accounts")
            if parsed.get("functionality_level") is not None:
                match["functionality_level"] = parsed.get("functionality_level")

            old_counts = parsed.get("old_password_counts") if isinstance(parsed.get("old_password_counts"), dict) else {}
            if old_counts:
                existing_old = match.get("old_password_counts") if isinstance(match.get("old_password_counts"), dict) else {}
                if not isinstance(existing_old, dict):
                    existing_old = {}
                existing_old = dict(existing_old)
                existing_old.update({k: v for k, v in old_counts.items() if v is not None})
                match["old_password_counts"] = existing_old

            inactive_counts = parsed.get("inactive_account_counts") if isinstance(parsed.get("inactive_account_counts"), dict) else {}
            if inactive_counts:
                existing_inactive = (
                    match.get("inactive_account_counts")
                    if isinstance(match.get("inactive_account_counts"), dict)
                    else {}
                )
                if not isinstance(existing_inactive, dict):
                    existing_inactive = {}
                existing_inactive = dict(existing_inactive)
                existing_inactive.update(
                    {k: v for k, v in inactive_counts.items() if v is not None}
                )
                match["inactive_account_counts"] = existing_inactive

        ad_state["domains"] = domain_records

        workbook_payload = build_workbook_entry_payload(project=project, areas={"ad": ad_state})
        project.workbook_data = workbook_payload
        project.data_artifacts = artifacts
        project.save(update_fields=["workbook_data", "data_artifacts"])

        return JsonResponse(
            {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
        )

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        if request.FILES:
            if "dns_csv" in request.FILES:
                return self._handle_dns_csv_upload(request, project)

            if "dns_xml" in request.FILES:
                return self._handle_dns_xml_upload(request, project)

            nexpose_upload_fields = {
                "external_nexpose_xml": "external_nexpose_xml.xml",
                "internal_nexpose_xml": "internal_nexpose_xml.xml",
                "iot_nexpose_xml": "iot_nexpose_xml.xml",
            }
            for upload_field, requirement_label in nexpose_upload_fields.items():
                if upload_field in request.FILES:
                    upload = request.FILES.get(upload_field)
                    if not upload:
                        return JsonResponse(
                            {"error": "No Nexpose XML provided."}, status=400
                        )

                    data_file = ProjectDataFile(
                        project=project,
                        requirement_slug=_slugify_identifier(
                            "required", requirement_label
                        ),
                        requirement_label=requirement_label,
                        requirement_context=f"{upload_field.replace('_', ' ')}",
                        description="",
                    )
                    data_file.file.save(upload.name, upload)
                    data_file.save()

                    project.rebuild_data_artifacts()
                    project.refresh_from_db(fields=["workbook_data", "data_artifacts"])

                    return JsonResponse(
                        {
                            "workbook_data": project.workbook_data,
                            "data_artifacts": project.data_artifacts,
                        }
                    )

            if "firewall_xml" in request.FILES:
                upload = request.FILES.get("firewall_xml")
                if not upload:
                    return JsonResponse({"error": "No Firewall XML provided."}, status=400)

                data_file = ProjectDataFile(
                    project=project,
                    requirement_slug=_slugify_identifier("required", "firewall_xml.xml"),
                    requirement_label="firewall_xml.xml",
                    requirement_context="firewall xml",
                    description="",
                )
                data_file.file.save(upload.name, upload)
                data_file.save()

                project.rebuild_data_artifacts()
                project.refresh_from_db(fields=["workbook_data", "data_artifacts"])

                return JsonResponse(
                    {"workbook_data": project.workbook_data, "data_artifacts": project.data_artifacts}
                )

            if "burp_xml" in request.FILES:
                upload = request.FILES.get("burp_xml")
                if not upload:
                    return JsonResponse({"error": "No Burp XML provided."}, status=400)

                data_file = ProjectDataFile(
                    project=project,
                    requirement_slug=_slugify_identifier("required", "burp_xml.xml"),
                    requirement_label="burp_xml.xml",
                    requirement_context="burp xml",
                    description="",
                )
                data_file.file.save(upload.name, upload)
                data_file.save()

                project.rebuild_data_artifacts()
                project.refresh_from_db(fields=["workbook_data", "data_artifacts"])

                return JsonResponse(
                    {
                        "workbook_data": project.workbook_data,
                        "data_artifacts": project.data_artifacts,
                    }
                )

            if "ad_csv" in request.FILES:
                return self._handle_ad_csv_upload(request, project)

            if "ad_log" in request.FILES:
                return self._handle_ad_log_upload(request, project)

            upload = request.FILES.get("osint_csv")
            if not upload:
                return JsonResponse({"error": "No OSINT CSV provided."}, status=400)

            rows, metrics, error_message = self._parse_osint_csv(upload)
            if error_message:
                return JsonResponse({"error": error_message}, status=400)

            workbook_payload = build_workbook_entry_payload(
                project=project,
                areas={"osint": metrics or {}},
            )
            artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            artifacts = dict(artifacts)
            if rows is not None:
                artifacts["osint"] = rows
                artifacts["osint_file_name"] = upload.name
            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.save(update_fields=["workbook_data", "data_artifacts"])
            return JsonResponse(
                {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
            )
        try:
            payload = json.loads(request.body.decode("utf-8")) if request.body else {}
        except json.JSONDecodeError:
            return JsonResponse({"error": "Invalid JSON payload."}, status=400)

        dns_payload = payload.get("dns") if isinstance(payload, dict) else None
        artifacts_updated = False
        areas_payload = payload.get("areas") if isinstance(payload.get("areas"), dict) else {}

        if isinstance(dns_payload, dict):
            artifacts = (
                project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            )
            existing_domains = self._extract_dns_domains(
                normalize_workbook_payload(project.workbook_data).get("dns")
            )
            submitted_domains = self._extract_dns_domains(dns_payload)
            removed_domains = existing_domains - submitted_domains
            if removed_domains:
                for domain in removed_domains:
                    slug = _slugify_identifier("required", "dns_report.csv", domain)
                    project.data_files.filter(requirement_slug=slug).delete()
                project.rebuild_data_artifacts()
                artifacts = (
                    project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
                )
                artifacts_updated = True

            unique_total = self._compute_dns_unique_total(
                dns_payload.get("records"), artifacts.get("dns_findings")
            )
            if unique_total is not None:
                dns_payload["unique"] = unique_total
            payload["dns"] = dns_payload
            if artifacts_updated:
                project.data_artifacts = artifacts

        ad_payload = areas_payload.get("ad") if isinstance(areas_payload.get("ad"), dict) else None
        if ad_payload is not None:
            artifacts = (
                project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            )
            artifacts = dict(artifacts)
            ad_artifacts = artifacts.get("ad") if isinstance(artifacts.get("ad"), dict) else {}
            if not isinstance(ad_artifacts, dict):
                ad_artifacts = {}
            existing_domains = self._extract_ad_domains(
                normalize_workbook_payload(project.workbook_data).get("ad")
            )
            submitted_domains = self._extract_ad_domains(ad_payload)
            removed_domains = existing_domains - submitted_domains
            if removed_domains:
                for domain in removed_domains:
                    ad_artifacts.pop(domain, None)
                if ad_artifacts:
                    artifacts["ad"] = ad_artifacts
                else:
                    artifacts.pop("ad", None)
                project.data_artifacts = artifacts
                artifacts_updated = True

        ad_removal = payload.get("remove_ad_metric")
        if isinstance(ad_removal, dict):
            domain = (ad_removal.get("domain") or "").strip()
            metric = (ad_removal.get("metric") or "").strip()

            if not domain or metric not in AD_CSV_HEADER_MAP:
                return JsonResponse({"error": "Invalid AD removal request."}, status=400)

            artifacts = (
                project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            )
            artifacts = dict(artifacts)
            ad_artifacts = artifacts.get("ad") if isinstance(artifacts.get("ad"), dict) else {}
            if not isinstance(ad_artifacts, dict):
                ad_artifacts = {}

            domain_key = domain.lower()
            domain_artifact = (
                ad_artifacts.get(domain_key) if isinstance(ad_artifacts, dict) else {}
            )
            if not isinstance(domain_artifact, dict):
                domain_artifact = {}
            domain_artifact.pop(metric, None)
            domain_artifact.pop(f"{metric}_file_name", None)

            if domain_artifact:
                ad_artifacts[domain_key] = domain_artifact
            else:
                ad_artifacts.pop(domain_key, None)

            if ad_artifacts:
                artifacts["ad"] = ad_artifacts
            else:
                artifacts.pop("ad", None)

            normalized_workbook = normalize_workbook_payload(project.workbook_data)
            ad_state = (
                normalized_workbook.get("ad")
                if isinstance(normalized_workbook.get("ad"), dict)
                else {}
            )
            if not isinstance(ad_state, dict):
                ad_state = {}
            domain_records = (
                ad_state.get("domains") if isinstance(ad_state.get("domains"), list) else []
            )
            if not isinstance(domain_records, list):
                domain_records = []

            match = None
            for record in domain_records:
                if not isinstance(record, dict):
                    continue
                domain_value = (record.get("domain") or record.get("name") or "").strip()
                if domain_value.lower() == domain_key:
                    match = record
                    break

            if match is None and domain:
                match = {"domain": domain}
                domain_records.append(match)

            if match is not None:
                match[metric] = None

            ad_state["domains"] = domain_records

            workbook_payload = build_workbook_entry_payload(
                project=project, areas={"ad": ad_state}
            )
            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.save(update_fields=["workbook_data", "data_artifacts"])
            return JsonResponse(
                {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
            )

        ad_domain_removal = payload.get("remove_ad_domain")
        if isinstance(ad_domain_removal, str):
            domain = ad_domain_removal.strip()
            if not domain:
                return JsonResponse({"error": "A domain name is required."}, status=400)

            artifacts = (
                project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            )
            artifacts = dict(artifacts)
            ad_artifacts = (
                artifacts.get("ad") if isinstance(artifacts.get("ad"), dict) else {}
            )
            if not isinstance(ad_artifacts, dict):
                ad_artifacts = {}

            ad_artifacts.pop(domain.lower(), None)
            if ad_artifacts:
                artifacts["ad"] = ad_artifacts
            else:
                artifacts.pop("ad", None)

            normalized_workbook = normalize_workbook_payload(project.workbook_data)
            ad_state = (
                normalized_workbook.get("ad")
                if isinstance(normalized_workbook.get("ad"), dict)
                else {}
            )
            if not isinstance(ad_state, dict):
                ad_state = {}
            domain_records = (
                ad_state.get("domains") if isinstance(ad_state.get("domains"), list) else []
            )
            if not isinstance(domain_records, list):
                domain_records = []

            domain_lower = domain.lower()
            domain_records = [
                record
                for record in domain_records
                if not isinstance(record, dict)
                or (record.get("domain") or record.get("name") or "").strip().lower()
                != domain_lower
            ]

            password_state = (
                normalized_workbook.get("password")
                if isinstance(normalized_workbook.get("password"), dict)
                else {}
            )
            password_policies = (
                password_state.get("policies")
                if isinstance(password_state.get("policies"), list)
                else []
            )
            password_policies = [
                policy
                for policy in password_policies
                if not isinstance(policy, dict)
                or (policy.get("domain_name") or "").strip().lower() != domain_lower
            ]
            removed_domains = password_state.get("removed_ad_domains")
            if isinstance(removed_domains, list):
                removed_domains = [
                    entry
                    for entry in removed_domains
                    if (entry or "").strip().lower() != domain_lower
                ]
                if removed_domains:
                    password_state["removed_ad_domains"] = removed_domains
                else:
                    password_state.pop("removed_ad_domains", None)
            password_state["policies"] = password_policies

            ad_state["domains"] = domain_records

            workbook_payload = build_workbook_entry_payload(
                project=project, areas={"ad": ad_state, "password": password_state}
            )
            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.rebuild_data_artifacts()
            project.refresh_from_db(
                fields=["workbook_data", "data_artifacts", "data_responses", "cap"]
            )
            return JsonResponse(
                {
                    "workbook_data": project.workbook_data,
                    "data_artifacts": project.data_artifacts,
                }
            )

        if payload.get("remove_osint"):
            artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            artifacts = dict(artifacts)
            artifacts.pop("osint", None)
            artifacts.pop("osint_file_name", None)
            workbook_payload = normalize_workbook_payload(project.workbook_data)
            workbook_payload["osint"] = {field: None for field in OSINT_FIELDS}
            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.save(update_fields=["workbook_data", "data_artifacts"])
            return JsonResponse(
                {"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts}
            )

        if payload.get("remove_web"):
            requirement_slug = _slugify_identifier("required", "burp_xml.xml")
            for data_file in project.data_files.filter(requirement_slug=requirement_slug):
                if data_file.file:
                    data_file.file.delete(save=False)
                data_file.delete()

            artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            artifacts = dict(artifacts)
            for key in (
                "web_findings",
                "web_metrics",
                "web_cap_map",
                "web_cap_entries",
                "web_issue_matrix_gaps",
                "web_issues",
            ):
                artifacts.pop(key, None)

            workbook_payload = normalize_workbook_payload(project.workbook_data)
            default_values = copy.deepcopy(WORKBOOK_DEFAULTS.get("web"))
            if default_values is not None:
                workbook_payload["web"] = default_values
            else:
                workbook_payload.pop("web", None)

            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.rebuild_data_artifacts()
            project.refresh_from_db(
                fields=["workbook_data", "data_artifacts", "data_responses", "cap"]
            )

            return JsonResponse(
                {
                    "workbook_data": project.workbook_data,
                    "data_artifacts": project.data_artifacts,
                }
            )

        if payload.get("remove_firewall"):
            requirement_slug = _slugify_identifier("required", "firewall_xml.xml")
            for data_file in project.data_files.filter(requirement_slug=requirement_slug):
                if data_file.file:
                    data_file.file.delete(save=False)
                data_file.delete()

            artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            artifacts = dict(artifacts)
            for key in (
                "firewall_findings",
                "firewall_metrics",
                "firewall_vulnerabilities",
            ):
                artifacts.pop(key, None)

            workbook_payload = normalize_workbook_payload(project.workbook_data)
            default_values = copy.deepcopy(WORKBOOK_DEFAULTS.get("firewall"))
            if default_values is not None:
                workbook_payload["firewall"] = default_values
            else:
                workbook_payload.pop("firewall", None)

            project.workbook_data = workbook_payload
            project.data_artifacts = artifacts
            project.rebuild_data_artifacts()
            project.refresh_from_db(
                fields=["workbook_data", "data_artifacts", "data_responses", "cap"]
            )

            return JsonResponse(
                {
                    "workbook_data": project.workbook_data,
                    "data_artifacts": project.data_artifacts,
                }
            )

        nexpose_removal_key = payload.get("remove_nexpose")
        if isinstance(nexpose_removal_key, str) and nexpose_removal_key:
            nexpose_removal_key = nexpose_removal_key.strip()

        nexpose_removal_map = {
            "external_nexpose": {
                "requirement_label": "external_nexpose_xml.xml",
                "artifact_keys": [
                    "external_nexpose_findings",
                    "external_nexpose_vulnerabilities",
                    "external_nexpose_metrics",
                ],
            },
            "internal_nexpose": {
                "requirement_label": "internal_nexpose_xml.xml",
                "artifact_keys": [
                    "internal_nexpose_findings",
                    "internal_nexpose_vulnerabilities",
                    "internal_nexpose_metrics",
                ],
            },
            "iot_iomt_nexpose": {
                "requirement_label": "iot_nexpose_xml.xml",
                "artifact_keys": [
                    "iot_iomt_nexpose_findings",
                    "iot_iomt_nexpose_vulnerabilities",
                    "iot_iomt_nexpose_metrics",
                    "iot_nexpose_vulnerabilities",
                ],
            },
        }

        if nexpose_removal_key and nexpose_removal_key in nexpose_removal_map:
            removal_meta = nexpose_removal_map[nexpose_removal_key]
            requirement_label = removal_meta["requirement_label"]
            requirement_slug = _slugify_identifier("required", requirement_label)

            for data_file in project.data_files.filter(
                requirement_slug=requirement_slug
            ):
                if data_file.file:
                    data_file.file.delete(save=False)
                data_file.delete()

            artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
            artifacts = dict(artifacts)
            for key in removal_meta.get("artifact_keys", []):
                artifacts.pop(key, None)

            project.data_artifacts = artifacts

            workbook_payload = normalize_workbook_payload(project.workbook_data)
            default_values = copy.deepcopy(WORKBOOK_DEFAULTS.get(nexpose_removal_key))
            if default_values is not None:
                workbook_payload[nexpose_removal_key] = default_values
            else:
                workbook_payload.pop(nexpose_removal_key, None)

            project.workbook_data = workbook_payload
            project.rebuild_data_artifacts()
            project.refresh_from_db(
                fields=["workbook_data", "data_artifacts", "data_responses", "cap"]
            )

            return JsonResponse(
                {
                    "workbook_data": project.workbook_data,
                    "data_artifacts": project.data_artifacts,
                }
            )

        workbook_payload = build_workbook_entry_payload(
            project=project,
            general=payload.get("general"),
            scores=payload.get("scores"),
            grades=payload.get("grades"),
            areas=areas_payload,
            dns=dns_payload,
        )

        project.workbook_data = workbook_payload
        update_fields = ["workbook_data"]
        if artifacts_updated:
            update_fields.append("data_artifacts")

        project.rebuild_data_artifacts()

        project.refresh_from_db(
            fields=["workbook_data", "data_artifacts", "data_responses", "cap", "risks"]
        )

        project_type_name = getattr(getattr(project, "project_type", None), "project_type", None)
        questions, _ = build_data_configuration(
            project.workbook_data,
            project_type_name,
            data_artifacts=project.data_artifacts,
            project_risks=project.risks,
        )
        existing_grouped = ensure_data_responses_defaults(
            project.data_responses if isinstance(project.data_responses, dict) else {}
        )
        refreshed_responses = _build_grouped_data_responses(
            existing_grouped,
            questions,
            existing_grouped=existing_grouped,
            workbook_data=project.workbook_data,
        )
        project.data_responses = ensure_data_responses_defaults(refreshed_responses)
        project.save(update_fields=["data_responses"])

        return JsonResponse({"workbook_data": workbook_payload, "data_artifacts": project.data_artifacts})


class ProjectDataFileUpload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Upload supporting data files for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self):
        return reverse("rolodex:project_detail", kwargs={"pk": self.get_object().pk}) + "#supplementals"

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        form = ProjectDataFileForm(request.POST, request.FILES)
        if form.is_valid():
            data_file = form.save(commit=False)
            data_file.project = project
            requirement_slug = request.POST.get("requirement_slug", "").strip()
            requirement_label = request.POST.get("requirement_label", "").strip()
            requirement_context = request.POST.get("requirement_context", "").strip()
            if requirement_slug:
                # Replace any previously uploaded file for this requirement so the latest upload is used.
                existing_files = list(project.data_files.filter(requirement_slug=requirement_slug))
                for existing in existing_files:
                    if existing.file:
                        existing.file.delete(save=False)
                    existing.delete()
                data_file.requirement_slug = requirement_slug
                data_file.requirement_label = requirement_label
                data_file.requirement_context = requirement_context
                if not data_file.description:
                    description_parts = [requirement_label]
                    if requirement_context:
                        description_parts.append(f"for {requirement_context}")
                    data_file.description = " ".join(part for part in description_parts if part).strip()
            data_file.save()
            project.rebuild_data_artifacts()
            messages.success(request, "Supporting data file uploaded.")
        else:
            error_message = form.errors.as_text()
            if error_message:
                messages.error(request, error_message)
            else:
                messages.error(request, "Unable to upload data file. Please review the form for errors.")
        return redirect(self.get_success_url())


class ProjectNexposeMissingMatrixDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Provide a CSV export of missing Nexpose matrix entries for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self, project: Project) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#supplementals"

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        artifact_key = (request.GET.get("artifact") or "").strip()
        summary = summarize_nexpose_matrix_gaps(project.data_artifacts or {})
        entries = summary.get(artifact_key)
        if not entries:
            messages.error(
                request,
                "No missing Nexpose matrix entries are available for download.",
            )
            return HttpResponseRedirect(self.get_success_url(project))

        buffer = io.StringIO()
        fieldnames = [
            "Vulnerability",
            "Action Required",
            "Remediation Impact",
            "Vulnerability Threat",
            "Category",
            "CVE",
        ]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in entries:
            if not isinstance(row, dict):
                continue
            writer.writerow({
                "Vulnerability": row.get("Vulnerability", ""),
                "Action Required": row.get("Action Required", ""),
                "Remediation Impact": row.get("Remediation Impact", ""),
                "Vulnerability Threat": row.get("Vulnerability Threat", ""),
                "Category": row.get("Category", ""),
                "CVE": row.get("CVE", ""),
            })

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        add_content_disposition_header(response, "nexpose-missing.csv")
        return response


class ProjectWebIssueMissingDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Provide a CSV export of missing web issue matrix entries for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self, project: Project) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#supplementals"

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        entries = summarize_web_issue_matrix_gaps(project.data_artifacts or {})
        if not entries:
            messages.error(request, "No missing Web issues are available for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        buffer = io.StringIO()
        fieldnames = ["issue", "impact", "fix"]
        writer = csv.DictWriter(buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in entries:
            if not isinstance(row, dict):
                continue
            writer.writerow(
                {
                    "issue": row.get("issue", ""),
                    "impact": row.get("impact", ""),
                    "fix": row.get("fix", ""),
                }
            )

        response = HttpResponse(buffer.getvalue(), content_type="text/csv")
        add_content_disposition_header(response, "burp-missing.csv")
        return response


class ProjectNexposeDataDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Provide the processed Nexpose XLSX download for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self, project: Project) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#processed-data"

    def _resolve_metrics_payload(self, project: Project, artifact: str) -> Optional[Dict[str, Any]]:
        artifacts = project.data_artifacts or {}
        if not isinstance(artifacts, dict):
            return None
        payload = artifacts.get(artifact)
        if isinstance(payload, dict):
            return payload
        metrics_key = NEXPOSE_METRICS_KEY_MAP.get(artifact)
        if metrics_key:
            payload = artifacts.get(metrics_key)
            if isinstance(payload, dict):
                return payload
        return None

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        artifact_key = (request.GET.get("artifact") or "").strip()
        if not artifact_key:
            messages.error(request, "A Nexpose artifact was not specified for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        payload = self._resolve_metrics_payload(project, artifact_key)
        if not payload:
            messages.error(request, "No Nexpose data file is available for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        workbook_b64 = payload.get("xlsx_base64")
        if not workbook_b64:
            messages.error(request, "The Nexpose data file is not available for download yet.")
            return HttpResponseRedirect(self.get_success_url(project))

        try:
            workbook_bytes = base64.b64decode(workbook_b64)
        except (ValueError, binascii.Error):  # pragma: no cover - defensive guard
            logger.exception("Failed to decode Nexpose XLSX payload")
            messages.error(request, "Unable to decode the Nexpose data file.")
            return HttpResponseRedirect(self.get_success_url(project))

        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = payload.get("xlsx_filename") or "nexpose_data.xlsx"
        add_content_disposition_header(response, filename)
        return response


class ProjectWebDataDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Provide the processed web findings XLSX download for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self, project: Project) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#processed-data"

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        artifacts = project.data_artifacts or {}
        if not isinstance(artifacts, dict):
            messages.error(request, "No web data file is available for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        payload = artifacts.get("web_metrics")
        if not isinstance(payload, dict):
            messages.error(request, "No web data file is available for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        workbook_b64 = payload.get("xlsx_base64")
        if not workbook_b64:
            messages.error(request, "The web data file is not available for download yet.")
            return HttpResponseRedirect(self.get_success_url(project))

        try:
            workbook_bytes = base64.b64decode(workbook_b64)
        except (ValueError, binascii.Error):  # pragma: no cover - defensive guard
            logger.exception("Failed to decode web XLSX payload")
            messages.error(request, "Unable to decode the web data file.")
            return HttpResponseRedirect(self.get_success_url(project))

        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = payload.get("xlsx_filename") or "burp_data.xlsx"
        add_content_disposition_header(response, filename)
        return response


class ProjectFirewallDataDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Provide the processed firewall findings XLSX download for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self, project: Project) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#processed-data"

    def get(self, request, *args, **kwargs):
        project = self.get_object()
        artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        payload = artifacts.get("firewall_metrics") if isinstance(artifacts, dict) else None
        if not isinstance(payload, dict):
            messages.error(request, "No firewall data file is available for download.")
            return HttpResponseRedirect(self.get_success_url(project))

        workbook_b64 = payload.get("xlsx_base64")
        if not workbook_b64:
            messages.error(request, "The firewall data file is not available for download yet.")
            return HttpResponseRedirect(self.get_success_url(project))

        try:
            workbook_bytes = base64.b64decode(workbook_b64)
        except (ValueError, binascii.Error):  # pragma: no cover - defensive guard
            logger.exception("Failed to decode firewall XLSX payload")
            messages.error(request, "Unable to decode the firewall data file.")
            return HttpResponseRedirect(self.get_success_url(project))

        response = HttpResponse(
            workbook_bytes,
            content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        )
        filename = payload.get("xlsx_filename") or "firewall_data.xlsx"
        add_content_disposition_header(response, filename)
        return response


class ProjectNexposeDistilledUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Toggle the Nexpose distilled flag for a project."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self) -> str:
        return reverse("rolodex:project_detail", kwargs={"pk": self.get_object().pk}) + "#processed-data"

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        distilled_selected = bool(request.POST.get("nexpose_distilled"))
        project_cap = dict(project.cap or {})
        nexpose_section = project_cap.get("nexpose")
        if isinstance(nexpose_section, dict):
            nexpose_section = dict(nexpose_section)
        else:
            nexpose_section = {}
        nexpose_section["distilled"] = distilled_selected
        project_cap["nexpose"] = nexpose_section
        project.cap = project_cap
        project.save(update_fields=["cap"])
        messages.success(request, "Updated Nexpose distilled preference.")
        return redirect(self.get_success_url())


class ProjectIPArtifactUpload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Upload supplemental IP address artifacts for a project."""

    model = Project
    form_class = ProjectIPArtifactForm

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self):
        return reverse("rolodex:project_detail", kwargs={"pk": self.get_object().pk}) + "#supplementals"

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        form = self.form_class(request.POST, request.FILES)
        if form.is_valid():
            ip_type = form.cleaned_data["ip_type"]
            definition = IP_ARTIFACT_DEFINITIONS[ip_type]
            ip_values = form.cleaned_data["parsed_ips"]
            content = "\n".join(ip_values) + "\n"

            existing_files = list(project.data_files.filter(requirement_slug=definition.slug))
            for existing in existing_files:
                if existing.file:
                    existing.file.delete(save=False)
                existing.delete()

            data_file = ProjectDataFile(
                project=project,
                requirement_slug=definition.slug,
                requirement_label=definition.label,
                description=f"{definition.label} list",
            )
            data_file.file.save(definition.filename, ContentFile(content), save=False)
            data_file.save()
            project.rebuild_data_artifacts()
            messages.success(request, f"{definition.label} saved for this project.")
        else:
            error_message = form.errors.as_text()
            if error_message:
                messages.error(request, error_message)
            else:
                messages.error(request, "Unable to process the submitted IP addresses. Please review the form for errors.")
        return redirect(self.get_success_url())


class ProjectDataFileDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete a supporting data file from a project."""

    model = ProjectDataFile

    def dispatch(self, request, *args, **kwargs):
        # Ensure ``self.request`` is available for ``get_object`` fallbacks that
        # rely on POST data before ``View.dispatch`` runs.
        self.request = request
        self.args = args
        self.kwargs = kwargs
        self.object = self.get_object()
        if self.object is None:
            if not request.user.is_authenticated:
                return self.handle_not_authenticated()
            project = self._resolve_project_from_request()
            if project is None or not project.user_can_edit(request.user):
                return self.handle_no_permission()
            self._resolved_project = project
            return self._handle_missing_file(request)
        self._resolved_project = getattr(self.object, "project", None)
        return super().dispatch(request, *args, **kwargs)

    def get_object(self, queryset=None):
        if hasattr(self, "_data_file_cache"):
            return self._data_file_cache

        queryset = (queryset or self.get_queryset()).select_related("project")
        pk = self.kwargs.get(self.pk_url_kwarg)
        data_file = None
        if pk is not None:
            data_file = queryset.filter(pk=pk).first()

        if data_file is None:
            project = self._resolve_project_from_request()
            slug = self._resolve_requirement_slug()
            if project is not None and slug:
                data_file = queryset.filter(project=project, requirement_slug=slug).first()

        if data_file is not None and not hasattr(self, "_resolved_project"):
            self._resolved_project = data_file.project

        self._data_file_cache = data_file
        return data_file

    def test_func(self):
        project = getattr(self, "_resolved_project", None)
        if project is None and self.object is not None:
            project = getattr(self.object, "project", None)
        if project is None:
            project = self._resolve_project_from_request()
        if project is None:
            return False
        self._resolved_project = project
        return project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self):
        project = getattr(self, "_resolved_project", None)
        if project is not None:
            return reverse("rolodex:project_detail", kwargs={"pk": project.pk}) + "#supplementals"
        if self.object is not None and getattr(self.object, "project", None) is not None:
            return (
                reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
                + "#supplementals"
            )
        return reverse("home:dashboard")

    def _resolve_requirement_slug(self) -> str:
        if hasattr(self, "_requirement_slug_cache"):
            return self._requirement_slug_cache
        slug = ""
        if hasattr(self, "request"):
            slug = (
                self.request.POST.get("requirement_slug")
                or self.request.GET.get("requirement_slug")
                or ""
            ).strip()
        self._requirement_slug_cache = slug
        return slug

    def _resolve_project_from_request(self) -> Optional[Project]:
        if hasattr(self, "_resolved_project") and self._resolved_project is not None:
            return self._resolved_project
        if not hasattr(self, "request"):
            return None
        project_id = self.request.POST.get("project_id") or self.request.GET.get("project_id")
        try:
            project_pk = int(project_id)
        except (TypeError, ValueError):
            return None
        project = Project.objects.filter(pk=project_pk).first()
        if project is not None:
            self._resolved_project = project
        return project

    def _handle_missing_file(self, request):
        messages.warning(
            request,
            "The selected data file could not be found. Please refresh the page and try again.",
        )
        redirect_url = self.get_success_url()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": False, "redirect_url": redirect_url}, status=404)
        return redirect(redirect_url)

    def post(self, request, *args, **kwargs):
        data_file = self.object
        if data_file is None:
            return self._handle_missing_file(request)
        if data_file.file:
            data_file.file.delete(save=False)
        project = data_file.project
        data_file.delete()
        project.rebuild_data_artifacts()
        messages.success(request, "Supporting data file deleted.")
        success_url = self.get_success_url()
        if request.headers.get("x-requested-with") == "XMLHttpRequest":
            return JsonResponse({"success": True, "redirect_url": success_url})
        return redirect(success_url)


class ProjectDataResponsesUpdate(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Persist responses to dynamically generated reporting questions."""

    model = Project

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to modify that project.")
        return redirect("home:dashboard")

    def get_success_url(self):
        return reverse("rolodex:project_detail", kwargs={"pk": self.get_object().pk}) + "#data"

    def post(self, request, *args, **kwargs):
        project = self.get_object()
        project_type_name = getattr(getattr(project, "project_type", None), "project_type", None)
        questions, _ = build_data_configuration(
            project.workbook_data,
            project_type_name,
            data_artifacts=project.data_artifacts,
            project_risks=project.risks,
        )
        form = ProjectDataResponsesForm(request.POST, question_definitions=questions)
        if form.is_valid():
            responses = dict(form.cleaned_data)
            scope_selection = responses.get("assessment_scope")
            normalized_scope = normalize_scope_selection(scope_selection)

            if normalized_scope:
                responses["assessment_scope"] = normalized_scope
                responses["scope_count"] = len(normalized_scope)

                raw_on_prem = responses.get("assessment_scope_cloud_on_prem")
                if "cloud" not in normalized_scope:
                    responses.pop("assessment_scope_cloud_on_prem", None)
                    on_prem_value: Optional[str] = None
                else:
                    on_prem_value = raw_on_prem if raw_on_prem in {"yes", "no"} else None
                    if on_prem_value is None:
                        responses.pop("assessment_scope_cloud_on_prem", None)
                    else:
                        responses["assessment_scope_cloud_on_prem"] = on_prem_value

                scope_summary = build_scope_summary(normalized_scope, on_prem_value)
                if scope_summary:
                    responses["scope_string"] = scope_summary
                else:
                    responses.pop("scope_string", None)
            else:
                responses.pop("assessment_scope", None)
                responses.pop("assessment_scope_cloud_on_prem", None)
                responses.pop("scope_count", None)
                responses.pop("scope_string", None)

            first_ca_value = responses.get("general_first_ca")
            if first_ca_value != "no":
                responses.pop("general_scope_changed", None)

            existing_grouped = (
                ensure_data_responses_defaults(project.data_responses)
                if isinstance(project.data_responses, dict)
                else ensure_data_responses_defaults({})
            )
            grouped_responses = _build_grouped_data_responses(
                responses,
                questions,
                existing_grouped=existing_grouped,
                workbook_data=project.workbook_data,
            )

            project.data_responses = ensure_data_responses_defaults(grouped_responses)
            project.save(update_fields=["data_responses"])
            project.rebuild_data_artifacts()
            project.refresh_from_db(
                fields=["workbook_data", "data_artifacts", "data_responses", "cap", "risks"]
            )
            messages.success(request, "Project data responses saved.")
        else:
            error_message = form.errors.as_text()
            if error_message:
                messages.error(request, error_message)
            else:
                messages.error(request, "Unable to save responses. Please review the form and try again.")
        return redirect(self.get_success_url())


class ProjectCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.Project` with zero or more
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective`.

    **Context**

    ``client``
        Instance of :model:`rolodex.Client` associated with this project
    ``assignments``
        Instance of the `ProjectAssignmentFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to projects list page

    **Template**

    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectForm
    template_name = "rolodex/project_form.html"

    def test_func(self):
        return Project.user_can_create(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Check if this request is for a specific client or not
        self.client = ""
        # Determine if ``pk`` is in the kwargs
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk")
            # Try to get the client from :model:`rolodex.Client`
            if pk:
                self.client = get_object_or_404(Client, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Project successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["client"] = self.client
        if self.client:
            ctx["cancel_link"] = reverse("rolodex:client_detail", kwargs={"pk": self.client.pk})
        else:
            ctx["cancel_link"] = reverse("rolodex:projects")
        ctx["assignments"] = self.assignments
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = None
        self.assignments = ProjectAssignmentFormSet(prefix="assign")
        self.assignments.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        self.assignments = ProjectAssignmentFormSet(request.POST, prefix="assign")
        if form.is_valid() and self.assignments.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        form.instance.extra_fields = ExtraFieldSpec.initial_json(self.model)

        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                obj = form.save(commit=False)
                self.object = obj
                obj.save()
                try:
                    for i in self.assignments.save(commit=False):
                        i.project = obj
                        i.save()
                    self.assignments.save_m2m()
                    form.save_m2m()
                except IntegrityError:  # pragma: no cover
                    form.add_error(None, "You cannot have duplicate assignments for a project.")
                    return self.form_invalid(form)
                return HttpResponseRedirect(self.get_success_url())
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.exception(message)
            return super().form_invalid(form)

    def get_initial(self):
        # Generate and assign a unique codename to the project
        codename_verified = False
        codename = ""
        while not codename_verified:
            codename = codenames.codename(uppercase=True)
            projects = Project.objects.filter(codename__iexact=codename)
            if not projects:
                codename_verified = True
        return {
            "client": self.client,
            "codename": codename,
        }


class ProjectUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Project`.

    **Context**

    ``object``
        Instance of :model:`rolodex.Project` being updated
    ``assignments``
        Instance of the `ProjectAssignmentFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to project's detail page

    **Template**

    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectForm
    template_name = "rolodex/project_form.html"

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.get_object()
        ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})
        ctx["assignments"] = self.assignments
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Project successfully saved.", extra_tags="alert-success")
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assignments = ProjectAssignmentFormSet(prefix="assign", instance=self.object)
        if self.object.projectassignment_set.all().count() < 1:
            self.assignments.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        self.assignments = ProjectAssignmentFormSet(request.POST, prefix="assign", instance=self.object)
        if form.is_valid() and self.assignments.is_valid():
            return self.form_valid(form)
        return self.form_invalid(form)

    def form_valid(self, form):
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                obj = form.save(commit=False)
                obj.save()
                try:
                    self.assignments.save()
                    form.save_m2m()
                except IntegrityError:  # pragma: no cover
                    form.add_error(None, "You cannot have duplicate assignments for a project.")
                    return self.form_invalid(form)
                return HttpResponseRedirect(self.get_success_url())
        except Exception:
            logger.exception("Failed to update the project.")
            return super().form_invalid(form)


class ProjectDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.Project`.

    **Context**

    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.Project`
    ``cancel_link``
        Link for the form's Cancel button to return to project's detail page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = Project
    template_name = "confirm_delete.html"

    def test_func(self):
        return verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "project and all associated data (reports, evidence, etc.)"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.id}))
        return ctx

    def get_success_url(self):
        return "{}#history".format(reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id}))


class ProjectComponentsUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update related components of an individual :model:`rolodex.Project`. This view is accessible
    to regular users to add, edit, and remove white cards, objectives, scopes, and targets..

    **Context**

    ``object``
        Instance of :model:`rolodex.Project` being updated
    ``whitecards``
        Instance of the `WhiteCardFormSet()` formset
    ``objectives``
        Instance of the `ProjectObjectiveFormSet()` formset
    ``scopes``
        Instance of the `ProjectScopeFormSet()` formset
    ``targets``
        Instance of the `ProjectTargetFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to project's detail page

    **Template**

    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectComponentForm
    template_name = "rolodex/project_form.html"

    def test_func(self):
        return self.get_object().user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["object"] = self.get_object()
        ctx["cancel_link"] = reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})
        if self.request.POST:
            ctx["objectives"] = ProjectObjectiveFormSet(self.request.POST, prefix="obj", instance=self.object)
            ctx["scopes"] = ProjectScopeFormSet(self.request.POST, prefix="scope", instance=self.object)
            ctx["targets"] = ProjectTargetFormSet(self.request.POST, prefix="target", instance=self.object)
            ctx["whitecards"] = WhiteCardFormSet(self.request.POST, prefix="card", instance=self.object)
            ctx["contacts"] = ProjectContactFormSet(self.request.POST, prefix="contact", instance=self.object)
        else:
            objectives = ProjectObjectiveFormSet(prefix="obj", instance=self.object)
            if self.object.projectobjective_set.all().count() < 1:
                objectives.extra = 1
            ctx["objectives"] = objectives
            scopes = ProjectScopeFormSet(prefix="scope", instance=self.object)
            if self.object.projectscope_set.all().count() < 1:
                scopes.extra = 1
            ctx["scopes"] = scopes
            targets = ProjectTargetFormSet(prefix="target", instance=self.object)
            if self.object.projecttarget_set.all().count() < 1:
                targets.extra = 1
            ctx["targets"] = targets
            whitecards = WhiteCardFormSet(prefix="card", instance=self.object)
            if self.object.whitecard_set.all().count() < 1:
                whitecards.extra = 1
            ctx["whitecards"] = whitecards
            contacts = ProjectContactFormSet(prefix="contact", instance=self.object)
            if self.object.projectcontact_set.all().count() < 1:
                contacts.extra = 1
            ctx["contacts"] = contacts
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Project components successfully saved.", extra_tags="alert-success")
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        scopes = ctx["scopes"]
        targets = ctx["targets"]
        objectives = ctx["objectives"]
        whitecards = ctx["whitecards"]
        contacts = ctx["contacts"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseProjectInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                obj = form.save()

                objectives_valid = objectives.is_valid()
                if objectives_valid:
                    objectives.instance = obj
                    objectives.save()

                scopes_valid = scopes.is_valid()
                if scopes_valid:
                    scopes.instance = obj
                    scopes.save()

                targets_valid = targets.is_valid()
                if targets_valid:
                    targets.instance = obj
                    targets.save()

                whitecards_valid = whitecards.is_valid()
                if whitecards_valid:
                    whitecards.instance = obj
                    whitecards.save()

                contacts_valid = contacts.is_valid()
                if contacts_valid:
                    contacts.instance = obj
                    try:
                        contacts.save()
                    except IntegrityError:  # pragma: no cover
                        form.add_error(None, "You cannot have duplicate contacts for a project.")

                # Proceed with form submission
                if (
                    form.is_valid()
                    and objectives_valid
                    and scopes_valid
                    and targets_valid
                    and whitecards_valid
                    and contacts_valid
                ):
                    obj.save()
                    return super().form_valid(form)
                # Raise an error to rollback transactions
                raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return ``form_invalid`` and display errors
        except Exception:
            logger.exception("Failed to update the project.")
            return super().form_invalid(form)


class ProjectNoteCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.ProjectNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Project` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to project's detail page

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ProjectNote
    form_class = ProjectNoteForm
    template_name = "note_form.html"

    def test_func(self):
        self.project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        return self.project_instance.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this project.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id}))

    def get_initial(self):
        return {"project": self.project_instance, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.project_instance
        ctx["cancel_link"] = "{}#notes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project_instance.id})
        )
        return ctx

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.operator = self.request.user
        obj.project_id = self.kwargs.get("pk")
        obj.save()
        return super().form_valid(form)


class ProjectNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ProjectNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Project` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to project's detail page

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ProjectNote
    form_class = ProjectNoteForm
    template_name = "note_form.html"

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("rolodex:project_detail", kwargs={"pk": self.get_object().project.pk}) + "#notes")

    def get_success_url(self):
        messages.success(self.request, "Note successfully updated.", extra_tags="alert-success")
        return "{}#notes".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.object.project
        ctx["cancel_link"] = "{}#notes".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id}))
        return ctx


class DeconflictionCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.Deconfliction`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to project detail page

    **Template**

    :template:`rolodex/deconfliction_form.html`
    """

    model = Deconfliction
    form_class = DeconflictionForm
    template_name = "rolodex/deconfliction_form.html"

    def test_func(self):
        self.project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        return self.project_instance.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Deconfliction successfully saved.",
            extra_tags="alert-success",
        )
        return "{}#deconflictions".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_initial(self):
        return {
            "status": 1,
        }

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.project_id = self.kwargs.get("pk")
        obj.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["project"] = self.project_instance
        ctx["cancel_link"] = "{}#deconflictions".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project_instance.id})
        )
        return ctx


class DeconflictionUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Deconfliction`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to Deconfliction detail page

    **Template**

    :template:`rolodex/deconfliction_form.html`
    """

    model = Deconfliction
    form_class = DeconflictionForm
    template_name = "rolodex/deconfliction_form.html"

    def test_func(self):
        return self.get_object().project.user_can_edit(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Deconfliction successfully saved.",
            extra_tags="alert-success",
        )
        return "{}#deconflictions".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#deconflictions".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx
