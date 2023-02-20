"""This contains all the database models used by the Users application."""

# Django Imports
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _

# 3rd Party Libraries
from timezone_field import TimeZoneField

# Roles used for user profiles and JWT authentication
active_roles = (
    ("user", "user"),
    ("manager", "manager"),
    ("admin", "admin"),
    ("restricted", "restricted"),
)


class User(AbstractUser):
    """
    Stores an individual user's name.
    """

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

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def get_display_name(self):
        """
        Return a display name appropriate for dropdown menus.
        """
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
