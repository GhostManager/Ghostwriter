"""This contains the ``allauth`` adapters used by the Users application."""

# Standard Libraries
import logging
from typing import Any

# Django Imports
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.http import HttpRequest
from django.shortcuts import redirect

# 3rd Party Libraries
from allauth.account.adapter import DefaultAccountAdapter
from allauth.account.utils import user_email, user_field, user_username
from allauth.exceptions import ImmediateHttpResponse
from allauth.socialaccount.adapter import DefaultSocialAccountAdapter
from allauth.utils import valid_email_or_none

logger = logging.getLogger(__name__)

User = get_user_model()


class AccountAdapter(DefaultAccountAdapter):  # pragma: no cover
    def is_open_for_signup(self, request: HttpRequest):
        return getattr(settings, "ACCOUNT_ALLOW_REGISTRATION", True)


class SocialAccountAdapter(DefaultSocialAccountAdapter):  # pragma: no cover
    def is_open_for_signup(self, request: HttpRequest, sociallogin: Any):
        return getattr(settings, "SOCIAL_ACCOUNT_ALLOW_REGISTRATION", True)

    def authentication_error(self, request, provider_id, error, exception, extra_context):
        logger.error("Error authenticating with social account: %s %s %s", error, exception, extra_context)
        super().authentication_error(request, provider_id, error, exception, extra_context)

    def populate_user(self, request, sociallogin, data):
        username = data.get("username")
        first_name = data.get("first_name")
        last_name = data.get("last_name")
        email = data.get("email")
        name = data.get("name")
        user = sociallogin.user
        user_username(user, username or "")
        user_email(user, valid_email_or_none(email) or "")

        # If the username is the email address, strip the domain
        if username == email:
            user_username(user, username.split("@")[0])

        name_parts = (name or "").partition(" ")
        user_field(user, "first_name", first_name or name_parts[0])
        user_field(user, "last_name", last_name or name_parts[2])

        # Set our custom user fields
        if not name:
            name = f"{first_name} {last_name}".strip()
        user_field(user, "name", name)

        return user

    def pre_social_login(self, request, sociallogin):
        # Check if registration is enabled
        # Otherwise, only allow social logins for existing users
        allow_reg = self.is_open_for_signup(request, sociallogin)

        # Allow social logins only for users who have an account
        try:
            User.objects.get(email=sociallogin.user.email)
        except User.DoesNotExist:
            if allow_reg:
                # TODO: Allow registration of new account from social login
                return
            messages.add_message(request, messages.ERROR, "Social logon from this account is not allowed.")
            return ImmediateHttpResponse(redirect("account_login"))
        except User.MultipleObjectsReturned:
            messages.add_message(
                request,
                messages.ERROR,
                "There are multiple accounts with this email. Please contact your administrator.",
            )
            return ImmediateHttpResponse(redirect("account_login"))
        else:
            user = User.objects.get(email=sociallogin.user.email)
            if not sociallogin.is_existing:
                sociallogin.connect(request, user)

        # TODO: Loop over all email addresses for a user?
        # TODO: Check if the email address is verified?
        # TODO: Implement allowlist for email domains for registration?

        # https://github.com/pennersr/django-allauth/issues/418
