"""This contains the ``allauth`` adapters used by the Users application."""

# Standard Libraries
import logging
from typing import Any

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.core.validators import validate_email
from django.http import HttpRequest
from django.shortcuts import redirect

# 3rd Party Libraries
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field, user_username
from allauth.core.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter

logger = logging.getLogger(__name__)

User = get_user_model()

#
class AccountAdapter(DefaultAccountAdapter):  # pragma: no cover
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)


class SocialAccountAdapter(DefaultSocialAccountAdapter):  # pragma: no cover
    """
    Custom adapter for social accounts. This adapter implements an allowlist for domain registration. It also populates
    some user fields not populated by default (e.g., the user's full name).
    """

    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        u = sociallogin.user
        allow_reg = getattr(settings, "SOCIAL_ACCOUNT_ALLOW_REGISTRATION", True)
        allowlist = getattr(settings, "SOCIAL_ACCOUNT_DOMAIN_ALLOWLIST", "")

        # If the allowlist isn't empty, split it into a list
        if allowlist:
            # If the allowlist is a string, split it into a list
            # This supports ``SOCIAL_ACCOUNT_DOMAIN_ALLOWLIST`` being set in a Python config file as a list
            if isinstance(allowlist, str):
                allowlist = allowlist.split()
        # If registration is allowed, check the email domain
        if allow_reg:
            if allowlist and u.email.rpartition("@")[-1] in allowlist:
                return True
            if not allowlist:
                return True
        # Registration is not allowed
        return False

    def authentication_error(
        self, request, provider_id, error, exception, extra_context
    ):
        logger.error(
            "Error authenticating with social account: %s %s %s",
            error,
            exception,
            extra_context,
        )
        super().on_authentication_error(
            request, provider_id, error, exception, extra_context
        )

    def populate_user(self, request, sociallogin, data):
        username = data.get("username") or sociallogin.account.extra_data.get(
            "username"
        )
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        name = data.get("name")

        # If no username or the username is the email address
        # Use the email address but strip the domain
        if username is None or (username == email):
            username = email.split("@")[0]

        user = sociallogin.user
        user_username(user, username or "")
        user_email(user, validate_email(email) or "")

        name_parts = (name or "").partition(" ")
        user_field(user, "first_name", first_name or name_parts[0])
        user_field(user, "last_name", last_name or name_parts[2])

        # Set our custom user fields
        if not name:
            name = f"{first_name} {last_name}".strip()
        user_field(user, "name", name)

        return user

    def pre_social_login(self, request, sociallogin):
        # The following pre-login checks look at the user's primary email address
        # If multiple accounts share the same email address, the SSO login is aborted with an error message

        # Allow social logins only for users who have an account
        email = sociallogin.user.email
        try:
            User.objects.get(email=email)
        except User.DoesNotExist:
            # If the user doesn't exist, do nothing right now
            pass
        except User.MultipleObjectsReturned:
            # ``django-allauth`` will default to connecting the oldest account when multiple accounts share an address
            # This is not the desired behavior for Ghostwriter, so we'll abort the login process
            logger.error("Multiple accounts found with email %s", email)
            messages.add_message(
                request,
                messages.ERROR,
                "There are multiple pre-existing accounts with this email. Please contact your administrator.",
            )
            raise ImmediateHttpResponse(redirect("account_login"))
        except Exception as e:
            logger.error("Error during social login: %s", e)
            messages.add_message(
                request,
                messages.ERROR,
                "There was an error processing the login from this provider. Please contact your administrator.",
            )
            raise ImmediateHttpResponse(redirect("account_login"))
