"""This contains all of the ``import_export`` model resources used by the Shepherd application."""

# 3rd Party Libraries
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

from .models import (
    Domain,
    DomainStatus,
    HealthStatus,
    ServerProvider,
    ServerStatus,
    StaticServer,
    WhoisStatus,
)


class DomainResource(resources.ModelResource):
    """
    Import and export for :model:`shepherd.Domain`.
    """

    domain_status = Field(
        attribute="domain_status",
        column_name="domain_status",
        widget=ForeignKeyWidget(DomainStatus, "domain_status"),
    )
    health_status = Field(
        attribute="health_status",
        column_name="health_status",
        widget=ForeignKeyWidget(HealthStatus, "health_status"),
    )
    whois_status = Field(
        attribute="whois_status",
        column_name="whois_status",
        widget=ForeignKeyWidget(WhoisStatus, "whois_status"),
    )

    class Meta:
        model = Domain
        skip_unchanged = True
        exclude = (
            "last_used_by",
            "dns_record",
        )

        export_order = (
            "id",
            "name",
            "domain_status",
            "health_status",
            "whois_status",
            "creation",
            "expiration",
            "auto_renew",
            "expired",
            "all_cat",
            "ibm_xforce_cat",
            "talos_cat",
            "bluecoat_cat",
            "fortiguard_cat",
            "opendns_cat",
            "trendmicro_cat",
            "mx_toolbox_status",
            "note",
            "burned_explanation",
        )


class StaticServerResource(resources.ModelResource):
    """
    Import and export for :model:`shepherd.Domain`.
    """

    server_status = Field(
        attribute="server_status",
        column_name="server_status",
        widget=ForeignKeyWidget(ServerStatus, "server_status"),
    )
    server_provider = Field(
        attribute="server_provider",
        column_name="server_provider",
        widget=ForeignKeyWidget(ServerProvider, "server_provider"),
    )

    class Meta:
        model = StaticServer
        skip_unchanged = True
        exclude = ("last_used_by",)

        export_order = (
            "id",
            "ip_address",
            "name",
            "server_status",
            "server_provider",
        )
