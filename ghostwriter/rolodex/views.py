"""This contains all of the views used by the Rolodex application."""

# Standard Libraries
import datetime
import json
import logging

# Django Imports
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View

# Ghostwriter Libraries
from ghostwriter.modules import codenames

from .filters import ClientFilter, ProjectFilter
from .forms_client import ClientContactFormSet, ClientForm, ClientNoteForm
from .forms_project import (
    ProjectAssignmentFormSet,
    ProjectForm,
    ProjectNoteForm,
    ProjectObjectiveFormSet,
    ProjectScopeFormSet,
    ProjectTargetFormSet,
)
from .models import (
    Client,
    ClientContact,
    ClientNote,
    ObjectivePriority,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectNote,
    ProjectObjective,
    ProjectScope,
    ProjectSubTask,
    ProjectTarget,
)

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
    html = render_to_string(
        "snippets/client_nav_tabs.html",
        {"client": client_instance},
    )
    return HttpResponse(html)


@login_required
def roll_codename(request):
    """
    Fetch a unique codename for use with a model.
    """

    try:
        codename_verified = False
        while not codename_verified:
            new_codename = codenames.codename(uppercase=True)
            try:
                Project.objects.filter(codename__iequal=new_codename)
                codename_verified = False
            except Exception:
                codename_verified = True
            try:
                Client.objects.filter(codename__iequal=new_codename)
                codename_verified = False
            except Exception:
                codename_verified = True
        data = {
            "result": "success",
            "message": "Codename successfuly generated",
            "codename": new_codename,
        }
        logger.info(
            "Generated new codename at request of %s",
            request.user,
        )
    except Exception as exception:
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
    if request.method == "POST" and request.is_ajax():
        data = request.POST.get("positions")
        project_id = request.POST.get("project")
        priority_class = request.POST.get("priority").replace("_priority", "")
        order = json.loads(data)

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
        # If all went well, return success
        data = {"result": "success"}
    else:
        data = {"result": "error"}
    return JsonResponse(data)


class ProjectObjectiveStatusUpdate(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Update the ``status`` field of an individual :model:`rolodex.ProjectObjective`.
    """

    model = ProjectObjective

    def post(self, *args, **kwargs):
        data = {}
        self.object = self.get_object()
        try:
            success = False
            # Save the old status
            old_status = self.object.status
            # Get all available status
            all_status = ObjectiveStatus.objects.all()
            total_status = all_status.count()
            for index, status in enumerate(all_status):
                if status == old_status:
                    # Check if we're at the last status
                    next_index = index + 1
                    if total_status - 1 >= next_index:
                        new_status = all_status[next_index]
                    # If at end, roll-over to the first status
                    else:
                        new_status = all_status[0]

                    self.object.status = new_status
                    logger.info("Switching to %s", new_status)
                    self.object.save()
                    success = True

            if not success:
                logger.warning(
                    "Failed to match old status, %s, with any existing status, so set status to ``0``"
                )
                new_status = all_status[0]
                self.object.status = new_status
                self.object.save()

            # Prepare the JSON response data
            data = {
                "result": "success",
                "status": new_status.objective_status,
            }
            logger.info(
                "Updated status of %s %s from %s to %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                old_status,
                new_status,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update objective status"}

        return JsonResponse(data)


class ProjectStatusToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.Project`.
    """

    model = Project

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.complete:
                self.object.complete = False
                data = {
                    "result": "success",
                    "message": "Project successfully marked as incomplete",
                    "status": "In Progress",
                    "toggle": 0,
                }
            else:
                self.object.complete = True
                data = {
                    "result": "success",
                    "message": "Project successfully marked as complete",
                    "status": "Complete",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update project status"}

        return JsonResponse(data)


class ProjectObjectiveDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectObjective`.
    """

    model = ProjectObjective

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Objective successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectAssignmentDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectAssignment`.
    """

    model = ProjectAssignment

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Assignment successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectNote`.
    """

    model = ProjectNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ClientNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ClientNote`.
    """

    model = ClientNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ClientContactDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ClientContact`.
    """

    model = ClientContact

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Contact successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTargetDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectTarget`.
    """

    model = ProjectTarget

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Target successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTargetToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``compromised`` field of an individual :model:`rolodex.ProjecTarget`.
    """

    model = ProjectTarget

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.compromised:
                self.object.compromised = False
                data = {
                    "result": "success",
                    "message": "Target successfully marked as NOT compromised",
                    "toggle": 0,
                }
            else:
                self.object.compromised = True
                data = {
                    "result": "success",
                    "message": "Target successfully marked as compromised",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update target status"}

        return JsonResponse(data)


class ProjectScopeDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectScope`.
    """

    model = ProjectScope

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Scope list successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTaskCreate(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Create a new :model:`rolodex.ProjectSubTask` for an individual :model:`ProjectObjective`.
    """

    model = ProjectObjective

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        task = self.request.POST.get("task", None)
        deadline = self.request.POST.get("deadline", None)
        try:
            if task and deadline:
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d")

                if deadline.date() <= self.object.deadline:
                    new_task = ProjectSubTask(
                        parent=self.object,
                        task=task,
                        deadline=deadline.date(),
                    )
                    new_task.save()
                    data = {
                        "result": "success",
                        "message": "Task successfully saved",
                    }
                    logger.info(
                        "Created new %s %s under %s %s by request of %s",
                        new_task.__class__.__name__,
                        new_task.id,
                        self.object.__class__.__name__,
                        self.object.id,
                        self.request.user,
                    )
                else:
                    data = {
                        "result": "error",
                        "message": "Your new due date must be before (or the same) as the objective due date",
                    }
            else:
                data = {
                    "result": "error",
                    "message": "Your new task must have a valid task and due date",
                }
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not create new task with provided values",
            }

        return JsonResponse(data)


class ProjectTaskToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.complete:
                self.object.complete = False
                self.object.marked_complete = None
                data = {
                    "result": "success",
                    "message": "Task successfully marked as incomplete",
                    "toggle": 0,
                }
            else:
                self.object.complete = True
                self.object.marked_complete = datetime.date.today()
                data = {
                    "result": "success",
                    "message": "Task successfully marked as complete",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update task status"}

        return JsonResponse(data)


class ProjectObjectiveToggle(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Toggle the ``complete`` field of an individual :model:`rolodex.ProjectObjective`.
    """

    model = ProjectObjective

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.complete:
                self.object.complete = False
                self.object.marked_complete = None
                data = {
                    "result": "success",
                    "message": "Objective successfully marked as incomplete",
                    "toggle": 0,
                }
            else:
                self.object.complete = True
                self.object.marked_complete = datetime.date.today()
                data = {
                    "result": "success",
                    "message": "Objective successfully marked as complete",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled status of %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update objective status"}

        return JsonResponse(data)


class ProjectTaskDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        obj_id = self.object.id
        self.object.delete()
        data = {"result": "success", "message": "Task successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            obj_id,
            self.request.user,
        )
        return JsonResponse(data)


class ProjectTaskUpdate(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Update an individual :model:`rolodex.ProjectSubTask`.
    """

    model = ProjectSubTask

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        task = self.request.POST.get("task", None)
        deadline = self.request.POST.get("deadline", None)
        try:
            if task and deadline:
                deadline = datetime.datetime.strptime(deadline, "%Y-%m-%d")
                logger.info(deadline.date())
                logger.info(self.object.deadline)
                if deadline.date() <= self.object.parent.deadline:
                    self.object.task = task
                    self.object.deadline = deadline.date()
                    self.object.save()
                    data = {
                        "result": "success",
                        "message": "Task successfully updated",
                    }
                    logger.info(
                        "Updated %s %s by request of %s",
                        self.object.__class__.__name__,
                        self.object.id,
                        self.request.user,
                    )
                else:
                    data = {
                        "result": "error",
                        "message": "Your task due date must be before (or the same) as the objective due date",
                    }
            else:
                data = {
                    "result": "error",
                    "message": "Task cannot be updated without a valid task and due date",
                }
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {
                "result": "error",
                "message": "Could not update the task with provided values",
            }

        return JsonResponse(data)


class ProjectTaskRefresh(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following an update or delete action related
    to an individual :model:`rolodex.ProjectSubTask.

    **Template**

    :template:`snippets/project_objective_subtasks.html`
    """

    model = ProjectObjective

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        html = render_to_string(
            "snippets/project_objective_subtasks.html",
            {"objective": self.object},
            request=self.request,
        )
        return HttpResponse(html)


class ProjectObjectiveRefresh(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following an update action related
    to an individual :model:`rolodex.ProjectObjective`.

    **Template**

    :template:`snippets/project_objective_row.html`
    """

    model = ProjectObjective

    def get(self, *args, **kwargs):
        self.object = self.get_object()
        html = render_to_string(
            "snippets/project_objective_row.html",
            {"objective": self.object},
            request=self.request,
        )
        return HttpResponse(html)


##################
# View Functions #
##################


@login_required
def index(request):
    """
    Display the main homepage.
    """
    return HttpResponseRedirect(reverse("home:dashboard"))


@login_required
def client_list(request):
    """
    Display a list of all :model:`rolodex.Client`.

    **Context**

    ``filter``
        Instance of :filter:`rolodex.ClientFilter`

    **Template**

    :template:`rolodex/client_list.html`
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get("client_search").strip()
    except Exception:
        search_term = ""
    if search_term:
        messages.success(
            request,
            "Displaying search results for: {}".format(search_term),
            extra_tags="alert-success",
        )
        client_list = Client.objects.filter(name__icontains=search_term).order_by("name")
    else:
        client_list = Client.objects.all().order_by("name")
    client_filter = ClientFilter(request.GET, queryset=client_list)
    return render(request, "rolodex/client_list.html", {"filter": client_filter})


@login_required
def project_list(request):
    """
    Display a list of all :model:`rolodex.Project`.

    **Context**

    ``filter``
        Instance of :filter:`rolodex.ProjectFilter`

    **Template**

    :template:`rolodex/project_list.html`
    """
    project_list = (
        Project.objects.select_related("client").all().order_by("complete", "client")
    )
    project_list = ProjectFilter(request.GET, queryset=project_list)
    return render(request, "rolodex/project_list.html", {"filter": project_list})


################
# View Classes #
################

# CBVs related to :model:`rolodex.Client`


class ClientDetailView(LoginRequiredMixin, DetailView):
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

    def get_context_data(self, **kwargs):
        # Ghostwriter Libraries
        from ghostwriter.shepherd.models import History, ServerHistory, TransientServer

        ctx = super(ClientDetailView, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        domain_history = History.objects.select_related("domain").filter(
            client=client_instance
        )
        server_history = ServerHistory.objects.select_related("server").filter(
            client=client_instance
        )
        projects = Project.objects.filter(client=client_instance)
        client_domains = []
        for domain in domain_history:
            client_domains.append(domain)
        client_servers = []
        for server in server_history:
            client_servers.append(server)
        client_vps = []
        for project in projects:
            vps_queryset = TransientServer.objects.filter(project=project)
            for vps in vps_queryset:
                client_vps.append(vps)
        ctx["domains"] = client_domains
        ctx["servers"] = client_servers
        ctx["vps"] = client_vps
        return ctx


class ClientCreate(LoginRequiredMixin, CreateView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            "Client successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(ClientCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("rolodex:clients")
        if self.request.POST:
            ctx["contacts"] = ClientContactFormSet(self.request.POST, prefix="poc")
        else:
            # Add extra forms to aid in configuration of a new client
            contacts = ClientContactFormSet(prefix="poc")
            contacts.extra = 1
            # Assign the re-configured formsets to context vars
            ctx["contacts"] = contacts
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        contacts = ctx["contacts"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseClientContactInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()

                contacts_valid = contacts.is_valid()
                if contacts_valid:
                    contacts.instance = self.object
                    contacts.save()

                if form.is_valid() and contacts_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super(ClientCreate, self).form_invalid(form)

    def get_initial(self):
        # Generate and assign a unique codename to the project
        codename_verified = False
        codename = ""
        while not codename_verified:
            codename = codenames.codename(uppercase=True)
            try:
                Project.objects.filter(codename__iequal=codename)
            except Exception:
                codename_verified = True
        return {
            "codename": codename,
        }


class ClientUpdate(LoginRequiredMixin, UpdateView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            "Client successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(ClientUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "rolodex:client_detail", kwargs={"pk": self.object.id}
        )
        if self.request.POST:
            ctx["contacts"] = ClientContactFormSet(
                self.request.POST, prefix="poc", instance=self.object
            )
        else:
            ctx["contacts"] = ClientContactFormSet(prefix="poc", instance=self.object)
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        contacts = ctx["contacts"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseClientContactInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()

                contacts_valid = contacts.is_valid()
                if contacts_valid:
                    contacts.instance = self.object
                    contacts.save()

                if form.is_valid() and contacts_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super(ClientUpdate, self).form_invalid(form)


class ClientDelete(LoginRequiredMixin, DeleteView):
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

    def get_context_data(self, **kwargs):
        ctx = super(ClientDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "client and all associated data"
        ctx["object_to_be_deleted"] = queryset.name
        ctx["cancel_link"] = reverse(
            "rolodex:client_detail", kwargs={"pk": self.object.id}
        )
        return ctx


class ClientNoteCreate(LoginRequiredMixin, CreateView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this client.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_initial(self):
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        client = client_instance
        return {"client": client, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(ClientNoteCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        ctx["note_object"] = client_instance
        ctx["cancel_link"] = "{}#notes".format(
            reverse("rolodex:client_detail", kwargs={"pk": client_instance.id})
        )
        return ctx

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.client_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class ClientNoteUpdate(LoginRequiredMixin, UpdateView):
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

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated.", extra_tags="alert-success"
        )
        return "{}#notes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ClientNoteUpdate, self).get_context_data(**kwargs)
        ctx["note_object"] = self.object.client
        ctx["cancel_link"] = "{}#notes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )
        return ctx


# CBVs related to :model:`rolodex.Project`


class ProjectDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`rolodex.Project`.

    **Template**

    :template:`rolodex/project_detail.html`
    """

    model = Project


class ProjectCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.Project` with zero or more
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective`.

    **Context**

    ``client``
        Instance of :model:`rolodex.CLient` associated with this project
    ``objectives``
        Instance of the `ProjectObjectiveFormSet()` formset
    ``assignments``
        Instance of the `ProjectAssignmentFormSet()` formset
    ``scopes``
        Instance of the `ProjectScopeFormSet()` formset
    ``targets``
        Instance of the `ProjectTargetFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to projects list page

    **Template**

    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectForm
    template_name = "rolodex/project_form.html"

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
        ctx = super(ProjectCreate, self).get_context_data(**kwargs)
        ctx["client"] = self.client
        if self.client:
            ctx["cancel_link"] = reverse(
                "rolodex:client_detail", kwargs={"pk": self.client.pk}
            )
        else:
            ctx["cancel_link"] = reverse("rolodex:projects")
        if self.request.POST:
            ctx["objectives"] = ProjectObjectiveFormSet(self.request.POST, prefix="obj")
            ctx["assignments"] = ProjectAssignmentFormSet(
                self.request.POST, prefix="assign"
            )
            ctx["scopes"] = ProjectScopeFormSet(self.request.POST, prefix="scope")
            ctx["targets"] = ProjectTargetFormSet(self.request.POST, prefix="target")
        else:
            # Add extra forms to aid in configuration of a new project
            objectives = ProjectObjectiveFormSet(prefix="obj")
            objectives.extra = 1
            assignments = ProjectAssignmentFormSet(prefix="assign")
            assignments.extra = 1
            scopes = ProjectScopeFormSet(prefix="scope")
            scopes.extra = 1
            targets = ProjectTargetFormSet(prefix="target")
            targets.extra = 1
            # Assign the re-configured formsets to context vars
            ctx["objectives"] = objectives
            ctx["assignments"] = assignments
            ctx["scopes"] = scopes
            ctx["targets"] = targets
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        scopes = ctx["scopes"]
        targets = ctx["targets"]
        objectives = ctx["objectives"]
        assignments = ctx["assignments"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseProjectInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()

                objectives_valid = objectives.is_valid()
                if objectives_valid:
                    objectives.instance = self.object
                    objectives.save()

                assignments_valid = assignments.is_valid()
                if assignments_valid:
                    assignments.instance = self.object
                    assignments.save()

                scopes_valid = scopes.is_valid()
                if scopes_valid:
                    scopes.instance = self.object
                    scopes.save()

                targets_valid = targets.is_valid()
                if targets_valid:
                    targets.instance = self.object
                    targets.save()

                if (
                    form.is_valid()
                    and objectives_valid
                    and assignments_valid
                    and scopes_valid
                    and targets_valid
                ):
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return ``form_invalid`` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super(ProjectCreate, self).form_invalid(form)

    def get_initial(self):
        # Generate and assign a unique codename to the project
        codename_verified = False
        codename = ""
        while not codename_verified:
            codename = codenames.codename(uppercase=True)
            try:
                Project.objects.filter(codename__iequal=codename)
            except Exception:
                codename_verified = True
        return {
            "client": self.client,
            "codename": codename,
        }


class ProjectUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Project`.

    **Context**

    ``object``
        Instance of :model:`rolodex.Project` being updated
    ``objectives``
        Instance of the `ProjectObjectiveFormSet()` formset
    ``assignments``
        Instance of the `ProjectAssignmentFormSet()` formset
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
    form_class = ProjectForm
    template_name = "rolodex/project_form.html"

    def get_context_data(self, **kwargs):
        ctx = super(ProjectUpdate, self).get_context_data(**kwargs)
        ctx["object"] = self.get_object()
        ctx["cancel_link"] = reverse(
            "rolodex:project_detail", kwargs={"pk": self.object.pk}
        )
        if self.request.POST:
            ctx["objectives"] = ProjectObjectiveFormSet(
                self.request.POST, prefix="obj", instance=self.object
            )
            ctx["assignments"] = ProjectAssignmentFormSet(
                self.request.POST, prefix="assign", instance=self.object
            )
            ctx["scopes"] = ProjectScopeFormSet(
                self.request.POST, prefix="scope", instance=self.object
            )
            ctx["targets"] = ProjectTargetFormSet(
                self.request.POST, prefix="target", instance=self.object
            )
        else:
            ctx["objectives"] = ProjectObjectiveFormSet(
                prefix="obj", instance=self.object
            )
            ctx["assignments"] = ProjectAssignmentFormSet(
                prefix="assign", instance=self.object
            )
            ctx["scopes"] = ProjectScopeFormSet(prefix="scope", instance=self.object)
            ctx["targets"] = ProjectTargetFormSet(prefix="target", instance=self.object)
        return ctx

    def get_success_url(self):
        messages.success(
            self.request, "Project successfully saved.", extra_tags="alert-success"
        )
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        scopes = ctx["scopes"]
        targets = ctx["targets"]
        objectives = ctx["objectives"]
        assignments = ctx["assignments"]

        # Ghostwriter Libraries
        from ghostwriter.shepherd.models import History, ServerHistory

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseProjectInlineFormSet``
        try:
            with transaction.atomic():
                # Update infrastructure if project's dates changed
                update = form.cleaned_data["update_checkouts"]
                if update:
                    if (
                        "end_date" in form.changed_data
                        or "start_date" in form.changed_data
                    ):
                        logger.info(
                            "Date changed on Project %s, so updating domain and server checkouts",
                            self.object.pk,
                        )
                        # Get the project's current dates
                        old_project_data = Project.objects.get(pk=self.object.pk)
                        old_start_date = old_project_data.start_date
                        old_end_date = old_project_data.end_date
                        # Form dates
                        new_start_date = form.cleaned_data["start_date"]
                        new_end_date = form.cleaned_data["end_date"]
                        # Timedelta changes
                        start_timedelta = new_start_date - old_start_date
                        end_timedelta = new_end_date - old_end_date
                        try:
                            # Update checkouts based on deltas
                            domain_checkouts = History.objects.filter(
                                project=self.object.pk
                            )
                            server_checkouts = ServerHistory.objects.filter(
                                project=self.object.pk
                            )
                            for checkout in domain_checkouts:
                                logger.info(
                                    "Updating checkout for %s from %s - %s to %s - %s",
                                    checkout.domain,
                                    checkout.start_date,
                                    checkout.end_date,
                                    checkout.start_date + start_timedelta,
                                    checkout.end_date + end_timedelta,
                                )
                                checkout.start_date = (
                                    checkout.start_date + start_timedelta
                                )
                                checkout.end_date = checkout.end_date + end_timedelta
                                checkout.save()
                            for checkout in server_checkouts:
                                logger.info(
                                    "Updating checkout for %s from %s-%s to %s-%s",
                                    checkout.server,
                                    checkout.start_date,
                                    checkout.end_date,
                                    checkout.start_date + start_timedelta,
                                    checkout.end_date + end_timedelta,
                                )
                                checkout.start_date = (
                                    checkout.start_date + start_timedelta
                                )
                                checkout.end_date = checkout.end_date + end_timedelta
                                checkout.save()
                        except Exception:
                            message = "Could not update checkouts with your changed project dates. Review your checkouts or uncheck the box for automatic updates."
                            form.add_error("update_checkouts", message)

                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()

                objectives_valid = objectives.is_valid()
                if objectives_valid:
                    objectives.instance = self.object
                    objectives.save()

                assignments_valid = assignments.is_valid()
                if assignments_valid:
                    assignments.instance = self.object
                    assignments.save()

                scopes_valid = scopes.is_valid()
                if scopes_valid:
                    scopes.instance = self.object
                    scopes.save()

                targets_valid = targets.is_valid()
                if targets_valid:
                    targets.instance = self.object
                    targets.save()

                # Proceed with form submission
                if (
                    form.is_valid()
                    and objectives_valid
                    and assignments_valid
                    and scopes_valid
                    and targets_valid
                ):
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return ``form_invalid`` and display errors
        except Exception:
            logger.exception("Failed to update the project")
            return super(ProjectUpdate, self).form_invalid(form)


class ProjectDelete(LoginRequiredMixin, DeleteView):
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

    def get_context_data(self, **kwargs):
        ctx = super(ProjectDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "project and all associated data (reports, evidence, etc.)"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.id})
        )
        return ctx

    def get_success_url(self):
        return "{}#history".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )


class ProjectNoteCreate(LoginRequiredMixin, CreateView):
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

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this project.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_initial(self):
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project = project_instance
        return {"project": project, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(ProjectNoteCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        ctx["note_object"] = project_instance
        ctx["cancel_link"] = "{}#notes".format(
            reverse("rolodex:project_detail", kwargs={"pk": project_instance.id})
        )
        return ctx

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.project_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class ProjectNoteUpdate(LoginRequiredMixin, UpdateView):
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

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated.", extra_tags="alert-success"
        )
        return "{}#notes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ProjectNoteUpdate, self).get_context_data(**kwargs)
        ctx["note_object"] = self.object.project
        ctx["cancel_link"] = "{}#notes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx
