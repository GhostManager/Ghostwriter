
import copy

from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import FullProjectSerializer
from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer


class ExportProjectBase(ExportBase):
    """
    Mixin class for exporting projects.

    Provides a `serialize_object` implementation for serializing the `Project` database object,
    and helper functions for creating Jinja contexts.
    """

    def serialize_object(self, object):
        return FullProjectSerializer(object).data

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
            "mk_caption": jinja_funcs.caption,
            "mk_ref": jinja_funcs.ref,
        }
        base_context.update(self.data)
        return base_context

    @classmethod
    def generate_lint_data(cls):
        context = {name: copy.deepcopy(LINTER_CONTEXT[name]) for name in [
            "project",
            "client",
            "team",
            "objectives",
            "targets",
            "scope",
            "deconflictions",
            "whitecards",
            "infrastructure",
            "logs",
            "company",
            "report_date",
            "extra_fields",
        ]}
        for field in ExtraFieldSpec.objects.filter(target_model=Report._meta.label):
            context["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Project._meta.label):
            context["project"]["extra_fields"][field.internal_name] = field.empty_value()
        for field in ExtraFieldSpec.objects.filter(target_model=Client._meta.label):
            context["client"]["extra_fields"][field.internal_name] = field.empty_value()
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
        return context
