
from ghostwriter.modules.custom_serializers import ReportDataSerializer
from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base.base import ExportBase


class ExportReportBase(ExportBase):
    """
    Mixin class for exporting reports.

    Provides a `serialize_object` implementation for serializing the `Report` database object,
    and helper functions for creating Jinja contexts.
    """

    def serialize_object(self, report):
        return ReportDataSerializer(
            report,
            exclude=["id"],
        ).data

    def jinja_richtext_base_context(self) -> dict:
        """
        Generates a Jinja context for use in rich text fields
        """
        base_context = {
            # `{{.foo}}` converts to `{{obsolete.foo}}`
            "_old_dot_vars": {
                "client": self.data["client"]["short_name"] or self.data["client"]["name"],
                "project_start": self.data["project"]["start_date"],
                "project_end": self.data["project"]["end_date"],
                "project_type": self.data["project"]["type"].lower(),
            },
            "mk_evidence": jinja_funcs.evidence,
            "mk_caption": jinja_funcs.caption,
            "mk_ref": jinja_funcs.ref,
        }
        base_context.update(self.data)
        for evidence in self.data["evidence"]:
            if evidence.get("friendly_name"):
                base_context["_old_dot_vars"][evidence["friendly_name"]] = jinja_funcs.evidence(evidence["friendly_name"])
        return base_context

    def jinja_richtext_finding_context(self, base_context: dict, finding: dict) -> dict:
        """
        Generates a Jinja context for use in finding-related rich text fields
        """
        finding_context = base_context.copy()
        finding_context.update(
            {
                "finding": finding,
                "_old_dot_vars": base_context["_old_dot_vars"].copy(),
            }
        )
        for evidence in finding["evidence"]:
            if evidence.get("friendly_name"):
                finding_context["_old_dot_vars"][evidence["friendly_name"]] = jinja_funcs.evidence(evidence["friendly_name"])
        return finding_context
