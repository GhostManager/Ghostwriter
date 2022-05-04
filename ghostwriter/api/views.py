"""This contains all of the views used by the API application."""

# Standard Libraries
import json
import logging
from base64 import b64encode
from datetime import datetime

# Django Imports
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import redirect
from django.urls import reverse
from django.views.decorators.http import require_http_methods
from django.views.generic.detail import SingleObjectMixin
from django.views.generic.edit import CreateView, FormView, View

# 3rd Party Libraries
import jwt

# Ghostwriter Libraries
from ghostwriter.api import utils
from ghostwriter.api.forms import ApiKeyForm
from ghostwriter.api.models import APIKey
from ghostwriter.modules.reportwriter import Reportwriter
from ghostwriter.reporting.models import Report
from ghostwriter.shepherd.models import Domain

# Using __name__ resolves to ghostwriter.api.views
logger = logging.getLogger(__name__)


User = get_user_model()


#####################
# GraphQL Functions #
#####################


def graphql_webhook(request):
    """
    Authentication and JWT generation logic for the Hasura ``login`` action.

    If request is authorized, the webhook must return a 200 response code. Any
    unauthorized request must return a 401 response code.

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


@require_http_methods(["POST", ])
def graphql_whoami(request):
    """
    User verification and information look-up for the Hasura ``whoami`` action.

    The ``graphql_webhook`` view is called before this view, so the token will
    have been verified.
    """
    status = 200

    if utils.verify_graphql_request(request.headers):
        # Get the forwarded ``Authorization`` header
        token = utils.get_jwt_from_request(request)
        if token:
            # Use :model:`api:APIKey` object if the token is an API key
            if APIKey.objects.filter(token=token):
                # Token has already been verified by webhook so we can trust it exists and is valid
                entry = APIKey.objects.get(token=token)
                data = {
                    "username": f"{entry.user.username}",
                    "role": f"{entry.user.role}",
                    "expires": f"{entry.expiry_date}",
                }
            # Otherwise, pull user data from JWT payload
            else:
                try:
                    jwt_token = utils.jwt_decode(token)
                    user_obj = utils.get_user_from_token(jwt_token)
                    data = {
                        "username": f"{user_obj.username}",
                        "role": f"{user_obj.role}",
                        "expires": datetime.fromtimestamp(jwt_token["exp"]),
                    }
                except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError, User.DoesNotExist) as exception:
                    status = 401
                    data = utils.generate_hasura_error_payload(f"{type(exception).__name__}", "JWTInvalid")
        else:
            status = 400
            data = utils.generate_hasura_error_payload("No ``Authorization`` header found", "JWTMissing")
    else:
        status = 403
        data = utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized")
    return JsonResponse(data, status=status)


@require_http_methods(["POST", ])
def graphql_domain_update_event(request):
    """Event webhook to fire :model:`shepherd.Domain` signals."""
    status = 200

    if utils.verify_graphql_request(request.headers):
        data = json.loads(request.body)
        object_data = data["event"]["data"]["new"]
        instance = Domain.objects.get(id=object_data["id"])
        instance.save()
    else:
        status = 403
        data = utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized")
    return JsonResponse(data, status=status)


@require_http_methods(["POST", ])
def graphql_generate_report(request):
    """Endpoint for generating a JSON report with the ``generateReport`` action."""
    status = 200

    if utils.verify_graphql_request(request.headers):
        try:
            input = json.loads(request.body)
            report_id = input["input"]["id"]
            report = Report.objects.get(id=report_id)

            token = utils.get_jwt_from_request(request)
            jwt_token = utils.jwt_decode(token)
            user_obj = utils.get_user_from_token(jwt_token)
            if utils.verify_project_access(user_obj, report.project):
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
            else:
                status = 401
                data = utils.generate_hasura_error_payload("Unauthorized access", "Unauthorized")
        except Report.DoesNotExist:
            status = 400
            data = utils.generate_hasura_error_payload("Report does not exist", "ReportDoesNotExist")
        except KeyError:
            status = 400
            data = utils.generate_hasura_error_payload("Invalid request body", "InvalidRequestBody")
    else:
        status = 403
        data = utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized")
    return JsonResponse(data, status=status)


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


################
# View Classes #
################


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
            token_obj, token = APIKey.objects.create_token(name=name, user=self.request.user, expiry_date=expiry)
            messages.info(
                self.request,
                token,
                extra_tags="api-token no-toast",
            )
        except Exception:
            logger.exception("Failed to create new API key")
            messages.error(
                self.request,
                "Could not generate a token for you – contact your admin!",
                extra_tags="alert-danger",
            )
        return super().form_valid(form)
