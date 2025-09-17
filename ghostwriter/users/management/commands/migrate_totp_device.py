import base64
import logging

from allauth.mfa.adapter import get_adapter
from allauth.mfa.models import Authenticator
from django.core.management.base import BaseCommand
from django_otp.plugins.otp_static.models import StaticDevice
from django_otp.plugins.otp_totp.models import TOTPDevice

logger = logging.getLogger(__name__)

class Command(BaseCommand):
    help = "Migrate existing TOTP devices to allauth.mfa authenticators"

    def handle(self, *args, **options):
        adapter = get_adapter()
        authenticators = []

        # Statistics
        users_total = TOTPDevice.objects.filter(confirmed=True).values('user_id').distinct().count()
        users_migrated = 0
        users_skipped = 0
        errors = 0

        logger.info(f"found {users_total} users with TOTP devices to migrate.")

        for totp in TOTPDevice.objects.filter(confirmed=True).iterator():
            try:
                user_exists = Authenticator.objects.filter(
                    user_id=totp.user_id, type=Authenticator.Type.TOTP
                ).exists()

                if user_exists:
                    users_skipped += 1
                    logger.info(f"Skipping user {totp.user_id}, already has TOTP authenticator.")
                    continue

                # Collect recovery codes for this user
                recovery_codes = set()
                for sdevice in StaticDevice.objects.filter(
                    confirmed=True, user_id=totp.user_id
                ).iterator():
                    recovery_codes.update(sdevice.token_set.values_list("token", flat=True))

                # Convert secret to correct format
                secret = base64.b32encode(bytes.fromhex(totp.key)).decode("ascii")

                # Create authenticators for this user
                authenticators = [
                    Authenticator(
                        user_id=totp.user_id,
                        type=Authenticator.Type.TOTP,
                        data={"secret": adapter.encrypt(secret)},
                    ),
                    Authenticator(
                        user_id=totp.user_id,
                        type=Authenticator.Type.RECOVERY_CODES,
                        data={
                            "migrated_codes": [adapter.encrypt(c) for c in recovery_codes],
                        },
                    )
                ]

                # Bulk create authenticators
                Authenticator.objects.bulk_create(authenticators)
                users_migrated += 1

            except (ValueError, TypeError) as e:
                # For errors in data conversion or formatting
                errors += 1
                logger.error(f"Error in data conversion for user {totp.user_id}: {str(e)}")
            except Authenticator.DoesNotExist as e:
                # For database lookup errors
                errors += 1
                logger.error(f"Authenticator not found for user {totp.user_id}: {str(e)}")
            except Authenticator.MultipleObjectsReturned as e:
                # For unexpected database state
                errors += 1
                logger.error(f"Multiple authenticators found for user {totp.user_id}: {str(e)}")
            except (IOError, OSError) as e:
                # For file system errors (if any)
                errors += 1
                logger.error(f"I/O error for user {totp.user_id}: {str(e)}")

        # Report results
        logger.info("\nMigration Summary:")
        logger.info(f"Total users processed: {users_total}")
        logger.info(f"Users migrated: {users_migrated}")
        logger.info(f"Users skipped (already migrated): {users_skipped}")
        logger.info(f"Errors: {errors}")
