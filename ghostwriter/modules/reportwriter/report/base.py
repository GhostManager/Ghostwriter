
import copy

from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import ReportDataSerializer
from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer


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
            # `{{.foo}}` converts to `{{_old_dot_vars.foo}}`
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

    @staticmethod
    def jinja_richtext_finding_context(base_context: dict, finding: dict) -> dict:
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

    @classmethod
    def generate_lint_data(cls):
        context = copy.deepcopy(LINTER_CONTEXT)
        for field in ExtraFieldSpec.objects.filter(target_model=Report._meta.label):
            context["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Project._meta.label):
            context["project"]["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Client._meta.label):
            context["client"]["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Finding._meta.label):
            for finding in context["findings"]:
                finding["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=OplogEntry._meta.label):
            for log in context["logs"]:
                for entry in log["entries"]:
                    entry["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Domain._meta.label):
            for domain in context["infrastructure"]["domains"]:
                domain["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=StaticServer._meta.label):
            for server in context["infrastructure"]["servers"]:
                server["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Observation._meta.label):
            for obs in context["observations"]:
                obs["extra_fields"][field.internal_name] = field.empty_value()
        return context
