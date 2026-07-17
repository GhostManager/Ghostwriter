"""This contains all the database models used by the Users application."""

# Standard Libraries
from binascii import hexlify

# Django Imports
from django.contrib.auth.models import AbstractUser
from django.db.models import BooleanField, CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from timezone_field import TimeZoneField

# Roles used for user profiles and JWT authentication
active_roles = (
    ("user", "user"),
    ("manager", "manager"),
    ("admin", "admin"),
)


class User(AbstractUser):
    """Stores an individual user's information."""

    REQUIRED_FIELDS = ["role"]

    # First Name and Last Name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None
    last_name = None
    timezone = TimeZoneField(
        "User's Timezone",
        default="America/Los_Angeles",
        help_text="Primary timezone for this user",
    )
    # The ITU E.164 states phone numbers should not exceed 15 characters
    # We want valid phone numbers, but validating them (here or in forms) is unnecessary
    # Numbers are not used for anything – and any future use would require some human involvement
    # The ``max_length`` allows for people adding spaces, other chars, and extension numbers
    phone = CharField(
        "Phone",
        max_length=50,
        null=True,
        blank=True,
        help_text="Enter a phone number for this user",
    )
    role = CharField(
        max_length=120,
        choices=active_roles,
        default="user",
        help_text="Role used for role-based access controls. Most users should be `user`. Users who need broader access to projects for oversight should be `manager`. See documentation for more details.",
    )
    enable_finding_create = BooleanField(
        default=False,
        help_text="Allow the user to create new findings in the library (only applies to account with the User role)",
        verbose_name="Allow Finding Creation",
    )
    enable_finding_edit = BooleanField(
        default=False,
        help_text="Allow the user to edit findings in the library (only applies to accounts with the User role)",
        verbose_name="Allow Finding Editing",
    )
    enable_finding_delete = BooleanField(
        default=False,
        help_text="Allow the user to delete findings in the library (only applies to accounts with the User role)",
        verbose_name="Allow Finding Deleting",
    )
    enable_observation_create = BooleanField(
        default=False,
        help_text="Allow the user to create new observations in the library (only applies to account with the User role)",
        verbose_name="Allow Observation Creation",
    )
    enable_observation_edit = BooleanField(
        default=False,
        help_text="Allow the user to edit observations in the library (only applies to accounts with the User role)",
        verbose_name="Allow Observation Editing",
    )
    enable_observation_delete = BooleanField(
        default=False,
        help_text="Allow the user to delete observations in the library (only applies to accounts with the User role)",
        verbose_name="Allow Observation Deleting",
    )
    require_mfa = BooleanField(
        # Keep the original database column name for backward compatibility with existing databases
        db_column='require_2fa',
        default=False,
        help_text="Require the user to set up multi-factor authentication",
        verbose_name="Require MFA",
    )

    def get_absolute_url(self):
        return reverse("users:user_detail", args=(self.username,))

    def get_display_name(self):
        """Return a display name appropriate for dropdown menus."""
        if self.name:
            display_name = "{full_name} ({username})".format(full_name=self.name, username=self.username)
        else:
            display_name = self.username.capitalize()

        # Modify display name is the user is disabled.
        if not self.is_active:
            display_name = "DISABLED – " + display_name

        return display_name

    def get_full_name(self):
        """
        Override the default method to return the user's full name. Django uses this to
        display the user's name in different places in the admin site.
        """
        return self.name

    def get_clean_username(self):
        """Return a hex-encoded username to ensure the username is safe for WebSockets channel names."""
        return hexlify(self.username.encode()).decode()

    @property
    def is_privileged(self):
        """
        Verify that the user holds a privileged role or the ``is_staff`` flag.
        """
        return self.role in ("admin", "manager") or self.is_staff

    def save(self, *args, **kwargs):
        # Align Django's permissions flags with the chosen role
        if self.role == "user":
            self.is_staff = False
            self.is_superuser = False

        # Set the `is_staff` and `is_superuser` flags based on the role
        if self.role in ["admin"]:
            self.is_staff = True
            self.is_superuser = True

        # Set the role to admin if the user is a superuser or staff
        if self.is_superuser or self.is_staff:
            self.role = "admin"

        super().save(*args, **kwargs)
