"""This contains all of the URL mappings used by the Stratum custom code."""

# Django Imports
from django.urls import path

from . import views

app_name = "stratum"

# URLs for the basic views
urlpatterns = [
    path("", views.report_findings_list, name="report_findings"),
]