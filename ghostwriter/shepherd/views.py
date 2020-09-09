"""This contains all of the views used by the Shepherd application."""

# Standard Libraries
import csv
import datetime
import logging
import logging.config
from io import StringIO

# Django & Other 3rd Party Libraries
from django import forms
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import ugettext_lazy as _
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View
from django_q.models import Task
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project

from .filters import DomainFilter, ServerFilter
from .forms import BurnForm, CheckoutForm, DomainForm, DomainLinkForm, DomainNoteForm
from .forms_server import (
    ServerAddressFormSet,
    ServerCheckoutForm,
    ServerForm,
    ServerNoteForm,
    TransientServerForm,
)
from .models import (
    AuxServerAddress,
    Domain,
    DomainNote,
    DomainServerConnection,
    DomainStatus,
    HealthStatus,
    History,
    ServerHistory,
    ServerNote,
    ServerProvider,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)

# Using __name__ resolves to ghostwriter.shepherd.views
logger = logging.getLogger(__name__)


##################
# AJAX Functions #
##################


@login_required
def update_domain_badges(request, pk):
    """
    Return an updated version of the template following a delete action related to
    an individual :model:`rolodex.Domain`.

    **Template**

    :template:`snippets/domain_nav_tabs.html`
    """
    domain_instance = get_object_or_404(Domain, pk=pk)
    html = render_to_string(
        "snippets/domain_nav_tabs.html", {"domain": domain_instance},
    )
    return HttpResponse(html)


@login_required
def ajax_load_projects(request):
    """
    Filter :model:`rolodex.Project` when user changes :model:`rolodex.Client` selection.

    **Context**

    ``projects``
        Filtered queryset for :model:`rolodex.Project`

    **Template**

    :template:`shepherd/project_dropdown_list.html`
    """
    client_id = request.GET.get("client")
    projects = Project.objects.filter(client_id=client_id).order_by("codename")
    return render(
        request, "shepherd/project_dropdown_list.html", {"projects": projects}
    )


@login_required
def ajax_load_project(request):
    """
    Retrieve individual :model:`rolodex.Project`.

    **Context**

    ``project``
        Individual :model:`rolodex.Project`
    """
    project_id = request.GET.get("project")
    project = Project.objects.filter(id=project_id)
    data = serializers.serialize("json", project)
    return HttpResponse(data, content_type="application/json")


class DomainRelease(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Set the ``domain_status`` field of an individual :model:`shepherd.Domain` to
    the ``Available`` entry in :model:`shepherd.DomainStatus` and update the
    associated :model:`shepherd.History` entry.
    """

    model = History

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        if self.request.user == self.object.operator:
            # Reset domain status to ``Available`` and commit the change
            domain_instance = Domain.objects.get(pk=self.object.domain.id)
            domain_instance.domain_status = DomainStatus.objects.get(
                domain_status="Available"
            )
            domain_instance.save()
            # Set the release date to now so historical record is accurate
            self.object.end_date = datetime.datetime.now()
            self.object.save()
            data = {"result": "success", "message": "Domain successfully released"}
            logger.info(
                "Released %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        else:
            data = {
                "result": "error",
                "message": "You are not authorized to release this domain",
            }
        return JsonResponse(data)


class ServerRelease(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Set the ``server_status`` field of an individual :model:`shepherd.StaticServer` to
    the ``Available`` entry in :model:`shepherd.DomainStatus` and update the
    associated :model:`shepherd.ServerHistory` entry.
    """

    model = ServerHistory

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        if self.request.user == self.object.operator:
            # Reset server status to ``Available`` and commit the change
            server_instance = StaticServer.objects.get(pk=self.object.server.id)
            server_instance.server_status = ServerStatus.objects.get(
                server_status="Available"
            )
            server_instance.save()
            # Set the release date to now so historical record is accurate
            self.object.end_date = datetime.datetime.now()
            self.object.save()
            data = {"result": "success", "message": "Server successfully released"}
            logger.info(
                "Released %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        else:
            data = {
                "result": "error",
                "message": "You are not authorized to release this server",
            }
        return JsonResponse(data)


class DomainUpdateHealth(LoginRequiredMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Domain Updates`` with
    :task:`shepherd.tasks.check_domains` for one or more :model:`shepherd.Domain`.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Determine if ``pk`` is in the kwargs to update just one domain
        self.domain = None
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk", None)
            # Try to get the domain from :model:`shepherd.Domain`
            if pk:
                self.domain = get_object_or_404(Domain, pk=pk)

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Domain Updates`` or ``Individual Domain Update``
        result = "success"
        try:
            if self.domain:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.check_domains",
                    domain=self.domain.id,
                    group="Individual Domain Update",
                    hook="ghostwriter.shepherd.tasks.send_slack_complete_msg",
                )
            else:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.check_domains",
                    group="Domain Updates",
                    hook="ghostwriter.shepherd.tasks.send_slack_complete_msg",
                )
            message = "Domain category update task (Task ID {task}) has been successfully queued".format(
                task=task_id
            )
        except Exception:
            result = "error"
            message = "Domain category update task could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class DomainUpdateDNS(LoginRequiredMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``DNS Updates`` with
    :task:`shepherd.tasks.update_dns` for one or more :model:`shepherd.Domain`.
    """

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        # Determine if ``pk`` is in the kwargs to update just one domain
        self.domain = None
        if "pk" in self.kwargs:
            pk = self.kwargs.get("pk", None)
            # Try to get the domain from :model:`shepherd.Domain`
            if pk:
                self.domain = get_object_or_404(Domain, pk=pk)

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``DNS Updates`` or ``Individual DNS Update``
        result = "success"
        try:
            if self.domain:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.update_dns",
                    domain=self.domain.id,
                    group="Individual DNS Update",
                    hook="ghostwriter.shepherd.tasks.send_slack_complete_msg",
                )
            else:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.update_dns",
                    group="DNS Updates",
                    hook="ghostwriter.shepherd.tasks.send_slack_complete_msg",
                )
            message = "DNS update task (Task ID {task}) has been successfully queued".format(
                task=task_id
            )
        except Exception:
            result = "error"
            message = "DNS update task could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class RegistrarSyncNamecheap(LoginRequiredMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Namecheap Update`` with
    :task:`shepherd.tasks.fetch_namecheap_domains` to create or update one or more
    :model:`shepherd.Domain`.
    """

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Namecheap Update``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.fetch_namecheap_domains",
                group="Namecheap Update",
            )
            message = "Namecheap update task (Task ID {task}) has been successfully queued.".format(
                task=task_id
            )
        except Exception:
            result = "error"
            message = "Namecheap update task could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class MonitorCloudInfrastructure(LoginRequiredMixin, View):
    """
    Create an individual :model:`django_q.Task` under group ``Cloud Infrastructure Review``
    with :task:`shepherd.tasks.review_cloud_infrastructure`.
    """

    def post(self, request, *args, **kwargs):
        # Add an async task grouped as ``Cloud Infrastructure Review``
        result = "success"
        try:
            task_id = async_task(
                "ghostwriter.shepherd.tasks.review_cloud_infrastructure",
                group="Cloud Infrastructure Review",
            )
            message = "Cloud monitor task (Task ID {task}) has been successfully queued.".format(
                task=task_id
            )
        except Exception:
            result = "error"
            message = "Cloud monitor task could not be queued"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class ServerNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`shepherd.ServerNote`.
    """

    model = ServerNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


class DomainNoteDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`shepherd.DomainNote`.
    """

    model = DomainNote

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


class TransientServerDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`shepherd.TransientServer`.
    """

    model = TransientServer

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        # self.object.delete()
        data = {"result": "success", "message": "VPS successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


class DomainServerConnectionDelete(LoginRequiredMixin, SingleObjectMixin, View):
    """
    Delete an individual :model:`shepherd.DomainServerConnection`.
    """

    model = DomainServerConnection

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.delete()
        data = {"result": "success", "message": "Link successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
            self.request.user,
        )
        return JsonResponse(data)


##################
# View Functions #
##################


@login_required
def index(request):
    """
    Redirect empty requests to the user dashboard.
    """
    return HttpResponseRedirect(reverse("home:dashboard"))


@login_required
def domain_list(request):
    """
    Display a list of all :model:`shepherd.Domain`.

    **Context**

    ``filter``
        Instance of :filter:`shepherd.DomainFilter`

    **Template**

    :template:`shepherd/domain_list.html`
    """
    # Check if a search parameter is in the request
    search_term = ""
    if "domain_search" in request.GET:
        search_term = request.GET.get("domain_search")
        if search_term is None or search_term == "":
            search_term = ""
    # If there is a search term, filter the query by domain name or category
    if search_term:
        messages.success(
            request,
            "Showing search results for: {}".format(search_term),
            extra_tags="alert-success",
        )
        domains_list = (
            Domain.objects.select_related(
                "domain_status", "whois_status", "health_status"
            )
            .filter(Q(name__icontains=search_term) | Q(all_cat__icontains=search_term))
            .order_by("name")
        )
    else:
        domains_list = Domain.objects.select_related(
            "domain_status", "whois_status", "health_status"
        ).all()
    # Copy the GET request data
    data = request.GET.copy()
    # If user has not submitted their own filter, default to showing only Available domains
    if len(data) == 0:
        data["domain_status"] = 1
    domains_filter = DomainFilter(data, queryset=domains_list)
    return render(request, "shepherd/domain_list.html", {"filter": domains_filter})


@login_required
def server_list(request):
    """
    Display a list of all :model:`shepherd.StaticServer`.

    **Context**

    ``filter``
        Instance of :filter:`shepherd.ServerFilter.

    **Template**

    :template:`shepherd/server_list.html`
    """
    servers_list = (
        StaticServer.objects.select_related("server_status")
        .all()
        .order_by("ip_address")
    )
    servers_filter = ServerFilter(request.GET, queryset=servers_list)
    return render(request, "shepherd/server_list.html", {"filter": servers_filter})


@login_required
def server_search(request):
    """
    Search :model:`shepherd.StaticServer` and :model:`shepherd.AuxServerAddress` for
    an instance of :model:`rolodex.Project` to return a matching :model:`shepherd.StaticServer`.
    """
    if request.method == "POST":
        ip_address = request.POST.get("server_search").strip()
        project_id = request.POST.get("project_id")
        try:
            server_instance = StaticServer.objects.get(ip_address=ip_address)
            if server_instance:
                unavailable = ServerStatus.objects.get(server_status="Unavailable")
                if server_instance.server_status == unavailable:
                    messages.warning(
                        request,
                        "The server matching {server} is currently marked as unavailable".format(
                            server=ip_address
                        ),
                        extra_tags="alert-warning",
                    )
                    return HttpResponseRedirect(
                        "{}#infrastructure".format(
                            reverse("rolodex:project_detail", kwargs={"pk": project_id})
                        )
                    )
                else:
                    return HttpResponseRedirect(
                        reverse(
                            "shepherd:server_checkout",
                            kwargs={"pk": server_instance.id},
                        )
                    )
            else:
                messages.success(
                    request,
                    "No server was found matching {server}".format(server=ip_address),
                    extra_tags="alert-success",
                )
                return HttpResponseRedirect(
                    "{}#infrastructure".format(
                        reverse("rolodex:project_detail", kwargs={"pk": project_id})
                    )
                )
        except Exception:
            # Pass here to move on to try auxiliary address search
            pass
        try:
            server_instance = AuxServerAddress.objects.select_related(
                "static_server"
            ).get(ip_address=ip_address)
            if server_instance:
                unavailable = ServerStatus.objects.get(server_status="Unavailable")
                if server_instance.static_server.server_status == unavailable:
                    messages.warning(
                        request,
                        "The server matching {server} is currently marked as unavailable".format(
                            server=ip_address
                        ),
                        extra_tags="alert-warning",
                    )
                    return HttpResponseRedirect(
                        "{}#infrastructure".format(
                            reverse("rolodex:project_detail", kwargs={"pk": project_id})
                        )
                    )
                else:
                    return HttpResponseRedirect(
                        reverse(
                            "shepherd:server_checkout",
                            kwargs={"pk": server_instance.static_server.id},
                        )
                    )
            else:
                messages.success(
                    request,
                    "No server was found matching {server}".format(server=ip_address),
                    extra_tags="alert-success",
                )
                return HttpResponseRedirect(
                    "{}#infrastructure".format(
                        reverse("rolodex:project_detail", kwargs={"pk": project_id})
                    )
                )
        except Exception:
            messages.warning(
                request,
                "No server was found matching {server}".format(server=ip_address),
                extra_tags="alert-warning",
            )
            return HttpResponseRedirect(
                "{}#infrastructure".format(
                    reverse("rolodex:project_detail", kwargs={"pk": project_id})
                )
            )
    else:
        return HttpResponseRedirect(reverse("rolodex:index"))


@login_required
def user_assets(request):
    """
    Display all :model:`shepherd.Domain` and :model:`shepherd.StaticServer` associated
    with the current :model:`users.User`.

    **Context**

    ``domains``
        All :model:`shepherd.Domain` associated with current :model:`users.User`
    ``server``
        All :model:`shepherd.StaticServer` associated with current :model:`users.User`

    **Template**

    :template:`checkouts_for_user.html`
    """
    # Fetch the domain history for the current user
    domains = []
    unavailable_domains = Domain.objects.select_related("domain_status").filter(
        domain_status__domain_status="Unavailable"
    )
    for domain in unavailable_domains:
        domain_history = (
            History.objects.filter(domain=domain).order_by("end_date").last()
        )
        if domain_history:
            if domain_history.operator == request.user:
                domains.append(domain_history)
    # Fetch the server history for the current user
    servers = []
    unavailable_servers = StaticServer.objects.select_related("server_status").filter(
        server_status__server_status="Unavailable"
    )
    for server in unavailable_servers:
        server_history = (
            ServerHistory.objects.filter(server=server).order_by("end_date").last()
        )
        if server_history:
            if server_history.operator == request.user:
                servers.append(server_history)
    # Pass the context on to the custom HTML
    context = {"domains": domains, "servers": servers}
    return render(request, "shepherd/checkouts_for_user.html", context)


@login_required
def burn(request, pk):
    """
    Update the ``health_status``, ``domain_status``, and ``burned_explanation`` fields
    for an individual :model:`shepherd.Domain`.

    **Context**

    ``form``
        Instance of :form:`shepjerd.BurnForm`
    ``domain_instance``
        Instance of :model:`shepherd.Domain` to be updated
    ``domain_name``
        Value of name field for instance of :model:`shepherd.Domain` to be updated
    ``cancel_link``

    **Template**

    :template:`shepherd/burn.html`
    """
    # Fetch the domain for the provided primary key
    domain_instance = get_object_or_404(Domain, pk=pk)
    # If this is a POST request then process the form data
    if request.method == "POST":
        # Create a form instance and populate it with data from the request
        form = BurnForm(request.POST)
        # Check if the form is valid
        if form.is_valid():
            # Update the domain status and commit it
            domain_instance.domain_status = DomainStatus.objects.get(
                domain_status="Burned"
            )
            domain_instance.health_status = HealthStatus.objects.get(
                health_status="Burned"
            )
            domain_instance.burned_explanation = form.cleaned_data["burned_explanation"]
            domain_instance.last_used_by = request.user
            domain_instance.save()
            # Redirect to the user's checked-out domains
            messages.warning(
                request, "Domain has been marked as burned.", extra_tags="alert-warning"
            )
            return HttpResponseRedirect(
                "{}#health".format(reverse("shepherd:domain_detail", kwargs={"pk": pk}))
            )
            return HttpResponseRedirect(
                reverse("shepherd:domain_detail", kwargs={"pk": pk})
            )
    # If this is a GET (or any other method) create the default form
    else:
        form = BurnForm()
    # Prepare the context for the burn form
    context = {
        "form": form,
        "domain_instance": domain_instance,
        "domain_name": domain_instance.name,
        "cancel_link": reverse("shepherd:domain_detail", kwargs={"pk": pk}),
    }
    # Render the burn form page
    return render(request, "shepherd/burn.html", context)


@login_required
def import_domains(request):
    """
    Display form and import CSV file to create bulk :model:`shepherd.Domain`.

    **Template**

    :template:`shepherd/domain_import.html`
    """
    # If the request is 'GET' return the upload page
    if request.method == "GET":
        return render(request, "shepherd/domain_import.html")
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES["csv_file"]
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith(".csv"):
            messages.error(
                request, "Your file is not a csv!", extra_tags="alert-danger"
            )
            return HttpResponseRedirect(reverse("shepherd:domain_import"))
        # The file is loaded into memory, so this view must be aware of
        # system limits
        if csv_file.multiple_chunks():
            messages.error(
                request,
                "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000)),
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("shepherd:domain_import"))
    except Exception as error:
        messages.error(
            request,
            "Unable to upload/read file: " + repr(error),
            extra_tags="alert-danger",
        )
        logger.error("Unable to upload/read file – %s", error)
    # Loop over the lines and save the domains to the Domains model
    try:
        # Try to read the file data
        csv_file_wrapper = StringIO(csv_file.read().decode("utf-8"))
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=",")
    except Exception as error:
        messages.error(
            request, "Unable to parse file: {}".format(error), extra_tags="alert-danger"
        )
        logger.error("Unable to parse file – %s", error)
        return HttpResponseRedirect(reverse("shepherd:domain_import"))
    try:
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            logger.info("Reviewing %s for entry into the database", entry["name"])
            try:
                health_status = HealthStatus.objects.get(
                    health_status__iexact=entry["health_status"].strip()
                )
            except Exception:
                health_status = HealthStatus.objects.get(
                    health_status__iexact="Healthy"
                )
            entry["health_status"] = health_status
            try:
                whois_status = WhoisStatus.objects.get(
                    whois_status__iexact=entry["whois_status"].strip()
                )
            except Exception:
                whois_status = WhoisStatus.objects.get(whois_status="Enabled")
            entry["whois_status"] = whois_status
            # Check if the optional note field is in the csv and add it as
            # NULL if not
            if "note" not in entry:
                entry["note"] = None
            # Check if the domain_status Foreign Key is in the csv and try to
            # resolve the status
            if "domain_status" in entry:
                try:
                    domain_status = DomainStatus.objects.get(
                        domain_status__iexact=entry["domain_status"].strip()
                    )
                except Exception:
                    domain_status = DomainStatus.objects.get(domain_status="Available")
                entry["domain_status"] = domain_status
            else:
                domain_status = DomainStatus.objects.get(domain_status="Available")
                entry["domain_status"] = domain_status
            # Accept a variety of "True" values to mean True
            # Thanks to @lez0sec for fixing this logic:
            #   https://github.com/GhostManager/Ghostwriter/issues/73
            if "auto_renew" in entry:
                if any(
                    yes_option in entry["auto_renew"].lower().strip()
                    for yes_option in ["yes", "enabled", "true", "x", "enable"]
                ):
                    entry["auto_renew"] = True
                else:
                    entry["auto_renew"] = False
            # The last_used_by field will only be set by Shepherd at check-out
            if "last_used_by" in entry:
                entry["last_used_by"] = None
            else:
                entry["last_used_by"] = None
            # Try to pass the dict object to the `Domain` model
            try:
                # First, check if a domain with this name exists
                domain_name = entry["name"].strip()
                try:
                    instance = Domain.objects.get(name=domain_name)
                except Domain.DoesNotExist:
                    instance = False
                if instance:
                    # This domain already exists so update that entry
                    logger.info(
                        "Domain %s already in the database, so updating existing record",
                        entry["name"],
                    )
                    for attr, value in entry.items():
                        setattr(instance, attr, value)
                    instance.save()
                else:
                    # This is a new domain so create it
                    new_domain = Domain(**entry)
                    new_domain.save()
                messages.success(
                    request,
                    "Successfully parsed {}".format(entry["name"]),
                    extra_tags="alert-success",
                )
            # If there is an error, store as string and then display
            except Exception as error:
                messages.error(
                    request,
                    "Failed parsing {}: {}".format(entry["name"], error),
                    extra_tags="alert-danger",
                )
                logger.error("Failed parsing %s: %s", entry["name"], error)
                pass
    except Exception as error:
        messages.error(
            request, "Unable to read rows: {}".format(error), extra_tags="alert-danger"
        )
        logger.error("Unable to read rows – %s", error)
    return HttpResponseRedirect(reverse("shepherd:domain_import"))


@login_required
def import_servers(request):
    """
    Display form and import CSV file to create bulk :model:`shepherd.StaticServer`.

    **Template**

    :template:`shepherd/server_import.html`
    """
    # If the request is 'GET' return the upload page
    if request.method == "GET":
        return render(request, "shepherd/server_import.html")
    # If not a GET, then proceed
    try:
        # Get the `csv_file` from the POSTed form data
        csv_file = request.FILES["csv_file"]
        # Do a lame/basic check to see if this is a csv file
        if not csv_file.name.endswith(".csv"):
            messages.error(
                request, "Your file is not a csv!", extra_tags="alert-danger"
            )
            return HttpResponseRedirect(reverse("shepherd:server_import"))
        # The file is loaded into memory, so this view must be aware of
        # system limits
        if csv_file.multiple_chunks():
            messages.error(
                request,
                "Uploaded file is too big (%.2f MB)." % (csv_file.size / (1000 * 1000)),
                extra_tags="alert-danger",
            )
            return HttpResponseRedirect(reverse("shepherd:server_import"))
    except Exception as error:
        messages.error(
            request,
            "Unable to upload/read file: {}".format(error),
            extra_tags="alert-danger",
        )
        logger.error("Unable to upload/read file – %s", error)
    # Loop over the lines and save the servers to the `StaticServer` model
    try:
        # Try to read the file data
        csv_file_wrapper = StringIO(csv_file.read().decode("utf-8"))
        csv_reader = csv.DictReader(csv_file_wrapper, delimiter=",")
    except Exception as error:
        messages.error(
            request,
            "Unable to parse file: {}",
            format(error),
            extra_tags="alert-danger",
        )
        logger.error("Unable to parse file – %s", error)
        return HttpResponseRedirect(reverse("shepherd:server_import"))
    try:
        # Process each csv row and commit it to the database
        for entry in csv_reader:
            logger.info("Adding %s to the database", entry["ip_address"])
            # Check if the optional note field is in the csv and add it as NULL if not
            if "note" not in entry:
                entry["note"] = None
            # Check if the optional name field is in the csv and add it as NULL if not
            if "name" not in entry:
                entry["name"] = None
            # Check if the server_status Foreign Key is in the csv and try to resolve the status
            if "server_status" in entry:
                try:
                    server_status = ServerStatus.objects.get(
                        server_status__iexact=entry["server_status"]
                    )
                except Exception:
                    server_status = ServerStatus.objects.get(server_status="Available")
            else:
                server_status = ServerStatus.objects.get(server_status="Available")
            entry["server_status"] = server_status
            # Check if the server_status Foreign Key is in the csv and try to resolve the status
            if "server_provider" in entry:
                try:
                    server_provider = ServerProvider.objects.get(
                        server_provider__iexact=entry["server_provider"]
                    )
                    entry["server_provider"] = server_provider
                except Exception:
                    messages.error(
                        request,
                        'Failed parsing %s: the "%s" server provider does not '
                        "exist in the database"
                        % (entry["ip_address"], entry["server_provider"]),
                        extra_tags="alert-danger",
                    )
                    continue
            # The last_used_by field will only be set by Shepherd at server check-out
            if "last_used_by" in entry:
                entry["last_used_by"] = None
            else:
                entry["last_used_by"] = None
            # Try to pass the dict object to the `StaticServer` model
            try:
                # First, check if a server with this address exists
                try:
                    instance = StaticServer.objects.get(ip_address=entry["ip_address"])
                except StaticServer.DoesNotExist:
                    instance = False
                if instance:
                    # This server already exists so update that entry
                    for attr, value in entry.items():
                        setattr(instance, attr, value)
                    instance.save()
                else:
                    # This is a new server so create it
                    new_server = StaticServer(**entry)
                    new_server.save()
                messages.success(
                    request,
                    "Successfully parsed %s" % entry["ip_address"],
                    extra_tags="alert-success",
                )
            # If there is an error, store as string and then display
            except Exception as error:
                messages.error(
                    request,
                    "Failed parsing {}: {}".format(entry["ip_address"], error),
                    extra_tags="alert-danger",
                )
                logger.error("Failed parsing %s: %s", entry["ip_address"], error)
                pass
    except Exception as error:
        messages.error(
            request, "Unable to read rows: {}".format(error), extra_tags="alert-danger"
        )
        logger.error("Unable to read rows – ", error)
    return HttpResponseRedirect(reverse("shepherd:server_import"))


@login_required
def update(request):
    """
    Display results for latest :model:`django_q.Task` and create new instances on demand.

    **Context**

    ``total_domains``
        Total of entries in :model:`shepherd.Domain`
    ``update_time``
        Calculated time estimate for updating health of all :model:`shepherd.Domain`
    ``sleep_time``
        The associated value from ``settings.DOMAINCHECK_CONFIG``
    ``cat_last_update_requested``
        Start time of latest :model:`django_q.Task` for group "Domain Updates"
    ``cat_last_update_completed``
        End time of latest :model:`django_q.Task` for group "Domain Updates"
    ``cat_last_update_time``
        Total runtime of latest :model:`django_q.Task` for group "Domain Updates"
    ``cat_last_result``
        Result of latest :model:`django_q.Task` for group "Domain Updates"
    ``dns_last_update_requested``
        Start time of latest :model:`django_q.Task` for group "Domain Updates"
    ``dns_last_update_completed``
        End time of latest :model:`django_q.Task` for group "Domain Updates"
    ``dns_last_update_time``
        Total runtime of latest :model:`django_q.Task` for group "Domain Updates"
    ``dns_last_result``
        Result of latest :model:`django_q.Task` for group "DNS Updates"
    ``enable_namecheap``
        The associated value from ``settings.NAMECHEAP_CONFIG``
    ``namecheap_last_update_requested``
        Start time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_update_completed``
        End time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_update_time``
        End time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_result``
        Result of latest :model:`django_q.Task` for group "Namecheap Update"
    ``enable_cloud_monitor``
        The associated value from ``settings.CLOUD_SERVICE_CONFIG``
    ``cloud_last_update_requested``
        Start time of latest :model:`django_q.Task` for group "Cloud Infrastructure Review"
    ``cloud_last_update_completed``
        End time of latest :model:`django_q.Task` for group "Cloud Infrastructure Review"
    ``cloud_last_update_time``
        Total runtime of latest :model:`django_q.Task` for group "Cloud Infrastructure Review"
    ``cloud_last_result``
        Result of latest :model:`django_q.Task` for group "Cloud Infrastructure Review"

    **Template**

    :template:`shepherd/update.html`
    """
    # Check if the request is a GET
    if request.method == "GET":
        # Collect data for category updates
        total_domains = Domain.objects.all().count()
        try:
            sleep_time = settings.DOMAINCHECK_CONFIG["sleep_time"]
            update_time = round(total_domains * sleep_time / 60, 2)
        except Exception:
            sleep_time = 20
            update_time = round(total_domains * sleep_time / 60, 2)
        try:
            # Get the latest completed task from `Domain Updates`
            queryset = Task.objects.filter(group="Domain Updates")[0]
            # Get the task's start date and time
            cat_last_update_requested = queryset.started
            # Get the task's completed time
            cat_last_result = queryset.result
            # Check if the task was flagged as successful or failed
            if queryset.success:
                cat_last_update_completed = queryset.stopped
                cat_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                cat_last_update_completed = "Failed"
                cat_last_update_time = ""
        except Exception:
            cat_last_update_requested = "Updates Have Not Been Run Yet"
            cat_last_update_completed = ""
            cat_last_update_time = ""
            cat_last_result = ""
        # Collect data for DNS updates
        try:
            queryset = Task.objects.filter(group="DNS Updates")[0]
            dns_last_update_requested = queryset.started
            dns_last_result = queryset.result
            if queryset.success:
                dns_last_update_completed = queryset.stopped
                dns_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                dns_last_update_completed = "Failed"
                dns_last_update_time = ""
        except Exception:
            dns_last_update_requested = "Updates Have Not Been Run Yet"
            dns_last_update_completed = ""
            dns_last_update_time = ""
            dns_last_result = ""
        # Collect data for Namecheap updates
        enable_namecheap = settings.NAMECHEAP_CONFIG["enable_namecheap"]
        try:
            queryset = Task.objects.filter(group="Namecheap Update")[0]
            namecheap_last_update_requested = queryset.started
            namecheap_last_result = queryset.result
            if queryset.success:
                namecheap_last_update_completed = queryset.stopped
                namecheap_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                namecheap_last_update_completed = "Failed"
                namecheap_last_update_time = ""
        except Exception:
            namecheap_last_update_requested = "A Namecheap Update Has Not Been Run Yet"
            namecheap_last_update_completed = ""
            namecheap_last_update_time = ""
            namecheap_last_result = ""
        # Collect data for cloud monitoring
        enable_cloud_monitor = settings.CLOUD_SERVICE_CONFIG["enable_cloud_monitor"]
        try:
            queryset = Task.objects.filter(group="Cloud Infrastructure Review")[0]
            cloud_last_update_requested = queryset.started
            cloud_last_result = queryset.result
            if queryset.success:
                cloud_last_update_completed = queryset.stopped
                cloud_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                cloud_last_update_completed = "Failed"
                cloud_last_update_time = ""
        except Exception:
            cloud_last_update_requested = "A Namecheap Update Has Not Been Run Yet"
            cloud_last_update_completed = ""
            cloud_last_update_time = ""
            cloud_last_result = ""
        # Assemble context for the page
        context = {
            "total_domains": total_domains,
            "update_time": update_time,
            "sleep_time": sleep_time,
            "cat_last_update_requested": cat_last_update_requested,
            "cat_last_update_completed": cat_last_update_completed,
            "cat_last_update_time": cat_last_update_time,
            "cat_last_result": cat_last_result,
            "dns_last_update_requested": dns_last_update_requested,
            "dns_last_update_completed": dns_last_update_completed,
            "dns_last_update_time": dns_last_update_time,
            "dns_last_result": dns_last_result,
            "enable_namecheap": enable_namecheap,
            "namecheap_last_update_requested": namecheap_last_update_requested,
            "namecheap_last_update_completed": namecheap_last_update_completed,
            "namecheap_last_update_time": namecheap_last_update_time,
            "namecheap_last_result": namecheap_last_result,
            "enable_cloud_monitor": enable_cloud_monitor,
            "cloud_last_update_requested": cloud_last_update_requested,
            "cloud_last_update_completed": cloud_last_update_completed,
            "cloud_last_update_time": cloud_last_update_time,
            "cloud_last_result": cloud_last_result,
        }
        return render(request, "shepherd/update.html", context=context)
    else:
        return HttpResponseRedirect(reverse("shepherd:update"))


################
# View Classes #
################


class DomainDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`shepherd.Domain`.

    **Template**

    :template:`shepherd/domain_detail.html`
    """

    model = Domain


class HistoryCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.History`.

    **Context**

    ``domain_name``
        Uppercase version of the domain name
    ``cancel_link``
        Link for the form's Cancel button to return to domain's detail page

    **Template**

    :template:`shepherd/checkout.html`
    """

    model = History
    form_class = CheckoutForm
    template_name = "shepherd/checkout.html"

    def get_initial(self):
        self.domain = get_object_or_404(Domain, pk=self.kwargs.get("pk"))
        return {
            "domain": self.domain,
            "operator": self.request.user,
        }

    def form_valid(self, form):
        # Update the domain status and commit it
        domain_instance = get_object_or_404(Domain, pk=self.kwargs.get("pk"))
        domain_instance.last_used_by = self.request.user
        domain_instance.domain_status = DomainStatus.objects.get(
            domain_status="Unavailable"
        )
        domain_instance.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(
            self.request, "Domain successfully checked-out.", extra_tags="alert-success"
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_context_data(self, **kwargs):
        ctx = super(HistoryCreate, self).get_context_data(**kwargs)
        ctx["domain_name"] = self.domain.name.upper()
        ctx["cancel_link"] = reverse(
            "shepherd:domain_detail", kwargs={"pk": self.kwargs.get("pk")}
        )
        return ctx


class HistoryUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.History`.

    **Context**

    ``domain_name``
        Uppercase version of the domain name
    ``cancel_link``
        Link for the form's Cancel button to return to domain's detail page

    **Template**

    :template:`shepherd/checkout.html`
    """

    model = History
    form_class = CheckoutForm
    template_name = "shepherd/checkout.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Domain history successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(HistoryUpdate, self).get_context_data(**kwargs)
        ctx["domain_name"] = self.object.domain.name.upper()
        ctx["cancel_link"] = "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )
        return ctx


class HistoryDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`shepherd.History`.

    **Context**

    ``object_type``
        A string describing what is to be deleted
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`shepherd.History`
    ``cancel_link``
        Link for the form's Cancel button to return to domain's detail page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = History
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request,
            "Project history successfully deleted.",
            extra_tags="alert-warning",
        )
        return "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(HistoryDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "domain checkout"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )
        return ctx

    def delete(self, request, *args, **kwargs):
        self.object = self.get_object()
        latest_history_entry = History.objects.filter(domain=self.object.domain).latest(
            "id"
        )
        if self.object == latest_history_entry:
            domain_instance = Domain.objects.get(pk=self.object.domain.id)
            domain_instance.domain_status = DomainStatus.objects.get(
                domain_status="Available"
            )
            domain_instance.save()
        return super(HistoryDelete, self).delete(request, *args, **kwargs)


class DomainCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.Domain`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to domains list page

    **Template**

    :template:`shepherd/domain_form.html`
    """

    model = Domain
    form_class = DomainForm

    def get_success_url(self):
        messages.success(
            self.request, "Domain successfully created.", extra_tags="alert-success"
        )
        return reverse("shepherd:domain_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(DomainCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("shepherd:domains")
        return ctx


class DomainUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.Domain`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to domain's details page

    **Template**

    :template:`shepherd/domain_form.html`
    """

    model = Domain
    form_class = DomainForm

    def get_success_url(self):
        messages.success(
            self.request, "Domain successfully updated.", extra_tags="alert-success"
        )
        return reverse("shepherd:domain_detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        ctx = super(DomainUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "shepherd:domain_detail", kwargs={"pk": self.object.id}
        )
        return ctx


class DomainDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`shepherd.Domain`.

    **Context**

    ``object_type``
        A string describing what is to be deleted
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`shepherd.Domain`
    ``cancel_link``
        Link for the form's Cancel button to return to domain's details page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = Domain
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request, "Domain successfully deleted.", extra_tags="alert-warning"
        )
        return reverse("shepherd:domains")

    def get_context_data(self, **kwargs):
        ctx = super(DomainDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "domain"
        ctx["object_to_be_deleted"] = queryset.name.upper()
        ctx["cancel_link"] = reverse(
            "shepherd:domain_detail", kwargs={"pk": self.object.id}
        )
        return ctx


class ServerDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`shepherd.StaticServer`.

    **Context**

    ``primary_address``
        Primary IP address from :model:`shepherd.AuxServerAddress` for :model:`shepherd.SaticServer`

    **Template**

    :template:`shepherd/server_detail.html`
    """

    model = StaticServer
    template_name = "shepherd/server_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super(ServerDetailView, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["primary_address"] = queryset.ip_address
        aux_addresses = AuxServerAddress.objects.filter(static_server=queryset)
        for address in aux_addresses:
            if address.primary:
                ctx["primary_address"] = address.ip_address
        return ctx


class ServerCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.StaticServer`.

    **Context**

    ``addresses``
        Instance of the `ServerAddressFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to servers list page

    **Template**

    :template:`shepherd/server_form.html`
    """

    model = StaticServer
    template_name = "shepherd/server_form.html"
    form_class = ServerForm

    def get_success_url(self):
        messages.success(
            self.request, "Server successfully created", extra_tags="alert-success"
        )
        return reverse("shepherd:server_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(ServerCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("shepherd:servers")
        if self.request.POST:
            ctx["addresses"] = ServerAddressFormSet(self.request.POST, prefix="address")
        else:
            ctx["addresses"] = ServerAddressFormSet(prefix="address")
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        addresses = ctx["addresses"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseServerAddressInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()
                addresses_valid = addresses.is_valid()
                if addresses_valid:
                    addresses.instance = self.object
                    addresses.save()
                if form.is_valid() and addresses_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super(ServerCreate, self).form_invalid(form)


class ServerUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.StaticServer`.

    **Context**

    ``addresses``
        Instance of the `ServerAddressFormSet()` formset
    ``cancel_link``
        Link for the form's Cancel button to return to servers list page

    **Template**

    :template:`shepherd/server_form.html`
    """

    model = StaticServer
    template_name = "shepherd/server_form.html"
    form_class = ServerForm

    def get_success_url(self):
        messages.success(
            self.request, "Server successfully updated", extra_tags="alert-success"
        )
        return reverse("shepherd:server_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super(ServerUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "shepherd:server_detail", kwargs={"pk": self.object.pk}
        )
        if self.request.POST:
            ctx["addresses"] = ServerAddressFormSet(
                self.request.POST, prefix="address", instance=self.object
            )
        else:
            ctx["addresses"] = ServerAddressFormSet(
                prefix="address", instance=self.object
            )
        return ctx

    def form_valid(self, form):
        # Get form context data – used for validation of inline forms
        ctx = self.get_context_data()
        addresses = ctx["addresses"]

        # Now validate inline formsets
        # Validation is largely handled by the custom base formset, ``BaseServerAddressInlineFormSet``
        try:
            with transaction.atomic():
                # Save the parent form – will rollback if a child fails validation
                self.object = form.save()
                addresses_valid = addresses.is_valid()
                if addresses_valid:
                    addresses.instance = self.object
                    addresses.save()
                if form.is_valid() and addresses_valid:
                    return super().form_valid(form)
                else:
                    # Raise an error to rollback transactions
                    raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super(ServerUpdate, self).form_invalid(form)


class ServerDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`shepherd.StaticServer`.

    **Context**

    ``object_type``
        A string describing what is to be deleted
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`shepherd.StaticServer`
    ``cancel_link``
        Link for the form's Cancel button to return to server's details page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = StaticServer
    template_name = "confirm_delete.html"

    def get_success_url(self):
        messages.warning(
            self.request, "Server successfully deleted.", extra_tags="alert-warning"
        )
        return reverse("shepherd:servers")

    def get_context_data(self, **kwargs):
        ctx = super(ServerDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "static server"
        ctx["object_to_be_deleted"] = queryset.ip_address
        ctx["cancel_link"] = reverse(
            "shepherd:server_detail", kwargs={"pk": self.object.id}
        )
        return ctx


class ServerHistoryCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.ServerHistory`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to server's details page

    **Template**

    :template:`shepherd/server_checkout.html`
    """

    model = ServerHistory
    form_class = ServerCheckoutForm
    template_name = "shepherd/server_checkout.html"

    def get_initial(self):
        self.server = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))
        return {
            "server": self.server,
            "operator": self.request.user,
        }

    def form_valid(self, form):
        # Update the domain status and commit it
        server_instance = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))
        server_instance.last_used_by = self.request.user
        server_instance.server_status = ServerStatus.objects.get(
            server_status="Unavailable"
        )
        server_instance.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(
            self.request, "Server successfully checked-out.", extra_tags="alert-success"
        )
        # return reverse('shepherd:user_assets')
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ServerHistoryCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "shepherd:server_detail", kwargs={"pk": self.get_object().id}
        )
        return ctx


class ServerHistoryUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.ServerHistory`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to server's details page

    **Template**

    :template:`shepherd/server_checkout.html`
    """

    model = ServerHistory
    form_class = ServerCheckoutForm
    template_name = "shepherd/server_checkout.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Server history successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ServerHistoryUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = reverse(
            "rolodex:project_detail", kwargs={"pk": self.object.project.pk}
        )
        return ctx


class ServerHistoryDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`shepherd.ServerHistory`.

    **Context**

    ``object_type``
        A string describing what is to be deleted
    ``object_to_be_deleted``
        The to-be-deleted instance of :model:`shepherd.ServerHistory`
    ``cancel_link``
        Link for the form's Cancel button to return to server's details page

    **Template**

    :template:`ghostwriter/confirm_delete.html`
    """

    model = ServerHistory
    template_name = "confirm_delete.html"
    success_url = reverse_lazy("shepherd:domains")

    def get_success_url(self):
        messages.warning(
            self.request,
            "Server history successfully deleted.",
            extra_tags="alert-warning",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ServerHistoryDelete, self).get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "server checkout"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}#history".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )
        return ctx


class TransientServerCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.TransientServer`.

    **Context**

    ``project_name``
        Codename from the related :model:`rolodex.Project`
    ``cancel_link``
        Link for the form's Cancel button to return to project's details page

    **Template**

    :template:`shepherd/vps_form.html`
    """

    model = TransientServer
    form_class = TransientServerForm
    template_name = "shepherd/vps_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Server successfully added to the project.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_initial(self):
        self.project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        return {"project": self.project_instance, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(TransientServerCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project_instance.id})
        )
        return ctx


class TransientServerUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.TransientServer`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to project's details page

    **Template**

    :template:`shepherd/vps_form.html`
    """

    model = TransientServer
    form_class = TransientServerForm
    template_name = "shepherd/vps_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Server information successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_context_data(self, **kwargs):
        ctx = super(TransientServerUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx


class DomainServerConnectionCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.DomainServerConnection`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to project's details page

    **Template**

    :template:`shepherd/connect_form.html`
    """

    model = DomainServerConnection
    form_class = DomainLinkForm
    template_name = "shepherd/connect_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Server successfully associated with domain.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(DomainServerConnectionCreate, self).get_form_kwargs(
            **kwargs
        )
        form_kwargs["project"] = self.project_instance
        return form_kwargs

    def get_initial(self):
        self.project_instance = get_object_or_404(Project, pk=self.kwargs.get("pk"))
        return {"project": self.project_instance}

    def get_context_data(self, **kwargs):
        ctx = super(DomainServerConnectionCreate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project_instance.id})
        )
        return ctx


class DomainServerConnectionUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.DomainServerConnection`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to project's details page

    **Template**

    :template:`shepherd/connect_form.html`
    """

    model = DomainServerConnection
    form_class = DomainLinkForm
    template_name = "shepherd/connect_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Connection information successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super(DomainServerConnectionUpdate, self).get_form_kwargs(
            **kwargs
        )
        form_kwargs["project"] = self.object.project
        return form_kwargs

    def get_context_data(self, **kwargs):
        ctx = super(DomainServerConnectionUpdate, self).get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx


class DomainNoteCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.DomainNote`.

    **Context**

    ``domain_name``
        Domain name value from the related :model:`shepherd.Domain`
    ``cancel_link``
        Link for the form's Cancel button to return to server's detail page

    **Template**

    :template:`note_form.html`
    """

    model = DomainNote
    form_class = DomainNoteForm
    template_name = "note_form.html"

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        messages.success(
            self.request,
            "Note successfully added to this domain",
            extra_tags="alert-success",
        )
        return "{}#notes".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )

    def get_initial(self):
        self.domain_instance = get_object_or_404(Domain, pk=self.kwargs.get("pk"))
        return {"domain": self.domain_instance, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(DomainNoteCreate, self).get_context_data(**kwargs)
        ctx["note_object"] = self.domain_instance.name.upper()
        ctx["cancel_link"] = "{}#notes".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.domain_instance.id})
        )
        return ctx


class DomainNoteUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.DomainNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to server's detail page

    **Template**

    :template:`note_form.html`
    """

    model = DomainNote
    form_class = DomainNoteForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated", extra_tags="alert-success"
        )
        return "{}#notes".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(DomainNoteUpdate, self).get_context_data(**kwargs)
        ctx["note_object"] = self.object.domain.name.upper()
        ctx["cancel_link"] = "{}#notes".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )
        return ctx


class ServerNoteCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`shepherd.ServerNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Project` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to server's detail page

    **Template**

    :template:`note_form.html`
    """

    model = ServerNote
    form_class = ServerNoteForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this server",
            extra_tags="alert-success",
        )
        return "{}#notes".format(
            reverse("shepherd:server_detail", kwargs={"pk": self.object.server.id})
        )

    def get_initial(self):
        self.server_instance = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))
        return {"server": self.server_instance, "operator": self.request.user}

    def get_context_data(self, **kwargs):
        ctx = super(ServerNoteCreate, self).get_context_data(**kwargs)
        ctx["note_object"] = self.server_instance.ip_address
        ctx["cancel_link"] = reverse(
            "shepherd:server_detail", kwargs={"pk": self.server_instance.id}
        )
        return ctx


class ServerNoteUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`shepherd.ServerNote`.

    **Context**

    ``note_object``
        Instance of :model:`rolodex.Project` associated with note
    ``cancel_link``
        Link for the form's Cancel button to return to server's detail page

    **Template**

    :template:`note_form.html`
    """

    model = ServerNote
    form_class = ServerNoteForm
    template_name = "note_form.html"

    def get_success_url(self):
        messages.success(
            self.request, "Note successfully updated", extra_tags="alert-success"
        )
        return "{}#notes".format(
            reverse("shepherd:server_detail", kwargs={"pk": self.object.server.id})
        )

    def get_context_data(self, **kwargs):
        ctx = super(ServerNoteUpdate, self).get_context_data(**kwargs)
        server_instance = self.object.server
        ctx["note_object"] = server_instance.ip_address
        ctx["cancel_link"] = reverse(
            "shepherd:server_detail", kwargs={"pk": self.object.server.id}
        )
        return ctx
