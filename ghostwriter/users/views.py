"""This contains all the views used by the Users application."""

# Django Imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin, UserPassesTestMixin
from django.shortcuts import get_object_or_404, redirect
from django.urls import reverse, reverse_lazy
from django.views.generic import DetailView, RedirectView, UpdateView

# 3rd Party Libraries
from allauth.account.views import PasswordChangeView, PasswordResetFromKeyView

# Ghostwriter Libraries
from ghostwriter.home.forms import UserProfileForm
from ghostwriter.home.models import UserProfile
from ghostwriter.users.forms import UserChangeForm

User = get_user_model()


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

    def get_object(self, queryset=None):
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

    def get_object(self, queryset=None):
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

    def get_redirect_url(self, *args, **kwargs):
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
