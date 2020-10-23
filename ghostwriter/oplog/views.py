"""This contains all of the views used by the Oplog application."""

# Standard Libraries
import logging

# Django & Other 3rd Party Libraries
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from rest_framework import viewsets
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework_api_key.models import APIKey
from rest_framework_api_key.permissions import HasAPIKey
from tablib import Dataset

from .admin import OplogEntryResource
from .forms import OplogCreateEntryForm, OplogCreateForm
from .models import Oplog, OplogEntry
from .serializers import OplogEntrySerializer, OplogSerializer

# Using __name__ resolves to ghostwriter.oplog.views
logger = logging.getLogger(__name__)


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

        if not result.has_errors():
            oplog_entry_resource.import_data(imported_data, format="csv", dry_run=False)
            return HttpResponseRedirect(reverse("oplog:index"))

    return render(request, "oplog/oplog_import.html")


@login_required
def OplogListEntries(request, pk):
    """
    Display all :model:`oplog.OplogEntry` associated with an individual
    :model:`oplog.Oplog`.

    **Template**

    :template:`oplog/entries_list.html`
    """
    entries = OplogEntry.objects.filter(oplog_id=pk).order_by("-start_date")
    name = Oplog.objects.get(pk=pk).name
    context = {"entries": entries, "pk": pk, "name": name}
    return render(request, "oplog/entries_list.html", context=context)


@login_required
def create_oplog(request):
    """
    Create an individual :model:`oplog.Oplog`.
    """
    context = {}
    context["cancel_link"] = reverse("oplog:index")
    if request.method == "POST":
        form = OplogCreateForm(request.POST)
        if form.is_valid():
            # Save the new :model:`oplog.Oplog` instance
            form.save()
            messages.success(
                request,
                "New operation log was successfully created",
                extra_tags="alert-success",
            )
            # Create new API key for this oplog
            try:
                oplog_name = form.instance.name
                api_key_name = oplog_name
                api_key, key = APIKey.objects.create_key(name=api_key_name)
                # Pass the API key via the messages framework
                messages.info(
                    request,
                    f"The API key for your log is { api_key }: { key }\r\nPlease store it somewhere safe: you will not be able to see it again.",
                    extra_tags="api-key no-toast",
                )
            except Exception:
                logger.exception("Failed to create new API key")
                messages.error(
                    request,
                    "Could not generate an API key for your new operation log – contact your admin!",
                    extra_tags="alert-danger",
                )
            return HttpResponseRedirect(reverse("oplog:index"))
    else:
        context["form"] = OplogCreateForm()
    return render(
        request,
        "oplog/oplog_form.html",
        context=context,
    )


################
# View Classes #
################


class OplogEntryCreate(LoginRequiredMixin, CreateView):
    """
    Create an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplogentry_form.html`
    """

    model = OplogEntry
    form_class = OplogCreateEntryForm

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogEntryUpdate(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`oplog.OplogEntry`.

    **Template**

    :template:`oplog/oplogentry_form.html`
    """

    model = OplogEntry
    fields = "__all__"

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogEntryDelete(LoginRequiredMixin, DeleteView):
    """
    Delete an individual :model:`oplog.OplogEntry`.
    """

    model = OplogEntry
    fields = "__all__"

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


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
            queryset = OplogEntry.objects.filter(oplog_id=oplog_id).order_by(
                "-start_date"
            )
        if "export" in request.query_params:
            format = request.query_params["export"]
            dataset = OplogEntryResource().export(queryset)
            try:
                return HttpResponse(getattr(dataset, format))
            except AttributeError:
                return None

        serializer = OplogEntrySerializer(queryset, many=True)
        return Response(serializer.data)


class OplogViewSet(viewsets.ModelViewSet):
    queryset = Oplog.objects.all()
    serializer_class = OplogSerializer
    permission_classes = [HasAPIKey | IsAuthenticated]
