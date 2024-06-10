
from collections import ChainMap
import copy
import html

from markupsafe import Markup

from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.custom_serializers import ReportDataSerializer
from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter import jinja_funcs
from ghostwriter.modules.reportwriter.base.base import ExportBase
from ghostwriter.modules.reportwriter.base.html_rich_text import HtmlAndRich
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
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

    def severity_rich_text(self, text, severity_color):
        """
        Creates an exporter specific rich text object for some text related to finding severity.
        This should be text colored by `severity_color`, if possible.
        """
        return text

    def _severity_rich_text(self, text, severity_color):
        if not text:
            return ""
        text = str(text)
        rich_html = Markup('''<span style="color: #{};">{}</span>'''.format(
            severity_color,
            html.escape(text),
        ))
        exporter_rich = self.severity_rich_text(text, severity_color)
        return HtmlAndRich(rich_html, exporter_rich)

    def map_rich_texts(self):
        base_context = copy.deepcopy(self.data)
        rich_text_overlay = ExportProjectBase.rich_text_jinja_overlay(self.data)
        rich_text_overlay["mk_evidence"] = jinja_funcs.mk_evidence
        rich_text_overlay["_evidences"] = self.create_evidences_lookup(self.data["evidence"])
        rich_text_overlay["_old_dot_vars"].update({name: jinja_funcs.raw_mk_evidence(id) for name, id in rich_text_overlay["_evidences"].items()})
        rich_text_context = ChainMap(
            rich_text_overlay,
            base_context,
        )

        # Fields on Project
        ExportProjectBase.process_projects_richtext(self, base_context, rich_text_context)

        # Findings
        for finding in base_context["findings"]:
            finding_overlay = {
                "finding": finding,
                "_old_dot_vars": rich_text_overlay["_old_dot_vars"].copy(),
                "_evidences": self.create_evidences_lookup(finding["evidence"], rich_text_overlay["_evidences"]),
            }
            finding_overlay["_old_dot_vars"].update({name: jinja_funcs.raw_mk_evidence(id) for name, id in finding_overlay["_evidences"].items()})

            finding_rich_text_context = ChainMap(
                finding_overlay,
                rich_text_overlay,
                base_context,
            )

            def finding_render(name, text):
                return self.create_lazy_template(f"{name} of finding {finding['title']}", text, finding_rich_text_context)

            finding["severity_rt"] = self._severity_rich_text(finding["severity"], finding["severity_color"])
            finding["cvss_score_rt"] = self._severity_rich_text(finding["cvss_score"], finding["severity_color"])
            finding["cvss_vector_rt"] = self._severity_rich_text(finding["cvss_vector"], finding["severity_color"])

            # Create subdocuments for each finding section
            finding["affected_entities_rt"] = finding_render("the affected entities section", finding["affected_entities"])
            finding["description_rt"] = finding_render("the description", finding["description"])
            finding["impact_rt"] = finding_render("the impact section", finding["impact"])

            # Include a copy of ``mitigation`` as ``recommendation`` to match legacy context
            mitigation_section = finding_render("the mitigation section", finding["mitigation"])
            finding["mitigation_rt"] = mitigation_section
            finding["recommendation_rt"] = mitigation_section

            finding["replication_steps_rt"] = finding_render("the replication steps section", finding["replication_steps"])
            finding["host_detection_techniques_rt"] = finding_render("the host detection techniques section", finding["host_detection_techniques"])
            finding["network_detection_techniques_rt"] = finding_render("the network detection techniques section", finding["network_detection_techniques"])
            finding["references_rt"] = finding_render("the references section", finding["references"])

        # Observations
        for observation in base_context["observations"]:
            if observation["description"]:
                observation["description_rt"] = self.create_lazy_template(f"the description of observation {observation['title']}", observation["description"], rich_text_context)
            self.process_extra_fields(f"observation {observation['title']}", observation["extra_fields"], Observation, rich_text_context)

        # Project
        base_context["project"]["note_rt"] = self.create_lazy_template("the project note", base_context["project"]["note"], rich_text_context)
        self.process_extra_fields("the project", base_context["project"]["extra_fields"], Project, rich_text_context)

        # Report extra fields
        self.process_extra_fields("the report", base_context["extra_fields"], Report, rich_text_context)

        # Report Evidence
        # for evidence in base_context["evidence"]:
        #     self.process_extra_fields("the evidence", evidence["extra_fields"], Evidence, rich_text_context)

        return base_context

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
