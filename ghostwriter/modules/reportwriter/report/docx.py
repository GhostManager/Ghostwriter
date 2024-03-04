
import io
import logging

from docxtpl import DocxTemplate, RichText

from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import Finding, Observation, Report
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer

logger = logging.getLogger(__name__)


class ExportReportDocx(ExportReportBase, ExportDocxBase):
    word_doc: DocxTemplate

    def process_richtext(self, context: dict):
        """
        Update the document context with ``RichText`` and ``Subdocument`` objects for
        each finding and any other values editable with a WYSIWYG editor.

        **Parameters**

        ``context``
            Pre-defined template context
        """

        p_style = self.input_object.docx_template.p_style

        base_context = self.jinja_richtext_base_context()
        base_evidences = {e["friendly_name"]: e for e in context["evidence"]}

        def base_render(text):
            return self.process_rich_text_docx(text, base_context, base_evidences, p_style)

        self.process_extra_fields(context["extra_fields"], Report, base_render)

        # Findings
        for finding in context["findings"]:
            logger.info("Processing %s", finding["title"])

            finding_context = self.jinja_richtext_finding_context(base_context, finding)
            finding_evidences = base_evidences | {e["friendly_name"]: e for e in finding["evidence"]}

            def finding_render(text):
                return self.process_rich_text_docx(text, finding_context, finding_evidences, p_style)

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

        # Client
        context["client"]["note_rt"] = base_render(context["client"]["note"])
        context["client"]["address_rt"] = base_render(context["client"]["address"])
        self.process_extra_fields(context["client"]["extra_fields"], Client, base_render)

        # Project
        context["project"]["note_rt"] = base_render(context["project"]["note"])
        self.process_extra_fields(context["project"]["extra_fields"], Project, base_render)

        # Assignments
        for assignment in context["team"]:
            if isinstance(assignment, dict):
                if assignment["note"]:
                    assignment["note_rt"] = base_render(assignment["note"])

        # Contacts
        for contact in context["client"]["contacts"]:
            if isinstance(contact, dict):
                if contact["note"]:
                    contact["note_rt"] = base_render(contact["note"])

        # Objectives
        for objective in context["objectives"]:
            if isinstance(objective, dict):
                if objective["description"]:
                    objective["description_rt"] = base_render(objective["description"])

        # Scope Lists
        for scope_list in context["scope"]:
            if isinstance(scope_list, dict):
                if scope_list["description"]:
                    scope_list["description_rt"] = base_render(scope_list["description"])

        # Targets
        for target in context["targets"]:
            if isinstance(target, dict):
                if target["note"]:
                    target["note_rt"] = base_render(target["note"])

        # Deconfliction Events
        for event in context["deconflictions"]:
            if isinstance(event, dict):
                if event["description"]:
                    event["description_rt"] = base_render(event["description"])

        # White Cards
        for card in context["whitecards"]:
            if isinstance(card, dict):
                if card["description"]:
                    card["description_rt"] = base_render(card["description"])

        # Infrastructure
        for asset_type in context["infrastructure"]:
            for asset in context["infrastructure"][asset_type]:
                if isinstance(asset, dict):
                    if asset["note"]:
                        asset["note_rt"] = base_render(asset["note"])
        for asset in context["infrastructure"]["domains"]:
            self.process_extra_fields(asset["extra_fields"], Domain, base_render)
        for asset in context["infrastructure"]["servers"]:
            self.process_extra_fields(asset["extra_fields"], StaticServer, base_render)

        # Logs
        for log in context["logs"]:
            for entry in log["entries"]:
                self.process_extra_fields(entry["extra_fields"], OplogEntry, base_render)

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
