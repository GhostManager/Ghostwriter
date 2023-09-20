"""This contains all the database models for the Home application."""

# Standard Libraries
import os

# Django Imports
from django.conf import settings
from django.db import models
from django.templatetags.static import static


# Create your models here.
class UserProfile(models.Model):
    """Stores an individual user profile form, related to :model:`users.User`."""

    def set_upload_destination(self, filename):
        """
        Set the ``upload_to`` destination to the ``user_avatars`` folder for the
        associated :model:`users.User` entry.
        """
        return os.path.join("images", "user_avatars", str(self.user.id), filename)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=set_upload_destination, default=None, blank=True)

    class Meta:

        ordering = ["user"]
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"

    @property
    def avatar_url(self):
        try:
            # Only return the image URL if the file is present
            if os.path.exists(self.avatar.path):
                return self.avatar.url
            return static("images/default_avatar.png")
        except ValueError:
            return static("images/default_avatar.png")
