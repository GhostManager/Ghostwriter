"""This contains all of the ``import_export`` model resources used by the Reporting application."""

# 3rd Party Libraries
from import_export import resources
from import_export.fields import Field
from import_export.widgets import ForeignKeyWidget

from .models import Finding, FindingType, Severity


class FindingResource(resources.ModelResource):
    """
    Import and export :model:`reporting.Finding`.
    """

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

    class Meta:
        model = Finding
        skip_unchanged = True
        fields = (
            "id",
            "severity",
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
        )
        export_order = (
            "id",
            "severity",
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
        )
