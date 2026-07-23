# Standard Libraries
from datetime import timedelta
from io import StringIO

# Django Imports
from django.contrib.sessions.models import Session
from django.core.management import call_command
from django.test import TestCase
from django.utils import timezone

# Ghostwriter Libraries
from ghostwriter.api.models import UserSession
from ghostwriter.factories import UserFactory


class ClearExpiredSessionsCommandTests(TestCase):
    """Collection of tests for the clear_expired_sessions management command."""

    @classmethod
    def setUpTestData(cls):
        cls.user = UserFactory()

    def test_clears_expired_django_and_graphql_login_sessions(self):
        yesterday = timezone.now() - timedelta(days=1)
        tomorrow = timezone.now() + timedelta(days=1)
        expired_session, _, _ = UserSession.objects.create_token(
            self.user,
            expires_at=yesterday,
        )
        active_session, _, _ = UserSession.objects.create_token(
            self.user,
            expires_at=tomorrow,
        )
        Session.objects.create(
            session_key="expired-session",
            session_data="",
            expire_date=yesterday,
        )
        Session.objects.create(
            session_key="active-session",
            session_data="",
            expire_date=tomorrow,
        )

        stdout = StringIO()
        call_command("clear_expired_sessions", stdout=stdout)

        self.assertFalse(UserSession.objects.filter(pk=expired_session.pk).exists())
        self.assertTrue(UserSession.objects.filter(pk=active_session.pk).exists())
        self.assertFalse(Session.objects.filter(session_key="expired-session").exists())
        self.assertTrue(Session.objects.filter(session_key="active-session").exists())
        self.assertIn(
            "Cleared 1 expired GraphQL login session(s).",
            stdout.getvalue(),
        )
