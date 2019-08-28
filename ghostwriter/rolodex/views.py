"""This contains all of the views for the Rolodex application's various
webpages.
"""

# Import logging functionality
import logging

# Django imports for generic views and template rendering
from django.urls import reverse
from django.views import generic
from django.contrib import messages
from django.shortcuts import render
from django.urls import reverse_lazy
from django.views.generic.edit import CreateView, UpdateView, DeleteView

# Django imports for verifying a user is logged-in to access a view
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin

# Django imports for forms
from django.http import HttpResponseRedirect
from django.shortcuts import get_object_or_404

# Import additional models
from .models import (Client, Project, ClientContact, ProjectAssignment,
                     ClientNote, ProjectNote, ProjectObjective, ObjectiveStatus)
from .forms import (ClientCreateForm, ProjectCreateForm,
                    ClientContactCreateForm, AssignmentCreateForm,
                    ClientNoteCreateForm, ProjectNoteCreateForm,
                    ProjectObjectiveCreateForm)
# from shepherd.models import History, ServerHistory, TransientServer

# Import additional modules
from ghostwriter.modules import codenames

# Import model filters for views
from .filters import ClientFilter, ProjectFilter


# Setup logger
logger = logging.getLogger(__name__)


##################
# View Functions #
##################


@login_required
def index(request):
    """View function to redirect empty requests to the dashboard."""
    return HttpResponseRedirect(reverse('home:dashboard'))


@login_required
def client_list(request):
    """View showing all clients. This view defaults to the client_list.html
    template.
    """
    # Check if a search parameter is in the request
    try:
        search_term = request.GET.get('client_search')
    except Exception:
        search_term = ''
    if search_term:
        messages.success(request, 'Displaying search results for: %s' %
                         search_term, extra_tags='alert-success')
        client_list = Client.objects.\
            filter(name__icontains=search_term).\
            order_by('name')
    else:
        client_list = Client.objects.all().order_by('name')
    client_filter = ClientFilter(request.GET, queryset=client_list)
    return render(request, 'rolodex/client_list.html',
                  {'filter': client_filter})


@login_required
def project_list(request):
    """View showing all projects. This view defaults to the project_list.html
    template and allows for filtering.
    """
    project_list = Project.objects.select_related('client').all().\
        order_by('complete', 'client')
    project_list = ProjectFilter(request.GET, queryset=project_list)
    return render(request, 'rolodex/project_list.html',
                    {'filter': project_list})


@login_required
def assign_client_codename(request, pk):
    """View function for assigning a codename to a client."""
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
    return HttpResponseRedirect(reverse('rolodex:client_detail', args=(pk,)))


@login_required
def assign_project_codename(request, pk):
    """View function for assigning a codename to a project."""
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
    return HttpResponseRedirect(reverse('rolodex:project_detail', args=(pk,)))


@login_required
def complete_project(request, pk):
    """View function to mark the specified project as complete."""
    try:
        project_instance = Project.objects.get(pk=pk)
        if project_instance:
            project_instance.complete = True
            project_instance.save()
            messages.success(
                request,
                'Project is now marked as complete and closed.',
                extra_tags='alert-success')
            return HttpResponseRedirect(reverse('rolodex:project_detail', args=(pk, )))
        else:
            messages.error(
                request,
                'The specified project does not exist!',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('rolodex:projects'))
    except Exception:
        messages.error(
            request,
            'Could not set the requested project as complete.',
            extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('rolodex:projects'))


@login_required
def reopen_project(request, pk):
    """View function to mark the specified project as incomplete."""
    try:
        project_instance = Project.objects.get(pk=pk)
        if project_instance:
            project_instance.complete = False
            project_instance.save()
            messages.success(
                request,
                'Project has been reopened.',
                extra_tags='alert-success')
            return HttpResponseRedirect(reverse('rolodex:project_detail', args=(pk, )))
        else:
            messages.error(
                request,
                'The specified project does not exist!',
                extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('rolodex:projects'))
    except Exception:
        messages.error(
            request,
            'Could not reopen the requested project.',
            extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('rolodex:projects'))


@login_required
def set_objective_status(request, pk, status):
    """View function to update the status for the specified objective."""
    try:
        project_objective = ProjectObjective.objects.get(pk=pk)
        if project_objective:
            if status == "active":
                project_objective.status = ObjectiveStatus.objects.get(pk=1)
                project_objective.save()
                messages.success(request, '"%s" is now Active.' %
                                    project_objective.objective,
                                    extra_tags='alert-success')
                return HttpResponseRedirect(reverse('rolodex:project_detail',
                                            args=(project_objective.project.pk, )))
            elif status == "onhold":
                project_objective.status = ObjectiveStatus.objects.get(pk=2)
                project_objective.save()
                messages.success(request, '"%s" is now On Hold.' %
                                    project_objective.objective,
                                    extra_tags='alert-success')
                return HttpResponseRedirect(reverse('rolodex:project_detail',
                                            args=(project_objective.project.pk, )))
            if status == "complete":
                project_objective.status = ObjectiveStatus.objects.get(pk=3)
                project_objective.save()
                messages.success(request, '"%s" is now Complete.' %
                                    project_objective.objective,
                                    extra_tags='alert-success')
                return HttpResponseRedirect(reverse('rolodex:project_detail',
                                            args=(project_objective.project.pk, )))
            else:
                messages.error(
                    request,
                    'You provided an invalid objective status ¯\_(ツ)_/¯',
                    extra_tags='alert-danger')
                return HttpResponseRedirect(reverse('rolodex:project_detail',
                                            args=(project_objective.project.pk, )))
        else:
            messages.error(request, 'The specified report does not exist!',
                            extra_tags='alert-danger')
            return HttpResponseRedirect(reverse('reporting:reports'))
    except Exception:
        messages.error(request, "Could not update the objective's status!",
                       extra_tags='alert-danger')
        return HttpResponseRedirect(reverse('rolodex:project',
                                    args=(project_objective.project.pk, )))


################
# View Classes #
################


class ClientDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified client. This view defaults to the
    client_detail.html template.
    """
    model = Client

    def get_context_data(self, **kwargs):
        from ghostwriter.shepherd.models import History, ServerHistory, TransientServer
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientDetailView, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        domain_history = History.objects.select_related('domain').\
            filter(client=client_instance)
        server_history = ServerHistory.objects.select_related('server').\
            filter(client=client_instance)
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
            print(vps_queryset)
            for vps in vps_queryset:
                client_vps.append(vps)
        ctx['domains'] = client_domains
        ctx['servers'] = client_servers
        ctx['vps'] = client_vps
        return ctx


class ClientCreate(LoginRequiredMixin, CreateView):
    """View for creating new client entries. This view defaults to the
    client_form.html template.
    """
    model = Client
    form_class = ClientCreateForm

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """Override form_valid to perform additional actions on new entries."""
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
    """View for updating existing client entries. This view defaults to the
    client_form.html template.
    """
    model = Client
    # fields = '__all__'
    form_class = ClientCreateForm

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        """Set the initial values for the form."""
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        return {
            'codename': client_instance.codename,
        }


class ClientDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing client entries. This view defaults to the
    confirm_delete.html template.
    """
    model = Client
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('rolodex:clients')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'client and all associated data'
        ctx['object_to_be_deleted'] = queryset.name
        return ctx


class ProjectDetailView(LoginRequiredMixin, generic.DetailView):
    """View showing the details for the specified client. This view defaults to the
    project_detail.html template.
    """
    model = Project


class ProjectCreate(LoginRequiredMixin, CreateView):
    """View for creating new projects. This view defaults to the
    project_form.html template.
    """
    model = Project
    form_class = ProjectCreateForm

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.pk})

    def form_valid(self, form):
        """Override form_valid to perform additional actions on new entries."""
        # Generate and assign a unique codename to the project
        codename_verified = False
        while not codename_verified:
            new_codename = codenames.codename(uppercase=True)
            try:
                Project.objects.filter(codename__iequal=new_codename)
            except Exception:
                codename_verified = True
        form.instance.codename = new_codename
        return super().form_valid(form)

    def get_initial(self):
        """Set the initial values for the form."""
        client = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        return {
            'client': client,
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        ctx['client_name'] = client_instance
        return ctx


class ProjectUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing project entries. This view defaults to the
    project_form.html template.
    """
    model = Project
    form_class = ProjectCreateForm

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.pk})

    def get_initial(self):
        """Set the initial values for the form."""
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        return {
            'codename': project_instance.codename,
        }


class ProjectDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing projects. This view defaults to the
    confirm_delete.html template.
    """
    model = Project
    template_name = 'confirm_delete.html'
    success_url = reverse_lazy('rolodex:projects')

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = \
            'project and all associated data (reports, evidence, etc.)'
        ctx['object_to_be_deleted'] = queryset
        return ctx


class ClientContactCreate(LoginRequiredMixin, CreateView):
    """View for creating new POC entries. This view defaults to the
    contact_form.html template.
    """
    model = ClientContact
    form_class = ClientContactCreateForm
    template_name = 'rolodex/contact_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.id})

    def get_initial(self):
        """Set the initial values for the form."""
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        client = client_instance
        return {
            'client': client,
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientContactCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        ctx['client_name'] = client_instance
        return ctx


class ClientContactUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing POC entries. This view defaults to the
    contact_form.html template.
    """
    model = ClientContact
    form_class = ClientContactCreateForm
    template_name = 'rolodex/contact_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.pk})


class ClientContactDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing POC entries. This view defaults to the
    confirm_delete.html template.
    """
    model = ClientContact
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the parent record after deletion."""
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientContactDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'point of contact'
        ctx['object_to_be_deleted'] = queryset.name
        return ctx


class AssignmentCreate(LoginRequiredMixin, CreateView):
    """View for assigning operators to a project. This view defaults to the
    assignment_form.html template.
    """
    model = ProjectAssignment
    form_class = AssignmentCreateForm
    template_name = 'rolodex/assignment_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_initial(self):
        """Set the initial values for the form."""
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project = project_instance
        return {
            'project': project,
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(AssignmentCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        ctx['project_name'] = project_instance
        return ctx


class AssignmentUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing operator assignments. This view defaults to the
    assignment_form.html template.
    """
    model = ProjectAssignment
    form_class = AssignmentCreateForm
    template_name = 'rolodex/assignment_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})


class AssignmentDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing operator assignments. This view defaults to
    the confirm_delete.html template.
    """
    model = ProjectAssignment
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the parent record after deletion."""
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(AssignmentDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'assignment'
        ctx['object_to_be_deleted'] = '{} will be unassigned from {}'.\
            format(
                queryset.operator.name,
                queryset.project)
        return ctx


class ClientNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    contact_form.html template.
    """
    model = ClientNote
    form_class = ClientNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this client.',
            extra_tags='alert-success')
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.id})

    def get_initial(self):
        """Set the initial values for the form."""
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        client = client_instance
        return {
            'client': client,
            'operator': self.request.user
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientNoteCreate, self).get_context_data(**kwargs)
        client_instance = get_object_or_404(Client, pk=self.kwargs.get('pk'))
        ctx['client_name'] = client_instance
        return ctx


class ClientNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    client_note_form.html template.
    """
    model = ClientNote
    form_class = ClientNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.pk})


class ClientNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = ClientNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the parent record after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:client_detail', kwargs={'pk': self.object.client.pk})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ClientNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx


class ProjectNoteCreate(LoginRequiredMixin, CreateView):
    """View for creating new note entries. This view defaults to the
    note_form.html template.
    """
    model = ProjectNote
    form_class = ProjectNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully added to this project.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_initial(self):
        """Set the initial values for the form."""
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project = project_instance
        return {
            'project': project,
            'operator': self.request.user
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectNoteCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        ctx['project_name'] = project_instance
        return ctx


class ProjectNoteUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing note entries. This view defaults to the
    project_note_form.html template.
    """
    model = ProjectNote
    form_class = ProjectNoteCreateForm
    template_name = 'note_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Note successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})


class ProjectNoteDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing note entries. This view defaults to the
    confirm_delete.html template.
    """
    model = ProjectNote
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the parent record after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectNoteDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'project note'
        ctx['object_to_be_deleted'] = queryset.note
        return ctx


class ProjectObjectiveCreate(LoginRequiredMixin, CreateView):
    model = ProjectObjective
    form_class = ProjectObjectiveCreateForm
    template_name = 'rolodex/objective_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Objective successfully added to this project.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_initial(self):
        """Set the initial values for the form."""
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        project = project_instance
        return {
            'project': project
        }

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectObjectiveCreate, self).get_context_data(**kwargs)
        project_instance = get_object_or_404(Project, pk=self.kwargs.get('pk'))
        ctx['project_name'] = project_instance
        return ctx


class ProjectObjectiveUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing objectives. This view defaults to the
    objective_form.html template.
    """
    model = ProjectObjective
    form_class = ProjectObjectiveCreateForm
    template_name = 'rolodex/objective_form.html'

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            'Objective successfully updated.',
            extra_tags='alert-success')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})


class ProjectObjectiveDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing objectives. This view defaults to the
    confirm_delete.html template.
    """
    model = ProjectObjective
    template_name = 'confirm_delete.html'

    def get_success_url(self):
        """Override the function to return to the parent record after deletion."""
        messages.warning(
            self.request,
            'Note successfully deleted.',
            extra_tags='alert-warning')
        return reverse('rolodex:project_detail', kwargs={'pk': self.object.project.id})

    def get_context_data(self, **kwargs):
        """Override the `get_context_data()` function to provide additional
        information.
        """
        ctx = super(ProjectObjectiveDelete, self).get_context_data(**kwargs)
        queryset = kwargs['object']
        ctx['object_type'] = 'project objective'
        ctx['object_to_be_deleted'] = queryset.objective
        return ctx