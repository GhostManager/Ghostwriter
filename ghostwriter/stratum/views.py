# Django Imports
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.shortcuts import render

# Ghostwriter Libraries
from ghostwriter.reporting.models import ReportFindingLink

from .filters import ReportFindingFilter


@login_required
def report_findings_list(request):
    """
    Display a list of all report findings based on search criteria.
    **Template**
    :template:`stratum/report_findings_list.html`
    """
    findings = (
        ReportFindingLink.objects.select_related("severity", "finding_type", "report")
        .all()
        .order_by("severity__weight", "-cvss_score", "finding_type", "title")
    )
    findings_filter = ReportFindingFilter(request.GET, queryset=findings)

    # Default to 15 findings per page
    page_size = request.GET.get("page_size", 15)

    paginator = Paginator(findings_filter.qs, page_size)
    page = request.GET.get("page")
    page_number = 1 if page == None else page
    page_obj = paginator.get_page(page_number)

    # Add parameters object to template for pagination to work in template HTML
    # Remove the page parameter as the HTML template will append the page parameter with the new value
    p = request.GET.copy()
    parameters = p.pop("page", True) and p.urlencode()

    context = {
        "filter": findings_filter,
        "page_obj": page_obj,
        "parameters": parameters,
        "page_size_values": [15, 30, 50, 100, 200, 500, 1000],
    }
    return render(request, "report_findings_list.html", context)
