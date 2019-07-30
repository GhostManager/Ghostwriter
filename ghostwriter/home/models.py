"""This contains all of the database models for the Home application."""

import os

from django.conf import settings
from django.db import models
from django.templatetags.static import static


# Create your models here.
class UserProfile(models.Model):
    """Model expanding the Django `User` model to add support for user avatars
    and additional information.

    There is a foreign key for the `User` model.
    """
    def set_upload_destination(instance, filename):
        """Sets the `upload_to` destination to the user_avatars folder for the
        associated user ID.
        """
        return os.path.join('images', 'user_avatars', str(instance.user.id), filename)

    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    avatar = models.ImageField(upload_to=set_upload_destination,
                               default=None)

    class Meta:
        """Metadata for the model."""
        ordering = ['user']
        verbose_name = 'User profile'
        verbose_name_plural = 'User profiles'

    def save(self, *args, **kwargs):
        """Override the `save()` method to delete the current avatar when
        uploading a replacement.
        """
        if self.avatar.name is not None:
            try:
                os.remove(self.avatar.path)
            except OSError as e:
                print("Error removing existing avatar. {}".format(e))
                pass
            except ValueError as e:
                print("Somehow had an issue with the avatar value.  Passing on the error. {}".format(e))
                pass
        super(UserProfile, self).save(*args, **kwargs)

    @property
    def avatar_url(self):
        try:
            return self.avatar.url
        except ValueError:
            return static('images/default_avatar.png')

    # @receiver(post_save, sender=User)
    # def create_user_profile(sender, instance, created, **kwargs):
    #     """Whenever a new `User` model entry is created create a `UserProfile`
    #     entry.
    #     """
    #     if created:
    #         UserProfile.objects.create(user=instance)
