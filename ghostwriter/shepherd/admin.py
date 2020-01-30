"""This contains customizations for the models in the Django admin panel."""

from django.contrib import admin
from .models import (Domain, HealthStatus, DomainStatus, WhoisStatus,
                             ActivityType, History, ServerRole, ServerStatus,
                             ServerProvider, ServerHistory, StaticServer,
                             TransientServer, DomainServerConnection,
                             AuxServerAddress)


# Define the admin classes and register models
@admin.register(Domain)
class DomainAdmin(admin.ModelAdmin):
    list_display = ('domain_status', 'name', 'whois_status', 'health_status',
                    'health_dns', 'registrar', 'note')
    list_filter = ('domain_status',)
    fieldsets = (
        (None, {
            'fields': ('name', 'domain_status', 'creation', 'expiration')
        }),
        ('Health Statuses', {
            'fields': ('whois_status', 'health_status', 'health_dns',
                       'burned_explanation')
        }),
        ('Categories', {
            'fields': ('all_cat', 'ibm_xforce_cat', 'talos_cat',
                       'bluecoat_cat', 'fortiguard_cat', 'opendns_cat',
                       'trendmicro_cat')
        }),
        ('Email and Spam', {
            'fields': ('mx_toolbox_status',)
        }),
        ('Misc', {
            'fields': ('note',)
        })
    )


@admin.register(DomainStatus)
class DomainStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(HealthStatus)
class HealthStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(WhoisStatus)
class WhoisStatusAdmin(admin.ModelAdmin):
    pass


@admin.register(ActivityType)
class ActivityTypeAdmin(admin.ModelAdmin):
    pass


@admin.register(History)
class HistoryAdmin(admin.ModelAdmin):
    list_display = ('client', 'domain', 'activity_type', 'end_date',
                    'operator')


@admin.register(ServerRole)
class ServerRoleRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerStatus)
class ServerStatusRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerProvider)
class ServerProviderRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(StaticServer)
class StaticServerRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(TransientServer)
class TransientServerRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(ServerHistory)
class ServerHistoryRoleAdmin(admin.ModelAdmin):
    pass


@admin.register(DomainServerConnection)
class DomainServerConnectionAdmin(admin.ModelAdmin):
    pass


@admin.register(AuxServerAddress)
class AuxServerAddressAdmin(admin.ModelAdmin):
    pass
