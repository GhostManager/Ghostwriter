"""This contains all of the views used by the Oplog application."""

# Standard Libraries
import logging

# Django Imports
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import HttpResponse, HttpResponseRedirect, JsonResponse
from django.shortcuts import get_object_or_404, render
from django.urls import reverse
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.edit import CreateView, DeleteView, UpdateView, View

# 3rd Party Libraries
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey
from tablib import Dataset

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project
from .admin import OplogEntryResource
from .forms import OplogEntryForm, OplogForm
from .models import Oplog, OplogEntry
from .serializers import OplogEntrySerializer, OplogSerializer

# Using __name__ resolves to ghostwriter.oplog.views
logger = logging.getLogger(__name__)


##################
#   AJAX Views   #
##################


class OplogMuteToggle(LoginRequiredMixin, SingleObjectMixin, UserPassesTestMixin, View):
    """
    Toggle the ``mute_notifications`` field of an individual :model:`oplog.Oplog`.
    """

    model = Oplog

    def test_func(self):
        if self.request.user.role in (
            "manager",
            "admin",
        ):
            return True
        return self.request.user.is_staff

    def handle_no_permission(self):
        if self.request.user.is_authenticated:
            data = {"result": "error", "message": "Only a manager or admin can mute notifications"}
        else:
            data = {"result": "error", "message": "You must be logged in"}
        return JsonResponse(data, status=403)

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        try:
            if self.object.mute_notifications:
                self.object.mute_notifications = False
                data = {
                    "result": "success",
                    "message": "Oplog monitor notifications have been unmuted",
                    "toggle": 0,
                }
            else:
                self.object.mute_notifications = True
                data = {
                    "result": "success",
                    "message": "Oplog monitor notifications have been muted",
                    "toggle": 1,
                }
            self.object.save()
            logger.info(
                "Toggled notifications for %s %s by request of %s",
                self.object.__class__.__name__,
                self.object.id,
                self.request.user,
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)
            data = {"result": "error", "message": "Could not update mute status for oplog monitor notifications"}

        return JsonResponse(data)


##################
# View Functions #
##################


@login_required
def index(request):
    """
    Display a list of all :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_list.html`
    """
    op_logs = Oplog.objects.all()
    context = {"op_logs": op_logs}
    return render(request, "oplog/oplog_list.html", context=context)


@login_required
def OplogEntriesImport(request):
    """
    Import a collection of :model:`oplog.OplogEntry` entries for an individual
    :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_import.html`
    """
    if request.method == "POST":
        oplog_entry_resource = OplogEntryResource()

        new_entries = request.FILES["csv_file"].read().decode("iso-8859-1")
        dataset = Dataset()

        imported_data = dataset.load(new_entries, format="csv")
        result = oplog_entry_resource.import_data(imported_data, dry_run=True)

        if result.has_errors():
            row_errors = result.row_errors()
            for exc in row_errors:
                messages.error(
                    request,
                    f"There was an error in row {exc[0]}: {exc[1][0].error}",
                    extra_tags="alert-danger",
                )
            return HttpResponseRedirect(reverse("oplog:oplog_import"))
        oplog_entry_resource.import_data(imported_data, format="csv", dry_run=False)
        # Get the first ``oplog_id`` value to use for a redirect
        oplog_id = imported_data["oplog_id"][0]
        messages.success(
            request,
            "Successfully imported log data",
            extra_tags="alert-success",
        )
        return HttpResponseRedirect(reverse("oplog:oplog_entries", kwargs={"pk": oplog_id}))

    return render(request, "oplog/oplog_import.html")


################
# View Classes #
################


class OplogListEntries(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`oplog.Oplog`.

    **Context**

    ``entries``
        :model:`oplog:OplogEntry` entries associated with the :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_detail.html`
    """

    model = Oplog


class OplogCreate(LoginRequiredMixin, CreateView):
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
                    self.project = get_object_or_404(Project, pk=self.kwargs.get("pk"))
                except Project.DoesNotExist:
                    logger.info(
                        "Received report create request for Project ID %s, but that Project does not exist",
                        pk,
                    )

    def get_form_kwargs(self):
        kwargs = super().get_form_kwargs()
        kwargs.update({"project": self.project})
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
                "There are no active projects for a new operation log",
                extra_tags="alert-error",
            )
        return form

    # TODO: The use of DRF and DRF API keys will be DEPRECATED in the near future and this section will need to be removed
    def form_valid(self, form):
        # Save the new :model:`oplog.Oplog` instance
        form.save()
        # Create new API key for this oplog
        try:
            project = form.instance.project.id
            oplog_name = form.instance.name
            api_key_name = oplog_name
            api_key, key = APIKey.objects.create_key(name=api_key_name[:50])
            # Pass the API key via the messages framework
            messages.info(
                self.request,
                f'The logging API key for project {project} and log "{api_key}" is: {key}\r\nPlease store it somewhere safe: you will not be able to see it again.',
                extra_tags="api-key no-toast",
            )
        except Exception:
            logger.exception("Failed to create new API key")
            messages.error(
                self.request,
                "Could not generate an API key for your new operation log – contact your admin!",
                extra_tags="alert-danger",
            )
        return super().form_valid(form)

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


class OplogUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/oplog_form.html`
    """

    model = Oplog
    form_class = OplogForm

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.id,))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("oplog:oplog_entries", kwargs={"pk": self.object.pk})
        return ctx


class AjaxTemplateMixin:
    def dispatch(self, request, *args, **kwargs):
        if not hasattr(self, "ajax_template_name"):
            split = self.template_name.split(".html")
            split[-1] = "_inner"
            split.append(".html")
            self.ajax_template_name = "".join(split)
        if request.is_ajax():
            self.template_name = self.ajax_template_name
        return super().dispatch(request, *args, **kwargs)


class OplogEntryCreate(LoginRequiredMixin, AjaxTemplateMixin, CreateView):
    """
    Create an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplog_modal.html`
    """

    model = OplogEntry
    form_class = OplogEntryForm
    template_name = "oplog/oplogentry_form.html"
    ajax_template_name = "oplog/snippets/oplogentry_form_inner.html"

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.save()
        form.save_m2m()
        return super().form_valid(form)


class OplogEntryUpdate(LoginRequiredMixin, AjaxTemplateMixin, UpdateView):
    """
    Update an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplog_modal.html`
    """

    model = OplogEntry
    form_class = OplogEntryForm
    template_name = "oplog/oplogentry_form.html"
    ajax_template_name = "oplog/snippets/oplogentry_form_inner.html"

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))

    def form_valid(self, form, **kwargs):
        obj = form.save(commit=False)
        obj.save()
        form.save_m2m()
        return super().form_valid(form)


class OplogEntryDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`oplog.OplogEntry`.
    """

    model = OplogEntry
    fields = "__all__"

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


# TODO: The use of DRF and DRF API keys will be DEPRECATED in the near future and this section will need to be removed
class OplogEntryViewSet(viewsets.ModelViewSet):
    serializer_class = OplogEntrySerializer
    queryset = OplogEntry.objects.all()
    permission_classes = [HasAPIKey | IsAuthenticated]

    def list(self, request):
        queryset = OplogEntry.objects.all().order_by("-start_date")
        if "oplog_id" not in self.request.query_params:
            queryset = OplogEntry.objects.all().order_by("-start_date")
        else:
            oplog_id = self.request.query_params["oplog_id"]
            queryset = OplogEntry.objects.filter(oplog_id=oplog_id).order_by("-start_date")
        if "export" in request.query_params:
            export_format = request.query_params["export"]
            dataset = OplogEntryResource().export(queryset)
            try:
                return HttpResponse(getattr(dataset, export_format))
            except AttributeError:
                return None

        serializer = OplogEntrySerializer(queryset, many=True)
        return Response(serializer.data)


# TODO: The use of DRF and DRF API keys will be DEPRECATED in the near future and this section will need to be removed
class OplogViewSet(viewsets.ModelViewSet):
    queryset = Oplog.objects.all()
    serializer_class = OplogSerializer
    permission_classes = [HasAPIKey | IsAuthenticated]
