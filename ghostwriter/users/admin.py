from django.contrib import admin
from django.contrib.auth import admin as auth_admin
from django.contrib.auth import get_user_model

from ghostwriter.users.forms import UserChangeForm, UserCreationForm

User = get_user_model()


class UserAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "username",
        "email",
        # "verified_email",
        "is_active",
        "is_staff",
        "is_superuser",
        "last_login",
        "password"
    )
    list_filter = (
        "is_active",
        "is_staff",
        "is_superuser",
    )
    readonly_fields = (
        "last_login",
        # "password",
        "date_joined",
        "user_permissions",
        # "activation_code",
    )
    list_editable = ("is_active",)
    search_fields = ("email",)
    fieldsets = (
        (
            None,
            {"fields": ("name", "username", "email",
                        "password", "is_active",
                        "last_login")},
        ),
        (
            "Advanced options",
            {
                "classes": ("collapse",),
                "fields": ("is_staff", "is_superuser",),
            },
        ),
    )


admin.site.register(User, UserAdmin)

# @admin.register(User)
# class UserAdmin(auth_admin.UserAdmin):

#     form = UserChangeForm
#     add_form = UserCreationForm
#     fieldsets = (("User", {"fields": ("name",)}),) + auth_admin.UserAdmin.fieldsets
#     list_display = ["username", "name", "is_superuser"]
#     search_fields = ["name"]
