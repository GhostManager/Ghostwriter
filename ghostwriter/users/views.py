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
from allauth.account.views import PasswordChangeView, PasswordResetFromKeyView

# Ghostwriter Libraries
from ghostwriter import utils
from ghostwriter.home.forms import UserProfileForm
from ghostwriter.home.models import UserProfile
from ghostwriter.users.forms import UserChangeForm

User = get_user_model()


@require_http_methods(["POST", ])
def graphql_login(request):
    """Authentication and JWT generation logic for the ``login`` action."""
    status = 200

    try:
        # Load the request body as JSON
        data = json.loads(request.body)
        data = data["input"]

        # Authenticate the user with Django's back-end
        user = authenticate(**data)
        # A successful auth will return a ``User`` object
        if user:
            payload, jwt_token = utils.generate_jwt_token(user)
            data = {"token": f"{jwt_token}", "expires": payload["exp"]}
        else:
            status = 403
            data = utils.generate_hasura_error_payload("Invalid credentials", "InvalidCredentials")
    except KeyError:
        status = 400
        data = utils.generate_hasura_error_payload("Invalid request body", "InvalidRequestBody")
    return JsonResponse(data, status=status)


@require_http_methods(["POST", ])
def graphql_whoami(request):
    """Authentication and JWT generation logic for the ``login`` action."""
    status = 200

    # Get the forwarded ``Authorization`` header
    token = request.META.get("HTTP_AUTHORIZATION", " ").split(" ")[1]
    if token:
        try:
            # Try to decode the JWT token
            jwt_token = utils.jwt_decode(token)
            data = {
                "username": jwt_token["username"],
                "role": jwt_token["https://hasura.io/jwt/claims"]["x-hasura-default-role"],
                "expires": jwt_token["exp"],
            }
        except Exception as exception:
            status = 403
            data = utils.generate_hasura_error_payload(f"{type(exception).__name__}", "JWTInvalid")
    else:
        status = 400
        data = utils.generate_hasura_error_payload("No ``Authorization`` header found", "JWTMissing")
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

    def get_slug_field(self):
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


class GhostwriterPasswordSetFromKeyView(PasswordResetFromKeyView):
    """
    Reset the password for individual :model:`users.User`.

    **Template**

    :template:`account/password_reset_from_key.html`
    """

    def get_success_url(self):
        return reverse_lazy("account_login")


account_reset_password_from_key = GhostwriterPasswordSetFromKeyView.as_view()
