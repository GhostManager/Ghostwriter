# Standard Libraries
import base64

# Django Imports
from django.test import TestCase
from django.core.management import call_command
from django.contrib.auth import get_user_model

# 3rd Party Libraries
from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from django_otp.plugins.otp_totp.models import TOTPDevice
from django_otp.plugins.otp_static.models import StaticDevice, StaticToken

# Ghostwriter Libraries
from ghostwriter.factories import UserFactory


class CommandMigrate2FAtoMFATests(TestCase):
    def setUp(self):
        self.user = UserFactory()
        # Simulate a TOTPDevice (use a fixed secret for reproducibility)
        self.totp = TOTPDevice.objects.create(
            user=self.user,
            confirmed=True,
            key="3132333435363738393031323334353637383930",  # hex for '12345678901234567890'
            name="default",
        )
        # Simulate StaticDevice + StaticTokens (recovery codes)
        self.static = StaticDevice.objects.create(user=self.user, confirmed=True, name="backup")
        StaticToken.objects.create(device=self.static, token="recovery1")
        StaticToken.objects.create(device=self.static, token="recovery2")

    def testearDown(self):
        Authenticator.objects.all().delete()

    def test_2fa_migration(self):
        # migrate_otp_to_allauth_mfa()
        call_command("migrate_totp_device")

        # TOTP Authenticator
        totp_auths = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.TOTP)
        self.assertEqual(totp_auths.count(), 1)
        adapter = get_adapter()
        # Check the secret was migrated and encrypted
        decrypted_secret = adapter.decrypt(totp_auths[0].data["secret"])
        expected_secret = base64.b32encode(bytes.fromhex(self.totp.key)).decode("ascii")
        self.assertEqual(decrypted_secret, expected_secret)

        # Recovery Codes Authenticator
        recovery_code_auth = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.RECOVERY_CODES)
        self.assertEqual(recovery_code_auth.count(), 1)
        migrated_codes = recovery_code_auth[0].data["migrated_codes"]
        decrypted_codes = [adapter.decrypt(c) for c in migrated_codes]
        self.assertIn("recovery1", decrypted_codes)
        self.assertIn("recovery2", decrypted_codes)

    def test_2fa_migration_idempotency(self):
        # First migration
        call_command("migrate_totp_device")
        totp_auths = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.TOTP)
        recovery_code_auth = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.RECOVERY_CODES)
        self.assertEqual(totp_auths.count(), 1)
        self.assertEqual(recovery_code_auth.count(), 1)

        # Second migration (should not create duplicates)
        call_command("migrate_totp_device")
        totp_auths_2 = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.TOTP)
        recovery_code_auth_2 = Authenticator.objects.filter(user=self.user, type=Authenticator.Type.RECOVERY_CODES)
        self.assertEqual(totp_auths_2.count(), 1)
        self.assertEqual(recovery_code_auth_2.count(), 1)