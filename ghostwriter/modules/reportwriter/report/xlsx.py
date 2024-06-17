
import io
import logging

from ghostwriter.modules.reportwriter.base.xlsx import ExportXlsxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.modules.reportwriter.extensions import IMAGE_EXTENSIONS, TEXT_EXTENSIONS
from ghostwriter.reporting.models import Evidence, Finding


logger = logging.getLogger(__name__)


class ExportReportXlsx(ExportXlsxBase, ExportReportBase):
    def run(self) -> io.BytesIO:
        context = self.map_rich_texts()

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
        for finding in context["findings"]:

            # Finding Name
            worksheet.write_string(
                row,
                col,
                finding["title"],
                bold_format,
            )
            col += 1

            # Update severity format bg color with the finding's severity color
            severity_format.set_bg_color(finding["severity_color"])

            # Severity and CVSS information
            worksheet.write_string(
                row,
                col,
                finding["severity"],
                severity_format,
            )
            col += 1
            if isinstance(finding["cvss_score"], float):
                worksheet.write_number(row, col, finding["cvss_score"], severity_format)
            else:
                worksheet.write_string(
                    row,
                    col,
                    str(finding["cvss_score"]) if finding["cvss_score"] is not None else "",
                    severity_format,
                )
            col += 1
            worksheet.write_string(
                row,
                col,
                str(finding["cvss_vector"]) if finding["cvss_vector"] is not None else "",
                severity_format,
            )
            col += 1

            # Affected Entities
            if finding["affected_entities"]:
                worksheet.write_string(
                    row,
                    col,
                    self.render_rich_text_xlsx(finding["affected_entities_rt"]),
                    asset_format,
                )
            else:
                worksheet.write_string(row, col, "N/A", asset_format)
            col += 1

            # Description
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["description_rt"]),
                wrap_format,
            )
            col += 1

            # Impact
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["impact_rt"]),
                wrap_format,
            )
            col += 1

            # Recommendation
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["recommendation_rt"]),
                wrap_format,
            )
            col += 1

            # Replication
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["replication_steps_rt"]),
                wrap_format,
            )
            col += 1

            # Detection
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["host_detection_techniques_rt"]),
                wrap_format,
            )
            col += 1
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["network_detection_techniques_rt"]),
                wrap_format,
            )
            col += 1

            # References
            worksheet.write_string(
                row,
                col,
                self.render_rich_text_xlsx(finding["references_rt"]),
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
                finding_evidence_names,
                wrap_format,
            )
            col += 1

            # Tags
            worksheet.write_string(
                row,
                col,
                ", ".join(finding["tags"]),
                wrap_format,
            )
            col += 1

            # Extra fields
            for field_spec in findings_extra_field_specs:
                field_value = field_spec.value_of(finding["extra_fields"])
                if field_spec.type == "rich_text":
                    field_value = self.render_rich_text_xlsx(field_value)
                else:
                    field_value = str(field_value)
                worksheet.write_string(row, col, field_value, wrap_format)
                col += 1

            # Increment row counter and reset columns before moving on to next finding
            row += 1
            col = 0

        # Add a filter to the worksheet
        worksheet.autofilter("A1:M{}".format(len(self.data["findings"]) + 1))

        return super().run()
