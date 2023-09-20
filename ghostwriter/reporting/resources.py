"""This contains all the ``import_export`` model resources used by the Reporting application."""

# 3rd Party Libraries
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget
from taggit.models import Tag

# Ghostwriter Libraries
from ghostwriter.modules.shared import TagFieldImport, TagWidget, taggit_before_import_row
from ghostwriter.reporting.models import Finding, FindingType, Severity


class FindingResource(resources.ModelResource):
    """Import and export :model:`reporting.Finding`."""

    severity = Field(
        attribute="severity",
        column_name="severity",
        widget=ForeignKeyWidget(Severity, "severity"),
    )
    finding_type = Field(
        attribute="finding_type",
        column_name="finding_type",
        widget=ForeignKeyWidget(FindingType, "finding_type"),
    )
    tags = TagFieldImport(attribute="tags", column_name="tags", widget=TagWidget(Tag, separator=","))

    def before_import_row(self, row, **kwargs):
        taggit_before_import_row(row)

    class Meta:
        model = Finding
        skip_unchanged = False
        fields = (
            "id",
            "severity",
            "cvss_score",
            "cvss_vector",
            "finding_type",
            "title",
            "description",
            "impact",
            "mitigation",
            "replication_steps",
            "host_detection_techniques",
            "network_detection_techniques",
            "references",
            "finding_guidance",
            "tags",
        )
        export_order = (
            "id",
            "severity",
            "cvss_score",
            "cvss_vector",
            "finding_type",
            "title",
            "description",
            "impact",
            "mitigation",
            "replication_steps",
            "host_detection_techniques",
            "network_detection_techniques",
            "references",
            "finding_guidance",
            "tags",
        )
