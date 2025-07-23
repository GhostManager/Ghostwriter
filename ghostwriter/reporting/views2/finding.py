
import logging

from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse, reverse_lazy
from django.contrib import messages
from django.views import View
from django.views.generic.detail import DetailView, SingleObjectMixin
from django.views.generic.list import ListView
from django.views.generic.edit import CreateView, DeleteView, UpdateView
from django.db.models import Q

from ghostwriter.api.utils import RoleBasedAccessControlMixin, get_project_list, verify_user_is_privileged
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.reporting.filters import FindingFilter
from ghostwriter.reporting.forms import FindingNoteForm
from ghostwriter.reporting.models import Finding, FindingNote, ReportFindingLink

logger = logging.getLogger(__name__)

class FindingListView(RoleBasedAccessControlMixin, ListView):
    """
    Display a list of all :model:`reporting.Finding`.

    **Context**

    ``filter``
        Instance of :filter:`reporting.FindingFilter`

    **Template**

    :template:`reporting/finding_list.html`
    """

    model = Finding # May also use ReportFindingLink
    template_name = "reporting/finding_list.html"

    def __init__(self):
        super().__init__()
        self.autocomplete = []
        self.searching_report_findings = False

    def get_queryset(self):
        if self.request.GET.get("on_reports", "").strip():
            findings = ReportFindingLink.objects.filter(report__project__in=get_project_list(self.request.user))
            self.searching_report_findings = True
            if self.request.GET.get("not_cloned", "").strip():
                # Filter the queryset to show only findings that started as blanks
                findings = findings.filter(added_as_blank=True)
        else:
            findings = Finding.objects.all()

        self.autocomplete = findings
        findings = findings.select_related("severity", "finding_type").order_by("severity__weight", "-cvss_score", "finding_type", "title")

        search_term = self.request.GET.get("finding", "").strip()
        if search_term:
            messages.success(
                self.request,
                "Displaying search results for: {}".format(search_term),
                extra_tags="alert-success",
            )
            findings = findings.filter(
                Q(title__icontains=search_term) | Q(description__icontains=search_term)
            ).order_by("severity__weight", "-cvss_score", "finding_type", "title")
        return findings

    def get(self, request, *args, **kwarg):
        findings_filter = FindingFilter(request.GET, queryset=self.get_queryset())
        return render(
            request, "reporting/finding_list.html", {
                "filter": findings_filter,
                "autocomplete": self.autocomplete,
                "searching_report_findings": self.searching_report_findings,
            }
        )


class FindingDetailView(RoleBasedAccessControlMixin, DetailView):
    """
    Display an individual :model:`reporting.Finding`.

    **Template**

    :template:`reporting/finding_detail.html`
    """

    model = Finding

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["finding_extra_fields_spec"] = ExtraFieldSpec.objects.filter(target_model=Finding._meta.label)
        return ctx


class FindingCreate(RoleBasedAccessControlMixin, View):
    def test_func(self):
        return Finding.user_can_create(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to create new findings.")
        return redirect("reporting:findings")

    def post(self, request) -> HttpResponse:
        obj = Finding(
            extra_fields=ExtraFieldSpec.initial_json(Finding),
        )
        obj.save()
        messages.success(
            self.request,
            "New finding created",
            extra_tags="alert-success",
        )
        return redirect("reporting:finding_update", pk=obj.id)


class ConvertFinding(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Create a copy of an individual :model:`reporting.ReportFindingLink` and prepare
    it to be saved as a new :model:`reporting.Finding`.
    """

    model = ReportFindingLink

    def test_func(self):
        return Finding.user_can_create(self.request.user) and self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to create new findings.")
        return redirect(reverse("reporting:report_detail", kwargs={"pk": self.get_object().report.pk}) + "#findings")

    def post(self, *args, **kwargs):
        rfl: ReportFindingLink = self.get_object()
        finding = Finding(
            title=rfl.title,
            description=rfl.description,
            impact=rfl.impact,
            mitigation=rfl.mitigation,
            replication_steps=rfl.replication_steps,
            host_detection_techniques=rfl.host_detection_techniques,
            network_detection_techniques=rfl.network_detection_techniques,
            references=rfl.references,
            finding_guidance=rfl.finding_guidance,
            severity=rfl.severity,
            finding_type=rfl.finding_type,
            cvss_score=rfl.cvss_score,
            cvss_vector=rfl.cvss_vector,
            extra_fields=rfl.extra_fields,
        )
        finding.save()
        finding.tags.set(rfl.tags.names())
        messages.info(self.request, "Finding cloned to library.")
        return redirect("reporting:finding_detail", pk=finding.pk)


class FindingUpdate(CollabModelUpdate):
    """
    Update an individual instance of :model:`reporting.Finding`.
    """

    model = Finding
    template_name = "reporting/finding_update.html"
    unauthorized_redirect = "reporting:findings"


class FindingDelete(RoleBasedAccessControlMixin, DeleteView):
    """
    Delete an individual instance of :model:`reporting.Finding`.

    **Context**

    ``object_type``
        String describing what is to be deleted
    ``object_to_be_deleted``
        To-be-deleted instance of :model:`reporting.Finding`
    ``cancel_link``
        Link for the form's Cancel button to return to finding list page

    **Template**

    :template:`confirm_delete.html`
    """

    model = Finding
    template_name = "confirm_delete.html"

    def test_func(self):
        return self.get_object().user_can_delete(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to delete findings.")
        return redirect(reverse("reporting:finding_detail", kwargs={"pk": self.get_object().pk}))

    def get_success_url(self):
        messages.warning(
            self.request,
            "Master record for {} was successfully deleted".format(self.get_object().title),
            extra_tags="alert-warning",
        )
        return reverse_lazy("reporting:findings")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        queryset = kwargs["object"]
        ctx["object_type"] = "finding master record"
        ctx["object_to_be_deleted"] = queryset.title
        ctx["cancel_link"] = reverse("reporting:findings")
        return ctx


class FindingNoteCreate(RoleBasedAccessControlMixin, CreateView):
    """
    Create an individual instance of :model:`reporting.FindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = FindingNote
    form_class = FindingNoteForm
    template_name = "note_form.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        finding_instance = get_object_or_404(Finding, pk=self.kwargs.get("pk"))
        ctx["cancel_link"] = reverse("reporting:finding_detail", kwargs={"pk": finding_instance.pk})
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully added your note to this finding.",
            extra_tags="alert-success",
        )
        return "{}#notes".format(reverse("reporting:finding_detail", kwargs={"pk": self.object.finding.id}))

    def form_valid(self, form, **kwargs):
        self.object = form.save(commit=False)
        self.object.operator = self.request.user
        self.object.finding_id = self.kwargs.get("pk")
        self.object.save()
        return super().form_valid(form)


class FindingNoteUpdate(RoleBasedAccessControlMixin, UpdateView):
    """
    Update an individual instance of :model:`reporting.FindingNote`.

    **Context**

    ``cancel_link``
        Link for the form's Cancel button to return to finding's detail page

    **Template**

    :template:`note_form.html`
    """

    model = FindingNote
    form_class = FindingNoteForm
    template_name = "note_form.html"

    def test_func(self):
        obj: FindingNote = self.get_object()
        return obj.operator.id == self.request.user.id or verify_user_is_privileged(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that.")
        return redirect(reverse("reporting:finding_detail", kwargs={"pk": self.get_object().finding.pk}))

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("reporting:finding_detail", kwargs={"pk": self.get_object().finding.pk})
        return ctx

    def get_success_url(self):
        messages.success(self.request, "Successfully updated the note.", extra_tags="alert-success")
        return reverse("reporting:finding_detail", kwargs={"pk": self.get_object().finding.pk})
