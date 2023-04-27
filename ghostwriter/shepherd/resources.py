"""This contains all the ``import_export`` model resources used by the Shepherd application."""

# 3rd Party Libraries
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from taggit.models import Tag

# Ghostwriter Libraries
from ghostwriter.modules.shared import TagFieldImport, TagWidget, taggit_before_import_row
from ghostwriter.shepherd.models import (
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
    tags = TagFieldImport(attribute="tags", column_name="tags", widget=TagWidget(Tag, separator=","))

    def before_import_row(self, row, **kwargs):
        taggit_before_import_row(row)

    class Meta:
        model = Domain
        skip_unchanged = False
        exclude = ("last_used_by", "last_health_check", "vt_permalink")

        export_order = (
            "id",
            "name",
            "domain_status",
            "registrar",
            "auto_renew",
            "creation",
            "expiration",
            "health_status",
            "whois_status",
            "expired",
            "categorization",
            "dns",
            "reset_dns",
            "note",
            "burned_explanation",
            "tags",
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
    tags = TagFieldImport(attribute="tags", column_name="tags", widget=TagWidget(Tag, separator=","))

    def before_import_row(self, row, **kwargs):
        taggit_before_import_row(row)

    class Meta:
        model = StaticServer
        skip_unchanged = False
        exclude = ("last_used_by",)

        export_order = (
            "id",
            "ip_address",
            "name",
            "server_status",
            "server_provider",
            "note",
            "tags",
        )
