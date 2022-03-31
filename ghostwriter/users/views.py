"""This contains all of the views used by the Users application."""

# Standard Libraries
import json

# Django Imports
from django.contrib import messages
from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.decorators.http import require_http_methods
from django.views.generic import DetailView, RedirectView, UpdateView

# 3rd Party Libraries
import jwt
from allauth.account.views import PasswordChangeView, PasswordResetFromKeyView

# Ghostwriter Libraries
from ghostwriter import utils
from ghostwriter.home.forms import UserProfileForm
from ghostwriter.home.models import UserProfile
from ghostwriter.users.forms import UserChangeForm

User = get_user_model()


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
    role = "public"
    user_id = -1
    username = "anonymous"
    payload = None

    token = utils.get_jwt_from_request(request)
    if token:
        # Attempt to decode and verify the payload
        payload = utils.get_jwt_payload(token)
        # Successful verification returns not ``None``
        if payload:
            # Verify the proper Hasura claims are present
            if utils.verify_hasura_claims(payload):
                # Verify the user is still active
                if utils.verify_jwt_user(payload["https://hasura.io/jwt/claims"]):
                    role = payload["https://hasura.io/jwt/claims"]["X-Hasura-Role"]
                    user_id = payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Id"]
                    username = payload["https://hasura.io/jwt/claims"]["X-Hasura-User-Name"]
                    status = 200
                else:
                    status = 401
            else:
                status = 401
        else:
            status = 401

    # Assemble final authorization data
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
    """User verification and information look-up for the Hasura ``whoami`` action."""
    status = 200

    if utils.verify_graphql_request(request.headers):
        # Get the forwarded ``Authorization`` header
        token = utils.get_jwt_from_request(request)
        if token:
            try:
                # Try to decode the JWT token
                jwt_token = utils.jwt_decode(token)
                data = {
                    "username": jwt_token["username"],
                    "role": jwt_token["https://hasura.io/jwt/claims"]["X-Hasura-Role"],
                    "expires": jwt_token["exp"],
                }
            except (jwt.ExpiredSignatureError, jwt.InvalidTokenError, jwt.DecodeError) as exception:
                status = 401
                data = utils.generate_hasura_error_payload(f"{type(exception).__name__}", "JWTInvalid")
        else:
            status = 400
            data = utils.generate_hasura_error_payload("No ``Authorization`` header found", "JWTMissing")
    else:
        status = 403
        data = utils.generate_hasura_error_payload("Unauthorized access method", "Unauthorized")
    return JsonResponse(data, status=status)


class UserDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`users.User`.

    **Template**

    :template:`users/profile.html`
    """

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"
    template_name = "users/profile.html"

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        return ctx

    def get_object(self):
        return get_object_or_404(User, username=self.kwargs.get("username"))

    def get_slug_field(self):  # pragma: no cover``
        return "user__username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Update details for an individual :model:`users.User`.

    **Context**

    ``form``
        A single ``UserChangeForm`` form.
    ``cancel_link``
        Link for the form's Cancel button to return to user's profile page

    **Template**

    :template:`users/profile_form.html`
    """
    model = User
    form_class = UserChangeForm
    template_name = "users/profile_form.html"

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.id == self.object.id

    def handle_no_permission(self):
        if self.request.user.username:
            messages.warning(self.request, "You do not have permission to access that")
            return redirect("users:redirect")
        return redirect("home:dashboard")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("users:user_detail", kwargs={"username": self.request.user.username})
        return ctx

    def get_object(self):
        return get_object_or_404(User, username=self.kwargs.get("username"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated your profile",
            extra_tags="alert-success",
        )
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


user_update_view = UserUpdateView.as_view()


class UserProfileUpdateView(LoginRequiredMixin, UserPassesTestMixin, UpdateView):
    """
    Update a :model:`home.UserProfile` for an individual :model:`users.User`.

    **Context**

    ``form``
        A single ``UserProfileForm`` form.
    ``cancel_link``
        Link for the form's Cancel button to return to user's profile page

    **Template**

    :template:`users/profile_form.html`
    """

    model = UserProfile
    form_class = UserProfileForm
    template_name = "users/profile_form.html"

    def test_func(self):
        self.object = self.get_object()
        return self.request.user.id == self.object.user.id

    def handle_no_permission(self):
        if self.request.user.username:
            messages.warning(self.request, "You do not have permission to access that")
            return redirect("users:redirect")
        return redirect("home:dashboard")

    def get_object(self):
        id_ = get_object_or_404(User, username=self.kwargs.get("username")).id
        return get_object_or_404(UserProfile, user_id=id_)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("users:user_detail", kwargs={"username": self.request.user.username})
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated your profile",
            extra_tags="alert-success",
        )
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


userprofile_update_view = UserProfileUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirect to the details view for an individual :model:`users.User`.

    **Context**

    ``username``
        Username of the current user

    **Template**

    :template:`None`
    """

    permanent = False

    def get_redirect_url(self):
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


class GhostwriterPasswordChangeView(LoginRequiredMixin, PasswordChangeView):
    """
    Update an existing password for individual :model:`users.User`.

    **Template**

    :template:`account/password_change.html`
    """

    def get_success_url(self):
        messages.success(
            self.request,
            "Your password was successfully updated!",
            extra_tags="alert-success",
        )
        return reverse_lazy("users:user_detail", kwargs={"username": self.request.user.username})


account_change_password = GhostwriterPasswordChangeView.as_view()


class GhostwriterPasswordSetFromKeyView(PasswordResetFromKeyView):  # pragma: no cover
    """
    Reset the password for individual :model:`users.User`.

    **Template**

    :template:`account/password_reset_from_key.html`
    """

    def get_success_url(self):
        return reverse_lazy("account_login")


account_reset_password_from_key = GhostwriterPasswordSetFromKeyView.as_view()
