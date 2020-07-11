"""This contains customizations for displaying the Home application models in the admin panel."""

from django.contrib import admin

from ghostwriter.home.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "avatar")
    list_filter = ("user",)
