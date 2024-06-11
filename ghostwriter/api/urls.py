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
    GraphqlDeleteReportTemplateAction,
    GraphqlDomainCheckoutDelete,
    GraphqlDomainUpdateEvent,
    GraphqlEventTestView,
    GraphqlEvidenceUpdateEvent,
    GraphqlGenerateCodenameAction,
    GraphqlGenerateReport,
    GraphqlGetExtraFieldSpecAction,
    GraphqlLoginAction,
    GraphqlOplogEntryCreateEvent,
    GraphqlOplogEntryDeleteEvent,
    GraphqlOplogEntryUpdateEvent,
    GraphqlProjectContactUpdateEvent,
    GraphqlProjectObjectiveUpdateEvent,
    GraphqlProjectSubTaskUpdateEvent,
    GraphqlReportFindingChangeEvent,
    GraphqlReportFindingDeleteEvent,
    GraphqlServerCheckoutDelete,
    GraphqlTestView,
    GraphqlWhoami,
    GraphqlUploadEvidenceView,
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
    path(
        "getExtraFieldSpec", csrf_exempt(GraphqlGetExtraFieldSpecAction.as_view()), name="graphql_get_extra_field_spec"
    ),
    path("generateReport", csrf_exempt(GraphqlGenerateReport.as_view()), name="graphql_generate_report"),
    path("checkoutDomain", csrf_exempt(GraphqlCheckoutDomain.as_view()), name="graphql_checkout_domain"),
    path("checkoutServer", csrf_exempt(GraphqlCheckoutServer.as_view()), name="graphql_checkout_server"),
    path("generateCodename", csrf_exempt(GraphqlGenerateCodenameAction.as_view()), name="graphql_generate_codename"),
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
    path("deleteTemplate", csrf_exempt(GraphqlDeleteReportTemplateAction.as_view()), name="graphql_delete_template"),
    path("attachFinding", csrf_exempt(GraphqlAttachFinding.as_view()), name="graphql_attach_finding"),
    path("uploadEvidence", csrf_exempt(GraphqlUploadEvidenceView.as_view()), name="graphql_upload_evidence"),
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
    path(
        "event/projectcontact/update",
        csrf_exempt(GraphqlProjectContactUpdateEvent.as_view()),
        name="graphql_projectcontact_update_event",
    ),
    path(
        "event/projectobjective/update",
        csrf_exempt(GraphqlProjectObjectiveUpdateEvent.as_view()),
        name="graphql_projectobjective_update_event",
    ),
    path(
        "event/projectsubtask/update",
        csrf_exempt(GraphqlProjectSubTaskUpdateEvent.as_view()),
        name="graphql_projectsubtaske_update_event",
    ),
    path(
        "event/evidence/update",
        csrf_exempt(GraphqlEvidenceUpdateEvent.as_view()),
        name="graphql_evidence_update_event",
    ),
    path("ajax/token/revoke/<int:pk>", ApiKeyRevoke.as_view(), name="ajax_revoke_token"),
    path("token/create", ApiKeyCreate.as_view(), name="ajax_create_token"),
]
