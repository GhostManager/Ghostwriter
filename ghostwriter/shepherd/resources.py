"""This contains all of the ``import_export`` model resources used by the Shepherd application."""

# 3rd Party Libraries
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

# Ghostwriter Libraries
from ghostwriter.rolodex.models import Project

from .models import (
    ActivityType,
    Domain,
    DomainStatus,
    HealthStatus,
    ServerProvider,
    ServerRole,
    ServerStatus,
    StaticServer,
    TransientServer,
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
    Import and export for :model:`shepherd.StaticServer`.
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


class TransientServerResource(resources.ModelResource):
    """
    Import and export for :model:`shepherd.TransientServer`.
    """

    activity_type = Field(
        attribute="activity_type",
        column_name="activity_type",
        widget=ForeignKeyWidget(ActivityType, "activity_type"),
    )
    project = Field(
        attribute="project",
        column_name="project",
        widget=ForeignKeyWidget(Project, "project"),
    )
    server_provider = Field(
        attribute="server_provider",
        column_name="server_provider",
        widget=ForeignKeyWidget(ServerProvider, "server_provider"),
    )
    server_role = Field(
        attribute="server_role",
        column_name="server_role",
        widget=ForeignKeyWidget(ServerRole, "server_role"),
    )

    class Meta:
        model = TransientServer
        skip_unchanged = True
        exclude = ()

        export_order = (
            "id",
            "ip_address",
            "name",
            "project",
            "server_provider",
            "server_role",
            "activity_type",
        )
