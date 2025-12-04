"""Helpers for generating supplemental XLSX documents from project data artifacts."""

from __future__ import annotations

import base64
import binascii
import io
import logging
import re
from typing import Any, Callable, Dict, Iterable, List, Sequence, Tuple

from django.utils.dateparse import parse_date, parse_datetime
from xlsxwriter.workbook import Workbook

from ghostwriter.rolodex.data_parsers import NEXPOSE_UPLOAD_REQUIREMENTS_BY_SLUG
from ghostwriter.rolodex.workbook import (
    CLOUD_MANAGEMENT_REQUIREMENT_SLUG,
    SQL_DATA_REQUIREMENT_SLUG,
    WIRELESS_DATA_REQUIREMENT_SLUG,
)

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
        data_files = getattr(project, "data_files", None)
        if data_files is not None:
            self.data_files_by_slug = {
                data_file.requirement_slug: data_file
                for data_file in data_files.all()
                if getattr(data_file, "requirement_slug", "")
            }
        else:
            self.data_files_by_slug = {}

    def build(self) -> List[Tuple[str, bytes]]:
        files: List[Tuple[str, bytes]] = []

        self._append_osint(files)
        self._append_dns_findings(files)
        self._append_dns_records(files)
        self._append_internal_software(files)
        self._append_ad_reports(files)
        self._append_snmp_reports(files)
        self._append_processed_metrics(files)
        self._append_cloud_management_upload(files)
        self._append_wireless_upload(files)
        self._append_sql_upload(files)
        self._append_uploaded_nexpose(files)

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

            widths = [self._string_width(header) for header in headers]
            normalized_rows: List[Tuple[List[str], Any]] = []
            for row in rows:
                normalized_row: List[str] = []
                for idx, header in enumerate(headers):
                    value = self._extract_cell_value(row, header)
                    normalized_row.append(value)
                    widths[idx] = max(widths[idx], self._string_width(value))
                normalized_rows.append((normalized_row, row))

            for col_idx, title in enumerate(headers):
                worksheet.write_string(0, col_idx, title, formats["header"])

            for row_idx, (row, raw_row) in enumerate(normalized_rows, start=1):
                is_banded = row_idx % 2 == 0
                row_format = formats["banded"] if is_banded else formats["default"]
                if row_format_fn:
                    row_format = row_format_fn(
                        row_idx,
                        raw_row,
                        formats,
                        is_banded,
                    )
                for col_idx, value in enumerate(row):
                    worksheet.write_string(row_idx, col_idx, value, row_format)

            for col_idx, width in enumerate(widths):
                worksheet.set_column(col_idx, col_idx, width + 2)

        workbook.close()
        output.seek(0)
        return output.getvalue()

    @staticmethod
    def _string_width(value: str) -> int:
        """Estimate column width based on the longest line of the value."""

        return max((len(line) for line in str(value).splitlines()), default=0)

    @staticmethod
    def _extract_cell_value(row: Any, header: str) -> str:
        if isinstance(row, dict):
            value = row.get(header)
            if value is None:
                alt_header = header.replace(" ", "")
                value = (
                    row.get(header.lower())
                    or row.get(header.replace(" ", "_"))
                    or row.get(alt_header)
                    or row.get(alt_header.lower())
                )
        else:
            value = row
        if value is None:
            return ""
        return str(value)

    def _append_osint(self, files: List[Tuple[str, bytes]]) -> None:
        osint_rows = self.artifacts.get("osint")
        if not isinstance(osint_rows, list) or not osint_rows:
            return

        sorted_rows = sorted(
            osint_rows,
            key=lambda row: (
                self._string_value(row, "Domain").lower(),
                self._string_value(row, "Hostname").lower(),
            ),
        )

        workbook_bytes = self._create_workbook(
            [
                {
                    "name": "OSINT",
                    "headers": ["Domain", "Hostname", "altNames", "IP", "Port", "Info"],
                    "rows": sorted_rows,
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
            files.append((f"{self.client_name} DNS Report.xlsx", workbook_bytes))

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
            files.append((f"{self.client_name} DNS Records.xlsx", workbook_bytes))

    def _append_internal_software(self, files: List[Tuple[str, bytes]]) -> None:
        internal = self.artifacts.get("internal_nexpose_findings")
        if not isinstance(internal, dict):
            return
        software_entries = internal.get("software")
        if not isinstance(software_entries, list) or not software_entries:
            return

        sorted_rows = sorted(
            software_entries,
            key=lambda row: (
                self._numeric_sort_key(self._string_value(row, "System")),
                self._string_value(row, "Software").lower(),
            ),
        )

        workbook_bytes = self._create_workbook(
            [
                {
                    "name": "Software",
                    "headers": ["System", "Software", "Version"],
                    "rows": sorted_rows,
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
                    ["Account", "Last Login", "Creation Date", "Days Past"],
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

        sort_strategies = {
            "inactive_accounts": lambda r: (
                self._numeric_sort_key_desc(self._string_value(r, "Days Past")),
                self._string_value(r, "Account").lower(),
            ),
            "generic_accounts": lambda r: (
                self._date_sort_key(self._string_value(r, "Creation Date")),
                self._string_value(r, "Account").lower(),
            ),
            "generic_logins": lambda r: (
                self._string_value(r, "Computer").lower(),
                self._string_value(r, "Username").lower(),
            ),
            "old_passwords": lambda r: (
                self._numeric_sort_key_desc(self._string_value(r, "Days Past Due")),
                self._string_value(r, "Account").lower(),
            ),
        }

        for key, label, headers in report_configs:
            sheets = []
            for domain, entries in ad_artifacts.items():
                if not isinstance(entries, dict):
                    continue
                domain_entries = entries.get(key)
                if not isinstance(domain_entries, list) or not domain_entries:
                    continue

                sorter = sort_strategies.get(key) or (
                    lambda r: (
                        self._date_sort_key(self._string_value(r, "Password Last Set")),
                        self._string_value(r, "Account").lower(),
                    )
                )
                sorted_rows = sorted(domain_entries, key=sorter)
                sheets.append(
                    {
                        "name": str(domain) if domain else label,
                        "headers": headers,
                        "rows": sorted_rows,
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
            sorted_snmp = sorted(
                snmp_entries,
                key=lambda r: (
                    self._numeric_sort_key(self._string_value(r, "Host")),
                    self._string_value(r, "String").lower(),
                ),
            )
            sheets.append(
                {
                    "name": "SNMP",
                    "headers": ["Host", "String", "Desc"],
                    "rows": sorted_snmp,
                    "row_format_fn": self._format_snmp_row,
                }
            )

        if isinstance(snmp_hosts, list) and snmp_hosts:
            sorted_hosts = sorted(
                snmp_hosts,
                key=lambda r: self._numeric_sort_key(self._string_value(r, "Host")),
            )
            sheets.append(
                {
                    "name": "Hosts",
                    "headers": ["Host"],
                    "rows": sorted_hosts,
                }
            )

        if sheets:
            workbook_bytes = self._create_workbook(sheets)
            files.append((f"{self.client_name} Insecure SNMP Community String Findings.xlsx", workbook_bytes))

    @staticmethod
    def _format_snmp_row(row_idx: int, row: List[str], formats: Dict[str, Any], is_banded: bool):
        access_value = ""
        if isinstance(row, dict):
            access_value = row.get("Access") or row.get("access") or row.get("ACCESS")
        elif isinstance(row, (list, tuple)):
            access_value = row[3] if len(row) > 3 else (row[1] if len(row) > 1 else "")

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
                base_filename = f"{self.client_name} Detailed Endpoint Findings.xlsx"
                if len(metrics_map) == 1:
                    payload = next(iter(metrics_map.values()))
                    self._append_processed_payload(files, payload, base_filename)
                else:
                    for idx, (domain, payload) in enumerate(metrics_map.items()):
                        suffix = f" - {domain}" if domain else f" - {idx + 1}"
                        self._append_processed_payload(files, payload, f"{base_filename[:-5]}{suffix}.xlsx")

        self._append_password_metrics(files)

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

    def _append_password_metrics(self, files: List[Tuple[str, bytes]]):
        password_payload = self.artifacts.get("password")
        if not isinstance(password_payload, dict):
            return

        raw_rows = password_payload.get("raw") if isinstance(password_payload.get("raw"), list) else []
        domains = password_payload.get("domains") if isinstance(password_payload.get("domains"), dict) else {}
        if not raw_rows or not domains:
            return

        workbook_bytes = self._render_password_workbook(
            raw_rows,
            domains,
            include_ntlm_state=False,
        )
        if not workbook_bytes:
            return

        filename = f"{self.client_name} Detailed Password Strength Findings.xlsx"
        files.append((filename, workbook_bytes))

    @staticmethod
    def _render_password_workbook(
        raw_rows: List[Dict[str, str]],
        domains: Dict[str, Dict[str, Any]],
        *,
        include_ntlm_state: bool,
    ) -> bytes | None:
        buffer = io.BytesIO()
        workbook = Workbook(buffer, {"in_memory": True})

        header_format = workbook.add_format(
            {"bold": True, "border": 1, "bg_color": "#0066CC", "font_color": "white"}
        )
        text_format = workbook.add_format({"text_wrap": True, "border": 1})
        banded_text_format = workbook.add_format(
            {"text_wrap": True, "border": 1, "bg_color": "#99CCFF"}
        )

        def _write_table(
            worksheet, headers: List[str], data_rows: List[List[str]]
        ) -> None:
            for col, header in enumerate(headers):
                worksheet.write(0, col, header, header_format)

            column_widths: List[int] = [len(header) for header in headers]
            for row_idx, row_values in enumerate(data_rows, start=1):
                row_format = banded_text_format if row_idx % 2 == 0 else text_format
                for col_idx, value in enumerate(row_values):
                    worksheet.write(row_idx, col_idx, value, row_format)
                    if col_idx >= len(column_widths):
                        column_widths.append(0)
                    column_widths[col_idx] = max(column_widths[col_idx], len(str(value)))

            for col, width in enumerate(column_widths):
                worksheet.set_column(col, col, min(max(width + 2, 10), 60))

        def _row_value(entry: Dict[str, Any], key: str) -> str:
            for current_key, value in entry.items():
                if (current_key or "").lower().strip() == key:
                    return (value or "").strip()
            return ""

        raw_headers = [
            "Domain",
            "Username",
            "NTLM Hash",
            "NTLM Password",
        ]
        if include_ntlm_state:
            raw_headers.append("NTLM State")
        raw_headers.extend(
            [
                "User Info",
                "Last Changed Time",
                "Lockout",
                "Disabled",
                "Expired",
                "No Expire",
                "LM Hash",
            ]
        )

        cracked_headers = [
            "Domain",
            "Username",
            "NTLM Hash",
            "NTLM Password",
        ]
        if include_ntlm_state:
            cracked_headers.append("NTLM State")
        cracked_headers.extend(
            [
                "User Info",
                "Last Changed Time",
                "Lockout",
                "Disabled",
                "Expired",
                "No Expire",
            ]
        )
        enabled_headers = [
            "Domain",
            "Username",
            "NTLM Password",
            "User Info",
            "Last Changed Time",
            "Lockout",
            "Disabled",
            "Expired",
            "No Expire",
        ]
        lanman_headers = ["Username", "LM Hash"]
        duplicates_headers = ["NTLM Password", "Count"]

        raw_sheet = workbook.add_worksheet("raw")
        raw_data_rows = [
            [_row_value(row, header.lower()) for header in raw_headers]
            for row in raw_rows
            if isinstance(row, dict)
        ]
        _write_table(raw_sheet, raw_headers, raw_data_rows)

        for domain_payload in domains.values():
            if not isinstance(domain_payload, dict):
                continue
            sheet_names = domain_payload.get("sheets") if isinstance(domain_payload.get("sheets"), dict) else {}
            domain_name = (domain_payload.get("domain") or "NoDomain")[:31] or "NoDomain"

            cracked_sheet = workbook.add_worksheet(sheet_names.get("cracked") or f"cracked-{domain_name}")
            cracked_rows = [
                [_row_value(row, header.lower()) for header in cracked_headers]
                for row in domain_payload.get("cracked", [])
                if isinstance(row, dict)
            ]
            _write_table(cracked_sheet, cracked_headers, cracked_rows)

            admin_sheet = workbook.add_worksheet(sheet_names.get("admin") or f"admin-{domain_name}")
            admin_rows = [
                [_row_value(row, header.lower()) for header in cracked_headers]
                for row in domain_payload.get("admin", [])
                if isinstance(row, dict)
            ]
            _write_table(admin_sheet, cracked_headers, admin_rows)

            enabled_sheet = workbook.add_worksheet(sheet_names.get("enabled") or f"enabled-{domain_name}")
            enabled_rows = [
                [_row_value(row, header.lower()) for header in enabled_headers]
                for row in domain_payload.get("enabled", [])
                if isinstance(row, dict)
            ]
            _write_table(enabled_sheet, enabled_headers, enabled_rows)

            lanman_sheet = workbook.add_worksheet(sheet_names.get("lanman") or f"LANMAN-{domain_name}")
            lanman_rows = [
                [_row_value(row, header.lower()) for header in lanman_headers]
                for row in domain_payload.get("lanman", [])
                if isinstance(row, dict)
            ]
            _write_table(lanman_sheet, lanman_headers, lanman_rows)

            duplicates_sheet = workbook.add_worksheet(sheet_names.get("duplicates") or f"duplicates-{domain_name}")
            duplicates_rows = [
                [entry.get("NTLM Password", ""), entry.get("Count", "")]
                for entry in domain_payload.get("duplicates", [])
                if isinstance(entry, dict)
            ]
            _write_table(duplicates_sheet, duplicates_headers, duplicates_rows)

        workbook.close()
        return buffer.getvalue()

    def _append_cloud_management_upload(self, files: List[Tuple[str, bytes]]):
        data_file = self.data_files_by_slug.get(CLOUD_MANAGEMENT_REQUIREMENT_SLUG)
        if not data_file or not getattr(data_file, "file", None):
            return

        try:
            content = data_file.file.read()
            if hasattr(data_file.file, "seek"):
                data_file.file.seek(0)
        except Exception:
            logger.exception(
                "Failed to read cloud management XLSX upload for project ID=%s",
                getattr(self.project, "id", "?"),
            )
            return

        if not isinstance(content, (bytes, bytearray)) or not content:
            return

        files.append(
            (
                f"{self.client_name} Detailed Cloud Management Benchmark Assessment.xlsx",
                content,
            )
        )

    def _append_wireless_upload(self, files: List[Tuple[str, bytes]]):
        data_file = self.data_files_by_slug.get(WIRELESS_DATA_REQUIREMENT_SLUG)
        if not data_file or not getattr(data_file, "file", None):
            return

        try:
            content = data_file.file.read()
            if hasattr(data_file.file, "seek"):
                data_file.file.seek(0)
        except Exception:
            logger.exception(
                "Failed to read wireless XLSX upload for project ID=%s",
                getattr(self.project, "id", "?"),
            )
            return

        if not isinstance(content, (bytes, bytearray)) or not content:
            return

        files.append(
            (f"{self.client_name} Detailed Wireless Findings.xlsx", content)
        )

    def _append_sql_upload(self, files: List[Tuple[str, bytes]]):
        data_file = self.data_files_by_slug.get(SQL_DATA_REQUIREMENT_SLUG)
        if not data_file or not getattr(data_file, "file", None):
            return

        try:
            content = data_file.file.read()
            if hasattr(data_file.file, "seek"):
                data_file.file.seek(0)
        except Exception:
            logger.exception(
                "Failed to read SQL XLSX upload for project ID=%s",
                getattr(self.project, "id", "?"),
            )
            return

        if not isinstance(content, (bytes, bytearray)) or not content:
            return

        files.append(
            (f"{self.client_name} SQL Instances Allowing Open Access.xlsx", content)
        )

    def _append_uploaded_nexpose(self, files: List[Tuple[str, bytes]]) -> None:
        for slug, definition in NEXPOSE_UPLOAD_REQUIREMENTS_BY_SLUG.items():
            data_file = self.data_files_by_slug.get(slug)
            if not data_file or not getattr(data_file, "file", None):
                continue

            try:
                content = data_file.file.read()
                if hasattr(data_file.file, "seek"):
                    data_file.file.seek(0)
            except Exception:
                logger.exception("Failed to read Nexpose XLSX upload for slug %s", slug)
                continue

            if not isinstance(content, (bytes, bytearray)) or not content:
                continue

            filename_template = definition.get("filename_template")
            if not filename_template:
                continue

            files.append((filename_template.format(client_name=self.client_name), content))

    @staticmethod
    def _string_value(row: Any, header: str) -> str:
        """Extract a cell value as a string without altering original row data."""

        if isinstance(row, dict):
            value = row.get(header)
            if value is None:
                alt_header = header.replace(" ", "")
                value = (
                    row.get(header.lower())
                    or row.get(header.replace(" ", "_"))
                    or row.get(alt_header)
                    or row.get(alt_header.lower())
                )
        else:
            value = row
        return "" if value is None else str(value)

    @staticmethod
    def _numeric_sort_key(value: str):
        """Sort helper that treats dotted-quad IPs and numeric strings numerically."""

        import ipaddress

        try:
            return (0, float(value))
        except (TypeError, ValueError):
            pass

        try:
            return (0, float(int(ipaddress.ip_address(value))))
        except (ValueError, ipaddress.AddressValueError):
            pass

        parts = [int(piece) if piece.isdigit() else piece.lower() for piece in re.split(r"(\d+)", value)]
        return (1, tuple(parts))

    def _numeric_sort_key_desc(self, value: str):
        """Descending numeric-first sort helper compatible with :meth:`_numeric_sort_key`."""

        flag, parsed = self._numeric_sort_key(value)
        if flag == 0:
            try:
                return (flag, -parsed)
            except TypeError:
                pass
        return (flag, parsed)

    @staticmethod
    def _date_sort_key(value: str) -> float:
        """Convert common date/datetime strings to a sortable timestamp, placing missing values last."""

        if not value:
            return float("inf")

        dt = parse_datetime(value) or parse_date(value)

        if dt is None:
            from datetime import datetime

            for fmt in (
                "%m/%d/%Y %H:%M",
                "%m/%d/%Y %H:%M:%S",
                "%m/%d/%y %H:%M",
                "%m/%d/%Y",
                "%m/%d/%y",
            ):
                try:
                    dt = datetime.strptime(value, fmt)
                    break
                except ValueError:
                    continue

        if dt is None:
            return float("inf")
        if hasattr(dt, "timestamp"):
            return dt.timestamp()

        from datetime import datetime as dt_class

        try:
            dt = dt_class.combine(dt, dt_class.min.time())
            return dt.timestamp()
        except Exception:
            return float("inf")
