
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

from ghostwriter.api.utils import RoleBasedAccessControlMixin, get_project_list, verify_finding_access, verify_user_is_privileged
from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.commandcenter.views import CollabModelUpdate
from ghostwriter.reporting.filters import FindingFilter
from ghostwriter.reporting.forms import FindingForm, FindingNoteForm
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
        obj = Finding()
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

    **Template**

    :template:`reporting/finding_form.html`
    """

    model = ReportFindingLink

    def test_func(self):
        return Finding.user_can_create(self.request.user) and self.get_object().user_can_view(self.request.user)

    def handle_no_permission(self):
        messages.error(self.request, "You do not have the necessary permission to create new findings.")
        return redirect(reverse("reporting:report_detail", kwargs={"pk": self.get_object().report.pk}) + "#findings")

    def get(self, *args, **kwargs):
        finding_instance = self.get_object()
        try:
            form = FindingForm(
                initial={
                    "title": finding_instance.title,
                    "description": finding_instance.description,
                    "impact": finding_instance.impact,
                    "mitigation": finding_instance.mitigation,
                    "replication_steps": finding_instance.replication_steps,
                    "host_detection_techniques": finding_instance.host_detection_techniques,
                    "network_detection_techniques": finding_instance.network_detection_techniques,
                    "references": finding_instance.references,
                    "severity": finding_instance.severity,
                    "finding_type": finding_instance.finding_type,
                    "cvss_score": finding_instance.cvss_score,
                    "cvss_vector": finding_instance.cvss_vector,
                    "tags": finding_instance.tags.all(),
                }
            )
        except Exception as exception:  # pragma: no cover
            template = "An exception of type {0} occurred. Arguments:\n{1!r}"
            log_message = template.format(type(exception).__name__, exception.args)
            logger.error(log_message)

            messages.error(
                self.request,
                "Encountered an error while trying to convert your finding: {}".format(exception.args),
                extra_tags="alert-error",
            )
            return HttpResponse(status=500)

        return render(self.request, "reporting/finding_form.html", {"form": form})

    def post(self, *args, **kwargs):
        form = FindingForm(self.request.POST)
        if form.is_valid():
            new_finding = form.save()
            return redirect("reporting:finding_detail", kwargs={"pk": new_finding.pk})
        logger.warning(form.errors.as_data())
        return render(self.request, "reporting/finding_form.html", {"form": form})


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
        return verify_finding_access(self.request.user, "delete")

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
