# Django Imports
from django.http import HttpRequest, HttpResponse
from django.conf import settings
from django.contrib import messages
from django.shortcuts import redirect
from django.utils.deprecation import MiddlewareMixin

# 3rd Party Libraries
from allauth.mfa.utils import is_mfa_enabled



class RequireMFAMiddleware(MiddlewareMixin):
    allowed_pages = [
        # Allowing changing passwords and logging out without MFA
        "account_change_password",
        "account_logout",
        "account_reset_password",
        # Allow the URLs required to set up multi-factor
        "mfa_activate_totp",
        # Allow the user's avatar to be displayed
        "avatar_download",
    ]

    require_mfa_message = (
        "You must enable multi-factor authentication before doing anything else."
    )

    def on_require_mfa(self, request: HttpRequest) -> HttpResponse:
        """
        If the current request requires MFA and the user does not have it
        enabled, this is executed. The result of this is returned from the
        middleware.
        """
        # See allauth.account.adapter.DefaultAccountAdapter.add_message.
        if "django.contrib.messages" in settings.INSTALLED_APPS:
            # If there is already a pending message related to multi-factor (likely
            # created by a redirect view), simply update the message text.
            storage = messages.get_messages(request)
            tag = "mfa_required"
            for m in storage:
                if m.extra_tags == tag:
                    m.message = self.require_mfa_message
                    break
            # Otherwise, create a new message.
            else:
                messages.error(request, self.require_mfa_message, extra_tags=tag)
            # Mark the storage as not processed so they'll be shown to the user.
            storage.used = False

        # Redirect user to multi-factor setup page.
        return redirect("mfa_activate_totp")

    def is_allowed_page(self, request: HttpRequest) -> bool:
        # Allowing `None` allows static URLs for CSS and JS
        return request.resolver_match.url_name in self.allowed_pages or request.resolver_match.url_name is None

    def require_mfa(self, request):
        # If we only check `require_mfa`, a new user cannot verify their MFA code
        # after creating their account, so we also check if they have a confirmed TOTP device.
        # This forces MFA set up if the box is checked and no device is confirmed while also allowing the user to
        # verify their MFA code after scanning their QR code.
        user = request.user
        return (
            user.require_mfa
            and user.is_authenticated
            and not is_mfa_enabled(user)
        )

    def process_view(
        self,
        request: HttpRequest,
        view_func,
        view_args,
        view_kwargs,
    ) -> HttpResponse | None:
        # The user is not logged in, do nothing.
        if request.user.is_anonymous:
            return None

        # If this doesn't require MFA, then stop processing.
        if not self.require_mfa(request):
            return None

        # If the user is on one of the allowed pages, do nothing.
        if self.is_allowed_page(request):
            return None

        # User already has multi-factor configured, do nothing.
        if is_mfa_enabled(request.user):
            return None

        # The request required MFA but it isn't configured!
        return self.on_require_mfa(request)
    