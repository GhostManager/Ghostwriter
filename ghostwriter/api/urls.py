"""This contains all of the URL mappings used by the API application."""

# Django Imports
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Ghostwriter Libraries
from ghostwriter.api.views import (
    graphql_domain_update_event,
    graphql_generate_report,
    graphql_login,
    graphql_webhook,
    graphql_whoami,
)

app_name = "api"

urlpatterns = [
    path("webhook", csrf_exempt(graphql_webhook), name="graphql_webhook"),
    path("login", csrf_exempt(graphql_login), name="graphql_login"),
    path("whoami", csrf_exempt(graphql_whoami), name="graphql_whoami"),
    path("generateReport", csrf_exempt(graphql_generate_report), name="graphql_generate_report"),
    path("event/domain/update", csrf_exempt(graphql_domain_update_event), name="graphql_domain_update_event"),
]
