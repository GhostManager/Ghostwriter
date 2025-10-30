"""This contains customizations for displaying the Users application models in the admin panel."""

# Django Imports
from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model
from django.contrib.auth.models import Group
from django.contrib.sessions.models import Session
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.home.models import UserProfile
from ghostwriter.users.forms import GroupAdminForm

User = get_user_model()


class SessionAdmin(admin.ModelAdmin):
    def _session_data(self, obj):
        return obj.get_decoded()

    list_display = ["session_key", "_session_data", "expire_date"]


admin.site.register(Session, SessionAdmin)


class AdminProfileInline(admin.StackedInline):
    model = UserProfile
    can_delete = False
    verbose_name_plural = "User profiles"


class UserAdmin(auth_admin.UserAdmin):
    list_display = (
        "name",
        "username",
        "email",
        "role",
        "require_mfa",
        "last_login",
        "is_active",
    )
    list_filter = ("role",)

    fieldsets = (
        (_("User Information"), {"fields": ("username", "password", "require_mfa")}),
        (_("Personal Information"), {"fields": ("name", "email", "phone", "timezone")}),
        (
            _("User Permissions"),
            {
                "fields": (
                    "role",
                    "is_active",
                    "is_staff",
                    "is_superuser",
                ),
            },
        ),
        (
            _("Permission Augmentation"),
            {
                "fields": (
                    "enable_finding_create",
                    "enable_finding_edit",
                    "enable_finding_delete",
                    "enable_observation_create",
                    "enable_observation_edit",
                    "enable_observation_delete",
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
    list_editable = (
        "is_active",
        "require_mfa",
    )
    list_display_links = ("name", "username", "email")
    inlines = (AdminProfileInline,)


admin.site.register(User, UserAdmin)

# Unregister the original Group admin
admin.site.unregister(Group)


class GroupAdmin(admin.ModelAdmin):
    form = GroupAdminForm
    filter_horizontal = ["permissions"]


# Register the new Group ModelAdmin
admin.site.register(Group, GroupAdmin)
