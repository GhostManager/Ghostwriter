"""This contains customizations for displaying the Home application models in the admin panel."""

# Standard Library Imports
import os

# Django Imports
from django.conf import settings
from django.contrib import admin
from django.urls import reverse
from django.utils.html import format_html

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user",)
    list_filter = ("user",)
    readonly_fields = ("avatar_download_link",)
    search_fields = ("user__username", "user__email")

    class Media:
        js = ('js/admin/userprofile_admin.js',)

    def avatar_download_link(self, obj):
        """Display a download link in the detail view."""
        try:
            file_path = obj.avatar.path
        except ValueError:
            file_path = os.path.join(settings.STATICFILES_DIRS[0], "images/default_avatar.png")

        if os.path.exists(file_path) and obj.avatar and obj.id:
            filename = os.path.basename(obj.avatar.name)
            return format_html(
                '<a href="{url}" download="{filename}">{filename}</a>',
                url=reverse("users:avatar_download", args=[obj.user.username]),
                filename=filename
            )
        return "File missing or not available for download"
    avatar_download_link.short_description = "Download File"
