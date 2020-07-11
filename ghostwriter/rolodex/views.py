"""This contains all of the views used by the Rolodex application."""

import logging

from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db import transaction
from django.forms import formset_factory, inlineformset_factory
from django.forms.utils import ErrorList
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404, render
from django.urls import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views import generic
from django.views.generic.edit import CreateView, DeleteView, UpdateView

from ghostwriter.modules import codenames

from .filters import ClientFilter, ProjectFilter
from .forms import (
    AssignmentCreateForm,
    AssignmentCreateFormset,
    BaseProjectAssignmentInlineFormSet,
    BaseProjectObjectiveInlineFormSet,
    ClientContactCreateForm,
    ClientCreateForm,
    ClientNoteCreateForm,
    ProjectCreateForm,
    ProjectNoteCreateForm,
    ProjectObjectiveCreateForm,
    ProjectObjectiveCreateFormset,
)
from .models import (
    Client,
    ClientContact,
    ClientNote,
    ObjectiveStatus,
    Project,
    ProjectAssignment,
    ProjectNote,
    ProjectObjective,
)

# Using __name__ resolves to ghostwriter.rolodex.views
logger = logging.getLogger(__name__)


##################
# AJAX Functions #
##################


@login_required
def ajax_load_project(request):
    """
    View used with AJAX requests to retrieve instances of :model:`rolodex.Project` during
    the creation of individual :model:`rolodex.ProjectAssignment`.

    **Template**

    :template:`rolodex/assignment_form.html`
    """
    project_id = request.GET.get("project")
    project = Project.objects.filter(id=project_id)
    data = serializers.serialize("json", project)
    return HttpResponse(data, content_type="application/json")


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

    **Template**

    :template:`rolodex/client_list.html`
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get("client_search")
    except Exception:
        search_term = ""
    if search_term:
        messages.success(
            request,
            "Displaying search results for: {}".format(search_term),
            extra_tags="alert-success",
        )
        client_list = Client.objects.filter(name__icontains=search_term).order_by(
            "name"
        )
    else:
        client_list = Client.objects.all().order_by("name")
    client_filter = ClientFilter(request.GET, queryset=client_list)
    return render(request, "rolodex/client_list.html", {"filter": client_filter})


@login_required
def project_list(request):
    """
    Display a list of all :model:`rolodex.Project`.

    **Template**

    :template:`rolodex/project_list.html`
    """
    project_list = (
        Project.objects.select_related("client").all().order_by("complete", "client")
    )
    project_list = ProjectFilter(request.GET, queryset=project_list)
    return render(request, "rolodex/project_list.html", {"filter": project_list})


@login_required
def assign_client_codename(request, pk):
    """
    Assign a codename to an individual :model:`rolodex.Client`.
    """
    client_instance = Client.objects.get(id=pk)
    codename_verified = False
    while not codename_verified:
        new_codename = codenames.codename(uppercase=True)
        try:
            Client.objects.filter(codename__iequal=new_codename)
        except Exception:
            codename_verified = True
    client_instance.codename = new_codename
    client_instance.save()
    # Redirect to the client's details page
    return HttpResponseRedirect(reverse("rolodex:client_detail", args=(pk,)))


@login_required
def assign_project_codename(request, pk):
    """
    Assign a codename to an individual :model:`rolodex.Project`.
    """
    project_instance = Project.objects.get(id=pk)
    codename_verified = False
    while not codename_verified:
        new_codename = codenames.codename(uppercase=True)
        try:
            Project.objects.filter(codename__iequal=new_codename)
        except Exception:
            codename_verified = True
    project_instance.codename = new_codename
    project_instance.save()
    # Redirect to the project's details page
    return HttpResponseRedirect(reverse("rolodex:project_detail", args=(pk,)))


@login_required
def complete_project(request, pk):
    """
    Toggle the `complete` field of an individual :model:`rolodex.Project` to `True`.
    """
    try:
        project_instance = Project.objects.get(pk=pk)
        if project_instance:
            project_instance.complete = True
            project_instance.save()
            messages.success(
                request,
                "Project is now marked as complete and closed.",
                extra_tags="alert-success",
            )
            return HttpResponseRedirect(reverse("rolodex:project_detail", args=(pk,)))
        else:
            messages.error(
                request,
                "The specified project does not exist!",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("rolodex:projects"))
    except Exception:
        messages.error(
            request,
            "Could not set the requested project as complete.",
            extra_tags="alert-danger",
        )
        return HttpResponseRedirect(reverse("rolodex:projects"))


@login_required
def reopen_project(request, pk):
    """
    Toggle the `complete` field of an individual :model:`rolodex.Project` to `False`.
    """
    try:
        project_instance = Project.objects.get(pk=pk)
        if project_instance:
            project_instance.complete = False
            project_instance.save()
            messages.success(
                request, "Project has been reopened.", extra_tags="alert-success"
            )
            return HttpResponseRedirect(reverse("rolodex:project_detail", args=(pk,)))
        else:
            messages.error(
                request,
                "The specified project does not exist!",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("rolodex:projects"))
    except Exception:
        messages.error(
            request,
            "Could not reopen the requested project.",
            extra_tags="alert-danger",
        )
        return HttpResponseRedirect(reverse("rolodex:projects"))


@login_required
def set_objective_status(request, pk, status):
    """
    Update the `status` field of an individual :model:`rolodex.ProjectObjective`.
    """
    try:
        project_objective = ProjectObjective.objects.get(pk=pk)
        if project_objective:
            if status == "active":
                project_objective.status = ObjectiveStatus.objects.get(pk=1)
                project_objective.save()
                messages.success(
                    request,
                    '"{}" is now Active.'.format(project_objective.objective),
                    extra_tags="alert-success",
                )
            elif status == "onhold":
                project_objective.status = ObjectiveStatus.objects.get(pk=2)
                project_objective.save()
                messages.success(
                    request,
                    '"{}" is now On Hold.'.format(project_objective.objective),
                    extra_tags="alert-success",
                )
            elif status == "complete":
                project_objective.status = ObjectiveStatus.objects.get(pk=3)
                project_objective.save()
                messages.success(
                    request,
                    '"{}" is now Complete.'.format(project_objective.objective),
                    extra_tags="alert-success",
                )
            else:
                messages.error(
                    request,
                    "You provided an invalid objective status ¯\_(ツ)_/¯",
                    extra_tags="alert-danger",
                )
            return HttpResponseRedirect(
                "{}#collapseObjectives".format(
                    reverse(
                        "rolodex:project_detail",
                        kwargs={"pk": project_objective.project.pk},
                    )
                )
            )
        else:
            messages.error(
                request,
                "The specified report does not exist!",
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("reporting:reports"))
    except Exception:
        messages.error(
            request,
            "Could not update the objective's status!",
            extra_tags="alert-danger",
        )
        return HttpResponseRedirect(
            reverse("rolodex:project", args=(project_objective.project.pk,))
        )


################
# View Classes #
################


class ClientDetailView(LoginRequiredMixin, generic.DetailView):
    """
    Display an individual :model:`rolodex.Client`.
    
    **Context**
    
    ``domains``
        List of :model:`shepherd.Domain` associated with :model:`rolodex.Client`.
    ``servers``
        List of :model:`shepherd.StaticServer` associated with :model:`rolodex.Client`.
    ``vps``
        List of :model:`shepherd.TransientServer` associated with :model:`rolodex.Client`.
    
    **Template**
    
    :template:`rolodex/client_detail.html`
    """

    model = Client

    def get_context_data(self, **kwargs):
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

    **Template**
    
    :template:`rolodex/client_form.html`
    """

    model = Client
    form_class = ClientCreateForm

    def get_success_url(self):
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def form_valid(self, form):
        codename_verified = False
        while not codename_verified:
            new_codename = codenames.codename(uppercase=True)
            try:
                Client.objects.filter(codename__iequal=new_codename)
            except Exception:
                codename_verified = True
        form.instance.codename = new_codename
        return super().form_valid(form)


class ClientUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Client`.
    
    **Template**
    
    :template:`rolodex/client_form.html`
    """

    model = Client
    form_class = ClientCreateForm

    def get_success_url(self):
        return reverse("rolodex:client_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        return {
            "codename": client_instance.codename,
        }


class ClientDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.Client`.
    
    **Context**
    
    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.Client`.
    
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
        return ctx


class ProjectDetailView(LoginRequiredMixin, generic.DetailView):
    """
    Display an individual :model:`rolodex.Project`.

    **Template**
    
    :template:`rolodex/project_detail.html`
    """

    model = Project


# Setup formsets for `ProjectCreate()`
# Default to one form each so initial form is not overly long
ObjectiveFormset = inlineformset_factory(
    Project,
    ProjectObjective,
    form=ProjectObjectiveCreateFormset,
    extra=1,
    formset=BaseProjectObjectiveInlineFormSet,
)
AssignmentFormset = inlineformset_factory(
    Project,
    ProjectAssignment,
    form=AssignmentCreateFormset,
    extra=1,
    formset=BaseProjectAssignmentInlineFormSet,
)


class ProjectCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.Project` with zero or more
    :model:`rolodex.ProjectAssignment` and :model:`rolodex.ProjectObjective`.
    
    **Context**
    
    ``client_name``
        An instance of :model:`rolodex.Client.
    ``objectives``
        An instance of `ObjectiveFormSet()`
    ``assignments``
        An instance of `AssignmentFormSet()`
    
    **Template**
    
    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectCreateForm

    def get_success_url(self):
        messages.success(
            self.request,
            "Project successfully created for this client.",
            extra_tags="alert-success",
        )
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(ProjectCreate, self).get_context_data(**kwargs)
        if self.request.POST:
            ctx["objectives"] = ObjectiveFormset(self.request.POST, prefix="obj")
            ctx["assignments"] = AssignmentFormset(self.request.POST, prefix="assign")
        else:
            ctx["objectives"] = ObjectiveFormset(prefix="obj")
            ctx["assignments"] = AssignmentFormset(prefix="assign")
        return ctx

    def form_valid(self, form):
        # Generate and assign a unique codename to the project
        codename_verified = False
        while not codename_verified:
            new_codename = codenames.codename(uppercase=True)
            try:
                Project.objects.filter(codename__iequal=new_codename)
            except Exception:
                codename_verified = True
        form.instance.codename = new_codename

        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        objectives = ctx["objectives"]
        assignments = ctx["assignments"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, `BaseProjectInlineFormSet`
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()

                objectives_valid = objectives.is_valid()
                if objectives_valid:
                    objectives.instance = self.object
                    objectives_object = objectives.save()

                assignments_valid = assignments.is_valid()
                if assignments_valid:
                    assignments.instance = self.object
                    assignments.save()

                if form.is_valid() and objectives_valid and assignments_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError("Invalid form data")
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(exception)
            return super(ProjectCreate, self).form_invalid(form)

    def get_initial(self):
        client = ""
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk")
            if pk:
                client = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        return {
            "client": client,
        }


class ProjectUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.Project`.
    
    **Template**
    
    :template:`rolodex/project_form.html`
    """

    model = Project
    form_class = ProjectCreateForm

    def get_context_data(self, **kwargs):
        ctx = super(ProjectUpdate, self).get_context_data(**kwargs)
        ctx["origin"] = self.request.META.get("HTTP_REFERER")
        if self.request.POST:
            ctx["objectives"] = ObjectiveFormset(
                self.request.POST, prefix="obj", instance=self.object
            )
            ctx["assignments"] = AssignmentFormset(
                self.request.POST, prefix="assign", instance=self.object
            )
        else:
            ctx["objectives"] = ObjectiveFormset(prefix="obj", instance=self.object)
            ctx["assignments"] = AssignmentFormset(
                prefix="assign", instance=self.object
            )
        return ctx

    def get_success_url(self):
        messages.success(
            self.request, "Project successfully updated.", extra_tags="alert-success"
        )
        return reverse("rolodex:project_detail", kwargs={"pk": self.object.pk})

    def get_initial(self):
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        return {
            "codename": project_instance.codename,
        }

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        objectives = ctx["objectives"]
        assignments = ctx["assignments"]
        print("GOT HERE")

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, `BaseProjectInlineFormSet`
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()
                print("SAVED")

                objectives_valid = objectives.is_valid()
                if objectives_valid:
                    objectives.instance = self.object
                    objectives_object = objectives.save()
                print(objectives_valid)
                assignments_valid = assignments.is_valid()
                if assignments_valid:
                    assignments.instance = self.object
                    assignments.save()
                print(assignments_valid)
                if form.is_valid() and objectives_valid and assignments_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError("Invalid form data")
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(exception)
            return super(ProjectUpdate, self).form_invalid(form)


class ProjectDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.Project`.
    
    **Context**
    
    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.Project`.
    
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
        return ctx

    def get_success_url(self):
        return "{}#collapseHistory".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )


class ClientContactCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.ClientContact`.
    
    **Context**
    
    ``client_name``
        An instance of :model:`rolodex.Client`.
    
    **Template**
    
    :template:`rolodex/contact_form.html`
    """

    model = ClientContact
    form_class = ClientContactCreateForm
    template_name = "rolodex/contact_form.html"

    def get_success_url(self):
        return "{}#collapsePOC".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_initial(self):
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        client = client_instance
        return {
            "client": client,
        }

    def get_context_data(self, **kwargs):
        ctx = super(ClientContactCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        ctx["client_name"] = client_instance
        return ctx


class ClientContactUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ClientContact`.
    
    **Template**
    
    :template:`rolodex/contact_form.html`
    """

    model = ClientContact
    form_class = ClientContactCreateForm
    template_name = "rolodex/contact_form.html"

    def get_success_url(self):
        return "{}#collapsePOC".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )


class ClientContactDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.ClientContact`.
    
    **Context**
    
    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.ClientContact`.
    
    **Template**
    
    :template:`templates/confirm_delete.html`
    """

    model = ClientContact
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return "{}#collapsePOC".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ClientContactDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "point of contact"
        ctx["object_to_be_deleted"] = queryset.name
        return ctx


class AssignmentCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.ProjectAssignment`.
    
    **Context**

    ``project_name``
        An instance of :model:`rolodex.Project`.
    
    **Template**
    
    :template:`rolodex/assignment_form.html`
    """

    model = ProjectAssignment
    form_class = AssignmentCreateForm
    template_name = "rolodex/assignment_form.html"

    def get_success_url(self):
        return "{}#collapseOperators".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_initial(self):
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project = project_instance
        return {
            "project": project,
        }

    def get_context_data(self, **kwargs):
        ctx = super(AssignmentCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        ctx["project_name"] = project_instance
        return ctx


class AssignmentUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ProjectAssignment`.
    
    **Template**
    
    :template:`rolodex/assignment_form.html`
    """

    model = ProjectAssignment
    form_class = AssignmentCreateForm
    template_name = "rolodex/assignment_form.html"

    def get_success_url(self):
        return "{}#collapseOperators".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )


class AssignmentDelete(LoginRequiredMixin, DeleteView):
    """
    Create an individual :model:`rolodex.ProjectAssignment`.
    
    **Context**
    
    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.ProjectAssignment`.
    
    **Template**
    
    :template:`ghostwriter/confirm_delete.html`
    """

    model = ProjectAssignment
    template_name = "confirm_delete.html"

    def get_success_url(self):
        return "{}#collapseOperators".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(AssignmentDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "assignment"
        ctx["object_to_be_deleted"] = "{} will be unassigned from {}".format(
            queryset.operator.name, queryset.project
        )
        return ctx


class ClientNoteCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.ClientNote`.

    **Context**

    ``client_name``
        An instance of :model:`rolodex.Client`.

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ClientNote
    form_class = ClientNoteCreateForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this client.",
            extra_tags="alert-success",
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_initial(self):
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        client = client_instance
        return {"client": client, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(ClientNoteCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get("pk"))
        ctx["client_name"] = client_instance
        return ctx


class ClientNoteUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ClientNote`.

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ClientNote
    form_class = ClientNoteCreateForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated.", extra_tags="alert-success"
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )


class ClientNoteDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.ClientNote`.

    **Context**

    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.ClientNote`.

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = ClientNote
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request, "Note successfully deleted.", extra_tags="alert-warning"
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:client_detail", kwargs={"pk": self.object.client.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ClientNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "note"
        ctx["object_to_be_deleted"] = queryset.note
        return ctx


class ProjectNoteCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.ProjectNote`.
    
    **Context**
    
    ``project_name``
        An instance of :model:`rolodex.Project`.
    
    **Template**
    
    :template:`ghostwriter/note_form.html`
    """

    model = ProjectNote
    form_class = ProjectNoteCreateForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this project.",
            extra_tags="alert-success",
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_initial(self):
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project = project_instance
        return {"project": project, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(ProjectNoteCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        ctx["project_name"] = project_instance
        return ctx


class ProjectNoteUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ProjectNote`.

    **Template**

    :template:`ghostwriter/note_form.html`
    """

    model = ProjectNote
    form_class = ProjectNoteCreateForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated.", extra_tags="alert-success"
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )


class ProjectNoteDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.ProjectNote`.
    
    **Context**
    
    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`rolodex.ProjectNote`.
    
    **Template**
    
    :template:`ghostwriter/confirm_delete.html`
    """

    model = ProjectNote
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request, "Note successfully deleted.", extra_tags="alert-warning"
        )
        return "{}#collapseNotes".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ProjectNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "project note"
        ctx["object_to_be_deleted"] = queryset.note
        return ctx


class ProjectObjectiveCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`rolodex.ProjectObjective`.

    **Context**

    ``project_name``
        An instance of :model:`rolodex.Project`.
    
    **Template**

    :template:`ghostwriter/templates/confirm_delete.html`
    """

    model = ProjectObjective
    form_class = ProjectObjectiveCreateForm
    template_name = "rolodex/objective_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Objective successfully added to this project.",
            extra_tags="alert-success",
        )
        return "{}#collapseObjectives".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_initial(self):
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        project = project_instance
        return {"project": project}

    def get_context_data(self, **kwargs):
        ctx = super(ProjectObjectiveCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        ctx["project_name"] = project_instance
        return ctx


class ProjectObjectiveUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`rolodex.ProjectObjective`.

    **Template**

    :template:`rolodex/objective_form.html`
    """

    model = ProjectObjective
    form_class = ProjectObjectiveCreateForm
    template_name = "rolodex/objective_form.html"

    def get_success_url(self):
        messages.success(
            self.request, "Objective successfully updated.", extra_tags="alert-success"
        )
        return "{}#collapseObjectives".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )


class ProjectObjectiveDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`rolodex.ProjectObjective`.

    **Context**

    ``object_type``
        A string describing what is to be deleted.
    ``object_to_be_deleted``
        A to-be-deleted instance of :model:`rolodex.ProjectObjective`.

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = ProjectObjective
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request, "Note successfully deleted.", extra_tags="alert-warning"
        )
        return "{}#collapseObjectives".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ProjectObjectiveDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "project objective"
        ctx["object_to_be_deleted"] = queryset.objective
        return ctx
