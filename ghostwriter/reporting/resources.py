"""This contains all of the ``import_export`` model resources used by the Reporting application."""

# Django & Other 3rd Party Libraries
from import_export import resources
from import_export.fields import Field

from .models import Finding


class FindingResource(resources.ModelResource):
    """
    Import and export :model:`reporting.Finding`.
    """

    severity = Field(attribute="severity__severity", column_name="severity")
    finding_type = Field(
        attribute="finding_type__finding_type", column_name="finding_type"
    )

    class Meta:
        model = Finding
        skip_unchanged = True
        fields = (
            "id",
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
