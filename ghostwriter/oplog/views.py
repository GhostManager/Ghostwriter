from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect, HttpResponse
from django.shortcuts import render
from django.urls import reverse
from django.views.generic.edit import CreateView, UpdateView, DeleteView

from rest_framework import viewsets
from rest_framework.response import Response
from tablib import Dataset

from .admin import OplogEntryResource
from .models import Oplog, OplogEntry
from .forms import OplogCreateForm, OplogCreateEntryForm
from .serializers import OplogSerializer, OplogEntrySerializer

from rest_framework.permissions import IsAuthenticated
from rest_framework_api_key.permissions import HasAPIKey

from ghostwriter.rolodex.models import Project


# Create your views here.
@login_required
def index(request):
    op_logs = Oplog.objects.all()
    context = {"op_logs": op_logs}
    return render(request, "oplog/oplog_list.html", context=context)


@login_required
def OplogEntriesImport(request):
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
    entries = OplogEntry.objects.filter(oplog_id=pk).order_by("-start_date")
    name = Oplog.objects.get(pk=pk).name
    context = {"entries": entries, "pk": pk, "name": name}
    return render(request, "oplog/entries_list.html", context=context)

@login_required
def load_projects(request):
    client = request.GET.get('client')
    try:
        projects = Project.objects.filter(client=client)
    except:
        projects = Project.objects.none()

    return render(request, 'project_dropdown_list.html', {'projects': projects})

class OplogCreateWithoutProject(LoginRequiredMixin, CreateView):
    model = Oplog
    form_class = OplogCreateForm

    def get_success_url(self):
        return reverse("oplog:index")


class OplogEntryCreate(LoginRequiredMixin, CreateView):
    model = OplogEntry
    form_class = OplogCreateEntryForm

    def get_success_url(self):
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogEntryUpdate(LoginRequiredMixin, UpdateView):
    """View for updating existing oplog entries. This view defaults to the
    oplogentry_form.html template.
    """

    model = OplogEntry
    fields = "__all__"

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
        return reverse("oplog:oplog_entries", args=(self.object.oplog_id.id,))


class OplogEntryDelete(LoginRequiredMixin, DeleteView):
    """View for deleting existing oplog entries. This view defaults to the
    oplogentry_form.html template.
    """

    model = OplogEntry
    fields = "__all__"

    def get_success_url(self):
        """Override the function to return to the new record after creation."""
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
            queryset = OplogEntry.objects.filter(oplog_id=oplog_id).order_by("-start_date")
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
