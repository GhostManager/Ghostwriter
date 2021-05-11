"""This contains all of the model Signals used by the Home application."""

# Django Imports
from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """
    Create a new :model:`home.UserProfile` whenever a new :model:`users.User` is created.
    """
    if created:
        UserProfile.objects.create(user=instance)
