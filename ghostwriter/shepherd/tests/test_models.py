# Standard Libraries
import logging
from datetime import date, timedelta

# Django Imports
from django.db import IntegrityError
from django.test import TestCase

# Ghostwriter Libraries
from ghostwriter.factories import (
    ActivityTypeFactory,
    AuxServerAddressFactory,
    DomainFactory,
    DomainNoteFactory,
    DomainServerConnectionFactory,
    DomainStatusFactory,
    HealthStatusFactory,
    HistoryFactory,
    ServerHistoryFactory,
    ServerNoteFactory,
    ServerProviderFactory,
    ServerRoleFactory,
    ServerStatusFactory,
    StaticServerFactory,
    TransientServerFactory,
    WhoisStatusFactory,
)

logging.disable(logging.CRITICAL)


class HealthStatusModelTests(TestCase):
    """Collection of tests for :model:`shepherd.HealthStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.HealthStatus = HealthStatusFactory._meta.model

    def test_crud(self):
        # Create
        status = HealthStatusFactory(health_status="Healthy")

        # Read
        self.assertEqual(status.health_status, "Healthy")
        self.assertEqual(status.pk, status.id)

        # Update
        status.health_status = "Burned"
        status.save()
        self.assertEqual(status.health_status, "Burned")

        # Delete
        status.delete()
        assert not self.HealthStatus.objects.all().exists()

    def test_prop_count_status(self):
        status = HealthStatusFactory(health_status="Healthy")
        DomainFactory(health_status=status)

        try:
            count = status.count
            self.assertEqual(count, 1)
        except Exception:
            self.fail("HealthStatus model `count` property failed unexpectedly!")


class DomainStatusModelTests(TestCase):
    """Collection of tests for :model:`shepherd.DomainStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.DomainStatus = DomainStatusFactory._meta.model

    def test_crud(self):
        # Create
        status = DomainStatusFactory(domain_status="Available")

        # Read
        self.assertEqual(status.domain_status, "Available")
        self.assertEqual(status.pk, status.id)

        # Update
        status.domain_status = "Unavailable"
        status.save()
        self.assertEqual(status.domain_status, "Unavailable")

        # Delete
        status.delete()
        assert not self.DomainStatus.objects.all().exists()

    def test_prop_count_status(self):
        status = DomainStatusFactory(domain_status="Available")
        DomainFactory(domain_status=status)

        try:
            count = status.count
            self.assertEqual(count, 1)
        except Exception:
            self.fail("DomainStatus model `count` property failed unexpectedly!")


class WhoisStatusModelTests(TestCase):
    """Collection of tests for :model:`shepherd.WhoisStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.WhoisStatus = WhoisStatusFactory._meta.model

    def test_crud(self):
        # Create
        status = WhoisStatusFactory(whois_status="Enabled")

        # Read
        self.assertEqual(status.whois_status, "Enabled")
        self.assertEqual(status.pk, status.id)

        # Update
        status.whois_status = "Unknown"
        status.save()
        self.assertEqual(status.whois_status, "Unknown")

        # Delete
        status.delete()
        assert not self.WhoisStatus.objects.all().exists()

    def test_prop_count_status(self):
        status = WhoisStatusFactory(whois_status="Enabled")
        DomainFactory(whois_status=status)

        try:
            count = status.count
            self.assertEqual(count, 1)
        except Exception:
            self.fail("WhoisStatus model `count` property failed unexpectedly!")


class ActivityTypeModelTests(TestCase):
    """Collection of tests for :model:`shepherd.ActivityType`."""

    @classmethod
    def setUpTestData(cls):
        cls.ActivityType = ActivityTypeFactory._meta.model

    def test_crud(self):
        # Create
        activity_type = ActivityTypeFactory(activity="Phishing")

        # Read
        self.assertEqual(activity_type.activity, "Phishing")
        self.assertEqual(activity_type.pk, activity_type.id)

        # Update
        activity_type.activity = "C2"
        activity_type.save()
        self.assertEqual(activity_type.activity, "C2")

        # Delete
        activity_type.delete()
        assert not self.ActivityType.objects.all().exists()


class DomainModelTests(TestCase):
    """Collection of tests for :model:`shepherd.Domain`."""

    @classmethod
    def setUpTestData(cls):
        cls.Domain = DomainFactory._meta.model

    def test_crud(self):
        # Create
        domain = DomainFactory(name="ghostwriter.wiki")

        # Read
        self.assertEqual(domain.name, "ghostwriter.wiki")
        self.assertEqual(domain.pk, domain.id)

        # Update
        domain.name = "SpecterOps. io"
        domain.save()
        self.assertEqual(domain.name, "specterops.io")

        # Delete
        domain.delete()
        assert not self.Domain.objects.all().exists()

    def test_get_absolute_url(self):
        domain = DomainFactory()
        try:
            domain.get_absolute_url()
        except:
            self.fail("Domain.get_absolute_url() raised an exception")

    def test_method_get_domain_age(self):
        creation = date.today() - timedelta(days=360)
        renewed = date.today() + timedelta(days=359)
        domain = DomainFactory(creation=creation, expiration=renewed, expired=False)

        expired = date.today() - timedelta(days=1)
        expired_domain = DomainFactory(creation=creation, expiration=expired, expired=True, auto_renew=False)

        try:
            age = domain.get_domain_age()
            self.assertEqual(age, 360)

            age = expired_domain.get_domain_age()
            self.assertEqual(age, 359)
        except Exception:
            self.fail("Domain model `get_domain_age` method failed unexpectedly!")

    def test_method_is_expired(self):
        creation = date.today() - timedelta(days=361)
        expiration = date.today() - timedelta(days=1)
        domain = DomainFactory(creation=creation, expiration=expiration, auto_renew=False)

        try:
            self.assertEqual(True, domain.is_expired())

            domain.auto_renew = True
            domain.save()
            self.assertEqual(False, domain.is_expired())

            domain.expiration = date.today() + timedelta(days=1)
            domain.save()
            self.assertEqual(False, domain.is_expired())
        except Exception:
            self.fail("Domain model `is_expired` method failed unexpectedly!")

    def test_method_is_expiring_soon(self):
        creation = date.today() - timedelta(days=345)
        expiration = date.today() + timedelta(days=15)
        domain = DomainFactory(creation=creation, expiration=expiration, auto_renew=False)

        try:
            self.assertEqual(True, domain.is_expiring_soon())

            domain.auto_renew = True
            domain.save()
            self.assertEqual(False, domain.is_expiring_soon())

            domain.expiration = date.today() + timedelta(days=31)
            domain.save()
            self.assertEqual(False, domain.is_expiring_soon())
        except Exception:
            self.fail("Domain model `is_expiring_soon` method failed unexpectedly!")


class HistoryModelTests(TestCase):
    """Collection of tests for :model:`shepherd.History`."""

    @classmethod
    def setUpTestData(cls):
        cls.History = HistoryFactory._meta.model
        cls.available_status = DomainStatusFactory(domain_status="Available")
        cls.unavailable_status = DomainStatusFactory(domain_status="Unavailable")

    def test_crud(self):
        # Create
        entry = HistoryFactory(domain=DomainFactory(name="ghostwriter.wiki"))

        # Read
        self.assertEqual(entry.domain.name, "ghostwriter.wiki")
        self.assertEqual(entry.pk, entry.id)

        # Update
        entry.end_date = date.today()
        entry.save()
        self.assertEqual(entry.end_date, date.today())

        # Delete
        entry.delete()
        assert not self.History.objects.all().exists()

    def test_get_absolute_url(self):
        checkout = HistoryFactory()
        try:
            checkout.get_absolute_url()
        except:
            self.fail("History.get_absolute_url() raised an exception")

    def test_method_will_be_released(self):
        start_date = date.today() - timedelta(days=20)
        end_date = date.today() + timedelta(days=7)
        domain = HistoryFactory(start_date=start_date, end_date=end_date)

        try:
            self.assertEqual(False, domain.will_be_released())

            domain.end_date = date.today()
            domain.save()
            self.assertEqual(True, domain.will_be_released())
        except Exception:
            self.fail("History model `will_be_released` method failed unexpectedly!")

    def test_delete_signal(self):
        domain = DomainFactory(domain_status=self.unavailable_status)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        two_weeks = today + timedelta(days=14)

        history_1 = HistoryFactory(start_date=today, end_date=tomorrow, domain=domain)
        history_2 = HistoryFactory(start_date=next_week, end_date=two_weeks, domain=domain)

        # Deleting this older checkout should not impact the domain's status
        history_1.delete()
        domain.refresh_from_db()
        self.assertTrue(domain.domain_status == self.unavailable_status)

        # Deleting this newer checkout should impact the domain's status
        history_2.delete()
        domain.refresh_from_db()
        self.assertTrue(domain.domain_status == self.available_status)


class ServerStatusModelTests(TestCase):
    """Collection of tests for :model:`shepherd.ServerStatus`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerStatus = ServerStatusFactory._meta.model

    def test_crud(self):
        # Create
        status = ServerStatusFactory(server_status="Available")

        # Read
        self.assertEqual(status.server_status, "Available")
        self.assertEqual(status.pk, status.id)

        # Update
        status.server_status = "Unavailable"
        status.save()
        self.assertEqual(status.server_status, "Unavailable")

        # Delete
        status.delete()
        assert not self.ServerStatus.objects.all().exists()

    def test_prop_count_status(self):
        status = ServerStatusFactory(server_status="Enabled")
        StaticServerFactory(server_status=status)

        try:
            count = status.count
            self.assertEqual(count, 1)
        except Exception:
            self.fail("ServerStatus model `count` property failed unexpectedly!")


class ServerProviderModelTests(TestCase):
    """Collection of tests for :model:`shepherd.ServerProvider`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerProvider = ServerProviderFactory._meta.model

    def test_crud(self):
        # Create
        provider = ServerProviderFactory(server_provider="Digital Ocean")

        # Read
        self.assertEqual(provider.server_provider, "Digital Ocean")
        self.assertEqual(provider.pk, provider.id)

        # Update
        provider.server_provider = "AWS"
        provider.save()
        self.assertEqual(provider.server_provider, "AWS")

        # Delete
        provider.delete()
        assert not self.ServerProvider.objects.all().exists()

    def test_prop_count_status(self):
        provider = ServerProviderFactory(server_provider="AWS")
        StaticServerFactory(server_provider=provider)

        try:
            count = provider.count
            self.assertEqual(count, 1)
        except Exception:
            self.fail("ServerProvider model `count` property failed unexpectedly!")


class ServerRoleModelTests(TestCase):
    """Collection of tests for :model:`shepherd.ServerRole`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerRole = ServerRoleFactory._meta.model

    def test_crud(self):
        # Create
        role = ServerRoleFactory(server_role="Redirector")

        # Read
        self.assertEqual(role.server_role, "Redirector")
        self.assertEqual(role.pk, role.id)

        # Update
        role.server_role = "Payload Delivery"
        role.save()
        self.assertEqual(role.server_role, "Payload Delivery")

        # Delete
        role.delete()
        assert not self.ServerRole.objects.all().exists()


class StaticServerModelTests(TestCase):
    """Collection of tests for :model:`shepherd.StaticServer`."""

    @classmethod
    def setUpTestData(cls):
        cls.StaticServer = StaticServerFactory._meta.model

    def test_crud(self):
        # Create
        server = StaticServerFactory(ip_address="192.168.1.100")

        # Read
        self.assertEqual(server.ip_address, "192.168.1.100")
        self.assertEqual(server.pk, server.id)

        # Update
        server.ip_address = "192.168.2.200"
        server.save()
        self.assertEqual(server.ip_address, "192.168.2.200")

        # Delete
        server.delete()
        assert not self.StaticServer.objects.all().exists()

    def test_get_absolute_url(self):
        server = StaticServerFactory()
        try:
            server.get_absolute_url()
        except:
            self.fail("StaticServer.get_absolute_url() raised an exception")


class TransientServerModelTests(TestCase):
    """Collection of tests for :model:`shepherd.TransientServer`."""

    @classmethod
    def setUpTestData(cls):
        cls.TransientServer = TransientServerFactory._meta.model

    def test_crud(self):
        # Create
        server = TransientServerFactory(ip_address="192.168.1.100")

        # Read
        self.assertEqual(server.ip_address, "192.168.1.100")
        self.assertEqual(server.pk, server.id)

        # Update
        server.ip_address = "192.168.2.200"
        server.save()
        self.assertEqual(server.ip_address, "192.168.2.200")

        # Delete
        server.delete()
        assert not self.TransientServer.objects.all().exists()


class AuxServerAddressModelTests(TestCase):
    """Collection of tests for :model:`shepherd.AuxServerAddress`."""

    @classmethod
    def setUpTestData(cls):
        cls.AuxServerAddress = AuxServerAddressFactory._meta.model

    def test_crud(self):
        # Create
        server = AuxServerAddressFactory(ip_address="192.168.1.100")

        # Read
        self.assertEqual(server.ip_address, "192.168.1.100")
        self.assertEqual(server.pk, server.id)

        # Update
        server.ip_address = "192.168.2.200"
        server.save()
        self.assertEqual(server.ip_address, "192.168.2.200")

        # Delete
        server.delete()
        assert not self.AuxServerAddress.objects.all().exists()


class ServerHistoryModelTests(TestCase):
    """Collection of tests for :model:`shepherd.History`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerHistory = ServerHistoryFactory._meta.model
        cls.available_status = ServerStatusFactory(server_status="Available")
        cls.unavailable_status = ServerStatusFactory(server_status="Unavailable")

    def test_crud(self):
        # Create
        entry = ServerHistoryFactory(server=StaticServerFactory(name="teamserver.local"))

        # Read
        self.assertEqual(entry.server.name, "teamserver.local")
        self.assertEqual(entry.pk, entry.id)

        # Update
        entry.end_date = date.today()
        entry.save()
        self.assertEqual(entry.end_date, date.today())

        # Delete
        entry.delete()
        assert not self.ServerHistory.objects.all().exists()

    def test_get_absolute_url(self):
        checkout = ServerHistoryFactory()
        try:
            checkout.get_absolute_url()
        except:
            self.fail("ServerHistory.get_absolute_url() raised an exception")

    def test_property_ip_address(self):
        entry = ServerHistoryFactory(server=StaticServerFactory(ip_address="192.168.1.100"))

        try:
            self.assertEqual(entry.ip_address, "192.168.1.100")
            entry.server.ip_address = "192.168.2.200"
            entry.server.save()
            self.assertEqual(entry.ip_address, "192.168.2.200")
        except Exception:
            self.fail("ServerHistory model `ip_address` property failed unexpectedly!")

    def test_property_server_name(self):
        entry = ServerHistoryFactory(server=StaticServerFactory(name="teamserver.local"))

        try:
            self.assertEqual(entry.server_name, "teamserver.local")
            entry.server.name = "new-server.local"
            entry.server.save()
            self.assertEqual(entry.server_name, "new-server.local")
        except Exception:
            self.fail("ServerHistory model `server_name` property failed unexpectedly!")

    def test_method_will_be_released(self):
        start_date = date.today() - timedelta(days=20)
        end_date = date.today() + timedelta(days=7)
        entry = ServerHistoryFactory(start_date=start_date, end_date=end_date)

        try:
            self.assertEqual(False, entry.will_be_released())

            entry.end_date = date.today()
            entry.save()
            self.assertEqual(True, entry.will_be_released())
        except Exception:
            self.fail("ServerHistory model `will_be_released` method failed unexpectedly!")

    def test_delete_signal(self):
        server = StaticServerFactory(server_status=self.unavailable_status)

        today = date.today()
        tomorrow = today + timedelta(days=1)
        next_week = today + timedelta(days=7)
        two_weeks = today + timedelta(days=14)

        history_1 = ServerHistoryFactory(start_date=today, end_date=tomorrow, server=server)
        history_2 = ServerHistoryFactory(start_date=next_week, end_date=two_weeks, server=server)

        # Deleting this older checkout should not impact the server's status
        history_1.delete()
        server.refresh_from_db()
        self.assertTrue(server.server_status == self.unavailable_status)

        # Deleting this newer checkout should impact the server's status
        history_2.delete()
        server.refresh_from_db()
        self.assertTrue(server.server_status == self.available_status)


class DomainServerConnectionModelTests(TestCase):
    """Collection of tests for :model:`shepherd.AuxServerAddress`."""

    @classmethod
    def setUpTestData(cls):
        cls.DomainServerConnection = DomainServerConnectionFactory._meta.model

    def test_crud(self):
        # Create
        entry = DomainServerConnectionFactory(subdomain="wiki")

        # Read
        self.assertEqual(entry.subdomain, "wiki")
        self.assertEqual(entry.pk, entry.id)

        server = f"{entry.static_server}{entry.transient_server}"

        # Update
        entry.ip_address = "192.168.2.200"
        entry.save()
        self.assertEqual(entry.ip_address, "192.168.2.200")

        # Delete
        entry.delete()
        assert not self.DomainServerConnection.objects.all().exists()

    def test_selecting_two_servers(self):
        entry = DomainServerConnectionFactory()
        entry.static_server = ServerHistoryFactory()
        entry.transient_server = TransientServerFactory()

        with self.assertRaises(IntegrityError):
            entry.save()

    def test_property_domain_name(self):
        entry = DomainServerConnectionFactory(domain=HistoryFactory(domain=DomainFactory(name="ghostwriter.wiki")))

        try:
            self.assertEqual(entry.domain_name, "ghostwriter.wiki")
            entry.domain.domain.name = "getghostwriter.io"
            entry.domain.domain.save()
            self.assertEqual(entry.domain_name, "getghostwriter.io")
        except Exception:
            self.fail("DomainServerConnection model `domain_name` property failed unexpectedly!")


class DomainNoteModelTests(TestCase):
    """Collection of tests for :model:`shepherd.DomainNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.DomainNote = DomainNoteFactory._meta.model

    def test_crud_note(self):
        # Create
        note = DomainNoteFactory(note="Test note")

        # Read
        self.assertEqual(note.note, "Test note")
        self.assertEqual(note.pk, note.id)
        self.assertEqual(len(self.DomainNote.objects.all()), 1)
        self.assertEqual(self.DomainNote.objects.first(), note)

        # Update
        note.note = "Updated note"
        note.save()
        self.assertEqual(note.note, "Updated note")

        # Delete
        note.delete()
        assert not self.DomainNote.objects.all().exists()


class ServerNoteModelTests(TestCase):
    """Collection of tests for :model:`shepherd.ServerNote`."""

    @classmethod
    def setUpTestData(cls):
        cls.ServerNote = ServerNoteFactory._meta.model

    def test_crud_note(self):
        # Create
        note = ServerNoteFactory(note="Test note")

        # Read
        self.assertEqual(note.note, "Test note")
        self.assertEqual(note.pk, note.id)
        self.assertEqual(len(self.ServerNote.objects.all()), 1)
        self.assertEqual(self.ServerNote.objects.first(), note)

        # Update
        note.note = "Updated note"
        note.save()
        self.assertEqual(note.note, "Updated note")

        # Delete
        note.delete()
        assert not self.ServerNote.objects.all().exists()
