# Standard Libraries
import logging

# Django Imports
from django.core.validators import validate_email
from django.db import IntegrityError, transaction
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    AdminFactory,
    ClientFactory,
    DomainFactory,
    MgrFactory,
    StaticServerFactory,
    UserFactory,
)

logging.disable(logging.CRITICAL)


class FactoryIdentityTests(TestCase):
    """Tests for deterministic, collision-safe factory identities."""

    def test_generated_identity_fields_are_unique(self):
        users = UserFactory.create_batch(10)
        clients = ClientFactory.create_batch(5)
        domains = DomainFactory.create_batch(5)
        servers = StaticServerFactory.create_batch(5)

        self.assertEqual(len({user.username for user in users}), len(users))
        self.assertEqual(len({client.name for client in clients}), len(clients))
        self.assertEqual(len({domain.name for domain in domains}), len(domains))
        self.assertEqual(len({server.ip_address for server in servers}), len(servers))

    def test_explicit_duplicate_identities_fail_loudly(self):
        cases = (
            (UserFactory, {"username": "duplicate-user"}),
            (ClientFactory, {"name": "Duplicate Client"}),
            (DomainFactory, {"name": "duplicate.example.com"}),
            (StaticServerFactory, {"ip_address": "192.0.2.10"}),
        )

        for factory_class, identity in cases:
            with self.subTest(factory=factory_class.__name__):
                factory_class(**identity)
                with self.assertRaises(IntegrityError):
                    with transaction.atomic():
                        factory_class(**identity)

    def test_explicit_username_does_not_corrupt_generated_email(self):
        user = UserFactory(username="benny@ghostwriter.wiki")

        validate_email(user.email)
        self.assertEqual(user.email.count("@"), 1)

    def test_role_factories_preserve_requested_roles(self):
        user = UserFactory()
        manager = MgrFactory()
        admin = AdminFactory()

        self.assertEqual(user.role, "user")
        self.assertFalse(user.is_privileged)
        self.assertEqual(manager.role, "manager")
        self.assertFalse(manager.is_staff)
        self.assertTrue(manager.is_privileged)
        self.assertEqual(admin.role, "admin")
        self.assertTrue(admin.is_staff)
        self.assertTrue(admin.is_superuser)
        self.assertTrue(admin.is_privileged)
