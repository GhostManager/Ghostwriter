"""This contains customizations for the models in the Django admin panel."""

from django.contrib import admin

from ghostwriter.home.models import UserProfile


# Define the admin classes and register models
@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'avatar')
    list_filter = ('user',)
