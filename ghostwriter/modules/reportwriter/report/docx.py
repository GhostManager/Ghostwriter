
import io
import logging

from docxtpl import RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.docx import ExportProjectDocx
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Project

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
