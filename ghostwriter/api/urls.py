"""This contains all of the URL mappings used by the API application."""

# Django Imports
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Ghostwriter Libraries
from ghostwriter.api.views import (
    ApiKeyCreate,
    ApiKeyRevoke,
    GraphqlCheckoutDomain,
    GraphqlCheckoutServer,
    GraphqlDomainUpdateEvent,
    GraphqlGenerateReport,
    GraphqlWhoami,
    graphql_login,
    graphql_webhook,
)

app_name = "api"

urlpatterns = [
    path("webhook", csrf_exempt(graphql_webhook), name="graphql_webhook"),
    path("login", csrf_exempt(graphql_login), name="graphql_login"),
    path("whoami", csrf_exempt(GraphqlWhoami.as_view()), name="graphql_whoami"),
    path("generateReport", csrf_exempt(GraphqlGenerateReport.as_view()), name="graphql_generate_report"),
    path("checkoutDomain", csrf_exempt(GraphqlCheckoutDomain.as_view()), name="graphql_checkout_domain"),
    path("checkoutServer", csrf_exempt(GraphqlCheckoutServer.as_view()), name="graphql_checkout_server"),
    path("event/domain/update", csrf_exempt(GraphqlDomainUpdateEvent.as_view()), name="graphql_domain_update_event"),
    path(
        "ajax/token/revoke/<int:pk>",
        ApiKeyRevoke.as_view(),
        name="ajax_revoke_token",
    ),
    path(
        "token/create",
        ApiKeyCreate.as_view(),
        name="ajax_create_token",
    ),
]
