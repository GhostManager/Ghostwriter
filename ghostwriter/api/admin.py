"""This contains customizations for displaying the GraphQL application models in the admin panel."""

# Standard Libraries
import typing

# Django Imports
from django.contrib import admin, messages
from django.db import models
from django.http.request import HttpRequest

# Ghostwriter Libraries
from ghostwriter.api.models import (
    AbstractAPIKey,
    APIKey,
    ServicePrincipal,
    ServiceToken,
    ServiceTokenPermission,
    UserSession,
)


class APIKeyModelAdmin(admin.ModelAdmin):
    model: typing.Type[AbstractAPIKey]

    list_display = (
        "name",
        "created",
        "expiry_date",
        "_has_expired",
        "revoked",
    )
    list_filter = ("created",)
    readonly_fields = ("identifier", "token_prefix", "secret_hash")
    search_fields = ("name", "token_prefix", "user__username", "user__email")

    def has_add_permission(self, request: HttpRequest) -> bool:
        return False

    def get_readonly_fields(
        self, request: HttpRequest, obj: models.Model = None
    ) -> typing.Tuple[str, ...]:
        obj = typing.cast(AbstractAPIKey, obj)
        fields: typing.Tuple[str, ...]

        fields = self.readonly_fields
        if obj is not None and obj.revoked:
            fields = fields + ("name", "revoked", "expiry_date")

        return fields


admin.site.register(APIKey, APIKeyModelAdmin)


@admin.register(UserSession)
class UserSessionAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "identifier",
        "created",
        "expires_at",
        "revoked_at",
        "is_valid",
    )
    list_filter = ("created", "expires_at", "revoked_at")
    readonly_fields = ("identifier", "created")
    search_fields = ("identifier", "user__username", "user__email")
    actions = ("revoke_sessions",)

    @admin.action(description="Revoke selected user sessions")
    def revoke_sessions(self, request, queryset):
        for session in queryset:
            session.revoke(revoked_by=request.user)


class ServiceTokenPermissionInline(admin.TabularInline):
    model = ServiceTokenPermission
    extra = 0


@admin.register(ServicePrincipal)
class ServicePrincipalAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service_type",
        "created_by",
        "active",
        "created",
    )
    list_filter = ("service_type", "active", "created")
    search_fields = ("name", "created_by__username", "created_by__email")


@admin.register(ServiceToken)
class ServiceTokenAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "service_principal",
        "created_by",
        "created",
        "expiry_date",
        "has_expired",
        "revoked",
        "last_used_at",
        "scope_display",
    )
    list_filter = ("created", "expiry_date", "revoked", "service_principal__service_type")
    search_fields = ("name", "service_principal__name", "created_by__username", "token_prefix")
    readonly_fields = ("token_prefix", "secret_hash", "created", "last_used_at")
    actions = ("revoke_tokens",)
    inlines = (ServiceTokenPermissionInline,)

    @admin.display(boolean=True, description="Has expired")
    def has_expired(self, obj: ServiceToken) -> bool:
        return obj.has_expired

    @admin.display(description="Scope")
    def scope_display(self, obj: ServiceToken) -> str:
        return obj.get_scope_display()

    @admin.action(description="Revoke selected service tokens")
    def revoke_tokens(self, request: HttpRequest, queryset):
        updated = queryset.filter(revoked=False).update(revoked=True)
        self.message_user(request, f"Revoked {updated} service token(s).", level=messages.SUCCESS)
