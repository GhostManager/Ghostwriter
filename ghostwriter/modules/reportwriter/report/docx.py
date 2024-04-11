
import copy
import io
import logging

from docxtpl import RichText
from ghostwriter.commandcenter.models import ExtraFieldSpec

from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.docx import ExportProjectDocx
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer

logger = logging.getLogger(__name__)


class ExportReportDocx(ExportDocxBase, ExportReportBase):
    def __init__(self, object, **kwargs):
        if kwargs.get("p_style") is None and not kwargs.get("is_raw"):
            kwargs["p_style"] = object.docx_template.p_style
        super().__init__(object, **kwargs)

    def process_richtext(self, context: dict):
        """
        Update the document context with ``RichText`` and ``Subdocument`` objects for
        each finding and any other values editable with a WYSIWYG editor.

        **Parameters**

        ``context``
            Pre-defined template context
        """

        base_context = self.jinja_richtext_base_context()
        base_evidences = {e["friendly_name"]: e for e in context["evidence"]}

        def base_render(text):
            return self.process_rich_text_docx(text, base_context, base_evidences)

        self.process_extra_fields(context["extra_fields"], Report, base_render)

        # Findings
        for finding in context["findings"]:
            logger.info("Processing %s", finding["title"])

            finding_context = self.jinja_richtext_finding_context(base_context, finding)
            finding_evidences = base_evidences | {e["friendly_name"]: e for e in finding["evidence"]}

            def finding_render(text):
                return self.process_rich_text_docx(text, finding_context, finding_evidences)

            self.process_extra_fields(finding["extra_fields"], Finding, finding_render)

            # Create ``RichText()`` object for a colored severity category
            finding["severity_rt"] = RichText(finding["severity"], color=finding["severity_color"])
            finding["cvss_score_rt"] = RichText(finding["cvss_score"], color=finding["severity_color"])
            finding["cvss_vector_rt"] = RichText(finding["cvss_vector"], color=finding["severity_color"])
            # Create subdocuments for each finding section
            finding["affected_entities_rt"] = finding_render(finding["affected_entities"])
            finding["description_rt"] = finding_render(finding["description"])
            finding["impact_rt"] = finding_render(finding["impact"])

            # Include a copy of ``mitigation`` as ``recommendation`` to match legacy context
            mitigation_section = finding_render(finding["mitigation"])
            finding["mitigation_rt"] = mitigation_section
            finding["recommendation_rt"] = mitigation_section

            finding["replication_steps_rt"] = finding_render(finding["replication_steps"])
            finding["host_detection_techniques_rt"] = finding_render(finding["host_detection_techniques"])
            finding["network_detection_techniques_rt"] = finding_render(finding["network_detection_techniques"])
            finding["references_rt"] = finding_render(finding["references"])

        # Project
        context["project"]["note_rt"] = base_render(context["project"]["note"])
        self.process_extra_fields(context["project"]["extra_fields"], Project, base_render)

        # Fields on Project
        ExportProjectDocx.process_projects_richtext(context, base_render, self.process_extra_fields)

        # Observations
        for observation in context["observations"]:
            if observation["description"]:
                observation["description_rt"] = base_render(observation["description"])
            self.process_extra_fields(observation["extra_fields"], Observation, base_render)

        # Report Evidence
        # for evidence in context["evidence"]:
        #    self.process_extra_fields(evidence["extra_fields"], Report, base_render)

    def run(self) -> io.BytesIO:
        self.process_richtext(self.data)
        return super().run()

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
