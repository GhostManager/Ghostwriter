
from django.views import View
from django.views.generic.detail import DetailView
from django.views.generic.list import ListView
from django.views.generic.edit import DeleteView
from django.contrib import messages
from django.shortcuts import redirect, render
from django.http import HttpRequest, HttpResponse
from django.urls import reverse, reverse_lazy
from django.db.models import Q
from taggit.models import Tag

from ghostwriter.api.utils import RoleBasedAccessControlMixin
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.reporting.filters import ObservationFilter
from ghostwriter.reporting.models import Observation


class ObservationList(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`reporting.Observation`.
    """

    model = Observation
    template_name = "reporting/observation_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []

    def get_queryset(self):
        search_term = ""
        observations = Observation.objects.all().order_by("title")

        # Build autocomplete list
        for observation in observations:
            self.autocomplete.append(observation)

        search_term = self.request.GET.get("observation", "").strip()
        if search_term:
            messages.success(
                self.request,
                "Displaying search results for: {}".format(search_term),
                extra_tags="alert-success",
            )
            return observations.filter(
                Q(title__icontains=search_term) | Q(description__icontains=search_term)
            ).order_by("title")
        return observations

    def get(self, request: HttpRequest, *args, **kwarg) -> HttpResponse:
        observation_filter = ObservationFilter(request.GET, queryset=self.get_queryset(), request=self.request)
        return render(
            request,
            "reporting/observation_list.html",
            {"filter": observation_filter, "autocomplete": self.autocomplete, "tags": Tag.objects.all(),},
        )


class ObservationDetail(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`reporting.Observation`.

    **Template**

    :template:`reporting/observation_detail.html`
    """

    model = Observation

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to view observations.")
        return redirect("reporting:observations")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx


class ObservationCreate(RoleBasedAccessControlMixin, View):
    def test_func(self):
        return Observation.user_can_create(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to create new observations.")
        return redirect("reporting:observations")

    def post(self, request: HttpRequest) -> HttpResponse:
        obj = Observation(
            extra_fields=ExtraFieldSpec.initial_json(Observation),
        )
        obj.save()
        messages.success(
            self.request,
            "New observation created",
            extra_tags="alert-success",
        )
        return redirect("reporting:observation_update", pk=obj.id)


class ObservationUpdate(CollabModelUpdate):
    """
    Display an individual :model:`reporting.Observation` for editing.
    """
    model = Observation
    template_name = "reporting/observation_update.html"
    unauthorized_redirect = "reporting:observations"

class ObservationDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.Observation`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.Observation`
    ``cancel_link``
        Link for the form's Cancel button to return to observation list page

    **Template**

    :template:`confirm_delete.html`
    """
    model = Observation
    template_name = "confirm_delete.html"

    def test_func(self):
        return self.get_object().user_can_delete(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to delete observations.")
        return redirect(reverse("reporting:observation_detail", kwargs={"pk": self.get_object().pk}))

    def get_success_url(self):
        messages.warning(
            self.request,
            "Observation {} was successfully deleted".format(self.get_object().title),
            extra_tags="alert-warning",
        )
        return reverse_lazy("reporting:observations")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "observation"
        ctx["object_to_be_deleted"] = queryset.title
        ctx["cancel_link"] = reverse("reporting:observations")
        return ctx
