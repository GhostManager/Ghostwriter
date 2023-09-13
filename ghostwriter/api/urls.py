"""This contains all the URL mappings used by the API application."""

# Django Imports
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

# Ghostwriter Libraries
from ghostwriter.api.views import (
    ApiKeyCreate,
    ApiKeyRevoke,
    GraphqlAttachFinding,
    GraphqlAuthenticationWebhook,
    GraphqlCheckoutDomain,
    GraphqlCheckoutServer,
    GraphqlDeleteEvidenceAction,
    GraphqlDeleteReportTemplateAction,
    GraphqlDomainCheckoutDelete,
    GraphqlDomainUpdateEvent,
    GraphqlEventTestView,
    GraphqlGenerateReport,
    GraphqlLoginAction,
    GraphqlOplogEntryCreateEvent,
    GraphqlOplogEntryDeleteEvent,
    GraphqlOplogEntryUpdateEvent,
    GraphqlReportFindingChangeEvent,
    GraphqlReportFindingDeleteEvent,
    GraphqlServerCheckoutDelete,
    GraphqlTestView,
    GraphqlWhoami,
)

app_name = "api"

urlpatterns = [
    # Actions
    path("test", csrf_exempt(GraphqlTestView.as_view()), name="graphql_test"),
    path("test_event", csrf_exempt(GraphqlEventTestView.as_view()), name="graphql_event_test"),
    path("webhook", csrf_exempt(GraphqlAuthenticationWebhook.as_view()), name="graphql_webhook"),
    path("login", csrf_exempt(GraphqlLoginAction.as_view()), name="graphql_login"),
    path("whoami", csrf_exempt(GraphqlWhoami.as_view()), name="graphql_whoami"),
    path("whoami", csrf_exempt(GraphqlWhoami.as_view()), name="graphql_whoami"),
    path("generateReport", csrf_exempt(GraphqlGenerateReport.as_view()), name="graphql_generate_report"),
    path("checkoutDomain", csrf_exempt(GraphqlCheckoutDomain.as_view()), name="graphql_checkout_domain"),
    path("checkoutServer", csrf_exempt(GraphqlCheckoutServer.as_view()), name="graphql_checkout_server"),
    path(
        "deleteDomainCheckout",
        csrf_exempt(GraphqlDomainCheckoutDelete.as_view()),
        name="graphql_domain_checkout_delete",
    ),
    path(
        "deleteServerCheckout",
        csrf_exempt(GraphqlServerCheckoutDelete.as_view()),
        name="graphql_server_checkout_delete",
    ),
    path("deleteEvidence", csrf_exempt(GraphqlDeleteEvidenceAction.as_view()), name="graphql_delete_evidence"),
    path("deleteTemplate", csrf_exempt(GraphqlDeleteReportTemplateAction.as_view()), name="graphql_delete_template"),
    path("attachFinding", csrf_exempt(GraphqlAttachFinding.as_view()), name="graphql_attach_finding"),
    # Events
    path("event/domain/update", csrf_exempt(GraphqlDomainUpdateEvent.as_view()), name="graphql_domain_update_event"),
    path(
        "event/oplogentry/create",
        csrf_exempt(GraphqlOplogEntryCreateEvent.as_view()),
        name="graphql_oplogentry_create_event",
    ),
    path(
        "event/oplogentry/update",
        csrf_exempt(GraphqlOplogEntryUpdateEvent.as_view()),
        name="graphql_oplogentry_update_event",
    ),
    path(
        "event/oplogentry/delete",
        csrf_exempt(GraphqlOplogEntryDeleteEvent.as_view()),
        name="graphql_oplogentry_delete_event",
    ),
    path(
        "event/report/finding/change",
        csrf_exempt(GraphqlReportFindingChangeEvent.as_view()),
        name="graphql_reportfinding_change_event",
    ),
    path(
        "event/report/finding/delete",
        csrf_exempt(GraphqlReportFindingDeleteEvent.as_view()),
        name="graphql_reportfinding_delete_event",
    ),
    path("ajax/token/revoke/<int:pk>", ApiKeyRevoke.as_view(), name="ajax_revoke_token"),
    path("token/create", ApiKeyCreate.as_view(), name="ajax_create_token"),
]
