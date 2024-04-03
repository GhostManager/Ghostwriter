
import io
import logging

from xlsxwriter.workbook import Workbook

from ghostwriter.modules.reportwriter.html_to_plain_text import html_to_plain_text
from ghostwriter.modules.reportwriter.export_report_base import ExportReportBase
from ghostwriter.modules.reportwriter.extensions import IMAGE_EXTENSIONS, TEXT_EXTENSIONS
from ghostwriter.reporting.models import Evidence, Finding


logger = logging.getLogger(__name__)


class ExportReportXlsx(ExportReportBase):
    output: io.BytesIO
    workbook: Workbook

    def __init__(self, report):
        super().__init__(report)
        self.output = io.BytesIO()
        self.workbook = Workbook(self.output, {
            "in_memory": True,
            "strings_to_formulas": False,
            "strings_to_urls": False,
        })

    def _process_rich_text_xlsx(self, html, template_vars, evidences) -> str:
        """
        Converts HTML from the TinyMCE rich text editor and returns a plain string
        """
        text = self.preprocess_rich_text(html, template_vars)
        return html_to_plain_text(text, evidences)

    def run(self) -> io.BytesIO:
        """
        Generate a complete Excel spreadsheet for the current report.

        **Parameters**

        ``memory_object``
            In-memory file-like object to write the Excel spreadsheet to
        """

        # Create an in-memory Excel workbook with a named worksheet
        xlsx_doc = self.workbook
        worksheet = xlsx_doc.add_worksheet("Findings")

        # Create a format for headers
        bold_format = xlsx_doc.add_format({"bold": True})
        bold_format.set_text_wrap()
        bold_format.set_align("vcenter")
        bold_format.set_align("center")

        # Create a format for affected entities
        asset_format = xlsx_doc.add_format()
        asset_format.set_text_wrap()
        asset_format.set_align("vcenter")
        asset_format.set_align("center")

        # Formatting for severity cells
        severity_format = xlsx_doc.add_format({"bold": True})
        severity_format.set_align("vcenter")
        severity_format.set_align("center")
        severity_format.set_font_color("black")

        # Create a format for everything else
        wrap_format = xlsx_doc.add_format()
        wrap_format.set_text_wrap()
        wrap_format.set_align("vcenter")

        # Create header row for findings
        col = 0
        headers = [
            "Finding",
            "Severity",
            "CVSS Score",
            "CVSS Vector",
            "Affected Entities",
            "Description",
            "Impact",
            "Recommendation",
            "Replication Steps",
            "Host Detection Techniques",
            "Network Detection Techniques",
            "References",
            "Supporting Evidence",
            "Tags",
        ]

        findings_extra_field_specs = self.extra_field_specs_for(Finding)
        base_evidences = {e["friendly_name"]: e for e in self.data["evidence"]}

        # Create 30 width columns and then shrink severity to 10
        for header in headers:
            worksheet.write_string(0, col, header, bold_format)
            col += 1
        for field in findings_extra_field_specs:
            worksheet.write_string(0, col, field.display_name, bold_format)
            col += 1
        worksheet.set_column(0, 13, 30)
        worksheet.set_column(1, 1, 10)
        worksheet.set_column(2, 2, 10)
        worksheet.set_column(3, 3, 40)

        # Loop through the findings to create the rest of the worksheet
        col = 0
        row = 1
        base_context = self.jinja_richtext_base_context()
        for finding in self.data["findings"]:
            finding_context = self.jinja_richtext_finding_context(base_context, finding)
            finding_evidences = base_evidences | {e["friendly_name"]: e for e in finding["evidence"]}

            # Finding Name
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["title"], finding_context, finding_evidences),
                bold_format,
            )
            col += 1

            # Update severity format bg color with the finding's severity color
            severity_format.set_bg_color(finding["severity_color"])

            # Severity and CVSS information
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["severity"], finding_context, finding_evidences),
                severity_format,
            )
            col += 1
            if isinstance(finding["cvss_score"], float):
                worksheet.write_number(row, col, finding["cvss_score"], severity_format)
            else:
                worksheet.write_string(
                    row,
                    col,
                    self._process_rich_text_xlsx(finding["cvss_score"], finding_context, finding_evidences),
                    severity_format,
                )
            col += 1
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["cvss_vector"], finding_context, finding_evidences),
                severity_format,
            )
            col += 1

            # Affected Entities
            if finding["affected_entities"]:
                worksheet.write_string(
                    row,
                    col,
                    self._process_rich_text_xlsx(finding["affected_entities"], finding_context, finding_evidences),
                    asset_format,
                )
            else:
                worksheet.write_string(row, col, "N/A", asset_format)
            col += 1

            # Description
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["description"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Impact
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["impact"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Recommendation
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["recommendation"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Replication
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["replication_steps"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Detection
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["host_detection_techniques"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(
                    finding["network_detection_techniques"], finding_context, finding_evidences
                ),
                wrap_format,
            )
            col += 1

            # References
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding["references"], finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Collect the evidence, if any, from the finding's folder and insert inline with description
            try:
                evidence_queryset = Evidence.objects.filter(finding=finding["id"])
            except Evidence.DoesNotExist:
                evidence_queryset = []
            except Exception:
                logger.exception("Query for evidence failed for finding %s", finding["id"])
                evidence_queryset = []
            evidence = [f.filename for f in evidence_queryset if f in TEXT_EXTENSIONS or f in IMAGE_EXTENSIONS]
            finding_evidence_names = "\r\n".join(map(str, evidence))
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(finding_evidence_names, finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Tags
            worksheet.write_string(
                row,
                col,
                self._process_rich_text_xlsx(", ".join(finding["tags"]), finding_context, finding_evidences),
                wrap_format,
            )
            col += 1

            # Extra fields
            for field_spec in findings_extra_field_specs:
                field_value = field_spec.value_of(finding["extra_fields"])
                if field_spec.type == "rich_text":
                    field_value = self._process_rich_text_xlsx(field_value, finding_context, finding_evidences)
                else:
                    field_value = str(field_value)
                worksheet.write_string(row, col, field_value, wrap_format)
                col += 1

            # Increment row counter and reset columns before moving on to next finding
            row += 1
            col = 0

        # Add a filter to the worksheet
        worksheet.autofilter("A1:M{}".format(len(self.data["findings"]) + 1))

        # Finalize document
        xlsx_doc.close()
        return self.output
