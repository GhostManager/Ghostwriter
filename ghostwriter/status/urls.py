"""This contains all the URL mappings used by the Status application."""

# Django Imports
from django.urls import path

# Ghostwriter Libraries
from ghostwriter.status.views import HealthCheckCustomView, HealthCheckSimpleView

app_name = "status"

# URLs for the basic domain views
urlpatterns = [
    path("", HealthCheckCustomView.as_view(), name="healthcheck"),
    path("simple/", HealthCheckSimpleView.as_view(), name="healthcheck_simple"),
]
