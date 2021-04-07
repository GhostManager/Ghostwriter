"""This contains customizations for displaying the Home application models in the admin panel."""

# Django Imports
from django.contrib import admin

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "avatar")
    list_filter = ("user",)
