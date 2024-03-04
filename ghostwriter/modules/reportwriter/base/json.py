
import json
import io

from ghostwriter.modules.reportwriter.base.base import ExportBase


class ExportBaseJson(ExportBase):
    """
    JSON exporter.

    Runs `json.dump` over `self.data` and returns the result.
    """
    def run(self) -> io.BytesIO:
        s_out = io.TextIOWrapper(io.BytesIO(), "utf-8", write_through=True)
        json.dump(self.data, s_out, indent=4, ensure_ascii=True)
        s_out.flush()
        return s_out.detach()
