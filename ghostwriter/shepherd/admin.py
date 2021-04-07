"""This contains customizations for displaying the Shepherd application models in the admin panel."""

# Django Imports
from django.contrib import admin

# 3rd Party Libraries
from import_export.admin import ImportExportModelAdmin

from .models import (
    ActivityType,
    AuxServerAddress,
    Domain,
    DomainNote,
    DomainServerConnection,
    DomainStatus,
    HealthStatus,
    History,
    ServerHistory,
    ServerNote,
    ServerProvider,
    ServerRole,
    ServerStatus,
    StaticServer,
    TransientServer,
    WhoisStatus,
)
from .resources import DomainResource, StaticServerResource


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(AuxServerAddress)
class AuxServerAddressAdmin(admin.ModelAdmin):
    list_display = ("primary", "ip_address", "static_server")
    list_filter = ("primary",)
    list_display_links = ("ip_address",)


@admin.register(DomainServerConnection)
class DomainServerConnectionAdmin(admin.ModelAdmin):
    list_display = (
        "subdomain",
        "domain_name",
        "endpoint",
        "static_server",
        "transient_server",
    )
    list_display_links = ("subdomain", "domain_name", "endpoint")
    fieldsets = (
        (
            "Domain Information",
            {"fields": ("domain", "subdomain", "endpoint")},
        ),
        (
            "Server Connection",
            {"fields": ("static_server", "transient_server")},
        ),
    )


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ("domain", "client", "activity_type", "start_date", "end_date")
    list_filter = ("activity_type", "client")
    list_display_links = ("domain", "client")
    fieldsets = (
        (
            "Domain Checkout Information",
            {"fields": ("domain", "client", "project")},
        ),
        (
            "Domain Use Information",
            {"fields": ("operator", "activity_type", "start_date", "end_date")},
        ),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(DomainNote)
class DomainNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "domain")
    list_filter = ("domain",)
    list_display_links = ("operator", "timestamp", "domain")


@admin.register(DomainStatus)
class DomainStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(Domain)
class DomainAdmin(ImportExportModelAdmin):
    resource_class = DomainResource
    list_display = (
        "domain_status",
        "name",
        "whois_status",
        "health_status",
        "last_health_check",
        "registrar",
        "note",
    )
    list_filter = ("domain_status", "whois_status", "health_status", "registrar")
    list_display_links = ("domain_status", "name")
    fieldsets = (
        (None, {"fields": ("name", "domain_status", "creation", "expiration")}),
        (
            "Health status",
            {
                "fields": (
                    "last_health_check",
                    "whois_status",
                    "health_status",
                    "health_dns",
                    "burned_explanation",
                )
            },
        ),
        ("DNS Status", {"fields": ("dns_record",)}),
        (
            "Categories",
            {
                "fields": (
                    "all_cat",
                    "ibm_xforce_cat",
                    "talos_cat",
                    "bluecoat_cat",
                    "fortiguard_cat",
                    "opendns_cat",
                    "trendmicro_cat",
                )
            },
        ),
        ("Email and Spam", {"fields": ("mx_toolbox_status",)}),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(HealthStatus)
class HealthStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerHistory)
class ServerHistoryRoleAdmin(admin.ModelAdmin):
    list_display = (
        "server_name",
        "ip_address",
        "client",
        "activity_type",
        "server_role",
        "start_date",
        "end_date",
    )
    list_filter = ("activity_type", "client")
    list_display_links = ("server_name", "ip_address", "client")
    fieldsets = (
        (
            "Server Checkout Information",
            {"fields": ("server", "client", "project")},
        ),
        (
            "Server Use Information",
            {
                "fields": (
                    "operator",
                    "activity_type",
                    "server_role",
                    "start_date",
                    "end_date",
                )
            },
        ),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(ServerNote)
class ServerNoteAdmin(admin.ModelAdmin):
    list_display = ("operator", "timestamp", "server")
    list_filter = ("server",)
    list_display_links = ("operator", "timestamp", "server")


@admin.register(ServerProvider)
class ServerProviderRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerRole)
class ServerRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerStatus)
class ServerStatusRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(StaticServer)
class StaticServerAdmin(ImportExportModelAdmin):
    resource_class = StaticServerResource
    list_display = ("name", "ip_address", "server_status", "server_provider")
    list_filter = ("server_status", "server_provider")
    list_display_links = ("name", "ip_address")
    fieldsets = (
        (
            "Basic Server Information",
            {"fields": ("ip_address", "name", "server_status", "server_provider")},
        ),
        (
            "Misc",
            {
                "fields": (
                    "last_used_by",
                    "note",
                )
            },
        ),
    )


@admin.register(TransientServer)
class TransientServerRoleAdmin(admin.ModelAdmin):
    list_display = (
        "name",
        "ip_address",
        "server_role",
        "activity_type",
        "server_provider",
    )
    list_filter = ("server_provider", "server_role", "activity_type")
    list_display_links = ("name", "ip_address")
    fieldsets = (
        ("Basic Server Information", {"fields": ("ip_address", "name")}),
        (
            "Server Use Information",
            {"fields": ("server_provider", "server_role", "activity_type", "operator")},
        ),
        ("Misc", {"fields": ("note",)}),
    )


@admin.register(WhoisStatus)
class WhoisStatusAdmin(admin.ModelAdmin):
    pass
