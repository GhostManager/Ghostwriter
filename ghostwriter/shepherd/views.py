"""This contains all the views used by the Shepherd application."""

# Standard Libraries
import json
import logging.config
from datetime import date, datetime

# Django Imports
from django import forms
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core import serializers
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View
from django.views.generic.list import ListView

# 3rd Party Libraries
from django_q.models import Task
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.api.utils import (
    ForbiddenJsonResponse,
    RoleBasedAccessControlMixin,
    get_project_list,
    verify_access,
    verify_user_is_privileged,
)
from ghostwriter.commandcenter.models import (
    CloudServicesConfiguration,
    ExtraFieldSpec,
    NamecheapConfiguration,
    VirusTotalConfiguration,
)
from ghostwriter.modules.shared import add_content_disposition_header
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.filters import DomainFilter, ServerFilter
from ghostwriter.shepherd.forms import (
    BurnForm,
    CheckoutForm,
    DomainForm,
    DomainLinkForm,
    DomainNoteForm,
)
from ghostwriter.shepherd.forms_server import (
    ServerAddressFormSet,
    ServerCheckoutForm,
    ServerForm,
    ServerNoteForm,
    TransientServerForm,
)
from ghostwriter.shepherd.models import (
    AuxServerAddress,
    Domain,
    DomainNote,
    DomainServerConnection,
    DomainStatus,
    HealthStatus,
    History,
    ServerHistory,
    ServerNote,
    ServerStatus,
    StaticServer,
    TransientServer,
)
from ghostwriter.shepherd.resources import DomainResource, StaticServerResource

# Using __name__ resolves to ghostwriter.shepherd.views
logger = logging.getLogger(__name__)


##################
# AJAX Functions #
##################


class AjaxLoadProjects(RoleBasedAccessControlMixin, View):
    """
    Filter :model:`rolodex.Project` when user changes :model:`rolodex.Client` selection.

    **Context**

    ``projects``
        Filtered queryset for :model:`rolodex.Project`

    **Template**

    :template:`shepherd/project_dropdown_list.html`
    """

    def get(self, request, *args, **kwargs):
        client_id = request.GET.get("client", None)
        if client_id:
            try:
                client_id = int(client_id)
                client = Client.objects.get(id=client_id)
                if verify_access(request.user, client):
                    projects = get_project_list(request.user)
                    projects = (
                        projects.filter(Q(client_id=client_id) & Q(complete=False))
                        .order_by("codename")
                        .defer("extra_fields")
                    )
                    return render(request, "shepherd/project_dropdown_list.html", {"projects": projects})
                return HttpResponse(status=403)
            except ValueError:
                logger.error("Received bad primary key value for client: %s", client_id)
        return HttpResponse(status=400)


class AjaxLoadProject(RoleBasedAccessControlMixin, View):
    """
    Retrieve individual :model:`rolodex.Project` and return it as JSON.

    **Context**

    ``project``
        Individual :model:`rolodex.Project`
    """

    def get(self, request, *args, **kwargs):
        project_id = request.GET.get("project", None)
        if project_id:
            try:
                project_id = int(project_id)
                project = Project.objects.get(id=project_id)
                if verify_access(request.user, project):
                    data = serializers.serialize("json", [project])
                    return JsonResponse(json.loads(data), safe=False)
                return ForbiddenJsonResponse()
            except (Project.DoesNotExist, ValueError):
                logger.error("Received bad primary key value for project: %s", project_id)
        return JsonResponse({"error": "Bad request"}, status=400)


class AjaxDomainOverwatch(RoleBasedAccessControlMixin, View):
    """
    Retrieve an individual :model:`shepherd.History` to check domain's past history
    prior to checkout.
    """

    def get(self, request, *args, **kwargs):
        domain_id = request.GET.get("domain", None)
        client_id = request.GET.get("client", None)

        if client_id and domain_id:
            try:
                domain_id = int(domain_id)
                client_id = int(client_id)

                client = Client.objects.get(id=client_id)
                if verify_access(request.user, client):
                    domain_history = History.objects.filter(Q(domain=domain_id) & Q(client=client_id))
                    if domain_history:
                        data = {
                            "result": "warning",
                            "message": "Domain has been used with this client in the past!",
                        }
                    else:
                        data = {"result": "success", "message": ""}
                    return JsonResponse(data)
                return ForbiddenJsonResponse()
            except (Client.DoesNotExist, ValueError):
                logger.error("Received bad primary key values for client and domain: %s and %s", client_id, domain_id)

        return JsonResponse({"result": "error", "message": "Bad request"}, status=400)


class AjaxUpdateDomainBadges(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following a delete action related to
    an individual :model:`rolodex.Domain`.

    **Template**

    :template:`snippets/domain_nav_tabs.html`
    """

    model = Domain

    def get(self, *args, **kwargs):
        html = render_to_string(
            "snippets/domain_nav_tabs.html",
            {"domain": self.get_object()},
        )
        return HttpResponse(html)


class AjaxUpdateServerBadges(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return an updated version of the template following a delete action related to
    an individual :model:`rolodex.StaticServer`.

    **Template**

    :template:`snippets/server_nav_tabs.html`
    """

    model = StaticServer

    def get(self, *args, **kwargs):
        html = render_to_string(
            "snippets/server_nav_tabs.html",
            {"staticserver": self.get_object()},
        )
        return HttpResponse(html)


class DomainRelease(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Set the ``domain_status`` field of an individual :model:`shepherd.Domain` to
    the ``Available`` entry in :model:`shepherd.DomainStatus` and update the
    associated :model:`shepherd.History` entry.
    """

    model = History

    def test_func(self):
        if self.request.user == self.get_object().operator and verify_access(
            self.request.user, self.get_object().project
        ):
            return True
        return False

    def handle_no_permission(self):
        return ForbiddenJsonResponse(
            data={"result": "error", "message": "You do not have permission to release this domain."}
        )

    def post(self, *args, **kwargs):
        obj = self.get_object()
        # Reset domain status to ``Available`` and commit the change
        domain_instance = Domain.objects.get(pk=obj.domain.id)
        domain_instance.domain_status = DomainStatus.objects.get(domain_status="Available")
        domain_instance.save()
        # Set the release date to now so historical record is accurate
        obj.end_date = date.today()
        obj.save()
        data = {"result": "success", "message": "Domain successfully released."}
        logger.info(
            "Released %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        # If domain is set to be reset on release get the necessary API config and task
        if domain_instance.reset_dns and domain_instance.registrar:
            # Namecheap
            if domain_instance.registrar.lower() == "namecheap":
                namecheap_config = NamecheapConfiguration.get_solo()
                if namecheap_config.enable:
                    async_task(
                        "ghostwriter.shepherd.tasks.namecheap_reset_dns",
                        namecheap_config=namecheap_config,
                        domain=domain_instance,
                        group="Individual Domain Update",
                        hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                    )
        return JsonResponse(data)


class ServerRelease(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Set the ``server_status`` field of an individual :model:`shepherd.StaticServer` to
    the ``Available`` entry in :model:`shepherd.ServerStatus` and update the
    associated :model:`shepherd.ServerHistory` entry.
    """

    model = ServerHistory

    def test_func(self):
        if self.request.user == self.get_object().operator and verify_access(
            self.request.user, self.get_object().project
        ):
            return True
        return False

    def handle_no_permission(self):
        return ForbiddenJsonResponse(
            data={"result": "error", "message": "You do not have permission to release this server."}
        )

    def post(self, *args, **kwargs):
        obj = self.get_object()
        # Reset server status to ``Available`` and commit the change
        server_instance = StaticServer.objects.get(pk=obj.server.id)
        server_instance.server_status = ServerStatus.objects.get(server_status="Available")
        server_instance.save()
        # Set the release date to now so historical record is accurate
        obj.end_date = date.today()
        obj.save()
        data = {"result": "success", "message": "Server successfully released."}
        logger.info(
            "Released %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        return JsonResponse(data)


class DomainUpdateHealth(RoleBasedAccessControlMixin, View):
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
                    group="Individual Domain Update",
                    hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                    domain_id=self.domain.id,
                )
            else:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.check_domains",
                    group="Domain Updates",
                    hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                )
            message = "Successfully queued domain category update task (Task ID {task}).".format(task=task_id)
        except Exception:
            result = "error"
            message = "Domain category update task could not be queued!"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class DomainUpdateDNS(RoleBasedAccessControlMixin, View):
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
                    hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                    group="Individual DNS Update",
                    domain=self.domain.id,
                )
            else:
                task_id = async_task(
                    "ghostwriter.shepherd.tasks.update_dns",
                    group="DNS Updates",
                    hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                )
            message = "Successfully queued DNS update task (Task ID {task}).".format(task=task_id)
        except Exception:
            result = "error"
            message = "DNS update task could not be queued!"
            logger.exception(message)

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class RegistrarSyncNamecheap(RoleBasedAccessControlMixin, View):
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
                hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
            )
            message = "Successfully queued Namecheap update task (Task ID {task}).".format(task=task_id)
        except Exception:
            result = "error"
            message = "Namecheap update task could not be queued!"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class MonitorCloudInfrastructure(RoleBasedAccessControlMixin, View):
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
            message = "Successfully queued the cloud monitor task (Task ID {task}).".format(task=task_id)
        except Exception:
            result = "error"
            message = "Cloud monitor task could not be queued!"

        data = {
            "result": result,
            "message": message,
        }
        return JsonResponse(data)


class ServerNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`shepherd.ServerNote`."""

    model = ServerNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("shepherd:server_detail", kwargs={"pk": self.get_object().server.pk}) + "#notes")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        return JsonResponse(data)


class DomainNoteDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`shepherd.DomainNote`."""

    model = DomainNote

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("shepherd:domain_detail", kwargs={"pk": self.get_object().domain.pk}) + "#notes")

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        data = {"result": "success", "message": "Note successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        return JsonResponse(data)


class TransientServerDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`shepherd.TransientServer`."""

    model = TransientServer

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        data = {"result": "success", "message": "VPS successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        return JsonResponse(data)


class DomainServerConnectionDelete(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Delete an individual :model:`shepherd.DomainServerConnection`."""

    model = DomainServerConnection

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        return ForbiddenJsonResponse()

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.delete()
        data = {"result": "success", "message": "Link successfully deleted!"}
        logger.info(
            "Deleted %s %s by request of %s",
            obj.__class__.__name__,
            obj.id,
            self.request.user,
        )
        return JsonResponse(data)


##################
# View Functions #
##################


@login_required
def index(request):
    """Redirect empty requests to the user dashboard."""
    return HttpResponseRedirect(reverse("home:dashboard"))


@login_required
def infrastructure_search(request):
    """
    Search :model:`shepherd.StaticServer`, :model:`shepherd.AuxServerAddress`, and
    :model:`shepherd:TransientServer` and return any matches with any related
    :model:`rolodex.Project` entries.
    """
    context = {}
    if request.method == "GET":
        search_term = ""
        try:
            if "query" in request.GET:
                search_term = request.GET.get("query").strip()
                if search_term is None or search_term == "":
                    search_term = ""

                if search_term:
                    projects = get_project_list(request.user)
                    server_qs = StaticServer.objects.filter(
                        Q(ip_address__contains=search_term) | Q(name__icontains=search_term)
                    )
                    vps_qs = TransientServer.objects.select_related("project").filter(
                        Q(ip_address__contains=search_term) | Q(name__icontains=search_term) & Q(project__in=projects)
                    )
                    aux_qs = AuxServerAddress.objects.select_related("static_server").filter(
                        ip_address__contains=search_term
                    )

                    total_result = server_qs.count() + vps_qs.count() + aux_qs.count()
                    context = {
                        "servers": server_qs,
                        "vps": vps_qs,
                        "addresses": aux_qs,
                        "total_result": total_result,
                    }

                    if total_result > 0:
                        messages.success(
                            request,
                            f"Found {total_result} results for: {search_term}",
                            extra_tags="alert-success",
                        )
                    else:
                        messages.warning(
                            request,
                            f"Found zero results for: {search_term}",
                            extra_tags="alert-warning",
                        )
        except Exception:
            messages.error(
                request,
                f"Failed searching for: {search_term}",
                extra_tags="alert-danger",
            )
            logger.exception("Encountered error with search query: %s", search_term)

    return render(request, "shepherd/server_search.html", context)


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
        domain_history = History.objects.filter(domain=domain).order_by("end_date").last()
        if domain_history:
            if domain_history.operator == request.user:
                domains.append(domain_history)
    # Fetch the server history for the current user
    servers = []
    unavailable_servers = StaticServer.objects.select_related("server_status").filter(
        server_status__server_status="Unavailable"
    )
    for server in unavailable_servers:
        server_history = ServerHistory.objects.filter(server=server).order_by("end_date").last()
        if server_history:
            if server_history.operator == request.user:
                servers.append(server_history)
    # Pass the context on to the custom HTML
    context = {"domains": domains, "servers": servers}
    return render(request, "shepherd/checkouts_for_user.html", context)


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
        The associated value from :model:`commandcenter.VirusTotalConfiguration`
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
        The associated value from :model:`commandcenter.NamecheapConfiguration`
    ``namecheap_last_update_requested``
        Start time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_update_completed``
        End time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_update_time``
        End time of latest :model:`django_q.Task` for group "Namecheap Update"
    ``namecheap_last_result``
        Result of latest :model:`django_q.Task` for group "Namecheap Update"
    ``enable_cloud_monitor``
        The associated value from :model:`commandcenter.CloudServicesConfiguration`
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
        # Get relevant configuration settings
        vt_config = VirusTotalConfiguration.get_solo()
        enable_vt = vt_config.enable
        sleep_time = vt_config.sleep_time
        cloud_config = CloudServicesConfiguration.get_solo()
        enable_cloud_monitor = cloud_config.enable
        namecheap_config = NamecheapConfiguration.get_solo()
        enable_namecheap = namecheap_config.enable

        # Collect data for category updates
        cat_last_update_completed = ""
        cat_last_update_time = ""
        cat_last_result = ""
        try:
            expired_status = DomainStatus.objects.get(domain_status="Expired")
        except DomainStatus.DoesNotExist:
            expired_status = None
        total_domains = Domain.objects.all().exclude(domain_status=expired_status).count()
        try:
            update_time = round(total_domains * sleep_time / 60, 2)
        except ZeroDivisionError:
            update_time = total_domains
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
        except IndexError:
            cat_last_update_requested = "Updates Have Not Been Run Yet"

        # Collect data for DNS updates
        dns_last_update_completed = ""
        dns_last_update_time = ""
        dns_last_result = ""
        try:
            queryset = Task.objects.filter(group="DNS Updates")[0]
            dns_last_update_requested = queryset.started
            dns_last_result = queryset.result
            if queryset.success:
                dns_last_update_completed = queryset.stopped
                dns_last_update_time = round(queryset.time_taken() / 60, 2)
            else:
                dns_last_update_completed = "Failed"
        except IndexError:
            dns_last_update_requested = "Updates Have Not Been Run Yet"

        # Collect data for Namecheap updates
        namecheap_last_update_completed = ""
        namecheap_last_update_time = ""
        namecheap_last_result = ""
        if enable_namecheap:
            try:
                queryset = Task.objects.filter(group="Namecheap Update")[0]
                namecheap_last_update_requested = queryset.started
                namecheap_last_result = queryset.result
                if queryset.success:
                    namecheap_last_update_completed = queryset.stopped
                    namecheap_last_update_time = round(queryset.time_taken() / 60, 2)
                    if namecheap_last_result["errors"]:
                        namecheap_last_update_completed = "Failed"
                else:
                    namecheap_last_update_completed = "Failed"
            except IndexError:
                namecheap_last_update_requested = "Namecheap Sync Has Not Been Run Yet"
        else:
            namecheap_last_update_requested = "Namecheap Syncing is Disabled"

        # Collect data for cloud monitoring
        cloud_last_update_completed = ""
        cloud_last_update_time = ""
        cloud_last_result = ""
        if enable_cloud_monitor:
            try:
                queryset = Task.objects.filter(group="Cloud Infrastructure Review")[0]
                cloud_last_update_requested = queryset.started
                cloud_last_result = queryset.result
                if queryset.success:
                    cloud_last_update_completed = queryset.stopped
                    cloud_last_update_time = round(queryset.time_taken() / 60, 2)
                else:
                    cloud_last_update_completed = "Failed"
            except IndexError:
                cloud_last_update_requested = "Cloud Review Has Not Been Run Yet"
        else:
            cloud_last_update_requested = "Cloud Services are Disabled"
        # Assemble context for the page
        context = {
            "total_domains": total_domains,
            "update_time": update_time,
            "enable_vt": enable_vt,
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
    return HttpResponseRedirect(reverse("shepherd:update"))


@login_required
def export_domains_to_csv(request):
    """
    Export all :model:`shepherd.Domain` to a csv file for download.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    domain_resource = DomainResource()
    dataset = domain_resource.export()
    response = HttpResponse(dataset.csv, content_type="text/csv")
    add_content_disposition_header(response, f"{timestamp}_domains.csv")

    return response


@login_required
def export_servers_to_csv(request):
    """
    Export all :model:`shepherd.Server` to a csv file for download.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    server_resource = StaticServerResource()
    dataset = server_resource.export()
    response = HttpResponse(dataset.csv, content_type="text/csv")
    add_content_disposition_header(response, f"{timestamp}_servers.csv")

    return response


################
# View Classes #
################


class DomainListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`shepherd.Domain`.

    **Context**

    ``filter``
        Instance of :filter:`shepherd.DomainFilter`
    ``autocomplete``
        List of all :model:`shepherd.Domain` names and categorization entries

    **Template**

    :template:`shepherd/domain_list.html`
    """

    model = Domain
    template_name = "shepherd/domain_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []

    def get_queryset(self):
        search_term = ""
        domains = Domain.objects.select_related("domain_status", "whois_status", "health_status").all()

        # Build autocomplete list
        for domain in domains:
            self.autocomplete.append(domain.name)
            if domain.categorization:
                try:
                    for key, value in domain.categorization.items():
                        if "," in value:
                            for item in value.split(","):
                                self.autocomplete.append(item.strip().lower())
                        else:
                            self.autocomplete.append(value.lower())
                except Exception as e:
                    logger.error("Failed to parse categorization autocomplete entries for %s: %s", domain.name, e)

        if "domain" in self.request.GET:
            search_term = self.request.GET.get("domain").strip()
            if search_term is None or search_term == "":
                search_term = ""
        if search_term:
            messages.success(
                self.request,
                "Showing search results for: {}".format(search_term),
                extra_tags="alert-success",
            )
            return domains.filter(Q(name__icontains=search_term) | Q(categorization__icontains=search_term)).order_by(
                "name"
            )
        return domains

    def get(self, request, *args, **kwarg):
        # If user has not submitted a filter, default showing available domains with expiry dates in the future
        data = request.GET.copy()
        if len(data) == 0:
            data["domain_status"] = 1
            data["exclude_expired"] = True
        domains_filter = DomainFilter(data, queryset=self.get_queryset())
        return render(
            request, "shepherd/domain_list.html", {"filter": domains_filter, "autocomplete": self.autocomplete}
        )


class ServerListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`shepherd.StaticServer`.

    **Context**

    ``filter``
        Instance of :filter:`shepherd.ServerFilter.
    ``autocomplete``
        List of all :model:`shepherd.StaticServer` names and IP addresses

    **Template**

    :template:`shepherd/server_list.html`
    """

    model = StaticServer
    template_name = "shepherd/server_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []

    def get_queryset(self):
        search_term = ""
        servers = StaticServer.objects.select_related("server_status").all().order_by("ip_address")

        # Build autocomplete list
        for server in servers:
            self.autocomplete.append(server.ip_address)
            if server.name:
                self.autocomplete.append(server.name)
            try:
                for address in server.auxserveraddress_set.all():
                    self.autocomplete.append(address.ip_address)
            except Exception as e:
                logger.error("Failed to parse aux addresses entries for %s: %s", server, e)

        if "server" in self.request.GET:
            search_term = self.request.GET.get("server").strip()
            if search_term is None or search_term == "":
                search_term = ""
        if search_term:
            messages.success(
                self.request,
                f"Showing search results for: {search_term}",
                extra_tags="alert-success",
            )
            return servers.filter(
                Q(ip_address__icontains=search_term)
                | Q(name__icontains=search_term)
                | Q(auxserveraddress__ip_address__icontains=search_term)
            ).order_by("ip_address")
        return servers

    def get(self, request, *args, **kwarg):
        # If user has not submitted their own filter, default to showing only available servers
        data = request.GET.copy()
        if len(data) == 0:
            data["server_status"] = 1
        servers_filter = ServerFilter(data, queryset=self.get_queryset())
        return render(
            request, "shepherd/server_list.html", {"filter": servers_filter, "autocomplete": self.autocomplete}
        )


class BurnDomain(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Update the ``health_status``, ``domain_status``, and ``burned_explanation`` fields
    for an individual :model:`shepherd.Domain`.

    **Context**

    ``form``
        Instance of :form:`shepherd.BurnForm`
    ``domain_instance``
        Instance of :model:`shepherd.Domain` to be updated
    ``domain_name``
        Value of name field for instance of :model:`shepherd.Domain` to be updated
    ``cancel_link``

    **Template**

    :template:`shepherd/burn.html`
    """

    model = Domain

    def __init__(self):
        self.domain = None
        super().__init__()

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.domain = self.get_object()

    def post(self, request, *args, **kwargs):
        form = BurnForm(request.POST)
        if form.is_valid():
            self.domain.domain_status = DomainStatus.objects.get(domain_status="Burned")
            self.domain.health_status = HealthStatus.objects.get(health_status="Burned")
            self.domain.burned_explanation = form.cleaned_data["burned_explanation"]
            self.domain.last_used_by = request.user
            self.domain.save()
            messages.warning(request, "Domain has been marked as burned.", extra_tags="alert-warning")
        return HttpResponseRedirect(
            "{}#health".format(reverse("shepherd:domain_detail", kwargs={"pk": self.domain.pk}))
        )

    def get(self, request, *args, **kwargs):
        form = BurnForm()
        context = {
            "form": form,
            "domain_instance": self.domain,
            "domain_name": self.domain.name,
            "cancel_link": reverse("shepherd:domain_detail", kwargs={"pk": self.domain.pk}),
        }
        return render(request, "shepherd/burn.html", context)


class DomainDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`shepherd.Domain`.

    **Template**

    :template:`shepherd/domain_detail.html`
    """

    model = Domain

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["domain_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=Domain._meta.label)
        return ctx


class HistoryCreate(RoleBasedAccessControlMixin, CreateView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.domain = get_object_or_404(Domain, pk=self.kwargs.get("pk"))

    def get_initial(self):
        return {"domain": self.domain}

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.domain = self.domain
        obj.operator = self.request.user
        obj.save()

        # Update the domain status and commit it
        self.domain.last_used_by = self.request.user
        self.domain.domain_status = DomainStatus.objects.get(domain_status="Unavailable")
        self.domain.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Domain successfully checked-out.", extra_tags="alert-success")
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["domain_name"] = self.domain.name.upper()
        ctx["domain"] = self.domain
        ctx["cancel_link"] = reverse("shepherd:domain_detail", kwargs={"pk": self.domain.pk})
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class HistoryUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Domain history successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#history".format(reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["domain_name"] = self.object.domain.name.upper()
        ctx["domain"] = self.get_object()
        ctx["cancel_link"] = "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class HistoryDelete(RoleBasedAccessControlMixin, DeleteView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.warning(
            self.request,
            "Domain history successfully deleted!",
            extra_tags="alert-warning",
        )
        return "{}#history".format(reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "domain checkout"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}#history".format(
            reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id})
        )
        return ctx


class DomainCreate(RoleBasedAccessControlMixin, CreateView):
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
        messages.success(self.request, "Domain successfully created", extra_tags="alert-success")
        return reverse("shepherd:domain_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("shepherd:domains")
        return ctx


class DomainUpdate(RoleBasedAccessControlMixin, UpdateView):
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
        messages.success(self.request, "Domain successfully updated", extra_tags="alert-success")
        return reverse("shepherd:domain_detail", kwargs={"pk": self.object.id})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("shepherd:domain_detail", kwargs={"pk": self.object.id})
        return ctx


class DomainDelete(RoleBasedAccessControlMixin, DeleteView):
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
        messages.warning(self.request, "Domain successfully deleted!", extra_tags="alert-warning")
        return reverse("shepherd:domains")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "domain"
        ctx["object_to_be_deleted"] = queryset.name.upper()
        ctx["cancel_link"] = reverse("shepherd:domain_detail", kwargs={"pk": self.object.id})
        return ctx


class ServerDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`shepherd.StaticServer`.

    **Context**

    ``primary_address``
        Primary IP address from :model:`shepherd.AuxServerAddress` for :model:`shepherd.StaticServer`

    **Template**

    :template:`shepherd/server_detail.html`
    """

    model = StaticServer
    template_name = "shepherd/server_detail.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["primary_address"] = queryset.ip_address
        aux_addresses = AuxServerAddress.objects.filter(static_server=queryset)
        for address in aux_addresses:
            if address.primary:
                ctx["primary_address"] = address.ip_address
        ctx["server_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=StaticServer._meta.label)
        return ctx


class ServerCreate(RoleBasedAccessControlMixin, CreateView):
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
        messages.success(self.request, "Server successfully created.", extra_tags="alert-success")
        return reverse("shepherd:server_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
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
                obj = form.save()

                addresses_valid = addresses.is_valid()
                if addresses_valid:
                    addresses.instance = obj
                    addresses.save()
                if form.is_valid() and addresses_valid:
                    obj.save()
                    return super().form_valid(form)
                # Raise an error to rollback transactions
                raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super().form_invalid(form)

    def get_initial(self):
        return {
            "server_status": 1,
        }


class ServerUpdate(RoleBasedAccessControlMixin, UpdateView):
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
        messages.success(self.request, "Server successfully updated.", extra_tags="alert-success")
        return reverse("shepherd:server_detail", kwargs={"pk": self.object.pk})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("shepherd:server_detail", kwargs={"pk": self.object.pk})
        if self.request.POST:
            ctx["addresses"] = ServerAddressFormSet(self.request.POST, prefix="address", instance=self.object)
        else:
            ctx["addresses"] = ServerAddressFormSet(prefix="address", instance=self.object)
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
                obj = form.save()

                addresses_valid = addresses.is_valid()
                if addresses_valid:
                    addresses.instance = obj
                    addresses.save()
                if form.is_valid() and addresses_valid:
                    obj.save()
                    return super().form_valid(form)
                # Raise an error to rollback transactions
                raise forms.ValidationError(_("Invalid form data"))
        # Otherwise return `form_invalid` and display errors
        except Exception as exception:
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            message = template.format(type(exception).__name__, exception.args)
            logger.error(message)
            return super().form_invalid(form)


class ServerDelete(RoleBasedAccessControlMixin, DeleteView):
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
        messages.warning(self.request, "Server successfully deleted!", extra_tags="alert-warning")
        return reverse("shepherd:servers")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "static server"
        ctx["object_to_be_deleted"] = queryset.ip_address
        ctx["cancel_link"] = reverse("shepherd:server_detail", kwargs={"pk": self.object.id})
        return ctx


class ServerHistoryCreate(RoleBasedAccessControlMixin, CreateView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.server = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))

    def get_initial(self):
        return {"server": self.server}

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.server = self.server
        obj.operator = self.request.user
        obj.save()

        # Update the server status and commit it
        server_instance = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))
        server_instance.last_used_by = self.request.user
        server_instance.server_status = ServerStatus.objects.get(server_status="Unavailable")
        server_instance.save()
        return super().form_valid(form)

    def get_success_url(self):
        messages.success(self.request, "Server successfully checked-out.", extra_tags="alert-success")
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["server"] = self.server
        ctx["cancel_link"] = reverse("shepherd:server_detail", kwargs={"pk": self.server.pk})
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class ServerHistoryUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Server history successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["server"] = self.get_object()
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )
        return ctx

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"user": self.request.user})
        return kwargs


class ServerHistoryDelete(RoleBasedAccessControlMixin, DeleteView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.warning(
            self.request,
            "Server history successfully deleted!",
            extra_tags="alert-warning",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "server checkout"
        ctx["object_to_be_deleted"] = queryset
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk})
        )
        return ctx


def check_duplicate_ip(request, project, ip_address, aux_address):
    """Check for duplicate IP addresses in other servers and cloud servers."""
    # Put all IP addresses into a list to cover checking any appearances (as the IP or an aux address)
    all_ips = [ip_address]
    for address in aux_address:
        all_ips.append(address)

    # Query servers that share one or more of the IPs in the list
    cloud_servers = TransientServer.objects.filter(Q(project=project) & Q(ip_address__in=all_ips) | Q(aux_address__overlap=all_ips))
    static_servers = ServerHistory.objects.filter(
        Q(project=project) & (Q(server__ip_address__in=all_ips) | Q(server__auxserveraddress__ip_address__in=all_ips))
    )

    # Add a warning to the request if any servers share the IP addresses
    sharing_servers = len(cloud_servers) + len(static_servers)
    if sharing_servers >= 1:
        messages.warning(
            request,
            f'You have {sharing_servers} server(s) that share one or more of the provided IP addresses.',
        )


class TransientServerCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual :model:`shepherd.TransientServer`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to project's details page

    **Template**

    :template:`shepherd/vps_form.html`
    """

    model = TransientServer
    form_class = TransientServerForm
    template_name = "shepherd/vps_form.html"

    def test_func(self):
        return verify_access(self.request.user, self.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.project = get_object_or_404(Project, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Server successfully added to the project.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.project = self.project
        obj.operator = self.request.user
        obj.save()
        check_duplicate_ip(self.request, self.project, obj.ip_address, obj.aux_address)
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project.id})
        )
        return ctx


class TransientServerUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Server information successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx

    def form_valid(self, form):
        check_duplicate_ip(self.request, self.object.project, self.object.ip_address, self.object.aux_address)
        return super().form_valid(form)


class DomainServerConnectionCreate(RoleBasedAccessControlMixin, CreateView):
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

    def test_func(self):
        return verify_access(self.request.user, self.project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.project = get_object_or_404(Project, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Server successfully associated with domain.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["project"] = self.project
        return form_kwargs

    def form_valid(self, form):
        obj = form.save(commit=False)
        obj.project = self.project
        obj.save()
        return super().form_valid(form)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.project.id})
        )
        return ctx


class DomainServerConnectionUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        return verify_access(self.request.user, self.get_object().project)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect("home:dashboard")

    def get_success_url(self):
        messages.success(
            self.request,
            "Connection information successfully updated.",
            extra_tags="alert-success",
        )
        return "{}#infrastructure".format(reverse("rolodex:project_detail", kwargs={"pk": self.object.project.pk}))

    def get_form_kwargs(self, **kwargs):
        form_kwargs = super().get_form_kwargs()
        form_kwargs["project"] = self.object.project
        return form_kwargs

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = "{}#infrastructure".format(
            reverse("rolodex:project_detail", kwargs={"pk": self.object.project.id})
        )
        return ctx


class DomainNoteCreate(RoleBasedAccessControlMixin, CreateView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.domain = get_object_or_404(Domain, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this domain.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.domain.name.upper()
        ctx["cancel_link"] = "{}#notes".format(reverse("shepherd:domain_detail", kwargs={"pk": self.domain.id}))
        return ctx

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.operator = self.request.user
        obj.domain_id = self.domain.id
        obj.save()
        return super().form_valid(form)


class DomainNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("shepherd:domain_detail", kwargs={"pk": self.get_object().domain.pk}) + "#notes")

    def get_success_url(self):
        messages.success(self.request, "Note successfully updated.", extra_tags="alert-success")
        return "{}#notes".format(reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.object.domain.name.upper()
        ctx["cancel_link"] = "{}#notes".format(reverse("shepherd:domain_detail", kwargs={"pk": self.object.domain.id}))
        return ctx


class ServerNoteCreate(RoleBasedAccessControlMixin, CreateView):
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

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.server = get_object_or_404(StaticServer, pk=self.kwargs.get("pk"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Note successfully added to this server.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(reverse("shepherd:server_detail", kwargs={"pk": self.object.server.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["note_object"] = self.server.ip_address
        ctx["cancel_link"] = reverse("shepherd:server_detail", kwargs={"pk": self.server.id})
        return ctx

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.operator = self.request.user
        obj.server_id = self.server.id
        obj.save()
        return super().form_valid(form)


class ServerNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
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

    def test_func(self):
        obj = self.get_object()
        return obj.operator.id == self.request.user.id

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("shepherd:server_detail", kwargs={"pk": self.get_object().server.pk}) + "#notes")

    def get_success_url(self):
        messages.success(self.request, "Note successfully updated.", extra_tags="alert-success")
        return "{}#notes".format(reverse("shepherd:server_detail", kwargs={"pk": self.object.server.id}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        server_instance = self.object.server
        ctx["note_object"] = server_instance.ip_address
        ctx["cancel_link"] = reverse("shepherd:server_detail", kwargs={"pk": self.object.server.id})
        return ctx
