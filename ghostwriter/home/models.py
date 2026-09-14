"""This contains all the database models for the Home application."""

# Standard Libraries
import os

# Django Imports
from django.conf import settings
from django.db import models


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
    hide_quickstart = models.BooleanField(default=False)

    class Meta:

        ordering = ["user"]
        verbose_name = "User profile"
        verbose_name_plural = "User profiles"


class DashboardExceptionDismissal(models.Model):
    """Record a cleared dashboard alert without deleting its task history."""

    task_id = models.CharField(max_length=32, unique=True)
    dismissed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        on_delete=models.SET_NULL,
        related_name="cleared_dashboard_exceptions",
    )
    dismissed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-dismissed_at"]
        verbose_name = "dashboard exception dismissal"
        verbose_name_plural = "dashboard exception dismissals"
