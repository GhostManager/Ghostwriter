"""This contains all of the views used by the Users application."""

# Django Imports
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse, reverse_lazy
from django.utils.translation import gettext_lazy as _
from django.views.generic import DetailView, RedirectView, UpdateView

# 3rd Party Libraries
from allauth.account.views import PasswordChangeView, PasswordResetFromKeyView

User = get_user_model()


class UserDetailView(LoginRequiredMixin, DetailView):
    """
    Display an individual :model:`users.User`.

    **Context**

    ``context``
        description.

    **Template**

    :template:`None`
    """

    model = User
    slug_field = "username"
    slug_url_kwarg = "username"


user_detail_view = UserDetailView.as_view()


class UserUpdateView(LoginRequiredMixin, UpdateView):
    """
    Update an individual :model:`users.User`.

    **Template**

    :template:`None`
    """

    model = User
    fields = ["name"]

    def get_success_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})

    def get_object(self):
        return User.objects.get(username=self.request.user.username)

    def form_valid(self, form):
        messages.add_message(self.request, messages.INFO, _("Infos successfully updated"))
        return super().form_valid(form)


user_update_view = UserUpdateView.as_view()


class UserRedirectView(LoginRequiredMixin, RedirectView):
    """
    Redirect to the details view for an individual :model:`users.User`.

    **Context**

    ``username``
        Username of the current user.

    **Template**

    :template:`None`
    """

    permanent = False

    def get_redirect_url(self):
        return reverse("users:detail", kwargs={"username": self.request.user.username})


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
        return reverse_lazy("home:profile")


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
