"""This contains all the model Signals used by the Home application."""

# Standard Libraries
import logging
import os

# Django Imports
from django.contrib.auth import get_user_model
from django.db.models.signals import post_delete, post_init, post_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile

User = get_user_model()

# Using __name__ resolves to ghostwriter.home.signals
logger = logging.getLogger(__name__)


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Create a new :model:`home.UserProfile` whenever a new :model:`users.User` is created."""
    if created:
        UserProfile.objects.create(user=instance)


@receiver(post_init, sender=UserProfile)
def backup_avatar_path(sender, instance, **kwargs):
    """
    Backup the file path of the old avatar image in the :model:`home.UserProfile`
    instance when a new image is uploaded.
    """
    instance._current_avatar = instance.avatar


@receiver(post_save, sender=UserProfile)
def delete_old_avatar_on_update(sender, instance, **kwargs):
    """
    Delete the old image file in the :model:`home.UserProfile` instance when a
    new image is uploaded.
    """
    if hasattr(instance, "_current_avatar"):
        if instance._current_avatar:
            if instance._current_avatar.path not in instance.avatar.path:
                try:
                    os.remove(instance._current_avatar.path)
                    logger.info("Deleted old avatar image file %s", instance._current_avatar.path)
                except Exception:  # pragma: no cover
                    logger.exception(
                        "Failed deleting old avatar image file: %s",
                        instance._current_avatar.path,
                    )


@receiver(post_delete, sender=UserProfile)
def remove_avatar_on_delete(sender, instance, **kwargs):
    """Deletes file from filesystem when related :model:`home.UserProfile` entry is deleted."""
    if instance.avatar:
        if os.path.isfile(instance.avatar.path):
            os.remove(instance.avatar.path)
