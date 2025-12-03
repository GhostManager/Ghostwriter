"""Helpers for generating supplemental XLSX documents from project data artifacts."""

from __future__ import annotations

import base64
import binascii
import io
import logging
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

from xlsxwriter.workbook import Workbook

logger = logging.getLogger(__name__)


RowFormatFn = Callable[[int, Any, Dict[str, Any], bool], Any]


class SupplementalDocumentBuilder:
    """Create supplemental XLSX documents based on ``project.data_artifacts``."""

    HEADER_FILL = "#0066CC"
    BANDED_FILL = "#99CCFF"
    HEADER_FONT = "#FFFFFF"
    RED_FONT = "#FF0000"

    def __init__(self, project):
        self.project = project
        self.artifacts = project.data_artifacts if isinstance(project.data_artifacts, dict) else {}
        self.client_name = getattr(getattr(project, "client", None), "name", "Client")

    def build(self) -> List[Tuple[str, bytes]]:
        files: List[Tuple[str, bytes]] = []

        self._append_osint(files)
        self._append_dns_findings(files)
        self._append_dns_records(files)
        self._append_internal_software(files)
        self._append_ad_reports(files)
        self._append_snmp_reports(files)
        self._append_processed_metrics(files)

        return files

    def _create_workbook(self, sheets: Sequence[Dict[str, Any]]) -> bytes:
        output = io.BytesIO()
        workbook = Workbook(
            output,
            {
                "in_memory": True,
                "strings_to_formulas": False,
                "strings_to_urls": False,
            },
        )

        base_font = {"font_name": "Arial", "font_size": 12, "border": 1}
        formats = {
            "header": workbook.add_format(
                {
                    **base_font,
                    "bold": True,
                    "bg_color": self.HEADER_FILL,
                    "font_color": self.HEADER_FONT,
                    "align": "center",
                    "valign": "vcenter",
                    "text_wrap": True,
                }
            ),
            "default": workbook.add_format({**base_font, "text_wrap": True, "valign": "top"}),
            "banded": workbook.add_format(
                {
                    **base_font,
                    "text_wrap": True,
                    "valign": "top",
                    "bg_color": self.BANDED_FILL,
                }
            ),
            "default_red": workbook.add_format(
                {
                    **base_font,
                    "text_wrap": True,
                    "valign": "top",
                    "font_color": self.RED_FONT,
                }
            ),
            "banded_red": workbook.add_format(
                {
                    **base_font,
                    "text_wrap": True,
                    "valign": "top",
                    "bg_color": self.BANDED_FILL,
                    "font_color": self.RED_FONT,
                }
            ),
        }

        for sheet in sheets:
            sheet_name = (sheet.get("name") or "Sheet1")[:31]
            headers: List[str] = list(sheet.get("headers") or [])
            rows: Iterable[Any] = sheet.get("rows") or []
            row_format_fn: RowFormatFn | None = sheet.get("row_format_fn")

            worksheet = workbook.add_worksheet(sheet_name or "Sheet1")
            worksheet.freeze_panes(1, 0)

            widths = [len(str(header)) for header in headers]
            normalized_rows: List[List[str]] = []
            for row in rows:
                normalized_row: List[str] = []
                for idx, header in enumerate(headers):
                    value = self._extract_cell_value(row, header)
                    normalized_row.append(value)
                    widths[idx] = max(widths[idx], len(value))
                normalized_rows.append(normalized_row)

            for col_idx, title in enumerate(headers):
                worksheet.write_string(0, col_idx, title, formats["header"])

            for row_idx, row in enumerate(normalized_rows, start=1):
                is_banded = row_idx % 2 == 0
                row_format = formats["banded"] if is_banded else formats["default"]
                if row_format_fn:
                    row_format = row_format_fn(
                        row_idx,
                        row,
                        formats,
                        is_banded,
                    )
                for col_idx, value in enumerate(row):
                    worksheet.write_string(row_idx, col_idx, value, row_format)

            for col_idx, width in enumerate(widths):
                worksheet.set_column(col_idx, col_idx, min(width + 2, 60))

        workbook.close()
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def _extract_cell_value(row: Any, header: str) -> str:
        if isinstance(row, dict):
            value = row.get(header)
            if value is None:
                value = row.get(header.lower()) or row.get(header.replace(" ", "_"))
        else:
            value = row
        if value is None:
            return ""
        return str(value)

    def _append_osint(self, files: List[Tuple[str, bytes]]) -> None:
        osint_rows = self.artifacts.get("osint")
        if not isinstance(osint_rows, list) or not osint_rows:
            return

        workbook_bytes = self._create_workbook(
            [
                {
                    "name": "OSINT",
                    "headers": ["Domain", "Hostname", "altNames", "IP", "Port", "Info"],
                    "rows": osint_rows,
                }
            ]
        )
        files.append((f"{self.client_name} OSINT Report.xlsx", workbook_bytes))

    def _append_dns_findings(self, files: List[Tuple[str, bytes]]) -> None:
        findings = self.artifacts.get("dns_findings")
        if not isinstance(findings, dict):
            return

        sheets = []
        for domain, entries in findings.items():
            if not isinstance(entries, list) or not entries:
                continue
            sheets.append(
                {
                    "name": str(domain) if domain else "DNS",
                    "headers": ["Test", "Status", "Info"],
                    "rows": entries,
                }
            )

        if sheets:
            workbook_bytes = self._create_workbook(sheets)
            files.append((f"{self.client_name} DNS Records.xlsx", workbook_bytes))

    def _append_dns_records(self, files: List[Tuple[str, bytes]]) -> None:
        records = self.artifacts.get("dns_records")
        if not isinstance(records, dict):
            return

        headers = [
            "type",
            "zone_transfer",
            "ns_server",
            "domain",
            "mname",
            "address",
            "target",
            "recursive",
            "Version",
            "exchange",
            "name",
            "strings",
        ]
        sheets = []
        for domain, entries in records.items():
            if not isinstance(entries, list) or not entries:
                continue
            sheets.append(
                {
                    "name": str(domain) if domain else "DNS Records",
                    "headers": headers,
                    "rows": entries,
                }
            )

        if sheets:
            workbook_bytes = self._create_workbook(sheets)
            files.append((f"{self.client_name} DNS Report.xlsx", workbook_bytes))

    def _append_internal_software(self, files: List[Tuple[str, bytes]]) -> None:
        internal = self.artifacts.get("internal_nexpose_findings")
        if not isinstance(internal, dict):
            return
        software_entries = internal.get("software")
        if not isinstance(software_entries, list) or not software_entries:
            return

        workbook_bytes = self._create_workbook(
            [
                {
                    "name": "Software",
                    "headers": ["System", "Software", "Version"],
                    "rows": software_entries,
                }
            ]
        )
        files.append((f"{self.client_name} Internal System Installed Software.xlsx", workbook_bytes))

    def _append_ad_reports(self, files: List[Tuple[str, bytes]]) -> None:
        ad_artifacts = self.artifacts.get("ad")
        if not isinstance(ad_artifacts, dict):
            return

        report_configs = [
            ("domain_admins", "IAM - Domain Admins", ["Account", "Password Last Set"]),
            ("ent_admins", "IAM - Enterprise Admins", ["Account", "Password Last Set"]),
            ("exp_passwords", "IAM - Accounts with Expired Passwords", ["Account", "Password Last Set"]),
            (
                "passwords_never_exp",
                "IAM - Accounts with Passwords that Never Expire",
                ["Account", "Password Last Set"],
            ),
            (
                "inactive_accounts",
                "IAM - Potentially Inactive Accounts",
                ["Account", "LastLogin", "Creation Date", "Days Past"],
            ),
            ("generic_accounts", "IAM - Generic Accounts", ["Account", "Creation Date"]),
            (
                "generic_logins",
                "IAM - Systems Logged in with Generic Accounts",
                ["Computer", "Username"],
            ),
            (
                "old_passwords",
                "IAM – Accounts with Old Passwords",
                ["Account", "Password Last Set Date", "Days Past Due"],
            ),
        ]

        for key, label, headers in report_configs:
            sheets = []
            for domain, entries in ad_artifacts.items():
                if not isinstance(entries, dict):
                    continue
                domain_entries = entries.get(key)
                if not isinstance(domain_entries, list) or not domain_entries:
                    continue
                sheets.append(
                    {
                        "name": str(domain) if domain else label,
                        "headers": headers,
                        "rows": domain_entries,
                    }
                )

            if sheets:
                workbook_bytes = self._create_workbook(sheets)
                files.append((f"{self.client_name} {label}.xlsx", workbook_bytes))

    def _append_snmp_reports(self, files: List[Tuple[str, bytes]]) -> None:
        snmp_entries = self.artifacts.get("snmp")
        snmp_hosts = self.artifacts.get("snmp_hosts")
        sheets = []

        if isinstance(snmp_entries, list) and snmp_entries:
            sheets.append(
                {
                    "name": "SNMP",
                    "headers": ["Host", "String", "Desc", "Access"],
                    "rows": snmp_entries,
                    "row_format_fn": self._format_snmp_row,
                }
            )

        if isinstance(snmp_hosts, list) and snmp_hosts:
            sheets.append(
                {
                    "name": "Hosts",
                    "headers": ["Host"],
                    "rows": snmp_hosts,
                }
            )

        if sheets:
            workbook_bytes = self._create_workbook(sheets)
            files.append((f"{self.client_name} Insecure SNMP Community String Findings.xlsx", workbook_bytes))

    @staticmethod
    def _format_snmp_row(row_idx: int, row: List[str], formats: Dict[str, Any], is_banded: bool):
        access_value = ""
        if isinstance(row, list) and len(row) >= 4:
            access_value = row[3]
        elif isinstance(row, dict):
            access_value = str(row.get("Access", ""))
        elif isinstance(row, (list, tuple)):
            access_value = row[1] if len(row) > 1 else ""

        if str(access_value).lower() == "read-write":
            return formats["banded_red"] if is_banded else formats["default_red"]
        return formats["banded"] if is_banded else formats["default"]

    def _append_processed_metrics(self, files: List[Tuple[str, bytes]]) -> None:
        self._append_processed_payload(
            files,
            self.artifacts.get("web_metrics"),
            f"{self.client_name} Detailed Web App Vulnerability Findings.xlsx",
        )
        self._append_processed_payload(
            files,
            self.artifacts.get("firewall_metrics"),
            f"{self.client_name} Detailed Firewall Vulnerability Findings.xlsx",
        )

        endpoint_artifacts = self.artifacts.get("endpoint")
        if isinstance(endpoint_artifacts, dict):
            metrics_map = (
                endpoint_artifacts.get("metrics")
                if isinstance(endpoint_artifacts.get("metrics"), dict)
                else {}
            )
            if metrics_map:
                for domain, payload in metrics_map.items():
                    filename = f"{self.client_name} Detailed Endpoint Findings.xlsx"
                    if domain:
                        filename = f"{self.client_name} Detailed Endpoint Findings ({domain}).xlsx"
                    self._append_processed_payload(files, payload, filename)

    def _append_processed_payload(self, files: List[Tuple[str, bytes]], payload: Any, filename: str) -> None:
        if not isinstance(payload, dict):
            return
        workbook_b64 = payload.get("xlsx_base64")
        if not workbook_b64:
            return

        try:
            workbook_bytes = base64.b64decode(workbook_b64)
        except (ValueError, binascii.Error):
            logger.exception("Failed to decode supplemental XLSX payload")
            return

        if not isinstance(workbook_bytes, (bytes, bytearray)):
            return

        files.append((filename, workbook_bytes))
