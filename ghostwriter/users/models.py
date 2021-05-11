"""This contains all of the database models used by the Users application."""

# Django Imports
from django.contrib.auth.models import AbstractUser
from django.db.models import CharField
from django.urls import reverse
from django.utils.translation import gettext_lazy as _


class User(AbstractUser):
    """
    Stores an individual user's name.
    """

    # First Name and Last Name do not cover name patterns around the globe
    name = CharField(_("Name of User"), blank=True, max_length=255)
    first_name = None
    last_name = None

    def get_absolute_url(self):
        return reverse("users:detail", kwargs={"username": self.username})

    def get_display_name(self):
        """
        Return a display name appropriate for dropdown menus.
        """
        if self.name:
            # Modify display name is the user is disabled
            if self.is_active:
                display_name = "{full_name} ({username})".format(
                    full_name=self.name, username=self.username
                )
            else:
                display_name = "DISABLED – {full_name} ({username})".format(
                    full_name=self.name, username=self.username
                )
        else:
            display_name = self.username.capitalize()
        return display_name
