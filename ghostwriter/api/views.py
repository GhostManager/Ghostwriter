"""This contains all of the views used by the API application."""

# Standard Libraries
import json
import logging
from base64 import b64encode
from datetime import date, datetime

# Django Imports
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import FormView, View

# 3rd Party Libraries
import jwt
from dateutil.parser import parse as parse_date
from dateutil.parser._parser import ParserError

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.forms import ApiKeyForm
from ghostwriter.api.models import APIKey
from ghostwriter.modules.reportwriter import Reportwriter
from ghostwriter.reporting.models import Report
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


class HasuraActionView(View):
    """Custom view class for Hasura Action endpoints."""
    # Default/expected status code for all JSON responses sent to Hasura
    status = 200
    # Allowed HTTP methods for Actions (Hasura will only use POST)
    http_method_names = ["post", ]
    # Inputs expected to receive from Hasura/the end user (default is none)
    required_inputs = []
    # Initialize default class attributes
    input = None
    encodeded_token = None
    decoded_token = None
    user_obj = None

    def setup(self, request, *args, **kwargs):
        # Load JSON data from request body and look for the Hasura ``input`` key
        data = json.loads(request.body)
        if "input" in data:
            self.input = data["input"]
        # Try to pull the JWT from the request header
        self.encoded_token = utils.get_jwt_from_request(request)
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        # Only begin dispatch if the requests checks out as a valid request from Hasura
        if utils.verify_graphql_request(request.headers):
            # Return 400 if no input was found but some input is required
            if not self.input and self.required_inputs:
                return JsonResponse(utils.generate_hasura_error_payload("Invalid request body", "InvalidRequestBody"), status=400)
            # Hasura checks for required values, but we check here in case of a discrepency between the GraphQL schema and the view
            else:
                for required_input in self.required_inputs:
                    if required_input not in self.input:
                        return JsonResponse(utils.generate_hasura_error_payload("Invalid request body", "InvalidRequestBody"), status=400)
            # Only proceed with final dispatch steps if a JWT was acquired
            # Typical requests should never get here without a JWT, but we check anyway for unit testing
            if self.encoded_token:
                # Decode the JWT, store the decoded payload, and resolve the user object
                # Should never fail because the auth webhook does the same, but we check anyway for unit testing
                try:
                    self.decoded_token = utils.jwt_decode(self.encoded_token)
                    self.user_obj = utils.get_user_from_token(self.decoded_token)
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError, User.DoesNotExist) as exception:
                    return JsonResponse(
                        utils.generate_hasura_error_payload(f"{type(exception).__name__}", "JWTInvalid"),
                        status=401
                    )
                return super().dispatch(request, *args, **kwargs)
            else:
                return JsonResponse(
                    utils.generate_hasura_error_payload("No ``Authorization`` header found", "JWTMissing"),
                    status=400
                )
        else:
            return JsonResponse(
                utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized"),
                status=403
            )


class CheckoutView(HasuraActionView):
    """
    Adds a custom ``post()`` method to the ``HasuraActionView`` class for
    ``checkoutDomain`` and ``checkoutServer`` actions. This class uses
    ``model`` and ``status_model`` attributes to determine which models to use
    for the checkout. It then handles the common validation steps for both actions.
    """
    model = None
    object = None
    status_model = None
    unavailable_status = None

    project_id = None
    activity_type = None
    start_date = None
    end_date = None
    note = None

    def post(self, request, *args, **kwargs):
        # Get the :model:`rolodex.Project`` object and verify access
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
                return JsonResponse(utils.generate_hasura_error_payload(f"{self.model.__name__} does not exist", f"{self.model.__name__}DoesNotExist"), status=400)
            # Verify the target object is currently marked as available
            if self.status_model == DomainStatus:
                self.unavailable_status = DomainStatus.objects.get(domain_status="Unavailable")
                if self.object.domain_status == self.unavailable_status:
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Domain is unavailable", "DomainUnavailable"),
                        status=400
                    )
            else:
                self.unavailable_status = ServerStatus.objects.get(server_status="Unavailable")
                if self.object.server_status == self.unavailable_status:
                    return JsonResponse(
                        utils.generate_hasura_error_payload("Server is unavailable", "ServerUnavailable"),
                        status=400
                    )
            # Get the requested :model:`shepherd.ActivityType` object
            activity_id = self.input["activityTypeId"]
            try:
                self.activity_type = ActivityType.objects.get(id=activity_id)
            except ActivityType.DoesNotExist:
                return JsonResponse(utils.generate_hasura_error_payload("Activity Type does not exist", "ActivityTypeDoesNotExist"), status=400)
            # Validate the provided dates are properly formatted and the start date is before the end date
            try:
                self.start_date = parse_date(self.input["startDate"])
                self.end_date = parse_date(self.input["endDate"])
            except ParserError:
                return JsonResponse(
                    utils.generate_hasura_error_payload("Invalid date values (must be YYYY-MM-DD)", "InvalidDates"),
                    status=400
                )
            if self.end_date < self.start_date:
                return JsonResponse(
                    utils.generate_hasura_error_payload("End date is before start date", "InvalidDates"),
                    status=400
                )
            # Set the optinal inputs (keys will not always exist)
            if "note" in self.input:
                self.note = self.input["note"]
        else:
            return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class HasuraEventView(View):
    """Custom view class for Hasura GraphQL Event endpoints."""
    # Default/expected status code for all JSON responses sent to Hasura
    status = 200
    # Allowed HTTP methods for Event triggers (Hasura will only use POST)
    http_method_names = ["post", ]
    # Initialize default class attributes for event data
    old_data = None
    new_data = None

    def setup(self, request, *args, **kwargs):
        self.data = json.loads(request.body)
        if "event" in self.data:
            self.event = self.data["event"]
            self.old_data = self.data["event"]["data"]["old"]
            self.new_data = self.data["event"]["data"]["new"]
        super().setup(request, *args, **kwargs)

    def dispatch(self, request, *args, **kwargs):
        if utils.verify_graphql_request(request.headers):
            return super().dispatch(request, *args, **kwargs)
        else:
            return JsonResponse(
                utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized"),
                status=403
            )


###########################
# Hasura Action Endpoints #
###########################


def graphql_webhook(request):
    """
    Authentication and JWT generation logic for the Hasura ``login`` action.

    If a request is authorized, the webhook must return a 200 response code. Any
    unauthorized requests must return a 401 response code.

    All requests must return the expected Hasura "session variables" (user ID,
    username, and user role) in the payload. Unauthorized requests default to
    using the ``public`` user role with the username ``anonymous`` and user ID
    of ``-1``.

    Ref: https://hasura.io/docs/latest/graphql/core/auth/authentication/webhook.html
    """
    status = 200
    payload = None

    # Response data for an unauthorized request
    role = "public"
    user_id = -1
    username = "anonymous"

    # Get token from ``Authorization`` header
    token = utils.get_jwt_from_request(request)
    # Lack of token means unauthorized and default to ``anonymous`` user
    if token:
        if APIKey.objects.filter(token=token).exists():
            if APIKey.objects.is_valid(token):
                token_entry = APIKey.objects.get(token=token)
                user_id = token_entry.user.id
                role = token_entry.user.role
                username = token_entry.user.username
            else:
                # If invalid, deny any further logic by setting validated to ``False``
                logger.warning(
                    "Received invalid or revoked API token with payload: %s",
                    utils.jwt_decode_no_verification(token)
                )
                status = 401
        else:
            payload = utils.get_jwt_payload(token)
            if payload and "sub" in payload:
                try:
                    user_obj = User.objects.get(id=payload["sub"])
                    if user_obj.is_active:
                        user_id = user_obj.id
                        role = user_obj.role
                        username = user_obj.username
                        status = 200
                    else:
                        status = 401
                except User.DoesNotExist:  # pragma: no cover
                    status = 401
            else:
                status = 401

    # Assemble final authorization data for Hasura
    data = {
        "X-Hasura-Role": f"{role}",
        "X-Hasura-User-Id": f"{user_id}",
        "X-Hasura-User-Name": f"{username}",
    }

    return JsonResponse(data, status=status)


@require_http_methods(["POST", ])
def graphql_login(request):
    """Authentication and JWT generation logic for the Hasura ``login`` action."""
    status = 200

    if utils.verify_graphql_request(request.headers):
        try:
            # Load the request body as JSON
            data = json.loads(request.body)
            data = data["input"]

            # Authenticate the user with Django's back-end
            user = authenticate(**data)
            # A successful auth will return a ``User`` object
            if user:
                payload, jwt_token = utils.generate_jwt(user)
                data = {"token": f"{jwt_token}", "expires": payload["exp"]}
            else:
                status = 401
                data = utils.generate_hasura_error_payload("Invalid credentials", "InvalidCredentials")
        # ``KeyError`` will occur if the request bypasses Hasura
        except KeyError:
            status = 400
            data = utils.generate_hasura_error_payload("Invalid request body", "InvalidRequestBody")
    else:
        status = 403
        data = utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized")
    return JsonResponse(data, status=status)


class GraphqlWhoami(HasuraActionView):
    def post(self, request, *args, **kwargs):
        # Use :model:`api:APIKey` object if the token is an API key
        if APIKey.objects.filter(token=self.encoded_token):
            # Token has already been verified by webhook so we can trust it exists and is valid
            entry = APIKey.objects.get(token=self.encoded_token)
            data = {
                "username": f"{entry.user.username}",
                "role": f"{entry.user.role}",
                "expires": f"{entry.expiry_date}",
            }
        # Otherwise, pull user data from JWT payload
        else:
            data = {
                "username": f"{self.user_obj.username}",
                "role": f"{self.user_obj.role}",
                "expires": datetime.fromtimestamp(self.decoded_token["exp"]),
            }
        return JsonResponse(data, status=self.status)


class GraphqlGenerateReport(HasuraActionView):
    """Endpoint for generating a JSON report with the ``generateReport`` action."""
    required_inputs = ["id", ]

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
        else:
            return JsonResponse(utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized"), status=401)


class GraphqlCheckoutDomain(CheckoutView):
    """Endpoint for reserving a :model:`shepherd.Domain` with the ``checkoutDomain`` action."""
    model = Domain
    status_model = DomainStatus
    required_inputs = ["domainId", "projectId", "activityTypeId", "startDate", "endDate", ]

    def post(self, request, *args, **kwargs):
        # Run validation on the input with in ``CheckoutView.post()``
        result = super().post(request, *args, **kwargs)
        # If validation fails, return the error response
        if result:
            return result
        # Otherwise, continue with the logic specific to this checkout action
        expired = self.object.expiration < date.today()
        if expired:
            return JsonResponse(
                utils.generate_hasura_error_payload("Domain is expired", "DomainExpired"),
                status=400
            )

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
        except ValidationError:
            return JsonResponse(
                utils.generate_hasura_error_payload("Could not create new checkout", "ValidationError"),
                status=422
            )


class GraphqlCheckoutServer(CheckoutView):
    """Endpoint for reserving a :model:`shepherd.StaticServer` with the ``checkoutServer`` action."""
    model = StaticServer
    status_model = ServerStatus
    required_inputs = ["serverId", "projectId", "activityTypeId", "serverRoleId", "startDate", "endDate", ]

    def post(self, request, *args, **kwargs):
        # Run validation on the input with in ``CheckoutView.post()``
        result = super().post(request, *args, **kwargs)
        # If validation fails, return the error response
        if result:
            return result
        role_id = self.input["serverRoleId"]
        try:
            server_role = ServerRole.objects.get(id=role_id)
        except ServerRole.DoesNotExist:
            return JsonResponse(utils.generate_hasura_error_payload("Server Role Type does not exist", "ServerRoleDoesNotExist"), status=400)

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
        except ValidationError:
            return JsonResponse(
                utils.generate_hasura_error_payload("Could not create new checkout", "ValidationError"),
                status=422
            )

##########################
# Hasura Event Endpoints #
##########################


class GraphqlDomainUpdateEvent(HasuraEventView):
    """Event webhook to fire :model:`shepherd.Domain` signals."""
    def post(self, request, *args, **kwargs):
        data = json.loads(request.body)
        instance = Domain.objects.get(id=self.new_data["id"])
        instance.save()
        return JsonResponse(data, status=self.status)


##################
# AJAX Functions #
##################


class ApiKeyRevoke(LoginRequiredMixin, SingleObjectMixin, UserPassesTestMixin, View):
    """
    Revoke an individual :model:`users.APIKey`.
    """

    model = APIKey

    def test_func(self):
        self.object = self.get_object()
        return self.object.user.id == self.request.user.id

    def handle_no_permission(self):
        messages.error(self.request, "You do not have permission to access that")
        return redirect("home:dashboard")

    def post(self, *args, **kwargs):
        self.object = self.get_object()
        self.object.revoked = True
        self.object.save()
        data = {"result": "success", "message": "Token successfully revoked!"}
        logger.info(
            "Revoked %s %s by request of %s",
            self.object.__class__.__name__,
            self.object.id,
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
