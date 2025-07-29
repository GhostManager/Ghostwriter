# Django Imports
from django.http import HttpRequest

# 3rd Party Libraries
from allauth_2fa.middleware import BaseRequire2FAMiddleware


class Require2FAMiddleware(BaseRequire2FAMiddleware):
    allowed_pages = [
        # Allowing changing passwords and logging out without 2FA
        "account_change_password",
        "account_logout",
        "account_reset_password",
        # Allow the URLs required to set up two-factor
        "two-factor-setup",
        # Allow the user's avatar to be displayed
        "avatar_download",
    ]

    def is_allowed_page(self, request: HttpRequest) -> bool:
        # Allowing `None` allows static URLs for CSS and JS
        return request.resolver_match.url_name in self.allowed_pages or request.resolver_match.url_name is None

    def require_2fa(self, request):
        # If we only check `require_2fa`, a new user cannot verify their 2FA code
        # after creating their account, so we also check if they have a confirmed TOTP device.
        # This forces 2FA set up if the box is checked and no device is confirmed while also allowing the user to
        # verify their 2FA code after scanning their QR code.
        user = request.user
        return (
            user.require_2fa
            and user.is_authenticated
            and not user.totpdevice_set.filter(confirmed=True).exists()
        )
