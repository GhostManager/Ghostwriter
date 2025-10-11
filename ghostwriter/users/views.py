"""This contains all the views used by the Users application."""


# Standard Libraries
import os

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import FileResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, RedirectView, UpdateView, View
from django.views.generic.detail import SingleObjectMixin

# 3rd Party Libraries
from allauth.account.views import PasswordChangeView, PasswordResetFromKeyView
from allauth.mfa.recovery_codes.views import GenerateRecoveryCodesView, ViewRecoveryCodesView
from allauth.mfa.recovery_codes.internal import flows

# Ghostwriter Libraries
from ghostwriter.api.utils import RoleBasedAccessControlMixin
from ghostwriter.home.forms import UserProfileForm
from ghostwriter.home.models import UserProfile
from ghostwriter.users.forms import UserChangeForm

User = get_user_model()


class UserDetailView(RoleBasedAccessControlMixin, DetailView):
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

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs.get("username"))

    def get_slug_field(self):  # pragma: no cover``
        return "user__username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(RoleBasedAccessControlMixin, UpdateView):
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
        user = self.get_object()
        return self.request.user.id == user.id

    def handle_no_permission(self):
        if self.request.user.username:
            messages.warning(self.request, "You do not have permission to access that.")
        return redirect("users:redirect")

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("users:user_detail", kwargs={"username": self.request.user.username})
        return ctx

    def get_object(self, queryset=None):
        return get_object_or_404(User, username=self.kwargs.get("username"))

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated your profile!",
            extra_tags="alert-success",
        )
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


user_update_view = UserUpdateView.as_view()


class UserProfileUpdateView(RoleBasedAccessControlMixin, UpdateView):
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
        profile = self.get_object()
        return self.request.user.id == profile.user.id

    def handle_no_permission(self):
        if self.request.user.username:
            messages.warning(self.request, "You do not have permission to access that.")
        return redirect("users:redirect")

    def get_object(self, queryset=None):
        id_ = get_object_or_404(User, username=self.kwargs.get("username")).id
        return get_object_or_404(UserProfile, user_id=id_)

    def get_context_data(self, **kwargs):
        ctx = super().get_context_data(**kwargs)
        ctx["cancel_link"] = reverse("users:user_detail", kwargs={"username": self.request.user.username})
        return ctx

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated your profile!",
            extra_tags="alert-success",
        )
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


userprofile_update_view = UserProfileUpdateView.as_view()


class UserRedirectView(RoleBasedAccessControlMixin, RedirectView):
    """
    Redirect to the details view for an individual :model:`users.User`.

    **Context**

    ``username``
        Username of the current user

    **Template**

    :template:`None`
    """

    permanent = False

    def get_redirect_url(self, *args, **kwargs):
        return reverse("users:user_detail", kwargs={"username": self.request.user.username})


user_redirect_view = UserRedirectView.as_view()


class GhostwriterPasswordChangeView(RoleBasedAccessControlMixin, PasswordChangeView):
    """
    Update an existing password for individual :model:`users.User`.

    **Template**

    :template:`account/password_change.html`
    """

    def get_success_url(self):
        messages.success(
            self.request,
            "Successfully updated your password!",
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


class AvatarDownload(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """
    Return the target :model:`users.User` entries avatar file from
    :model:`home.UserProfile` for download.
    """

    model = UserProfile
    slug_field = "username"
    slug_url_kwarg = "username"

    def get_object(self, queryset=None):
        return get_object_or_404(UserProfile, user__username=self.kwargs.get("slug"))

    def get(self, *args, **kwargs):
        obj = self.get_object()
        try:
            file_path = os.path.join(settings.MEDIA_ROOT, obj.avatar.path)
        except ValueError:
            file_path = os.path.join(settings.STATICFILES_DIRS[0], "images/default_avatar.png")

        if not os.path.exists(file_path):
            file_path = os.path.join(settings.STATICFILES_DIRS[0], "images/default_avatar.png")

        return FileResponse(
            open(file_path, "rb"),
            as_attachment=True,
            filename=os.path.basename(file_path),
        )


avatar_download = AvatarDownload.as_view()


class HideQuickStart(RoleBasedAccessControlMixin, SingleObjectMixin, View):
    """Disable the Quickstart card on the dashboard for the target :model:`users.User` entry."""

    model = UserProfile
    slug_field = "username"
    slug_url_kwarg = "username"

    def test_func(self):
        return self.get_object().user.id == self.request.user.id

    def get_object(self, queryset=None):
        return get_object_or_404(UserProfile, user__username=self.kwargs.get("slug"))

    def post(self, *args, **kwargs):
        obj = self.get_object()
        obj.hide_quickstart = True
        obj.save()
        return JsonResponse({"result": "success"})

hide_quickstart = HideQuickStart.as_view()


class RecoveryCodesView(ViewRecoveryCodesView):
    """Hide the Recovery Codes card on the MFA page"""
    def get_context_data(self, **kwargs):
        ret = super().get_context_data(**kwargs)
        ret.update({"reveal_tokens": settings.MFA_REVEAL_TOKENS})
        return ret

    def post(self, request, *args, **kwargs):
        # Only generate codes if the button was pressed
        flows.generate_recovery_codes(self.request)
        return redirect(GenerateRecoveryCodesView.success_url)
    