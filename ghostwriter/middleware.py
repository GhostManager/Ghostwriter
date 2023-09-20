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
    ]

    def is_allowed_page(self, request: HttpRequest) -> bool:
        # Allowing `None` allows static URLs for CSS and JS
        return request.resolver_match.url_name in self.allowed_pages or request.resolver_match.url_name is None

    def require_2fa(self, request):
        return request.user.require_2fa
