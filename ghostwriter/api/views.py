"""This contains all the views used by the API application."""

# Standard Libraries
import json
import logging
from asgiref.sync import async_to_sync
from base64 import b64encode
from datetime import date, datetime
from json import JSONDecodeError

# Django Imports
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView, View

# 3rd Party Libraries
from channels.layers import get_channel_layer
from dateutil.parser import parse as parse_date
from dateutil.parser._parser import ParserError

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.forms import ApiKeyForm
from ghostwriter.api.models import APIKey
from ghostwriter.modules.model_utils import to_dict
from ghostwriter.modules.reportwriter import Reportwriter
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import (
    Evidence,
    Finding,
    Report,
    ReportFindingLink,
    ReportTemplate,
)
from ghostwriter.reporting.views import get_position
from ghostwriter.rolodex.models import Project
from ghostwriter.shepherd.models import (
    ActivityType,
    Domain,
    DomainStatus,
    History,
    ServerHistory,
    ServerRole,
    ServerStatus,
    StaticServer,
)

# Using __name__ resolves to ghostwriter.api.views
logger = logging.getLogger(__name__)

User = get_user_model()


########################
# Custom CBVs & Mixins #
########################


class HasuraView(View):
    """
    Custom view class that handles Ghostwriter's JWT authentication via
    the Hasura GraphQL Engine.
    """

    # Default/expected status code for all JSON responses sent to Hasura
    status = 200
    # Set model for actions that will interact with a specific model
    model = None
    object = None
    # Allowed HTTP methods for Actions (Hasura will only use POST for actions)
    http_method_names = [
        "post",
    ]
    # Initialize default class attributes
    user_obj = None
    encoded_token = None

    def setup(self, request, *args, **kwargs):
        # Try to pull the JWT from the request header
        self.encoded_token = utils.get_jwt_from_request(request)
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Only proceed with final dispatch steps if a JWT was acquired
        if self.encoded_token:
            # Decode the JWT, store the decoded payload, and resolve the user object
            if APIKey.objects.filter(token=self.encoded_token).exists():
                if APIKey.objects.is_valid(self.encoded_token):
                    token_entry = APIKey.objects.get(token=self.encoded_token)
                    self.user_obj = User.objects.get(id=token_entry.user.id)
                else:
                    logger.warning(
                        "Received an invalid or revoked API token: %s",
                        utils.jwt_decode_no_verification(self.encoded_token),
                    )
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Received invalid API token", "JWTInvalid"), status=401
                    )
            else:
                payload = utils.get_jwt_payload(self.encoded_token)
                if payload and "sub" in payload:
                    try:
                        self.user_obj = User.objects.get(id=payload["sub"])
                    except User.DoesNotExist:  # pragma: no cover
                        logger.warning("Received JWT for a user that does not exist: %s", payload)
                        return JsonResponse(
                            utils.generate_hasura_error_payload("Received invalid API token", "JWTInvalid"), status=401
                        )
                else:
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Received invalid API token", "JWTInvalid"), status=401
                    )
            # Only proceed if user is still active
            if not self.user_obj.is_active:
                logger.warning("Received JWT for inactive user: %s", self.user_obj.username)
                return JsonResponse(
                    utils.generate_hasura_error_payload("Received invalid API token", "JWTInvalid"), status=401
                )
        # JWT may be legitimately missing for actions like ``login``, so we proceed with dispatch either way
        return super().dispatch(request, *args, **kwargs)


class JwtRequiredMixin:
    """Mixin for ``HasuraView`` to require a JWT to be present in the request header."""

    def dispatch(self, request, *args, **kwargs):
        # This does not allow the use of Hasura's ``x-hasura-admin-secret`` header in lieu of a JWT
        if self.encoded_token:
            return super().dispatch(request, *args, **kwargs)

        return JsonResponse(
            utils.generate_hasura_error_payload("No ``Authorization`` header found", "JWTMissing"), status=400
        )


class HasuraActionView(HasuraView):
    """
    Custom view class for Hasura Action endpoints. This class adds the following functionality:
    - Validates the request headers contain the Hasura Action secret
    - Validates the JSON data from the request body
    - Ensures a JWT is present
    """

    input = None
    required_inputs = []

    def setup(self, request, *args, **kwargs):
        # Load JSON data from request body and look for the Hasura ``input`` key
        try:
            data = json.loads(request.body)
            if "input" in data:
                self.input = data["input"]
        except JSONDecodeError:
            logger.exception("Failed to decode JSON data from supposed Hasura Action request: %s", request.body)
        return super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # For actions, only proceed if the requests checks out as a valid request from Hasura, and we have a JWT
        if utils.verify_graphql_request(request.headers):
            # Return 400 if no input was found but some input is required
            if not self.input and self.required_inputs:
                return JsonResponse(
                    utils.generate_hasura_error_payload("Missing all required inputs", "InvalidRequestBody"), status=400
                )
            # Hasura checks for required values, but we check here in case of a discrepancy between the GraphQL schema and the view
            for required_input in self.required_inputs:
                if required_input not in self.input:
                    return JsonResponse(
                        utils.generate_hasura_error_payload(
                            "Missing one or more required inputs", "InvalidRequestBody"
                        ),
                        status=400,
                    )
            return super().dispatch(request, *args, **kwargs)

        return JsonResponse(
            utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized"), status=403
        )


class HasuraCheckoutView(JwtRequiredMixin, HasuraActionView):
    """
    Adds a custom ``post()`` method to the ``HasuraActionView`` class for
    ``checkoutDomain`` and ``checkoutServer`` actions. This class adds a
    ``status_model`` attribute to determine which status model to use for
    adjusting the domain or server after checkout. It then handles the
    common validation steps for both actions.
    """

    status_model = None
    unavailable_status = None

    project_id = None
    activity_type = None
    start_date = None
    end_date = None
    note = None

    def post(self, request, *args, **kwargs):
        # Get the :model:`rolodex.Project` object and verify access
        project_id = self.input["projectId"]
        try:
            self.project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)
        if utils.verify_project_access(self.user_obj, self.project):
            # Get the target object – :model:`shepherd.Domain` or :model:`shepherd.StaticServer``
            if "domainId" in self.input:
                object_id = self.input["domainId"]
            else:
                object_id = self.input["serverId"]
            try:
                self.object = self.model.objects.get(id=object_id)
            except (Domain.DoesNotExist, StaticServer.DoesNotExist):
                return JsonResponse(
                    utils.generate_hasura_error_payload(
                        f"{self.model.__name__} does not exist", f"{self.model.__name__}DoesNotExist"
                    ),
                    status=400,
                )
            # Verify the target object is currently marked as available
            if self.status_model == DomainStatus:
                self.unavailable_status = DomainStatus.objects.get(domain_status="Unavailable")
                if self.object.domain_status == self.unavailable_status:
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Domain is unavailable", "DomainUnavailable"), status=400
                    )
            else:
                self.unavailable_status = ServerStatus.objects.get(server_status="Unavailable")
                if self.object.server_status == self.unavailable_status:
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Server is unavailable", "ServerUnavailable"), status=400
                    )
            # Get the requested :model:`shepherd.ActivityType` object
            activity_id = self.input["activityTypeId"]
            try:
                self.activity_type = ActivityType.objects.get(id=activity_id)
            except ActivityType.DoesNotExist:
                return JsonResponse(
                    utils.generate_hasura_error_payload("Activity Type does not exist", "ActivityTypeDoesNotExist"),
                    status=400,
                )
            # Validate the provided dates are properly formatted and the start date is before the end date
            try:
                self.start_date = parse_date(self.input["startDate"])
                self.end_date = parse_date(self.input["endDate"])
            except ParserError:
                return JsonResponse(
                    utils.generate_hasura_error_payload("Invalid date values (must be YYYY-MM-DD)", "InvalidDates"),
                    status=400,
                )
            if self.end_date < self.start_date:
                return JsonResponse(
                    utils.generate_hasura_error_payload("End date is before start date", "InvalidDates"), status=400
                )
            # Set the optional inputs (keys will not always exist)
            if "note" in self.input:
                self.note = self.input["note"]
        else:
            return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class HasuraCheckoutDeleteView(JwtRequiredMixin, HasuraActionView):
    """
    Custom view for deleting checkouts via Hasura Actions. This view handles
    the deletion so Django can fire the ``pre_delete`` signals the
    :model:`shepherd.History` and :model:`shepherd.ServerHistory`.
    """

    required_inputs = [
        "checkoutId",
    ]

    def post(self, request, *args, **kwargs):
        checkout_id = self.input["checkoutId"]
        try:
            instance = self.model.objects.get(id=checkout_id)
        except self.model.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Checkout does not exist", f"{self.model.__name__}DoesNotExist"),
                status=400,
            )
        if utils.verify_project_access(self.user_obj, instance.project):
            # Delete the checkout which triggers the ``pre_delete`` signal
            instance.delete()
            data = {
                "result": "success",
            }
            return JsonResponse(data, status=self.status)

        return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class HasuraEventView(View):
    """Custom view class for Hasura GraphQL Event endpoints."""

    # Default/expected status code for all JSON responses sent to Hasura
    status = 200
    # Allowed HTTP methods for Event triggers (Hasura will only use POST)
    http_method_names = [
        "post",
    ]
    # Initialize default class attributes for event data
    data = None
    old_data = None
    new_data = None

    def setup(self, request, *args, **kwargs):
        try:
            self.data = json.loads(request.body)
            # Ref: https://hasura.io/docs/latest/graphql/core/event-triggers/payload/
            if "event" in self.data:
                self.event = self.data["event"]
                self.old_data = self.data["event"]["data"]["old"]
                self.new_data = self.data["event"]["data"]["new"]
        except JSONDecodeError:
            logger.exception("Failed to decode JSON data from supposed Hasura Event trigger: %s", request.body)
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Return 400 if no input was found
        if not self.data:
            return JsonResponse(
                utils.generate_hasura_error_payload("Missing event data", "InvalidRequestBody"), status=400
            )

        if utils.verify_graphql_request(request.headers):
            return super().dispatch(request, *args, **kwargs)

        return JsonResponse(
            utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized"), status=403
        )


###########################
# Hasura Action Endpoints #
###########################


class GraphqlTestView(JwtRequiredMixin, HasuraActionView):
    """Test view for unit testing views that use ``HasuraView`` or ``HasuraActionView``."""

    required_inputs = [
        "id",
        "function",
        "args",
    ]

    def post(self, request, *args, **kwargs):
        """Test method for unit testing."""
        return JsonResponse({"result": "success"}, status=self.status)


class GraphqlEventTestView(HasuraEventView):
    """Test view for unit testing views that use ``HasuraEventView``."""

    def post(self, request, *args, **kwargs):
        """Test method for unit testing."""
        return JsonResponse({"result": "success"}, status=self.status)


class GraphqlAuthenticationWebhook(HasuraView):
    """
    Authentication webhook for Hasura GraphQL.

    If a request is authorized, the webhook must return a 200 response code. Any
    unauthorized requests must return a 401 response code (handled in ``HasuraView``).

    All requests must return the expected Hasura "session variables" (user ID,
    username, and user role) in the payload. Unauthorized requests default to
    using the ``public`` user role with the username ``anonymous`` and user ID
    of ``-1``.

    Ref: https://hasura.io/docs/latest/graphql/core/auth/authentication/webhook/
    """

    http_method_names = [
        "get",
    ]

    def get(self, request, *args, **kwargs):
        # Default response data for an unauthenticated/anonymous request
        role = "public"
        user_id = -1
        username = "anonymous"

        # A non-null user object means the user has been authenticated in ``HasuraView``
        if self.user_obj:
            user_id = self.user_obj.id
            role = self.user_obj.role
            username = self.user_obj.username

        # Assemble final authorization data for Hasura
        data = {
            "X-Hasura-Role": f"{role}",
            "X-Hasura-User-Id": f"{user_id}",
            "X-Hasura-User-Name": f"{username}",
        }

        return JsonResponse(data, status=200)


class GraphqlLoginAction(HasuraActionView):
    """Authentication and JWT generation logic for the Hasura ``login`` action."""

    required_inputs = [
        "username",
        "password",
    ]

    def post(self, request, *args, **kwargs):
        # Authenticate the user with Django's back-end
        user = authenticate(**self.input)
        # A successful auth will return a ``User`` object
        if user:
            payload, jwt_token = utils.generate_jwt(user)
            data = {"token": f"{jwt_token}", "expires": payload["exp"]}
        else:
            self.status = 401
            data = utils.generate_hasura_error_payload("Invalid credentials", "InvalidCredentials")

        return JsonResponse(data, status=self.status)


class GraphqlWhoami(JwtRequiredMixin, HasuraActionView):
    def post(self, request, *args, **kwargs):
        # Use :model:`api:APIKey` object if the token is an API key
        if APIKey.objects.filter(token=self.encoded_token):
            # Token has already been verified by webhook, so we can trust it exists and is valid
            entry = APIKey.objects.get(token=self.encoded_token)
            expiration = entry.expiry_date
            if expiration is None:
                expiration = "Never"
            data = {
                "username": f"{entry.user.username}",
                "role": f"{entry.user.role}",
                "expires": f"{expiration}",
            }
        # Otherwise, pull user data from JWT payload
        else:
            payload = utils.get_jwt_payload(self.encoded_token)
            data = {
                "username": f"{self.user_obj.username}",
                "role": f"{self.user_obj.role}",
                "expires": datetime.fromtimestamp(payload["exp"]),
            }
        return JsonResponse(data, status=self.status)


class GraphqlGenerateReport(JwtRequiredMixin, HasuraActionView):
    """Endpoint for generating a JSON report with the ``generateReport`` action."""

    required_inputs = [
        "id",
    ]

    def post(self, request, *args, **kwargs):
        report_id = self.input["id"]
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)

        if utils.verify_project_access(self.user_obj, report.project):
            engine = Reportwriter(report, template_loc=None)
            json_report = engine.generate_json()
            report_bytes = json.dumps(json_report).encode("utf-8")
            base64_bytes = b64encode(report_bytes)
            base64_string = base64_bytes.decode("utf-8")
            data = {
                "reportData": base64_string,
                "docxUrl": reverse("reporting:generate_docx", args=[report_id]),
                "xlsxUrl": reverse("reporting:generate_xlsx", args=[report_id]),
                "pptxUrl": reverse("reporting:generate_pptx", args=[report_id]),
            }
            return JsonResponse(data, status=self.status)

        return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class GraphqlCheckoutDomain(HasuraCheckoutView):
    """Endpoint for reserving a :model:`shepherd.Domain` with the ``checkoutDomain`` action."""

    model = Domain
    status_model = DomainStatus
    required_inputs = [
        "domainId",
        "projectId",
        "activityTypeId",
        "startDate",
        "endDate",
    ]

    def post(self, request, *args, **kwargs):
        # Run validation on the input with in ``HasuraCheckoutView.post()``
        result = super().post(request, *args, **kwargs)
        # If validation fails, return the error response
        if result:
            return result
        # Otherwise, continue with the logic specific to this checkout action
        expired = self.object.expiration < date.today()
        if expired:
            return JsonResponse(utils.generate_hasura_error_payload("Domain is expired", "DomainExpired"), status=400)

        try:
            History.objects.create(
                domain=self.object,
                activity_type=self.activity_type,
                start_date=self.start_date,
                end_date=self.end_date,
                note=self.note,
                operator=self.user_obj,
                project=self.project,
                client=self.project.client,
            )

            # Update the domain status and commit it
            self.object.last_used_by = self.user_obj
            self.object.domain_status = self.unavailable_status
            self.object.save()
            data = {
                "result": "success",
            }
            return JsonResponse(data, status=self.status)
        except ValidationError:  # pragma: no cover
            return JsonResponse(
                utils.generate_hasura_error_payload("Could not create new checkout", "ValidationError"), status=422
            )


class GraphqlCheckoutServer(HasuraCheckoutView):
    """Endpoint for reserving a :model:`shepherd.StaticServer` with the ``checkoutServer`` action."""

    model = StaticServer
    status_model = ServerStatus
    required_inputs = [
        "serverId",
        "projectId",
        "activityTypeId",
        "serverRoleId",
        "startDate",
        "endDate",
    ]

    def post(self, request, *args, **kwargs):
        # Run validation on the input with in ``HasuraCheckoutView.post()``
        result = super().post(request, *args, **kwargs)
        # If validation fails, return the error response
        if result:
            return result
        role_id = self.input["serverRoleId"]
        try:
            server_role = ServerRole.objects.get(id=role_id)
        except ServerRole.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Server Role Type does not exist", "ServerRoleDoesNotExist"),
                status=400,
            )

        try:
            ServerHistory.objects.create(
                server=self.object,
                activity_type=self.activity_type,
                start_date=self.start_date,
                end_date=self.end_date,
                server_role=server_role,
                note=self.note,
                operator=self.user_obj,
                project=self.project,
                client=self.project.client,
            )

            # Update the domain status and commit it
            self.object.last_used_by = self.user_obj
            self.object.server_status = self.unavailable_status
            self.object.save()
            data = {
                "result": "success",
            }
            return JsonResponse(data, status=self.status)
        except ValidationError:  # pragma: no cover
            return JsonResponse(
                utils.generate_hasura_error_payload("Could not create new checkout", "ValidationError"), status=422
            )


class GraphqlDomainCheckoutDelete(HasuraCheckoutDeleteView):
    """
    Endpoint for releasing a :model:`shepherd.Domain` when deleting the entry's
    latest :model:`shepherd.History` entry with the `deleteDomainCheckout` action.
    """

    model = History


class GraphqlServerCheckoutDelete(HasuraCheckoutDeleteView):
    """
    Endpoint for releasing a :model:`shepherd.StaticServer` when deleting the entry's
    latest :model:`shepherd.ServerHistory` entry with the `deleteServerCheckout` action.
    """

    model = ServerHistory


class GraphqlDeleteEvidenceAction(JwtRequiredMixin, HasuraActionView):
    """
    Endpoint for deleting an individual :model:`reporting.Evidence` with the
    ``delete_evidence`` action. This is preferable to Hasura's standard delete
    mutation because it ensures Django's ``pre_delete`` and ``post_delete`` signals
    for filesystem clean-up.
    """

    required_inputs = [
        "evidenceId",
    ]

    def post(self, request, *args, **kwargs):
        evidence_id = self.input["evidenceId"]
        try:
            evidence = Evidence.objects.get(id=evidence_id)
        except Evidence.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Evidence does not exist", "EvidenceDoesNotExist"), status=400
            )

        if utils.verify_project_access(self.user_obj, evidence.finding.report.project):
            evidence.delete()
            data = {
                "result": "success",
            }
            return JsonResponse(data, status=self.status)

        return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class GraphqlDeleteReportTemplateAction(JwtRequiredMixin, HasuraActionView):
    """
    Endpoint for deleting an individual :model:`reporting.ReportTemplate` with the
    ``delete_reportTemplate`` action. This is preferable to Hasura's standard delete
    mutation because it ensures Django's ``pre_delete`` and ``post_delete`` signals
    for filesystem clean-up.
    """

    required_inputs = [
        "templateId",
    ]

    def post(self, request, *args, **kwargs):
        template_id = self.input["templateId"]
        try:
            template = ReportTemplate.objects.get(id=template_id)
        except ReportTemplate.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Template does not exist", "ReportTemplateDoesNotExist"), status=400
            )

        if template.protected:
            if not any(
                [
                    self.user_obj.is_staff,
                    self.user_obj.is_superuser,
                    self.user_obj.role == "manager",
                    self.user_obj.role == "admin",
                ]
            ):
                return JsonResponse(
                    utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401
                )

        template.delete()
        data = {
            "result": "success",
        }
        return JsonResponse(data, status=self.status)


class GraphqlAttachFinding(JwtRequiredMixin, HasuraActionView):
    """
    Endpoint for attaching a :model:`reporting.Finding` to a :model:`reporting.Report`
    as a new :model:`reporting.ReportFindingLink`.
    """

    required_inputs = [
        "findingId",
        "reportId",
    ]

    def post(self, request, *args, **kwargs):
        finding_id = self.input["findingId"]
        report_id = self.input["reportId"]
        try:
            report = Report.objects.get(id=report_id)
        except Report.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Report does not exist", "ReportDoesNotExist"), status=400
            )
        try:
            finding = Finding.objects.get(id=finding_id)
        except Finding.DoesNotExist:
            return JsonResponse(
                utils.generate_hasura_error_payload("Finding does not exist", "FindingDoesNotExist"), status=400
            )

        if utils.verify_project_access(self.user_obj, report.project):
            finding_dict = to_dict(finding, resolve_fk=True)
            # Remove the tags from the finding dict to add them later with the ``taggit`` API
            del finding_dict["tags"]
            del finding_dict["tagged_items"]

            report_link = ReportFindingLink(
                report=report,
                assigned_to=self.user_obj,
                position=get_position(report.id, finding.severity),
                **finding_dict,
            )
            report_link.save()
            report_link.tags.add(*finding.tags.all())
            data = {
                "id": report_link.pk,
            }
            return JsonResponse(data, status=self.status)

        return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


##########################
# Hasura Event Endpoints #
##########################


class GraphqlDomainUpdateEvent(HasuraEventView):
    """Event webhook to fire :model:`shepherd.Domain` signals."""

    def post(self, request, *args, **kwargs):
        instance = Domain.objects.get(id=self.new_data["id"])
        instance.save()
        return JsonResponse(self.data, status=self.status)


class GraphqlOplogEntryCreateEvent(HasuraEventView):
    """Event webhook to fire :model:`oplog.OplogEntry` insert signals."""

    def post(self, request, *args, **kwargs):
        instance = OplogEntry.objects.get(id=self.new_data["id"])
        instance.save()
        return JsonResponse(self.data, status=self.status)


class GraphqlOplogEntryUpdateEvent(HasuraEventView):
    """Event webhook to fire :model:`oplog.OplogEntry` update signals."""

    def post(self, request, *args, **kwargs):
        instance = OplogEntry.objects.get(id=self.new_data["id"])
        instance.save()
        return JsonResponse(self.data, status=self.status)


class GraphqlOplogEntryDeleteEvent(HasuraEventView):
    """Event webhook to fire :model:`oplog.OplogEntry` delete signals."""

    def post(self, request, *args, **kwargs):
        channel_layer = get_channel_layer()
        json_message = json.dumps({"action": "delete", "data": self.old_data["id"]})
        async_to_sync(channel_layer.group_send)(
            str(self.old_data["oplog_id_id"]), {"type": "send_oplog_entry", "text": json_message}
        )
        return JsonResponse(self.data, status=self.status)


##################
# AJAX Functions #
##################


class ApiKeyRevoke(LoginRequiredMixin, SingleObjectMixin, UserPassesTestMixin, View):
    """
    Revoke an individual :model:`users.APIKey`.
    """

    model = APIKey

    def test_func(self):
        return self.get_object().user.id == self.request.user.id

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, *args, **kwargs):
        token = self.get_object()
        token.revoked = True
        token.save()
        data = {"result": "success", "message": "Token successfully revoked!"}
        logger.info(
            "Revoked %s %s by request of %s",
            token.__class__.__name__,
            token.id,
            self.request.user,
        )
        return JsonResponse(data)


##################
# API Token Mgmt #
##################


class ApiKeyCreate(LoginRequiredMixin, FormView):
    """
    Create an individual :model:`api.APIKey`.

    **Template**

    :template:`api/token_form.html`
    """

    form_class = ApiKeyForm
    template_name = "token_form.html"

    def get_success_url(self):
        messages.success(
            self.request,
            "Token successfully saved.",
            extra_tags="alert-success",
        )
        return reverse("users:user_detail", kwargs={"username": self.request.user})

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("users:user_detail", kwargs={"username": self.request.user.username})
        return ctx

    def form_valid(self, form):
        name = form.cleaned_data["name"]
        expiry = form.cleaned_data["expiry_date"]
        try:
            _, token = APIKey.objects.create_token(name=name, user=self.request.user, expiry_date=expiry)
            messages.info(
                self.request,
                token,
                extra_tags="api-token no-toast",
            )
        except Exception:  # pragma: no cover
            logger.exception("Failed to create new API key")
            messages.error(
                self.request,
                "Could not generate a token for you – contact your admin!",
                extra_tags="alert-danger",
            )
        return super().form_valid(form)
