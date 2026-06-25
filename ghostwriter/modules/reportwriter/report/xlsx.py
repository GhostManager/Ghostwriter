import io
import json
import logging

import bs4
from xlsxwriter.utility import xl_col_to_name

from ghostwriter.modules.reportwriter.base.xlsx import ExportXlsxBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase
from ghostwriter.reporting.models import Finding


logger = logging.getLogger(__name__)


class ExportReportXlsx(ExportXlsxBase, ExportReportBase):
    def referenced_evidence_names(self, rich_texts) -> list[str]:
        """
        Return report evidence friendly names referenced by rendered rich-text sections.
        """
        names = []
        seen = set()
        valid_names = {
            evidence["friendly_name"] for evidence in self.evidences_by_id.values()
        }

        for rich_text in rich_texts:
            html = rich_text.render_html()
            soup = bs4.BeautifulSoup(html, "lxml")
            for span in soup.find_all(["div", "span"]):
                name = None
                if (
                    "data-evidence-id" in span.attrs
                    and "richtext-evidence" in span.attrs.get("class", [])
                ):
                    try:
                        evidence = self.evidences_by_id[
                            int(span.attrs["data-evidence-id"])
                        ]
                    except (KeyError, ValueError):
                        continue
                    name = evidence["friendly_name"]
                elif "data-gw-evidence" in span.attrs:
                    try:
                        evidence = self.evidences_by_id[
                            int(span.attrs["data-gw-evidence"])
                        ]
                    except (KeyError, ValueError):
                        continue
                    name = evidence["friendly_name"]
                elif "data-gw-caption" in span.attrs:
                    ref_name = span.attrs["data-gw-caption"]
                    name = ref_name if ref_name in valid_names else None
                elif "data-gw-ref" in span.attrs:
                    ref_name = span.attrs["data-gw-ref"]
                    name = ref_name if ref_name in valid_names else None

                if name and name not in seen:
                    seen.add(name)
                    names.append(name)
        return names

    def finding_rich_texts(self, finding, findings_extra_field_specs):
        rich_texts = [
            finding["affected_entities_rt"],
            finding["description_rt"],
            finding["impact_rt"],
            finding["recommendation_rt"],
            finding["replication_steps_rt"],
            finding["host_detection_techniques_rt"],
            finding["network_detection_techniques_rt"],
            finding["references_rt"],
        ]
        for field_spec in findings_extra_field_specs:
            if field_spec.type == "rich_text":
                rich_texts.append(field_spec.value_of(finding["extra_fields"]))
        return rich_texts

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

        severity_formats = {}

        def get_severity_format(color):
            if color not in severity_formats:
                severity_format = xlsx_doc.add_format({"bold": True})
                severity_format.set_align("vcenter")
                severity_format.set_align("center")
                severity_format.set_font_color("black")
                severity_format.set_bg_color(color)
                severity_formats[color] = severity_format
            return severity_formats[color]

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
        column_count = len(headers) + len(findings_extra_field_specs)

        # Create 30 width columns and then shrink severity to 10
        for header in headers:
            worksheet.write_string(0, col, header, bold_format)
            col += 1
        for field in findings_extra_field_specs:
            worksheet.write_string(0, col, field.display_name, bold_format)
            col += 1
        worksheet.set_column(0, column_count - 1, 30)
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

            severity_format = get_severity_format(finding["severity_color"])

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
                    str(finding["cvss_score"])
                    if finding["cvss_score"] is not None
                    else "",
                    severity_format,
                )
            col += 1
            worksheet.write_string(
                row,
                col,
                str(finding["cvss_vector"])
                if finding["cvss_vector"] is not None
                else "",
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

            # Supporting Evidence
            worksheet.write_string(
                row,
                col,
                ", ".join(
                    self.referenced_evidence_names(
                        self.finding_rich_texts(finding, findings_extra_field_specs)
                    )
                ),
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
                elif field_spec.type == "json":
                    field_value = json.dumps(field_value)
                else:
                    field_value = str(field_value)
                worksheet.write_string(row, col, field_value, wrap_format)
                col += 1

            # Increment row counter and reset columns before moving on to next finding
            row += 1
            col = 0

        # Add a filter to the worksheet
        worksheet.autofilter(
            "A1:{}{}".format(
                xl_col_to_name(column_count - 1), len(self.data["findings"]) + 1
            )
        )

        return super().run()
