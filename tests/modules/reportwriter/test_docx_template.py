"""Tests for the extended DOCX templating behaviour."""

from __future__ import annotations

import io
import re
import zipfile
from importlib import util
from pathlib import Path
from types import SimpleNamespace

import pytest
from docx.opc.packuri import PackURI
from docx.oxml import parse_xml
from jinja2 import Environment
from lxml import etree

MODULE_PATH = Path(__file__).resolve().parents[3] / "ghostwriter" / "modules" / "reportwriter" / "base" / "docx_template.py"
SPEC = util.spec_from_file_location("gw_docx_template", MODULE_PATH)
docx_template = util.module_from_spec(SPEC)
assert SPEC and SPEC.loader
SPEC.loader.exec_module(docx_template)
GhostwriterDocxTemplate = docx_template.GhostwriterDocxTemplate


DIAGRAM_XML = (
    '<dgm:data xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram">'
    "<dgm:t>{}</dgm:t>"
    "</dgm:data>"
)

DIAGRAM_SPLIT_XML = (
    '<dgm:data xmlns:dgm="http://schemas.openxmlformats.org/drawingml/2006/diagram">'
    "<dgm:t>{{{{</dgm:t><dgm:t>{}</dgm:t><dgm:t>}}}}</dgm:t>"
    "</dgm:data>"
)

WORKSHEET_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    "<row r=\"1\">"
    "<c r=\"A1\" t=\"inlineStr\"><is><t>{{ number }}</t></is></c>"
    "<c r=\"A2\" t=\"s\"><v>0</v></c>"
    "</row>"
    "</sheetData>"
    "</worksheet>"
)

SHARED_STRINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    "count=\"1\" uniqueCount=\"1\">"
    "<si><t>{{ chart_value }}</t></si>"
    "</sst>"
)

WORKSHEET_CHART_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    "<row r=\"1\">"
    "<c r=\"A1\"><v>{{ first_val }}</v></c>"
    "<c r=\"B1\" t=\"inlineStr\"><is><t>{{ first_label }}</t></is></c>"
    "</row>"
    "<row r=\"2\">"
    "<c r=\"A2\" t=\"s\"><v>0</v></c>"
    "<c r=\"B2\" t=\"s\"><v>1</v></c>"
    "</row>"
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TR_TC_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    "<row>{%tr for row in rows %}</row>"
    "<row>{% endtr %}</row>"
    "<c>{{tc row.value }}</c>"
    "<c>{%tc%}</c>"
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TR_TC_TRIMMED_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    "<row>{%-tr for row in rows -%}</row>"
    "<row>{%- endtr -%}</row>"
    "<c>{%-tc row.value -%}</c>"
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TR_ENDFOR_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    "<row>{%tr for site in sites %}</row>"
    "<row>{%tr endfor %}</row>"
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TR_SPLIT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    '<row><c t="inlineStr"><is><r><t>{%</t></r><r><t>tr for site in project.workbook_data.web.sites %}</t></r></is></c></row>'
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><r><t>{{ site.url }}</t></r></is></c>'
    '<c r="B2" t="inlineStr"><is><r><t>{{ site.unique_high }}</t></r></is></c>'
    '<c r="C2" t="inlineStr"><is><r><t>{{ site.unique_med }}</t></r></is></c>'
    '<c r="D2" t="inlineStr"><is><r><t>{{ site.unique_low }}</t></r></is></c>'
    '</row>'
    '<row><c t="inlineStr"><is><r><t>{%</t></r><r><t>tr endfor %}</t></r></is></c></row>'
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TC_SPLIT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
    "<sheetData>"
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><r><t>{{</t></r><r><t>tc site.url }}</t></r></is></c>'
    '<c r="B2" t="inlineStr"><is><r><t>{{</t></r><r><t>tc site.unique_high }}</t></r></is></c>'
    '</row>'
    "</sheetData>"
    "</worksheet>"
)

WORKSHEET_TR_LOOP_ROWS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<dimension ref="A1:D2"/>'
    '<sheetData>'
    '<row r="1">'
    '<c r="A1" t="inlineStr"><is><t>Site</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>High</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>Medium</t></is></c>'
    '<c r="D1" t="inlineStr"><is><t>Low</t></is></c>'
    '</row>'
    '<row>{%tr for site in sites %}</row>'
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><t>{{tc site.url }}</t></is></c>'
    '<c r="B2"><v>{{tc site.high }}</v></c>'
    '<c r="C2"><v>{{tc site.medium }}</v></c>'
    '<c r="D2"><v>{{tc site.low }}</v></c>'
    '</row>'
    '<row>{%tr endfor %}</row>'
    '</sheetData>'
    '</worksheet>'
)

WORKSHEET_TC_LOOP_TEMPLATE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheetData>'
    '<row r="1">'
    '<c r="A1" t="inlineStr"><is><t>Old Passwords</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>{%tc for domain in domains %}</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>{{ domain.name }}</t></is></c>'
    '<c r="D1" t="inlineStr"><is><t>{%tc endfor %}</t></is></c>'
    '</row>'
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><t>Compliant</t></is></c>'
    '<c r="B2" t="inlineStr"><is><t>{%tc for domain in domains %}</t></is></c>'
    '<c r="C2"><v>{{ domain.compliant }}</v></c>'
    '<c r="D2" t="inlineStr"><is><t>{%tc endfor %}</t></is></c>'
    '</row>'
    '<row r="3">'
    '<c r="A3" t="inlineStr"><is><t>Stale</t></is></c>'
    '<c r="B3" t="inlineStr"><is><t>{%tc for domain in domains %}</t></is></c>'
    '<c r="C3"><v>{{ domain.stale }}</v></c>'
    '<c r="D3" t="inlineStr"><is><t>{%tc endfor %}</t></is></c>'
    '</row>'
    '</sheetData>'
    '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
    '</worksheet>'
)

WORKSHEET_TC_RENDERED_COLUMNS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<sheetData>'
    '<row r="1">'
    '<c r="A1" t="inlineStr"><is><t>Metric</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>Edge-FW01</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>Edge-FW02</t></is></c>'
    '</row>'
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><t>High Risk</t></is></c>'
    '<c r="B2"><v>2</v></c>'
    '<c r="C2"><v>1</v></c>'
    '</row>'
    '<row r="3">'
    '<c r="A3" t="inlineStr"><is><t>Medium Risk</t></is></c>'
    '<c r="B3"><v>5</v></c>'
    '<c r="C3"><v>4</v></c>'
    '</row>'
    '<row r="4">'
    '<c r="A4" t="inlineStr"><is><t>Low Risk</t></is></c>'
    '<c r="B4"><v>3</v></c>'
    '<c r="C4"><v>2</v></c>'
    '</row>'
    '</sheetData>'
    '<tableParts count="1"><tablePart r:id="rId1"/></tableParts>'
    '</worksheet>'
)

WORKSHEET_TR_PROJECT_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<dimension ref="A1:D2"/>'
    '<sheetData>'
    '<row><c r="A1" t="inlineStr"><is><t>{%tr for site in project.workbook_data.web.sites %}</t></is></c></row>'
    '<row r="2">'
    '<c r="A2" t="inlineStr"><is><t>{{ site.url }}</t></is></c>'
    '<c r="B2" t="inlineStr"><is><t>{{ site.unique_high }}</t></is></c>'
    '<c r="C2" t="inlineStr"><is><t>{{ site.unique_med }}</t></is></c>'
    '<c r="D2" t="inlineStr"><is><t>{{ site.unique_low }}</t></is></c>'
    '</row>'
    '<row><c r="A3" t="inlineStr"><is><t>{%tr endfor %}</t></is></c></row>'
    '</sheetData>'
    '</worksheet>'
)

WORKSHEET_TR_RENDERED_GAPS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<dimension ref="A1:D5"/>'
    '<sheetData>'
    '<row r="1">'
    '<c r="A1" t="inlineStr"><is><t>Site</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>High Risk</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>Medium Risk</t></is></c>'
    '<c r="D1" t="inlineStr"><is><t>Low Risk</t></is></c>'
    '</row>'
    '<row r="2" spans="1:4"/>'
    '<row r="3">'
    '<c r="A3" t="inlineStr"><is><t>https://alpha</t></is></c>'
    '<c r="B3"><v>3</v></c>'
    '<c r="C3"><v>7</v></c>'
    '<c r="D3"><v>5</v></c>'
    '</row>'
    '<row r="4">'
    '<c r="A4" t="inlineStr"><is><t> </t></is></c>'
    '</row>'
    '<row r="5">'
    '<c r="A5" t="inlineStr"><is><t>https://beta</t></is></c>'
    '<c r="B5"><v>1</v></c>'
    '<c r="C5"><v>4</v></c>'
    '<c r="D5"><v>2</v></c>'
    '</row>'
    '</sheetData>'
    '</worksheet>'
)

WORKSHEET_TR_SHARED_STRINGS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    '<dimension ref="A1:D2"/>'
    '<sheetData>'
    '<row r="1">'
    '<c r="A1" t="inlineStr"><is><t>Site</t></is></c>'
    '<c r="B1" t="inlineStr"><is><t>High</t></is></c>'
    '<c r="C1" t="inlineStr"><is><t>Medium</t></is></c>'
    '<c r="D1" t="inlineStr"><is><t>Low</t></is></c>'
    '</row>'
    '<row>{%tr for site in sites %}</row>'
    '<row r="2">'
    '<c r="A2" t="s"><v>0</v></c>'
    '<c r="B2" t="s"><v>1</v></c>'
    '<c r="C2" t="s"><v>2</v></c>'
    '<c r="D2" t="s"><v>3</v></c>'
    '</row>'
    '<row>{%tr endfor %}</row>'
    '</sheetData>'
    '</worksheet>'
)

SHARED_STRINGS_TR_LOOP_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'count="4" uniqueCount="4">'
    '<si><t>{{tc site.url }}</t></si>'
    '<si><t>{{tc site.high }}</t></si>'
    '<si><t>{{tc site.medium }}</t></si>'
    '<si><t>{{tc site.low }}</t></si>'
    '</sst>'
)

SHARED_STRINGS_CHART_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    "count=\"2\" uniqueCount=\"2\">"
    "<si><t>{{ second_val }}</t></si>"
    "<si><t>{{ second_label }}</t></si>"
    "</sst>"
)

CHART_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<c:chart>"
    "<c:plotArea>"
    "<c:lineChart>"
    "<c:ser>"
    "<c:val><c:numRef><c:f>Sheet1!$A$1:$A$2</c:f>"
    "<c:numCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>1</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>2</c:v></c:pt>"
    "</c:numCache></c:numRef>"
    "<c:numLit><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>3</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>4</c:v></c:pt>"
    "</c:numLit></c:val>"
    "<c:cat><c:strRef><c:f>Sheet1!$B$1:$B$2</c:f>"
    "<c:strCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>First</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Second</c:v></c:pt>"
    "</c:strCache></c:strRef>"
    "<c:strLit><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>Old</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Values</c:v></c:pt>"
    "</c:strLit></c:cat>"
    "</c:ser>"
    "</c:lineChart>"
    "</c:plotArea>"
    "</c:chart>"
    "<c:externalData r:id=\"rId1\"><c:autoUpdate val=\"0\"/></c:externalData>"
    "</c:chartSpace>"
)

CHART_RICH_TEXT_SPLIT_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
    "<c:chart>"
    "<c:title><c:tx><c:rich>"
    "<a:p><a:pPr><a:defRPr/></a:pPr>"
    "<a:r><a:rPr lang=\"en-US\"/></a:r>"
    "<a:r><a:t>{{</a:t></a:r>"
    "<a:r><a:rPr lang=\"en-US\"/></a:r>"
    "<a:r><a:t> value }}</a:t></a:r>"
    "</a:p></c:rich></c:tx></c:title>"
    "</c:chart>"
    "</c:chartSpace>"
)

CHART_TC_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
    "<c:chart><c:plotArea><c:ser>"
    "{%tc for device in devices %}"
    '<c:idx val="{{ loop.index0 }}"/>'
    "<c:tx><c:v>{{ device.name }}</c:v></c:tx>"
    "{%tc endfor %}"
    "</c:ser></c:plotArea></c:chart>"
    "</c:chartSpace>"
)

CHART_TR_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart">'
    "<c:chart><c:plotArea><c:ser>"
    "{%tr for device in devices %}"
    '<c:idx val="{{ loop.index0 }}"/>'
    "<c:tx><c:v>{{ device.name }}</c:v></c:tx>"
    "{%tr endfor %}"
    "</c:ser></c:plotArea></c:chart>"
    "</c:chartSpace>"
)

CHART_EXT_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
    'xmlns:x14="http://schemas.microsoft.com/office/drawing/2010/chart">'
    "<c:chart>"
    "<c:plotArea>"
    "<c:barChart>"
    "<c:ser>"
    "<c:val><c:numRef><c:f>Sheet1!$A$1:$A$2</c:f>"
    "<c:numCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>1</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>2</c:v></c:pt>"
    "</c:numCache>"
    "<c:extLst><c:ext uri=\"{C5E0089C-D5B0-43F5-8A56-9C2E5A163620}\">"
    "<x14:numRef><x14:f>Sheet1!$A$1:$A$2</x14:f>"
    "<x14:numCache><x14:ptCount val=\"2\"/>"
    "<x14:pt idx=\"0\"><x14:v>1</x14:v></x14:pt>"
    "<x14:pt idx=\"1\"><x14:v>2</x14:v></x14:pt>"
    "</x14:numCache></x14:numRef>"
    "</c:ext></c:extLst>"
    "</c:numRef></c:val>"
    "<c:cat><c:strRef><c:f>Sheet1!$B$1:$B$2</c:f>"
    "<c:strCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>Old</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Data</c:v></c:pt>"
    "</c:strCache>"
    "<c:extLst><c:ext uri=\"{C5E0089C-D5B0-43F5-8A56-9C2E5A163620}\">"
    "<x14:strRef><x14:f>Sheet1!$B$1:$B$2</x14:f>"
    "<x14:strCache><x14:ptCount val=\"2\"/>"
    "<x14:pt idx=\"0\"><x14:v>Old</x14:v></x14:pt>"
    "<x14:pt idx=\"1\"><x14:v>Data</x14:v></x14:pt>"
    "</x14:strCache></x14:strRef>"
    "</c:ext></c:extLst>"
    "</c:strRef></c:cat>"
    "</c:ser>"
    "</c:barChart>"
    "</c:plotArea>"
    "</c:chart>"
    "<c:externalData r:id=\"rId1\"><c:autoUpdate val=\"0\"/></c:externalData>"
    "</c:chartSpace>"
)

WORKBOOK_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<sheets><sheet name=\"Sheet1\" sheetId=\"1\" r:id=\"rId1\"/></sheets>"
    "</workbook>"
)

WORKBOOK_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" '
    'Target="worksheets/sheet1.xml"/>'
    "</Relationships>"
)

CONTENT_TYPES_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    "</Types>"
)

CONTENT_TYPES_WITH_TABLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>'
    '<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>'
    '<Override PartName="/xl/sharedStrings.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sharedStrings+xml"/>'
    '<Override PartName="/xl/tables/table1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.table+xml"/>'
    "</Types>"
)

WORKSHEET_TABLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<sheetData>"
    "<row r=\"1\">"
    "<c r=\"A1\" t=\"inlineStr\"><is><t>Numbers</t></is></c>"
    "<c r=\"B1\" t=\"inlineStr\"><is><t>Labels</t></is></c>"
    "</row>"
    "<row r=\"2\">"
    "<c r=\"A2\"><v>{{ first_number }}</v></c>"
    "<c r=\"B2\" t=\"inlineStr\"><is><t>{{ first_label }}</t></is></c>"
    "</row>"
    "<row r=\"3\">"
    "<c r=\"A3\"><v>{{ second_number }}</v></c>"
    "<c r=\"B3\" t=\"inlineStr\"><is><t>{{ second_label }}</t></is></c>"
    "</row>"
    "</sheetData>"
    "<tableParts count=\"1\"><tablePart r:id=\"rId1\"/></tableParts>"
    "</worksheet>"
)

WORKSHEET_TABLE_RENAME_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<sheetData>"
    "<row r=\"1\">"
    "<c r=\"A1\" t=\"inlineStr\"><is><t>{{ first_header }}</t></is></c>"
    "<c r=\"B1\" t=\"inlineStr\"><is><t>{{ second_header }}</t></is></c>"
    "</row>"
    "<row r=\"2\">"
    "<c r=\"A2\"><v>{{ first_number }}</v></c>"
    "<c r=\"B2\" t=\"inlineStr\"><is><t>{{ first_label }}</t></is></c>"
    "</row>"
    "<row r=\"3\">"
    "<c r=\"A3\"><v>{{ second_number }}</v></c>"
    "<c r=\"B3\" t=\"inlineStr\"><is><t>{{ second_label }}</t></is></c>"
    "</row>"
    "</sheetData>"
    "<tableParts count=\"1\"><tablePart r:id=\"rId1\"/></tableParts>"
    "</worksheet>"
)

WORKSHEET_TABLE_LOOP_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<sheetData>"
    "<row r=\"1\">"
    "<c r=\"A1\" t=\"inlineStr\"><is><t>Numbers</t></is></c>"
    "<c r=\"B1\" t=\"inlineStr\"><is><t>Labels</t></is></c>"
    "</row>"
    "{% for row in rows %}"
    "<row r=\"{{ loop.index + 1 }}\">"
    "<c r=\"A{{ loop.index + 1 }}\"><v>{{ row.number }}</v></c>"
    "<c r=\"B{{ loop.index + 1 }}\" t=\"inlineStr\"><is><t>{{ row.label }}</t></is></c>"
    "</row>"
    "{% endfor %}"
    "</sheetData>"
    "<tableParts count=\"1\"><tablePart r:id=\"rId1\"/></tableParts>"
    "</worksheet>"
)

TABLE_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'id="1" name="Table1" displayName="Table1" ref="A1:B3" headerRowCount="1">'
    '<tableColumns count="2">'
    '<tableColumn id="1" name="Numbers"/>'
    '<tableColumn id="2" name="Labels"/>'
    '</tableColumns>'
    '<autoFilter ref="A1:B3"/>'
    '</table>'
)

TABLE_PLACEHOLDER_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'id="1" name="Table1" displayName="Table1" ref="A1:B3" headerRowCount="1">'
    '<tableColumns count="2">'
    '<tableColumn id="1" name="Column1"/>'
    '<tableColumn id="2" name="Column2"/>'
    '</tableColumns>'
    '<autoFilter ref="A1:B3"/>'
    '</table>'
)

TABLE_SMALL_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'id="1" name="Table1" displayName="Table1" ref="A1:B2" headerRowCount="1">'
    '<tableColumns count="2">'
    '<tableColumn id="1" name="Numbers"/>'
    '<tableColumn id="2" name="Labels"/>'
    '</tableColumns>'
    '<autoFilter ref="A1:B2"/>'
    '</table>'
)

TABLE_TC_NARROW_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<table xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" '
    'id="1" name="Table1" displayName="Table1" ref="A1:B4" headerRowCount="1">'
    '<tableColumns count="2">'
    '<tableColumn id="1" name="Metric"/>'
    '<tableColumn id="2" name="Placeholder"/>'
    '</tableColumns>'
    '<autoFilter ref="A1:B4"/>'
    '</table>'
)

SHEET_TABLE_RELS_XML = (
    '<?xml version="1.0" encoding="UTF-8"?>'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/table" '
    'Target="../tables/table1.xml"/>'
    "</Relationships>"
)

CHART_TABLE_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<c:chart>"
    "<c:plotArea>"
    "<c:lineChart>"
    "<c:ser>"
    "<c:val><c:numRef><c:f>Sheet1!Table1[Numbers]</c:f>"
    "<c:numCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>1</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>2</c:v></c:pt>"
    "</c:numCache></c:numRef></c:val>"
    "<c:cat><c:strRef><c:f>Sheet1!Table1[Labels]</c:f>"
    "<c:strCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>First</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Second</c:v></c:pt>"
    "</c:strCache></c:strRef></c:cat>"
    "</c:ser>"
    "</c:lineChart>"
    "</c:plotArea>"
    "</c:chart>"
    "<c:externalData r:id=\"rId1\"><c:autoUpdate val=\"0\"/></c:externalData>"
    "</c:chartSpace>"
)

CHART_TABLE_PLACEHOLDER_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<c:chart>"
    "<c:plotArea>"
    "<c:lineChart>"
    "<c:ser>"
    "<c:val><c:numRef><c:f>Sheet1!Table1[Column1]</c:f>"
    "<c:numCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>1</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>2</c:v></c:pt>"
    "</c:numCache></c:numRef></c:val>"
    "<c:cat><c:strRef><c:f>Sheet1!Table1[Column2]</c:f>"
    "<c:strCache><c:ptCount val=\"2\"/>"
    "<c:pt idx=\"0\"><c:v>First</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Second</c:v></c:pt>"
    "</c:strCache></c:strRef></c:cat>"
    "</c:ser>"
    "</c:lineChart>"
    "</c:plotArea>"
    "</c:chart>"
    "<c:externalData r:id=\"rId1\"><c:autoUpdate val=\"0\"/></c:externalData>"
    "</c:chartSpace>"
)

CHART_NUMCACHE_MISMATCH_XML = (
    '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
    'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
    "<c:chart>"
    "<c:plotArea>"
    "<c:barChart>"
    "<c:ser>"
    "<c:tx><c:strRef><c:f>Sheet1!$B$1</c:f>"
    "<c:strCache><c:ptCount val=\"1\"/><c:pt idx=\"0\"><c:v>High Risk</c:v></c:pt></c:strCache>"
    "</c:strRef></c:tx>"
    "<c:val><c:numRef><c:f>Sheet1!$B$2:$B$4</c:f>"
    "<c:numCache><c:ptCount val=\"3\"/><c:pt idx=\"0\"><c:v>12</c:v></c:pt></c:numCache>"
    "</c:numRef></c:val>"
    "<c:cat><c:strRef><c:f>Sheet1!$A$2:$A$4</c:f>"
    "<c:strCache><c:ptCount val=\"3\"/>"
    "<c:pt idx=\"0\"><c:v>High</c:v></c:pt>"
    "<c:pt idx=\"1\"><c:v>Medium</c:v></c:pt>"
    "<c:pt idx=\"2\"><c:v>Low</c:v></c:pt>"
    "</c:strCache></c:strRef></c:cat>"
    "</c:ser>"
    "</c:barChart>"
    "</c:plotArea>"
    "<c:externalData r:id=\"rId1\"><c:autoUpdate val=\"0\"/></c:externalData>"
    "</c:chart>"
    "</c:chartSpace>"
)


class FakeXmlPart:
    """Minimal XML part used to exercise templating helpers."""

    def __init__(self, partname: str, xml: str):
        self.partname = PackURI(partname)
        self._element = parse_xml(xml.encode("utf-8"))
        self._blob = etree.tostring(self._element)

    @property
    def blob(self) -> bytes:
        return self._blob


class FakeXlsxPart:
    """Embedded Excel part for exercising templating."""

    def __init__(
        self,
        partname: str,
        worksheet_xml: str,
        shared_xml: str | None = None,
        *,
        content_types_xml: str | None = None,
        extra_files: dict[str, str | bytes] | None = None,
    ):
        self.partname = PackURI(partname)
        self._blob = self._build_blob(
            worksheet_xml,
            shared_xml,
            content_types_xml=content_types_xml,
            extra_files=extra_files,
        )

    @staticmethod
    def _build_blob(
        worksheet_xml: str,
        shared_xml: str | None,
        *,
        content_types_xml: str | None,
        extra_files: dict[str, str | bytes] | None,
    ) -> bytes:
        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w") as archive:
            archive.writestr("[Content_Types].xml", content_types_xml or CONTENT_TYPES_XML)
            archive.writestr("xl/workbook.xml", WORKBOOK_XML)
            archive.writestr("xl/_rels/workbook.xml.rels", WORKBOOK_RELS_XML)
            archive.writestr("xl/worksheets/sheet1.xml", worksheet_xml)
            if shared_xml is not None:
                archive.writestr("xl/sharedStrings.xml", shared_xml)
            if extra_files:
                for name, data in extra_files.items():
                    archive.writestr(name, data if isinstance(data, bytes) else data.encode("utf-8"))
        return buffer.getvalue()

    @property
    def blob(self) -> bytes:
        return self._blob


class FakeRelationship:
    """Relationship pointing a chart to an embedded workbook."""

    def __init__(self, target_part=None, *, reltype: str | None = None):
        self.reltype = (
            reltype
            or "http://schemas.openxmlformats.org/officeDocument/2006/relationships/embeddedPackage"
        )
        self._reltype = self.reltype
        self.target_part = target_part


class FakeExternalRelationship:
    """Relationship that mimics python-docx external targets."""

    def __init__(self, target_ref: str = "http://example.com/external.bin"):
        self.reltype = f"{docx_template._RELATIONSHIP_NS}/image"
        self._reltype = self.reltype
        self.target_ref = target_ref
        self.is_external = True

    @property
    def target_part(self):  # pragma: no cover - exercised through template call
        raise ValueError(
            "target_part property on _Relationship is undefined when target mode is External"
        )


class FakeHyperlinkRelationship:
    """Relationship describing an external hyperlink."""

    def __init__(self, rel_id: str, target: str):
        self.reltype = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
        self.is_external = True
        self.target_ref = target
        self.rel_id = rel_id


class FakeRelationships(dict):
    """Minimal relationship mapping with an internal target lookup."""

    def __init__(self, mapping: dict[str, FakeRelationship] | None = None):
        super().__init__(mapping or {})
        self._target_parts_by_rId = dict(self)


class FakeChartPart(FakeXmlPart):
    """Chart XML part with a relationship to a workbook."""

    def __init__(self, partname: str, xml: str, target_part):
        super().__init__(partname, xml)
        self.rels = FakeRelationships({"rId1": FakeRelationship(target_part)})

    def drop_rel(self, rel_id):
        self.rels.pop(rel_id, None)


class FakeWorkbookPart:
    """Workbook part stub exposing only a ``partname`` attribute."""

    def __init__(self, partname: str = "/word/embeddings/workbook.xlsx"):
        self.partname = partname


class FakeRelPart(FakeXmlPart):
    """XML part with arbitrary relationships for cleanup tests."""

    def __init__(self, partname: str, xml: str, rels: dict[str, FakeRelationship]):
        super().__init__(partname, xml)
        self.rels = FakeRelationships(rels)

    def drop_rel(self, rel_id):
        self.rels.pop(rel_id, None)


class FakeContentTypePart:
    """Lightweight part exposing a mutable content type."""

    def __init__(self, partname: str, content_type: str):
        self.partname = PackURI(partname)
        self._content_type = content_type

    @property
    def content_type(self):
        return self._content_type


class FakeAppPropertiesPart:
    """App properties part with mutable XML and blob values."""

    def __init__(self, xml: str):
        self.partname = PackURI("/docProps/app.xml")
        self._blob = xml.encode("utf-8")
        self._element = parse_xml(xml)


class FakeStubbornRelPart(FakeRelPart):
    """Relationship cleanup stub that never removes relationships via ``drop_rel``."""

    def drop_rel(self, rel_id):
        # Simulate python-docx refusing to remove the relationship because it still sees
        # references in the part XML.
        return None


def test_cleanup_part_relationships_removes_unused_ids():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body><w:p><w:r><w:t>Keep</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    part = FakeRelPart("/word/document.xml", xml, {"rId1": FakeRelationship(object())})

    template._cleanup_part_relationships(part, xml)

    assert part.rels == {}


def test_cleanup_part_relationships_forces_removal_when_drop_rel_keeps_id():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body><w:p><w:r><w:t>Only text</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    part = FakeStubbornRelPart("/word/document.xml", xml, {"rId7": FakeRelationship(object())})

    template._cleanup_part_relationships(part, xml)

    assert "rId7" not in part.rels
    assert "rId7" not in part.rels._target_parts_by_rId


def test_cleanup_part_relationships_keeps_used_ids():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body><w:p><w:hyperlink r:id=\"rId1\"><w:r><w:t>Link</w:t></w:r></w:hyperlink></w:p>"
        "</w:body></w:document>"
    )
    part = FakeRelPart("/word/document.xml", xml, {"rId1": FakeRelationship(object())})

    template._cleanup_part_relationships(part, xml)

    assert "rId1" in part.rels


def test_cleanup_part_relationships_preserves_core_document_parts():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>"
        "<w:p><w:r><w:t>Body</w:t></w:r></w:p>"
        "<w:p><w:commentRangeStart w:id=\"1\"/><w:r><w:t>Issue</w:t></w:r><w:commentRangeEnd w:id=\"1\"/></w:p>"
        "</w:body></w:document>"
    )

    rel_ns = docx_template._RELATIONSHIP_NS
    rels = {
        "rIdStyles": FakeRelationship(object(), reltype=f"{rel_ns}/styles"),
        "rIdNumbering": FakeRelationship(object(), reltype=f"{rel_ns}/numbering"),
        "rIdComments": FakeRelationship(object(), reltype=f"{rel_ns}/comments"),
        "rIdChart": FakeRelationship(object(), reltype=f"{rel_ns}/chart"),
    }

    part = FakeRelPart("/word/document.xml", xml, rels)

    template._cleanup_part_relationships(part, xml)

    assert set(part.rels) == {"rIdStyles", "rIdNumbering", "rIdComments"}


def test_cleanup_word_markup_balances_bookmarks_and_hyperlinks():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>"
        "<w:p><w:bookmarkStart w:id=\"1\" w:name=\"Keep\"/><w:r><w:t>Intro</w:t></w:r>"
        "<w:bookmarkEnd w:id=\"1\"/></w:p>"
        "<w:p><w:bookmarkStart w:id=\"2\" w:name=\"_Drop\"/></w:p>"
        "<w:p><w:bookmarkEnd w:id=\"3\"/></w:p>"
        "<w:p><w:hyperlink w:anchor=\"Keep\"><w:r><w:t>Valid</w:t></w:r></w:hyperlink></w:p>"
        "<w:p><w:hyperlink w:anchor=\"keep\"><w:r><w:t>Valid lowercase</w:t></w:r></w:hyperlink></w:p>"
        "<w:p><w:hyperlink w:anchor=\"_Missing\"><w:r><w:t>Broken</w:t></w:r></w:hyperlink></w:p>"
        "</w:body></w:document>"
    )

    part = FakeRelPart("/word/document.xml", xml, {})
    tree = parse_xml(xml.encode("utf-8"))

    cleaned = template._cleanup_word_markup(part, tree)
    cleaned_xml = etree.tostring(cleaned, encoding="unicode")

    assert "_Drop" not in cleaned_xml
    assert 'w:id="3"' not in cleaned_xml
    assert '<w:hyperlink w:anchor="_Missing"' not in cleaned_xml
    assert "Broken" in cleaned_xml
    assert '<w:hyperlink w:anchor="Keep"' in cleaned_xml
    assert '<w:hyperlink w:anchor="keep"' in cleaned_xml


def test_cleanup_word_markup_removes_unbalanced_comment_ranges():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>"
        "<w:p><w:commentRangeStart w:id=\"1\"/><w:r><w:t>Keep</w:t></w:r>"
        "<w:commentRangeEnd w:id=\"1\"/></w:p>"
        "<w:p><w:commentRangeStart w:id=\"2\"/></w:p>"
        "<w:p><w:commentRangeEnd w:id=\"3\"/></w:p>"
        "<w:p><w:commentRangeStart w:id=\"4\"/></w:p>"
        "<w:p><w:commentRangeStart w:id=\"4\"/></w:p>"
        "<w:p><w:commentRangeEnd w:id=\"4\"/></w:p>"
        "<w:p><w:commentRangeStart w:id=\"5\"/><w:r><w:t>Dup end</w:t></w:r></w:p>"
        "<w:p><w:commentRangeEnd w:id=\"5\"/></w:p>"
        "<w:p><w:commentRangeEnd w:id=\"5\"/></w:p>"
        "<w:p><w:permStart w:id=\"7\"/><w:r><w:t>Hold</w:t></w:r><w:permEnd w:id=\"7\"/></w:p>"
        "<w:p><w:permStart w:id=\"8\"/></w:p>"
        "<w:p><w:permEnd w:id=\"9\"/></w:p>"
        "</w:body></w:document>"
    )

    part = FakeRelPart("/word/document.xml", xml, {})
    tree = parse_xml(xml.encode("utf-8"))

    cleaned = template._cleanup_word_markup(part, tree)
    cleaned_xml = etree.tostring(cleaned, encoding="unicode")

    assert 'w:commentRangeStart w:id="2"' not in cleaned_xml
    assert 'w:commentRangeEnd w:id="3"' not in cleaned_xml
    assert cleaned_xml.count('w:commentRangeStart w:id="4"') == 1
    assert cleaned_xml.count('w:commentRangeEnd w:id="4"') == 1
    assert cleaned_xml.count('w:commentRangeEnd w:id="5"') == 1
    assert 'w:permStart w:id="8"' not in cleaned_xml
    assert 'w:permEnd w:id="9"' not in cleaned_xml


def test_cleanup_comments_part_removes_orphan_entries():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    template._referenced_comment_ids = {"1", "3"}

    comments_xml = (
        '<w:comments xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:comment w:id=\"1\"><w:p/></w:comment>"
        "<w:comment w:id=\"2\"><w:p/></w:comment>"
        "<w:comment w:id=\"3\"><w:p/></w:comment>"
        "</w:comments>"
    )
    comments_part = FakeXmlPart("/word/comments.xml", comments_xml)

    def part_related_by(reltype):
        if reltype == f"{docx_template._RELATIONSHIP_NS}/comments":
            return comments_part
        raise KeyError(reltype)

    template.docx = SimpleNamespace(_part=SimpleNamespace(part_related_by=part_related_by))
    template.get_part_xml = lambda part: part._blob.decode("utf-8")

    template._cleanup_comments_part()

    updated_xml = comments_part._blob.decode("utf-8")
    assert 'w:id="1"' in updated_xml
    assert 'w:id="3"' in updated_xml
    assert 'w:id="2"' not in updated_xml


def test_cleanup_word_markup_removes_duplicate_bookmarks_and_missing_fields():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
        "<w:body>"
        "<w:p><w:bookmarkStart w:id=\"1\" w:name=\"Keep\"/>"
        "<w:r><w:t>Intro</w:t></w:r><w:bookmarkEnd w:id=\"1\"/></w:p>"
        "<w:p><w:bookmarkStart w:id=\"2\" w:name=\"Keep\"/>"
        "<w:r><w:t>Duplicate</w:t></w:r><w:bookmarkEnd w:id=\"2\"/></w:p>"
        "<w:p><w:bookmarkStart w:id=\"3\" w:name=\"keep\"/>"
        "<w:r><w:t>Duplicate lowercase</w:t></w:r><w:bookmarkEnd w:id=\"3\"/></w:p>"
        "<w:p><w:fldSimple w:instr=\" REF Missing \\h \">"
        "<w:r><w:t>Broken simple</w:t></w:r></w:fldSimple></w:p>"
        "<w:p><w:fldSimple w:instr=\" REF Keep \\h \">"
        "<w:r><w:t>Valid simple</w:t></w:r></w:fldSimple></w:p>"
        "<w:p>"
        "<w:r><w:fldChar w:fldCharType=\"begin\"/></w:r>"
        "<w:r><w:instrText xml:space=\"preserve\"> REF Missing \\h </w:instrText></w:r>"
        "<w:r><w:fldChar w:fldCharType=\"separate\"/></w:r>"
        "<w:r><w:t>Broken complex</w:t></w:r>"
        "<w:r><w:fldChar w:fldCharType=\"end\"/></w:r>"
        "</w:p>"
        "<w:p>"
        "<w:r><w:fldChar w:fldCharType=\"begin\"/></w:r>"
        "<w:r><w:instrText xml:space=\"preserve\"> REF Keep \\h </w:instrText></w:r>"
        "<w:r><w:fldChar w:fldCharType=\"separate\"/></w:r>"
        "<w:r><w:t>Valid complex</w:t></w:r>"
        "<w:r><w:fldChar w:fldCharType=\"end\"/></w:r>"
        "</w:p>"
        "</w:body></w:document>"
    )

    part = FakeRelPart("/word/document.xml", xml, {})
    tree = parse_xml(xml.encode("utf-8"))

    cleaned = template._cleanup_word_markup(part, tree)
    cleaned_xml = etree.tostring(cleaned, encoding="unicode")

    assert cleaned_xml.count('w:bookmarkStart w:name="Keep"') == 1
    assert 'w:id="2"' not in cleaned_xml
    assert 'w:id="3"' not in cleaned_xml
    assert "Broken simple" not in cleaned_xml
    assert "Broken complex" not in cleaned_xml
    assert "Valid simple" in cleaned_xml
    assert "Valid complex" in cleaned_xml


def test_cleanup_word_markup_strips_paragraph_ids():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:w14="http://schemas.microsoft.com/office/word/2010/wordml">'
        "<w:body>"
        '<w:p w14:paraId="212d559b"><w:r><w:t>Intro</w:t></w:r></w:p>'
        '<w:p w14:paraId="212D559B"><w:r><w:t>Duplicate</w:t></w:r></w:p>'
        "<w:p><w:r><w:t>Missing</w:t></w:r></w:p>"
        "</w:body></w:document>"
    )

    part = FakeRelPart("/word/document.xml", xml, {})
    tree = parse_xml(xml.encode("utf-8"))

    cleaned = template._cleanup_word_markup(part, tree)

    word_ns = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"
    w14_ns = "http://schemas.microsoft.com/office/word/2010/wordml"
    para_tag = f"{{{word_ns}}}p"
    para_attr = f"{{{w14_ns}}}paraId"

    para_ids = [para.get(para_attr) for para in cleaned.iter(para_tag)]

    assert all(pid is None for pid in para_ids)


def test_renumber_media_parts_renames_charts_and_embeddings():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    chart1 = FakeXmlPart(
        "/word/charts/chart1.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )
    chart3 = FakeXmlPart(
        "/word/charts/chart3.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )
    workbook1 = FakeXmlPart("/word/embeddings/Microsoft_Excel_Worksheet1.xlsx", "<root/>")
    workbook4 = FakeXmlPart("/word/embeddings/Microsoft_Excel_Worksheet4.xlsx", "<root/>")

    doc_xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body/>"
        "</w:document>"
    )
    rel_chart1 = FakeRelationship(chart1)
    rel_chart1.target_ref = "charts/chart1.xml"
    rel_chart1._target = PackURI("/word/charts/chart1.xml")
    rel_chart3 = FakeRelationship(chart3)
    rel_chart3.target_ref = "charts/chart3.xml"
    rel_chart3._target = PackURI("/word/charts/chart3.xml")

    document_part = FakeRelPart(
        "/word/document.xml",
        doc_xml,
        {"rId1": rel_chart1, "rId2": rel_chart3},
    )

    chart1_rel = FakeRelationship(workbook1)
    chart1_rel.target_ref = "../embeddings/Microsoft_Excel_Worksheet1.xlsx"
    chart1_rel._target = PackURI("/word/embeddings/Microsoft_Excel_Worksheet1.xlsx")
    chart3_rel = FakeRelationship(workbook4)
    chart3_rel.target_ref = "../embeddings/Microsoft_Excel_Worksheet4.xlsx"
    chart3_rel._target = PackURI("/word/embeddings/Microsoft_Excel_Worksheet4.xlsx")

    chart1.rels = FakeRelationships({"rId1": chart1_rel})
    chart3.rels = FakeRelationships({"rId1": chart3_rel})

    parts = [document_part, chart1, chart3, workbook1, workbook4]
    overrides = {
        part.partname: "application/test" for part in parts if hasattr(part, "partname")
    }

    package = SimpleNamespace(
        parts=parts,
        _parts={part.partname: part for part in parts if hasattr(part, "partname")},
        _partnames={part.partname: part for part in parts if hasattr(part, "partname")},
        _content_types=SimpleNamespace(_overrides=overrides),
    )

    for part in parts:
        part.package = package

    template.docx = SimpleNamespace(_part=document_part)
    document_part.package = package

    template._renumber_media_parts()

    assert chart3.partname == PackURI("/word/charts/chart2.xml")
    assert workbook4.partname == PackURI("/word/embeddings/Microsoft_Excel_Worksheet2.xlsx")

    assert document_part.rels["rId2"].target_ref == "charts/chart2.xml"
    assert document_part.rels["rId2"]._target == PackURI("/word/charts/chart2.xml")

    assert chart3.rels["rId1"].target_ref == "../embeddings/Microsoft_Excel_Worksheet2.xlsx"
    assert chart3.rels["rId1"]._target == PackURI(
        "/word/embeddings/Microsoft_Excel_Worksheet2.xlsx"
    )

    assert PackURI("/word/charts/chart2.xml") in package._parts
    assert PackURI("/word/charts/chart3.xml") not in package._parts

    overrides_keys = package._content_types._overrides
    assert PackURI("/word/embeddings/Microsoft_Excel_Worksheet2.xlsx") in overrides_keys
    assert all("Worksheet4" not in str(key) for key in overrides_keys)


def test_renumber_media_parts_is_noop_when_sequential():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    chart1 = FakeXmlPart(
        "/word/charts/chart1.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )
    chart2 = FakeXmlPart(
        "/word/charts/chart2.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )

    parts = [chart1, chart2]
    package = SimpleNamespace(
        parts=parts,
        _parts={chart1.partname: chart1, chart2.partname: chart2},
        _partnames={chart1.partname: chart1, chart2.partname: chart2},
        _content_types=SimpleNamespace(
            _overrides={chart1.partname: "chart", chart2.partname: "chart"}
        ),
    )

    for part in parts:
        part.package = package

    main_part = SimpleNamespace(package=package)
    template.docx = SimpleNamespace(_part=main_part)

    template._renumber_media_parts()

    assert chart1.partname == PackURI("/word/charts/chart1.xml")
    assert chart2.partname == PackURI("/word/charts/chart2.xml")
    assert PackURI("/word/charts/chart1.xml") in package._parts
    assert PackURI("/word/charts/chart2.xml") in package._parts


def test_renumber_media_parts_skips_external_relationships():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    chart1 = FakeXmlPart(
        "/word/charts/chart1.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )
    chart3 = FakeXmlPart(
        "/word/charts/chart3.xml",
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart"/>',
    )

    rel_chart1 = FakeRelationship(chart1)
    rel_chart1.target_ref = "charts/chart1.xml"
    rel_chart1._target = PackURI("/word/charts/chart1.xml")
    rel_chart3 = FakeRelationship(chart3)
    rel_chart3.target_ref = "charts/chart3.xml"
    rel_chart3._target = PackURI("/word/charts/chart3.xml")

    external_rel = FakeExternalRelationship()
    external_rel.target_ref = "http://example.com/template.dotx"

    document_part = FakeRelPart(
        "/word/document.xml",
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"/>',
        {"rId1": rel_chart1, "rId2": rel_chart3, "rIdExt": external_rel},
    )

    parts = [document_part, chart1, chart3]
    package = SimpleNamespace(
        parts=parts,
        _parts={part.partname: part for part in parts if hasattr(part, "partname")},
        _partnames={part.partname: part for part in parts if hasattr(part, "partname")},
        _content_types=SimpleNamespace(_overrides={part.partname: "chart" for part in parts[1:]}),
    )

    for part in parts:
        part.package = package

    template.docx = SimpleNamespace(_part=document_part)

    template._renumber_media_parts()

    assert chart3.partname == PackURI("/word/charts/chart2.xml")

    assert document_part.rels["rIdExt"].target_ref == "http://example.com/template.dotx"
    assert "chart2.xml" in document_part.rels["rId2"].target_ref

def test_cleanup_word_markup_removes_external_file_hyperlinks():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body>"
        "<w:p><w:hyperlink r:id=\"rIdFile\"><w:r><w:t>Unsafe</w:t></w:r></w:hyperlink></w:p>"
        "<w:p><w:hyperlink r:id=\"rIdWeb\"><w:r><w:t>Safe</w:t></w:r></w:hyperlink></w:p>"
        "</w:body></w:document>"
    )

    rels = {
        "rIdFile": FakeHyperlinkRelationship("rIdFile", "file:///tmp/untrusted.docx"),
        "rIdWeb": FakeHyperlinkRelationship("rIdWeb", "https://example.com"),
    }
    part = FakeRelPart("/word/document.xml", xml, rels)

    cleaned = template._cleanup_word_markup(part, xml)

    assert "rIdFile" not in part.rels
    assert "rIdWeb" in part.rels
    assert 'r:id="rIdFile"' not in cleaned
    assert 'r:id="rIdWeb"' in cleaned


def test_cleanup_word_markup_removes_attached_template_relationship():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:attachedTemplate r:id=\"rIdTpl\"/>"
        "<w:trackRevisions/>"
        "</w:settings>"
    )

    rels = {
        "rIdTpl": FakeRelationship(
            reltype=f"{docx_template._RELATIONSHIP_NS}/attachedTemplate"
        )
    }
    part = FakeRelPart("/word/settings.xml", xml, rels)

    cleaned = template._cleanup_word_markup(part, xml)

    assert "attachedTemplate" not in cleaned
    assert "trackRevisions" in cleaned
    assert part.rels == {}


def test_cleanup_settings_part_removes_attached_template_relationship():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = (
        '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:attachedTemplate r:id=\"rIdTpl\"/>"
        "<w:trackRevisions/>"
        "</w:settings>"
    )
    rels = {
        "rIdTpl": FakeRelationship(
            reltype=f"{docx_template._RELATIONSHIP_NS}/attachedTemplate"
        )
    }
    settings_part = FakeRelPart("/word/settings.xml", xml, rels)

    def part_related_by(reltype):
        if reltype == f"{docx_template._RELATIONSHIP_NS}/settings":
            return settings_part
        raise KeyError(reltype)

    template.docx = SimpleNamespace(_part=SimpleNamespace(part_related_by=part_related_by))
    template.get_part_xml = lambda part: part._blob.decode("utf-8")

    template._cleanup_settings_part()

    assert settings_part.rels == {}
    assert b"attachedTemplate" not in settings_part._blob
    assert b"trackRevisions" in settings_part._blob


def test_collect_relationship_ids_handles_multiple_values():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '<w:body><w:p><w:bookmarkStart w:id="0" w:name="_GoBack" r:ids="rId5 rId6"/></w:p>'
        "</w:body></w:document>"
    )

    ids = template._collect_relationship_ids(xml)

    assert ids == {"rId5", "rId6"}


def test_iter_additional_parts_filters_to_known_patterns(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    matching = FakeXmlPart("/word/diagrams/data1.xml", DIAGRAM_XML.format("value"))
    chart = FakeXmlPart("/word/charts/chart1.xml", DIAGRAM_XML.format("value"))
    other = FakeXmlPart("/word/document.xml", DIAGRAM_XML.format("value"))

    monkeypatch.setattr(
        template,
        "_iter_reachable_parts",
        lambda: iter([template.docx._part, matching, chart, other]),
    )

    assert list(template._iter_additional_parts()) == [matching, chart]


def test_render_additional_parts_updates_diagram_xml(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    part = FakeXmlPart("/word/diagrams/data1.xml", DIAGRAM_SPLIT_XML.format(" item "))
    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([part]))

    template._render_additional_parts({"item": "Rendered"}, None)

    text = etree.tostring(part._element, encoding="unicode")
    assert "Rendered" in text


def test_render_additional_parts_removes_unused_chart_relationship(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    chart_xml = (
        '<c:chartSpace xmlns:c="http://schemas.openxmlformats.org/drawingml/2006/chart" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        '{% if include_workbook %}<c:externalData r:id="rId1"/>{% endif %}'
        "</c:chartSpace>"
    )
    workbook_part = FakeWorkbookPart()
    chart_part = FakeChartPart("/word/charts/chart1.xml", chart_xml, workbook_part)
    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([chart_part]))

    template._render_additional_parts({"include_workbook": False}, None)

    assert chart_part.rels == {}


def test_iter_additional_parts_includes_excel_parts(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_XML,
        SHARED_STRINGS_XML,
    )

    monkeypatch.setattr(
        template,
        "_iter_reachable_parts",
        lambda: iter([template.docx._part, excel]),
    )

    assert list(template._iter_additional_parts()) == [excel]


def test_render_additional_parts_updates_excel_data(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_XML,
        SHARED_STRINGS_XML,
    )
    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    template._render_additional_parts({"number": 7, "chart_value": 21}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        sheet = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        shared = archive.read("xl/sharedStrings.xml").decode("utf-8")

    assert "<c r=\"A1\"><v>7</v></c>" in sheet
    assert "<c r=\"A2\"><v>21</v></c>" in sheet
    assert "{{" not in shared


def test_render_additional_parts_updates_chart_cache(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_CHART_XML,
        SHARED_STRINGS_CHART_XML,
    )
    chart = FakeChartPart(
        "/word/charts/chart1.xml",
        CHART_XML,
        excel,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel, chart]))

    template._render_additional_parts(
        {
            "first_val": 10,
            "second_val": 20,
            "first_label": "Alpha",
            "second_label": "Beta",
        },
        None,
    )

    chart_xml = etree.tostring(chart._element, encoding="unicode")
    assert "<c:pt idx=\"0\"><c:v>10</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>20</c:v></c:pt>" in chart_xml
    assert "<c:numLit><c:ptCount val=\"2\"/>" in chart_xml
    assert "<c:numLit><c:ptCount val=\"2\"/><c:pt idx=\"0\"><c:v>10</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>20</c:v></c:pt></c:numLit>" in chart_xml
    assert "<c:pt idx=\"0\"><c:v>Alpha</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>Beta</c:v></c:pt>" in chart_xml
    assert "<c:strLit><c:ptCount val=\"2\"/>" in chart_xml
    assert "<c:strLit><c:ptCount val=\"2\"/><c:pt idx=\"0\"><c:v>Alpha</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>Beta</c:v></c:pt></c:strLit>" in chart_xml
    assert "<c:autoUpdate val=\"0\"/>" in chart_xml
    assert "{{" not in chart_xml


def test_render_additional_parts_updates_chart_cache_structured_ref(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TABLE_XML,
        None,
        content_types_xml=CONTENT_TYPES_WITH_TABLE_XML,
        extra_files={
            "xl/worksheets/_rels/sheet1.xml.rels": SHEET_TABLE_RELS_XML,
            "xl/tables/table1.xml": TABLE_XML,
        },
    )
    chart = FakeChartPart(
        "/word/charts/chart1.xml",
        CHART_TABLE_XML,
        excel,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel, chart]))

    template._render_additional_parts(
        {
            "first_number": 5,
            "second_number": 7,
            "first_label": "One",
            "second_label": "Two",
        },
        None,
    )

    chart_xml = etree.tostring(chart._element, encoding="unicode")
    assert "<c:pt idx=\"0\"><c:v>5</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>7</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"0\"><c:v>One</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>Two</c:v></c:pt>" in chart_xml
    assert "<c:autoUpdate val=\"0\"/>" in chart_xml
    assert "{{" not in chart_xml

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        table_xml = archive.read("xl/tables/table1.xml").decode("utf-8")

    assert "ref=\"A1:B3\"" in table_xml
    assert "{{" not in table_xml


def test_render_additional_parts_updates_chart_cache_structured_ref_headers(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TABLE_RENAME_XML,
        None,
        content_types_xml=CONTENT_TYPES_WITH_TABLE_XML,
        extra_files={
            "xl/worksheets/_rels/sheet1.xml.rels": SHEET_TABLE_RELS_XML,
            "xl/tables/table1.xml": TABLE_PLACEHOLDER_XML,
        },
    )
    chart = FakeChartPart(
        "/word/charts/chart1.xml",
        CHART_TABLE_PLACEHOLDER_XML,
        excel,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel, chart]))

    template._render_additional_parts(
        {
            "first_header": "Numbers",
            "second_header": "Labels",
            "first_number": 5,
            "second_number": 7,
            "first_label": "One",
            "second_label": "Two",
        },
        None,
    )

    chart_xml = etree.tostring(chart._element, encoding="unicode")
    assert "Table1[Numbers]" in chart_xml
    assert "Table1[Labels]" in chart_xml
    assert "<c:pt idx=\"0\"><c:v>5</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>7</c:v></c:pt>" in chart_xml


def test_render_additional_parts_updates_chart_cache_extensions(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_CHART_XML,
        SHARED_STRINGS_CHART_XML,
    )
    chart = FakeChartPart(
        "/word/charts/chart1.xml",
        CHART_EXT_XML,
        excel,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel, chart]))

    template._render_additional_parts(
        {
            "first_val": 10,
            "second_val": 20,
            "first_label": "Alpha",
            "second_label": "Beta",
        },
        None,
    )

    chart_xml = etree.tostring(chart._element, encoding="unicode")
    assert "<c:pt idx=\"0\"><c:v>10</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>20</c:v></c:pt>" in chart_xml
    assert "<x14:pt idx=\"0\"><x14:v>10</x14:v></x14:pt>" in chart_xml
    assert "<x14:pt idx=\"1\"><x14:v>20</x14:v></x14:pt>" in chart_xml
    assert "<c:pt idx=\"0\"><c:v>Alpha</c:v></c:pt>" in chart_xml
    assert "<c:pt idx=\"1\"><c:v>Beta</c:v></c:pt>" in chart_xml
    assert "<x14:pt idx=\"0\"><x14:v>Alpha</x14:v></x14:pt>" in chart_xml
    assert "<x14:pt idx=\"1\"><x14:v>Beta</x14:v></x14:pt>" in chart_xml
    assert "<c:autoUpdate val=\"0\"/>" in chart_xml
    assert "{{" not in chart_xml


def test_sync_chart_cache_repairs_mismatched_point_counts():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    workbook = FakeWorkbookPart("/word/embeddings/Microsoft_Excel_Worksheet1.xlsx")
    chart = FakeChartPart(
        "/word/charts/chart1.xml",
        CHART_NUMCACHE_MISMATCH_XML,
        workbook,
    )

    repaired_xml = template._sync_chart_cache(
        CHART_NUMCACHE_MISMATCH_XML,
        chart,
        {},
    )

    tree = etree.fromstring(repaired_xml.encode("utf-8"))
    num_cache = tree.find(".//{*}numCache")
    assert num_cache is not None
    pts = num_cache.findall("{*}pt")
    assert len(pts) == 3
    assert [pt.get("idx") for pt in pts] == ["0", "1", "2"]
    assert [pt.findtext("{*}v") for pt in pts] == ["12", "0", "0"]
    pt_count = num_cache.find("{*}ptCount")
    assert pt_count is not None
    assert pt_count.get("val") == "3"


def test_get_undeclared_variables_includes_diagram_parts(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    part = FakeXmlPart("/word/diagrams/drawing1.xml", DIAGRAM_SPLIT_XML.format(" missing "))
    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([part]))
    monkeypatch.setattr(template, "get_xml", lambda: "")
    monkeypatch.setattr(template, "get_headers_footers", lambda _uri: [])

    variables = template.get_undeclared_template_variables()

    assert "missing" in variables


def test_get_undeclared_variables_includes_excel_parts(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    worksheet = WORKSHEET_XML.replace("{{ number }}", "{{ missing_excel }}")
    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        worksheet,
        None,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))
    monkeypatch.setattr(template, "get_xml", lambda: "")
    monkeypatch.setattr(template, "get_headers_footers", lambda _uri: [])

    variables = template.get_undeclared_template_variables()

    assert "missing_excel" in variables


def test_patch_xml_removes_namespaced_tags_inside_jinja():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(DIAGRAM_SPLIT_XML.format(" value "))

    assert "{{ value }}" in cleaned
    assert "{{<" not in cleaned


def test_patch_xml_handles_excel_tc_tr_tags():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(WORKSHEET_TR_TC_XML)

    assert "{% for row in rows %}" in cleaned
    assert "{% endfor %}" in cleaned
    assert "{% for for" not in cleaned
    assert "{{ row.value }}" in cleaned
    assert "{{tc" not in cleaned
    assert "{%tc" not in cleaned


def test_patch_xml_handles_trimmed_excel_tr_tags():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(WORKSHEET_TR_TC_TRIMMED_XML)

    assert "{%- for row in rows -%}" in cleaned
    assert "{%- endfor -%}" in cleaned
    assert "tr for" not in cleaned
    assert "endtr" not in cleaned


def test_patch_xml_handles_excel_tr_endfor_tags():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(WORKSHEET_TR_ENDFOR_XML)

    assert "{% for site in sites %}" in cleaned
    assert "{% endfor %}" in cleaned
    assert "tr for" not in cleaned
    assert "tr endfor" not in cleaned


def test_patch_xml_handles_split_excel_tr_tags():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(WORKSHEET_TR_SPLIT_XML)

    assert "{% for site in project.workbook_data.web.sites %}" in cleaned
    assert "{% endfor %}" in cleaned
    assert "tr for" not in cleaned
    assert "tr endfor" not in cleaned
    assert not re.search(r"<row[^>]*>\\s*{% for", cleaned)
    assert not re.search(r"{% endfor %}\\s*</row", cleaned)


def test_patch_xml_handles_split_excel_tc_tags():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(WORKSHEET_TC_SPLIT_XML)

    assert "tc site.url" not in cleaned
    assert "tc site.unique_high" not in cleaned
    assert "{{ site.url }}" in cleaned
    assert "{{ site.unique_high }}" in cleaned


def test_patch_xml_preserves_chart_paragraph_markup():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(CHART_RICH_TEXT_SPLIT_XML)

    assert "<a:pPr>" in cleaned
    assert "</a:pPr>" in cleaned
    etree.fromstring(cleaned.encode("utf-8"))


def test_patch_xml_strips_tc_in_chart_parts():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(CHART_TC_XML)

    assert "{%tc" not in cleaned
    assert "for device in devices" in cleaned


def test_patch_xml_strips_tr_in_chart_parts():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")

    cleaned = template.patch_xml(CHART_TR_XML)

    assert "{% for device in devices %}" in cleaned
    assert "{% endfor %}" in cleaned
    assert "tr for" not in cleaned
    assert "tr endfor" not in cleaned


def test_render_additional_parts_expands_table_range_for_loop(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TABLE_LOOP_XML,
        None,
        content_types_xml=CONTENT_TYPES_WITH_TABLE_XML,
        extra_files={
            "xl/worksheets/_rels/sheet1.xml.rels": SHEET_TABLE_RELS_XML,
            "xl/tables/table1.xml": TABLE_SMALL_XML,
        },
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    template._render_additional_parts(
        {
            "rows": [
                {"number": 1, "label": "One"},
                {"number": 2, "label": "Two"},
                {"number": 3, "label": "Three"},
            ]
        },
        None,
    )

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        table_xml = archive.read("xl/tables/table1.xml").decode("utf-8")

    assert "ref=\"A1:B4\"" in table_xml
    assert "{{" not in table_xml


def test_render_additional_parts_updates_table_columns_for_tc(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TC_RENDERED_COLUMNS_XML,
        content_types_xml=CONTENT_TYPES_WITH_TABLE_XML,
        extra_files={
            "xl/worksheets/_rels/sheet1.xml.rels": SHEET_TABLE_RELS_XML,
            "xl/tables/table1.xml": TABLE_TC_NARROW_XML,
        },
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    template._render_additional_parts({}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        table_xml = archive.read("xl/tables/table1.xml").decode("utf-8")

    tree = etree.fromstring(table_xml.encode("utf-8"))
    ns = tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    assert 'ref="A1:C4"' in table_xml
    assert tree.get("ref") == "A1:C4"
    columns = tree.findall(f"{prefix}tableColumns/{prefix}tableColumn")
    assert len(columns) == 3
    assert [column.get("name") for column in columns] == [
        "Metric",
        "Edge-FW01",
        "Edge-FW02",
    ]


def test_render_additional_parts_renders_tc_column_loops(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TC_LOOP_TEMPLATE_XML,
        content_types_xml=CONTENT_TYPES_WITH_TABLE_XML,
        extra_files={
            "xl/worksheets/_rels/sheet1.xml.rels": SHEET_TABLE_RELS_XML,
            "xl/tables/table1.xml": TABLE_TC_NARROW_XML,
        },
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    domains = [
        {"name": "corp.example.com", "compliant": 145, "stale": 30},
        {"name": "lab.example.com", "compliant": 120, "stale": 25},
    ]

    template._render_additional_parts({"domains": domains}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        table_xml = archive.read("xl/tables/table1.xml").decode("utf-8")

    sheet_tree = etree.fromstring(sheet_xml.encode("utf-8"))
    ns = sheet_tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    rows = sheet_tree.findall(f"{prefix}sheetData/{prefix}row")
    assert len(rows) == 3

    def row_values(row):
        values = []
        for cell in row.findall(f"{prefix}c"):
            value = cell.find(f"{prefix}v")
            if value is not None and value.text is not None:
                values.append(value.text)
                continue
            inline = cell.find(f"{prefix}is")
            if inline is None:
                values.append("")
                continue
            text = "".join(
                node.text or ""
                for node in inline.findall(f".//{prefix}t")
            )
            values.append(text)
        return values

    assert [cell.get("r") for cell in rows[0].findall(f"{prefix}c")] == [
        "A1",
        "B1",
        "C1",
    ]
    assert row_values(rows[0]) == [
        "Old Passwords",
        "corp.example.com",
        "lab.example.com",
    ]

    assert [cell.get("r") for cell in rows[1].findall(f"{prefix}c")] == [
        "A2",
        "B2",
        "C2",
    ]
    assert row_values(rows[1]) == [
        "Compliant",
        "145",
        "120",
    ]

    assert [cell.get("r") for cell in rows[2].findall(f"{prefix}c")] == [
        "A3",
        "B3",
        "C3",
    ]
    assert row_values(rows[2]) == [
        "Stale",
        "30",
        "25",
    ]

    table_tree = etree.fromstring(table_xml.encode("utf-8"))
    table_ns = table_tree.nsmap.get(None)
    table_prefix = f"{{{table_ns}}}" if table_ns else ""

    assert table_tree.get("ref") == "A1:C3"
    columns = table_tree.findall(f"{table_prefix}tableColumns/{table_prefix}tableColumn")
    assert [column.get("name") for column in columns] == [
        "Old Passwords",
        "corp.example.com",
        "lab.example.com",
    ]


def test_render_additional_parts_inserts_rows_for_tr_loop(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TR_LOOP_ROWS_XML,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    sites = [
        {"url": "https://alpha", "high": 5, "medium": 3, "low": 1},
        {"url": "https://beta", "high": 4, "medium": 2, "low": 0},
        {"url": "https://gamma", "high": 6, "medium": 1, "low": 2},
    ]

    template._render_additional_parts({"sites": sites}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")

    tree = etree.fromstring(sheet_xml.encode("utf-8"))
    ns = tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    rows = tree.findall(f"{prefix}sheetData/{prefix}row")
    assert [row.get("r") for row in rows] == ["1", "2", "3", "4"]

    data_rows = rows[1:]
    for idx, row in enumerate(data_rows, start=2):
        cells = row.findall(f"{prefix}c")
        assert [cell.get("r") for cell in cells] == [
            f"A{idx}",
            f"B{idx}",
            f"C{idx}",
            f"D{idx}",
        ]

    dimension = tree.find(f"{prefix}dimension")
    assert dimension is not None
    assert dimension.get("ref") == "A1:D4"

    for site in sites:
        assert site["url"] in sheet_xml
        assert f">{site['high']}<" in sheet_xml
        assert f">{site['medium']}<" in sheet_xml
        assert f">{site['low']}<" in sheet_xml


def test_render_additional_parts_reindexes_project_loop_rows(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TR_PROJECT_XML,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    sites = [
        {"url": "https://alpha", "unique_high": 7, "unique_med": 5, "unique_low": 3},
        {"url": "https://beta", "unique_high": 4, "unique_med": 2, "unique_low": 1},
    ]

    template._render_additional_parts({"project": {"workbook_data": {"web": {"sites": sites}}}}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")

    tree = etree.fromstring(sheet_xml.encode("utf-8"))
    ns = tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    rows = tree.findall(f"{prefix}sheetData/{prefix}row")
    assert [row.get("r") for row in rows] == ["1", "2"]

    dimension = tree.find(f"{prefix}dimension")
    assert dimension is not None
    assert dimension.get("ref") == "A1:D2"

    first_cells = rows[0].findall(f"{prefix}c")
    assert [cell.get("r") for cell in first_cells] == ["A1", "B1", "C1", "D1"]

    first_values = {cell.get("r"): cell for cell in first_cells}
    url = first_values["A1"].find(f"{prefix}is/{prefix}t")
    assert url is not None and url.text == sites[0]["url"]

    for column, key in zip(("B", "C", "D"), ("unique_high", "unique_med", "unique_low")):
        value = first_values[f"{column}1"].find(f"{prefix}v")
        assert value is not None
        assert value.text == str(sites[0][key])

    second_cells = rows[1].findall(f"{prefix}c")
    assert [cell.get("r") for cell in second_cells] == ["A2", "B2", "C2", "D2"]

    second_values = {cell.get("r"): cell for cell in second_cells}
    url = second_values["A2"].find(f"{prefix}is/{prefix}t")
    assert url is not None and url.text == sites[1]["url"]

    for column, key in zip(("B", "C", "D"), ("unique_high", "unique_med", "unique_low")):
        value = second_values[f"{column}2"].find(f"{prefix}v")
        assert value is not None
        assert value.text == str(sites[1][key])


def test_normalise_sheet_rows_removes_empty_rows():
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    normalised = template._normalise_sheet_rows(WORKSHEET_TR_RENDERED_GAPS_XML)

    tree = etree.fromstring(normalised.encode("utf-8"))
    ns = tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    rows = tree.findall(f"{prefix}sheetData/{prefix}row")
    assert [row.get("r") for row in rows] == ["1", "2", "3"]

    header_cells = rows[0].findall(f"{prefix}c")
    assert [cell.get("r") for cell in header_cells] == ["A1", "B1", "C1", "D1"]

    first_data = rows[1].findall(f"{prefix}c")
    assert [cell.get("r") for cell in first_data] == ["A2", "B2", "C2", "D2"]

    second_data = rows[2].findall(f"{prefix}c")
    assert [cell.get("r") for cell in second_data] == ["A3", "B3", "C3", "D3"]

    dimension = tree.find(f"{prefix}dimension")
    assert dimension is not None
    assert dimension.get("ref") == "A1:D3"


def test_render_additional_parts_handles_tr_loop_shared_strings(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TR_SHARED_STRINGS_XML,
        SHARED_STRINGS_TR_LOOP_XML,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    sites = [
        {"url": "alpha", "high": 3, "medium": 2, "low": 1},
        {"url": "beta", "high": 4, "medium": 3, "low": 2},
    ]

    template._render_additional_parts({"sites": sites}, None)

    with zipfile.ZipFile(io.BytesIO(excel._blob)) as archive:
        sheet_xml = archive.read("xl/worksheets/sheet1.xml").decode("utf-8")
        shared_xml = archive.read("xl/sharedStrings.xml").decode("utf-8")

    assert "{{" not in shared_xml

    tree = etree.fromstring(sheet_xml.encode("utf-8"))
    ns = tree.nsmap.get(None)
    prefix = f"{{{ns}}}" if ns else ""

    rows = tree.findall(f"{prefix}sheetData/{prefix}row")
    assert len(rows) == len(sites) + 1

    data_rows = rows[1:]
    for row, site in zip(data_rows, sites):
        row_index = int(row.get("r"))
        cells = {cell.get("r"): cell for cell in row.findall(f"{prefix}c")}

        url_cell = cells[f"A{row_index}"]
        assert url_cell.get("t") == "inlineStr"
        url_text = url_cell.find(f"{prefix}is/{prefix}t")
        assert url_text is not None
        assert url_text.text == site["url"]

        for column, key in zip(("B", "C", "D"), ("high", "medium", "low")):
            ref = f"{column}{row_index}"
            cell = cells[ref]
            assert cell.get("t") is None
            value = cell.find(f"{prefix}v")
            assert value is not None
            assert value.text == str(site[key])

    dimension = tree.find(f"{prefix}dimension")
    assert dimension is not None
    assert dimension.get("ref") == f"A1:D{len(sites) + 1}"


def test_get_undeclared_variables_ignores_tr_loop_variables(monkeypatch):
    template = GhostwriterDocxTemplate("DOCS/sample_reports/template.docx")
    template.init_docx()

    excel = FakeXlsxPart(
        "/word/embeddings/Microsoft_Excel_Worksheet1.xlsx",
        WORKSHEET_TR_PROJECT_XML,
    )

    monkeypatch.setattr(template, "_iter_additional_parts", lambda: iter([excel]))

    env = Environment()

    class _AnyFilter(dict):
        def __contains__(self, key):  # pragma: no cover - behaviour exercised via meta
            return True

        def __missing__(self, key):  # pragma: no cover - behaviour exercised via meta
            stub = lambda value, *args, **kwargs: value
            self[key] = stub
            return stub

        def get(self, key, default=None):  # pragma: no cover - behaviour exercised via meta
            try:
                return super().__getitem__(key)
            except KeyError:
                return self.__missing__(key)

    env.filters = _AnyFilter(env.filters)

    undeclared = template.get_undeclared_template_variables(env)
    assert "project" in undeclared
    assert "site" not in undeclared


def test_collect_template_statements_limits_preview_entries():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = """
    <root>
    {% if foo %}
    <node>{{ value }}</node>
    {% for item in items %}
    {{ item.name }}
    {% endfor %}
    {% endif %}
    </root>
    """.strip()

    preview, total = template._collect_template_statements(xml, limit=2)

    assert total == 5
    assert preview == [
        {"line": 2, "statement": "{% if foo %}"},
        {"line": 3, "statement": "{{ value }}"},
    ]


def test_collect_template_statements_focuses_on_error_line():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    statements = [f"{{{{ value_{index} }}}}" for index in range(1, 11)]
    xml = "\n".join(["<root>"] + statements + ["</root>"])

    preview, total = template._collect_template_statements(xml, limit=3, focus_line=8)

    assert total == 10
    assert [entry["line"] for entry in preview] == [8, 9, 10]
    assert [entry["statement"] for entry in preview] == [
        "{{ value_8 }}",
        "{{ value_9 }}",
        "{{ value_10 }}",
    ]


def test_collect_template_statements_includes_word_context():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Intro</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>{% if foo > bar %}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>More</w:t></w:r></w:p>"
        "<w:tbl>"
        "<w:tr>"
        "<w:tc><w:p><w:r><w:t>{{ row.value }}</w:t></w:r></w:p></w:tc>"
        "<w:tc><w:p><w:r><w:t>{{ row.other }}</w:t></w:r></w:p></w:tc>"
        "</w:tr>"
        "</w:tbl>"
        "</w:body>"
        "</w:document>"
    )

    preview, total = template._collect_template_statements(xml, limit=5)

    assert total == 3
    assert preview[0]["paragraph_index"] == 2
    assert preview[0]["paragraph_text"] == "{% if foo > bar %}"

    first_cell = preview[1]
    assert first_cell["paragraph_index"] == 4
    assert first_cell["table_index"] == 1
    assert first_cell["table_row_index"] == 1
    assert first_cell["table_cell_index"] == 1
    assert first_cell["paragraph_text"] == "{{ row.value }}"

    second_cell = preview[2]
    assert second_cell["paragraph_index"] == 5
    assert second_cell["table_index"] == 1
    assert second_cell["table_row_index"] == 1
    assert second_cell["table_cell_index"] == 2
    assert second_cell["paragraph_text"] == "{{ row.other }}"


def test_format_statement_preview_includes_context():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    statements = [
        {
            "line": 2,
            "statement": "{% if foo > bar %}",
            "paragraph_index": 2,
            "paragraph_text": "{% if foo > bar %}",
        },
        {
            "line": 4,
            "statement": "{{ row.value }}",
            "paragraph_index": 4,
            "paragraph_text": "{{ row.value }}",
            "table_index": 1,
            "table_row_index": 1,
            "table_cell_index": 1,
        },
    ]

    summary = template._format_statement_preview(statements, total=3)

    assert "line 2" in summary
    assert "paragraph 2" in summary
    assert "text='{% if foo > bar %}'" in summary
    assert "table 1, row 1, cell 1" in summary
    assert "…and 1 more templating statements not shown" in summary


def test_format_statement_preview_handles_empty_preview():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    summary_no_statements = template._format_statement_preview([], total=0)
    assert summary_no_statements == "No templating statements were found in the templated XML."

    summary_without_preview = template._format_statement_preview([], total=5)
    assert "Collected 5 templating statements" in summary_without_preview


def test_render_xml_part_logs_preview(monkeypatch, caplog):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body>"
        "<w:p><w:r><w:t>Intro</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>{% if foo > bar %}</w:t></w:r></w:p>"
        "<w:p><w:r><w:t>More</w:t></w:r></w:p>"
        "</w:body>"
        "</w:document>"
    )

    class FakePart:
        partname = PackURI("/word/document.xml")

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(docx_template.DocxTemplate, "render_xml_part", _boom)

    with caplog.at_level("ERROR", logger=docx_template.logger.name):
        with pytest.raises(RuntimeError):
            template.render_xml_part(xml, FakePart(), {}, Environment())

    assert caplog.records
    message = caplog.records[0].getMessage()
    assert "Failed to render DOCX template part word/document.xml" in message
    assert "line 2" in message
    assert "paragraph 2" in message
    assert "text='{% if foo > bar %}'" in message


def test_render_xml_part_logs_preview_focuses_on_template_error(monkeypatch, caplog):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml_lines = [
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">',
        "<w:body>",
    ]
    xml_lines.extend(
        f"<w:p><w:r><w:t>{{{{ value_{index} }}}}</w:t></w:r></w:p>" for index in range(1, 21)
    )
    xml_lines.extend(["</w:body>", "</w:document>"])
    xml = "\n".join(xml_lines)

    class FakePart:
        partname = PackURI("/word/document.xml")

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(docx_template.DocxTemplate, "render_xml_part", _boom)
    monkeypatch.setattr(
        GhostwriterDocxTemplate,
        "_extract_template_error_line",
        lambda self, exc: 20,
    )

    with caplog.at_level("ERROR", logger=docx_template.logger.name):
        with pytest.raises(RuntimeError):
            template.render_xml_part(xml, FakePart(), {}, Environment())

    assert caplog.records
    message = caplog.records[0].getMessage()
    assert "error near template line 20" in message
    assert "{{ value_20 }}" in message
    assert "{{ value_1 }}" not in message
    assert caplog.records[0].docx_template_error_line == 20


def test_extract_template_error_line_from_traceback():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    try:
        exec(compile("\n\nraise TypeError('boom')", "<template>", "exec"), {})
    except TypeError as exc:
        line = template._extract_template_error_line(exc)
    else:  # pragma: no cover - exec always raises in this block
        pytest.fail("Expected TypeError to be raised")

    assert line == 3


def test_extract_template_debug_context_returns_lines(monkeypatch):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    class FakeFrame:
        def __init__(self, filename, lineno, source):
            self.filename = filename
            self.lineno = lineno
            self.source = source

    class FakeTraceback:
        def __init__(self, frames):
            self.frames = frames

        @classmethod
        def from_exception(cls, exc):  # noqa: D401 - signature mirrors real API
            source = "\n".join(
                [
                    "{% set limit = 5 %}",
                    "{% if value is not none %}",
                    "{{ value > limit }}",
                    "{% endif %}",
                ]
            )
            return cls([FakeFrame("<template>", 3, source)])

    monkeypatch.setattr(
        docx_template,
        "JinjaTraceback",
        FakeTraceback,
        raising=False,
    )

    line, context = template._extract_template_debug_context(RuntimeError("boom"), before=1, after=1)

    assert line == 3
    assert context == [
        (2, "{% if value is not none %}"),
        (3, "{{ value > limit }}"),
        (4, "{% endif %}"),
    ]


def test_extract_template_debug_context_handles_missing_traceback(monkeypatch):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    monkeypatch.setattr(docx_template, "JinjaTraceback", None, raising=False)

    line, context = template._extract_template_debug_context(RuntimeError("boom"))

    assert line is None
    assert context == []


def test_format_template_context_marks_error_line():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    context_lines = [
        (2, "{% if foo %}"),
        (3, "{{ bar > 10 }}"),
        (4, "{% endif %}"),
    ]

    summary = template._format_template_context(context_lines, error_line=3)

    assert summary.startswith("template context:")
    assert "line 3 (error)='{{ bar > 10 }}'" in summary


def test_render_xml_part_logs_template_context(monkeypatch, caplog):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = "<root>{{ value }}</root>"

    class FakePart:
        partname = PackURI("/word/document.xml")

    def _boom(*args, **kwargs):
        raise RuntimeError("boom")

    monkeypatch.setattr(docx_template.DocxTemplate, "render_xml_part", _boom)
    monkeypatch.setattr(
        GhostwriterDocxTemplate,
        "_extract_template_error_line",
        lambda self, exc: 3,
    )
    monkeypatch.setattr(
        GhostwriterDocxTemplate,
        "_extract_template_debug_context",
        lambda self, exc: (
            3,
            [
                (2, "{% if value is not none %}"),
                (3, "{{ value > limit }}"),
                (4, "{% endif %}"),
            ],
        ),
    )

    with caplog.at_level("ERROR", logger=docx_template.logger.name):
        with pytest.raises(RuntimeError):
            template.render_xml_part(xml, FakePart(), {}, Environment())

    record = caplog.records[0]
    message = record.getMessage()
    assert "template context:" in message
    assert "line 3 (error)='{{ value > limit }}'" in message
    assert record.docx_template_error_context == [
        {"line": 2, "text": "{% if value is not none %}"},
        {"line": 3, "text": "{{ value > limit }}"},
        {"line": 4, "text": "{% endif %}"},
    ]


def test_normalise_package_content_types_updates_comments_extended():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    part = FakeContentTypePart(
        "/word/commentsExtended.xml",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.commentsExtended+xml",
    )
    package = SimpleNamespace(parts=[part])
    template.docx = SimpleNamespace(_part=SimpleNamespace(package=package))

    template._normalise_package_content_types()

    assert (
        part.content_type
        == docx_template._MS_COMMENTS_EXTENDED_CONTENT_TYPE
    )


def test_cleanup_part_relationships_upgrades_comments_extended_reltype():
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)
    xml = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
        'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">'
        "<w:body><w:p><w:r><w:t>Content</w:t></w:r></w:p></w:body>"
        "</w:document>"
    )
    rel = FakeRelationship(
        reltype=docx_template._COMMENTS_EXTENDED_RELTYPE_2011
    )
    part = FakeRelPart("/word/document.xml", xml, {"rId5": rel})

    template._cleanup_part_relationships(part, xml)

    assert rel.reltype == docx_template._COMMENTS_EXTENDED_RELTYPE_2017
    assert rel._reltype == docx_template._COMMENTS_EXTENDED_RELTYPE_2017


def test_repair_app_properties_fills_empty_titles(monkeypatch):
    template = GhostwriterDocxTemplate.__new__(GhostwriterDocxTemplate)

    app_xml = (
        "<?xml version='1.0' encoding='UTF-8'?>"
        "<Properties xmlns='http://schemas.openxmlformats.org/officeDocument/2006/extended-properties' "
        "xmlns:vt='http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes'>"
        "<HeadingPairs><vt:vector size='2' baseType='variant'>"
        "<vt:variant><vt:lpstr>Title</vt:lpstr></vt:variant>"
        "<vt:variant><vt:i4>1</vt:i4></vt:variant>"
        "</vt:vector></HeadingPairs>"
        "<TitlesOfParts><vt:vector size='1' baseType='lpstr'><vt:lpstr/></vt:vector></TitlesOfParts>"
        "</Properties>"
    )

    app_part = FakeAppPropertiesPart(app_xml)

    package = SimpleNamespace(parts=[app_part])
    template.docx = SimpleNamespace(_part=SimpleNamespace(package=package))

    monkeypatch.setattr(template, "get_part_xml", lambda self, part: part._blob)

    template._repair_app_properties()

    updated_xml = app_part._blob.decode("utf-8")
    assert "Document" in updated_xml

    parsed = etree.fromstring(app_part._blob)
    namespaces = {
        "ep": "http://schemas.openxmlformats.org/officeDocument/2006/extended-properties",
        "vt": "http://schemas.openxmlformats.org/officeDocument/2006/docPropsVTypes",
    }

    titles_vector = parsed.find(".//ep:TitlesOfParts/vt:vector", namespaces)
    assert titles_vector is not None
    assert titles_vector.get("size") == "1"
    lpstr = titles_vector.find("vt:lpstr", namespaces)
    assert lpstr is not None
    assert lpstr.text


def test_numeric_tests_handle_missing_values():
    env = Environment()
    GhostwriterDocxTemplate._install_numeric_tests(env)

    assert env.tests["gt"](2, 1) is True
    assert env.tests["lt"](1, 2) is True
    assert env.tests["ge"](5, 5) is True
    assert env.tests["le"](3, 4) is True

    assert env.tests["gt"](None, 0) is False
    assert env.tests["ge"](None, 0) is True
    assert env.tests["lt"](None, 1) is True
    assert env.tests["le"](None, 0) is True

    undefined_value = env.undefined("missing")
    assert env.tests["gt"](undefined_value, 0) is False
    assert env.tests["lt"](undefined_value, 1) is True

    assert env.tests["gt"]("5", 1) is False
    assert env.tests["lt"](10, "1") is False
