
import json
import io

from ghostwriter.modules.reportwriter.export_report_base import ExportReportBase


class ExportReportJson(ExportReportBase):
    def run(self) -> io.StringIO:
        out = io.StringIO()
        json.dump(self.data, out, indent=4, ensure_ascii=True)
        return out
