from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

from django.contrib.auth import get_user_model

from ghostwriter.home.models import UserProfile

User = get_user_model()


@receiver(post_save, sender=User)
def create_user_profile(sender, instance, created, **kwargs):
    """Whenever a new `User` model entry is created create a `UserProfile`
    entry.
    """
    if created:
        UserProfile.objects.create(user=instance)
