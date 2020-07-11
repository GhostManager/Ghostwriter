"""This contains all of the model Signals used by the Home application."""

from django.contrib.auth import get_user_model
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from ghostwriter.home.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a new :model:`home.UserProfile` whenever a new :model:`users.User` is created.
    """
    if created:
        UserProfile.objects.create(user=instance)
