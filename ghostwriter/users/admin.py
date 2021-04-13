"""This contains customizations for displaying the Users application models in the admin panel."""

# Django Imports
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.users.forms import GroupAdminForm

User = get_user_model()


class UserAdmin(auth_admin.UserAdmin):
    list_display = (
        "name",
        "username",
        "email",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )

    fieldsets = (
        (_("User Information"), {"fields": ("username", "password")}),
        (_("Personal Information"), {"fields": ("name", "email")}),
        (
            _("User Permissions"),
            {
                "fields": (
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (_("Important Dates"), {"fields": ("last_login", "date_joined")}),
    )
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": ("username", "password1", "password2"),
            },
        ),
    )
    search_fields = ("username", "name", "email")
    list_editable = ("is_active",)
    list_display_links = ("name", "username", "email")


admin.site.register(User, UserAdmin)


# Unregister the original Group admin
admin.site.unregister(Group)


class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ["permissions"]


# Register the new Group ModelAdmin
admin.site.register(Group, GroupAdmin)
