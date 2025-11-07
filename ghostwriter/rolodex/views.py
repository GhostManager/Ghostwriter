"""This contains all the views used by the Rolodex application."""

# Standard Libraries
import datetime
import json
import logging

# Django Imports
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError, transaction
from django.db.models import Q
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
    ProjectInviteFormSet,
    ProjectNoteForm,
    ProjectObjectiveFormSet,
    ProjectScopeFormSet,
    ProjectTargetFormSet,
    WhiteCardFormSet,
)
from ghostwriter.rolodex.models import (
    Client,
    ClientContact,
    ClientInvite,
    ClientNote,
    Deconfliction,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectContact,
    ProjectInvite,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
)
from ghostwriter.shepherd.models import History, ServerHistory, TransientServer

# Using __name__ resolves to ghostwriter.rolodex.views
logger = logging.getLogger(__name__)


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
        return ctx


class ProjectCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`rolodex.Project` with zero or more
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective`.

    **Context**

    ``client``
        Instance of :model:`rolodex.Client` associated with this project
    ``assignments``
        Instance of the `ProjectAssignmentFormSet()` formset
    ``invites``
        Instance of the `ProjectInviteFormSet()` formset
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
        ctx["invites"] = self.invites
        return ctx

    def get(self, request, *args, **kwargs):
        self.object = None
        self.assignments = ProjectAssignmentFormSet(prefix="assign")
        self.assignments.extra = 1
        self.invites = ProjectInviteFormSet(prefix="invite")
        self.invites.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = None
        form = self.get_form()
        self.assignments = ProjectAssignmentFormSet(request.POST, prefix="assign")
        self.invites = ProjectInviteFormSet(request.POST, prefix="invite")
        if form.is_valid() and self.assignments.is_valid() and self.invites.is_valid():
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
                    for i in self.invites.save(commit=False):
                        i.project = obj
                        i.save()
                    self.assignments.save_m2m()
                    self.invites.save_m2m()
                    form.save_m2m()
                except IntegrityError:  # pragma: no cover
                    form.add_error(None, "You cannot have duplicate assignments or invites for a project.")
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
    ``invites``
        Instance of the `ProjectInviteFormSet()` formset
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
        ctx["invites"] = self.invites
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Project successfully saved.", extra_tags="alert-success")
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def get(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.assignments = ProjectAssignmentFormSet(prefix="assign", instance=self.object)
        if self.object.projectassignment_set.all().count() < 1:
            self.assignments.extra = 1
        self.invites = ProjectInviteFormSet(prefix="invite", instance=self.object)
        if self.object.projectinvite_set.all().count() < 1:
            self.invites.extra = 1
        return super().get(request, *args, **kwargs)

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        form = self.get_form()
        self.assignments = ProjectAssignmentFormSet(request.POST, prefix="assign", instance=self.object)
        self.invites = ProjectInviteFormSet(request.POST, prefix="invite", instance=self.object)
        if form.is_valid() and self.assignments.is_valid() and self.invites.is_valid():
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
                    self.invites.save()
                    form.save_m2m()
                except IntegrityError:  # pragma: no cover
                    form.add_error(None, "You cannot have duplicate assignments or invites for a project.")
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
