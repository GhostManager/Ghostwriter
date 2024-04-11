

import copy
import io
from ghostwriter.modules.linting_utils import LINTER_CONTEXT
from ghostwriter.modules.reportwriter.base.docx import ExportDocxBase
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
from ghostwriter.oplog.models import OplogEntry
from ghostwriter.reporting.models import ReportTemplate
from ghostwriter.rolodex.models import Client, Project
from ghostwriter.shepherd.models import Domain, StaticServer


class ExportProjectDocx(ExportDocxBase, ExportProjectBase):
    def __init__(self, object: ReportTemplate, *, p_style=None, **kwargs):
        if p_style is None:
            p_style = object.docx_template.p_style
        super().__init__(object, p_style=p_style, **kwargs)

    @staticmethod
    def process_projects_richtext(
        context: dict,
        base_render,
        process_extra_fields,
    ):
        """
        Helper for processing the project-related rich text fields in both the `ProjectSerializer` and
        `ReportDataSerializer`.

        Arguments are the serialized data to read and alter, the render function, and the bound `process_extra_fields`
        method.
        """

        # Client
        context["client"]["note_rt"] = base_render(context["client"]["note"])
        context["client"]["address_rt"] = base_render(context["client"]["address"])
        process_extra_fields(context["client"]["extra_fields"], Client, base_render)

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
            process_extra_fields(asset["extra_fields"], Domain, base_render)
        for asset in context["infrastructure"]["servers"]:
            process_extra_fields(asset["extra_fields"], StaticServer, base_render)

        # Logs
        for log in context["logs"]:
            for entry in log["entries"]:
                process_extra_fields(entry["extra_fields"], OplogEntry, base_render)

    def run(self) -> io.BytesIO:
        context = self.data
        base_context = self.jinja_richtext_base_context()

        def base_render(text):
            return self.process_rich_text_docx(text, base_context, {})

        # Fields on Project
        ExportProjectDocx.process_projects_richtext(context, base_render, self.process_extra_fields)

        # Project
        context["project"]["note_rt"] = base_render(context["project"]["note"])
        self.process_extra_fields(context["project"]["extra_fields"], Project, base_render)

        return super().run()

    @classmethod
    def generate_lint_data(cls):
        return {name: copy.deepcopy(LINTER_CONTEXT[name]) for name in [
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
        ]}
