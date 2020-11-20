#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""
This module contains the tools required for generating Microsoft Office documents for
reporting. The ``Reportwriter`` class accepts data and produces a docx, xlsx, pptx,
and json using the provided data.
"""

# Standard Libraries
import io
import json
import logging
import os
import random
import re
from datetime import datetime

# Django & Other 3rd Party Libraries
import docx
import jinja2
import pptx
from bs4 import BeautifulSoup, NavigableString
from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder
from docxtpl import DocxTemplate, RichText
from docx.enum.dml import MSO_THEME_COLOR_INDEX
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.opc.exceptions import PackageNotFoundError as DocxPackageNotFoundError
from docx.oxml.shared import OxmlElement, qn
from docx.enum.style import WD_STYLE_TYPE
from docx.shared import Inches, Pt, RGBColor
from jinja2.exceptions import TemplateSyntaxError
from pptx import Presentation
from pptx.dml.color import RGBColor as PptxRGBColor
from pptx.enum.text import MSO_ANCHOR, MSO_AUTO_SIZE, PP_ALIGN
from pptx.exc import PackageNotFoundError as PptxPackageNotFoundError
from xlsxwriter.workbook import Workbook

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import CompanyInformation, ReportConfiguration

# Using __name__ resolves to ghostwriter.modules.reporting
logger = logging.getLogger(__name__)


class ReportConstants:
    """Constant values used for report generation."""

    DEFAULT_STYLE_VALUES = {
        "bold": False,
        "underline": False,
        "italic": False,
        "inline_code": False,
        "strikethrough": False,
        "font_family": None,
        "font_size": None,
        "font_color": None,
        "highlight": None,
        "superscript": False,
        "subscript": False,
        "hyperlink": False,
        "hyperlink_url": None,
    }


class Reportwriter:
    """Generate report documents in Microsoft Office formats."""

    # Allowlist for HTML tags expected to come from the WYSIWYG
    tag_allowlist = [
        "code",
        "span",
        "p",
        "ul",
        "ol",
        "li",
        "a",
        "em",
        "strong",
        "u",
        "b",
        "pre",
        "sub",
        "sup",
        "del",
    ]

    # Allowlist for evidence file extensions / filetypes
    image_extensions = ["png", "jpeg", "jpg"]
    text_extensions = ["txt", "ps1", "py", "md", "log"]

    def __init__(self, report_queryset, output_path, evidence_path, template_loc=None):
        self.output_path = output_path
        self.template_loc = template_loc
        self.evidence_path = evidence_path
        self.report_queryset = report_queryset

        # Get the global report configuration
        global_report_config = ReportConfiguration.get_solo()
        self.company_config = CompanyInformation.get_solo()

        # Track report type for different Office XML
        self.report_type = None

        # Picture border settings for Word
        self.enable_borders = global_report_config.enable_borders
        self.border_color = global_report_config.border_color
        self.border_weight = global_report_config.border_weight

        # Caption options
        prefix_figure = global_report_config.prefix_figure.strip()
        self.prefix_figure = f" {prefix_figure} "
        label_figure = global_report_config.label_figure.strip()
        self.label_figure = f"{label_figure} "
        label_table = global_report_config.label_table.strip()
        self.label_table = f"{label_table} "

        # Setup Jinja2 rendering environment + custom filters
        self.jinja_env = jinja2.Environment(extensions=["jinja2.ext.debug"])
        self.jinja_env.filters["filter_severity"] = self.filter_severity
        self.jinja_env.filters["strip_html"] = self.strip_html

        logger.info(
            "Generating a report for %s using the template at %s and referencing the evidence in %s",
            self.report_queryset,
            self.template_loc,
            self.evidence_path,
        )

    def filter_severity(self, findings, allowlist):
        """
        Filter list of findings to return only those with a severity in the allowlist.

        **Parameters**

        ``findings``
            List of dictionary objects (JSON) for findings
        ``allowlist``
            List of strings matching severity categories to allow through filter
        """
        filtered_values = []
        allowlist = [severity.lower() for severity in allowlist]
        for finding in findings:
            if finding["severity"].lower() in allowlist:
                filtered_values.append(finding)
        return filtered_values

    def strip_html(self, s):
        """
        Strip HTML tags from the provided HTML while preserving newlines created by
        ``<br />`` and ``<p>`` tags and spaces.

        **Parameters**

        ``s``
            String of HTML text to strip down
        """
        html = BeautifulSoup(s, "lxml")
        output = ""
        for tag in html.descendants:
            if isinstance(tag, str):
                output += tag
            elif tag.name == "br" or tag.name == "p":
                output += "\n"
        return output

    def valid_xml_char_ordinal(self, c):
        """
        Clean string to make all characters XML compatible for Word documents.

        Source:
            https://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python

        **Parameters**

        ``c`` : string
            String of characters to validate
        """
        codepoint = ord(c)
        # Conditions ordered by presumed frequency
        return (
            0x20 <= codepoint <= 0xD7FF
            or codepoint in (0x9, 0xA, 0xD)
            or 0xE000 <= codepoint <= 0xFFFD
            or 0x10000 <= codepoint <= 0x10FFFF
        )

    def generate_json(self):
        """
        Export a report as a JSON dictionary for archiving and to generate other report types.
        """
        project_name = str(self.report_queryset.project)
        # Client data
        report_dict = {}
        report_dict["client"] = {}
        report_dict["client"]["id"] = self.report_queryset.project.client.id
        report_dict["client"]["full_name"] = self.report_queryset.project.client.name
        report_dict["client"][
            "short_name"
        ] = self.report_queryset.project.client.short_name
        report_dict["client"]["codename"] = self.report_queryset.project.client.codename
        # Client points of contact data
        report_dict["client"]["poc"] = {}
        for poc in self.report_queryset.project.client.clientcontact_set.all():
            report_dict["client"]["poc"][poc.id] = {}
            report_dict["client"]["poc"][poc.id]["id"] = poc.id
            report_dict["client"]["poc"][poc.id]["name"] = poc.name
            report_dict["client"]["poc"][poc.id]["job_title"] = poc.job_title
            report_dict["client"]["poc"][poc.id]["email"] = poc.email
            report_dict["client"]["poc"][poc.id]["phone"] = poc.phone
            report_dict["client"]["poc"][poc.id]["note"] = poc.note
        # Project data
        report_dict["project"] = {}
        report_dict["project"]["id"] = self.report_queryset.project.id
        report_dict["project"]["name"] = project_name
        report_dict["project"]["codename"] = self.report_queryset.project.codename
        report_dict["project"][
            "project_type"
        ] = self.report_queryset.project.project_type.project_type
        report_dict["project"]["note"] = self.report_queryset.project.note
        # Project dates
        start_datetime = self.report_queryset.project.start_date
        end_datetime = self.report_queryset.project.end_date
        start_month = start_datetime.strftime("%B")
        start_day = start_datetime.day
        start_year = start_datetime.year
        end_month = end_datetime.strftime("%B")
        end_day = end_datetime.day
        end_year = end_datetime.year
        if start_month == end_month:
            if start_year == end_year:
                execution_window = f"{start_month} {start_day}-{end_day}, {start_year}"
                execution_window_uk = (
                    f"{start_day}-{end_day} {start_month} {start_year}"
                )
            else:
                execution_window = f"{start_month} {start_day}, {start_year} - {end_month} {end_day}, {end_year}"
                execution_window_uk = f"{start_day} {start_month} {start_year} - {end_day} {end_month} {end_year}"
        else:
            if start_year == end_year:
                execution_window = (
                    f"{start_month} {start_day} - {end_month} {end_day}, {end_year}"
                )
                execution_window_uk = (
                    f"{start_day} {start_month} - {end_day} {end_month} {end_year}"
                )
            else:
                execution_window = f"{start_month} {start_day}, {start_year} - {end_month} {end_day}, {end_year}"
                execution_window_uk = f"{start_day} {start_month} {start_year} - {end_day} {end_month} {end_year}"
        report_dict["project"]["start_date"] = start_datetime.strftime("%B %d, %Y")
        report_dict["project"]["start_date_uk"] = start_datetime.strftime("%d %B %Y")
        report_dict["project"]["end_date"] = end_datetime.strftime("%B %d, %Y")
        report_dict["project"]["end_date_uk"] = end_datetime.strftime("%d %B %Y")
        report_dict["project"]["execution_window"] = execution_window
        report_dict["project"]["execution_window_uk"] = execution_window_uk
        # Finding data
        report_dict["findings"] = {}
        for finding in self.report_queryset.reportfindinglink_set.all():
            report_dict["findings"][finding.id] = {}
            report_dict["findings"][finding.id]["title"] = finding.title
            report_dict["findings"][finding.id]["severity"] = finding.severity.severity
            report_dict["findings"][finding.id][
                "severity_color"
            ] = finding.severity.color
            report_dict["findings"][finding.id][
                "severity_color_rgb"
            ] = finding.severity.color_rgb
            report_dict["findings"][finding.id][
                "severity_color_hex"
            ] = finding.severity.color_hex
            if finding.affected_entities:
                report_dict["findings"][finding.id][
                    "affected_entities"
                ] = finding.affected_entities
            else:
                report_dict["findings"][finding.id][
                    "affected_entities"
                ] = "<p>Must Be Provided</p>"
            report_dict["findings"][finding.id]["description"] = finding.description
            report_dict["findings"][finding.id]["impact"] = finding.impact
            report_dict["findings"][finding.id]["recommendation"] = finding.mitigation
            report_dict["findings"][finding.id][
                "replication_steps"
            ] = finding.replication_steps
            report_dict["findings"][finding.id][
                "host_detection_techniques"
            ] = finding.host_detection_techniques
            report_dict["findings"][finding.id][
                "network_detection_techniques"
            ] = finding.network_detection_techniques
            report_dict["findings"][finding.id]["references"] = finding.references
            # Get any evidence
            report_dict["findings"][finding.id]["evidence"] = {}
            for evidence_file in finding.evidence_set.all():
                evidence_name = evidence_file.friendly_name
                report_dict["findings"][finding.id]["evidence"][evidence_name] = {}
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "id"
                ] = evidence_file.id
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "friendly_name"
                ] = evidence_file.friendly_name
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "uploaded_by"
                ] = evidence_file.uploaded_by.username
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "upload_date"
                ] = evidence_file.upload_date
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "description"
                ] = evidence_file.description
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "caption"
                ] = evidence_file.caption
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "url"
                ] = evidence_file.document.url
                report_dict["findings"][finding.id]["evidence"][evidence_name][
                    "file_path"
                ] = str(evidence_file.document)
        # Infrastructure data
        report_dict["infrastructure"] = {}
        report_dict["infrastructure"]["domains"] = {}
        report_dict["infrastructure"]["servers"] = {}
        report_dict["infrastructure"]["servers"]["static"] = {}
        report_dict["infrastructure"]["servers"]["cloud"] = {}
        report_dict["infrastructure"]["domains_and_servers"] = {}
        for domain in self.report_queryset.project.history_set.all():
            report_dict["infrastructure"]["domains"][domain.domain.id] = {}
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "id"
            ] = domain.domain.id
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "name"
            ] = domain.domain.name
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "activity"
            ] = domain.activity_type.activity
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "operator"
            ] = domain.operator.username
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "start_date"
            ] = domain.start_date
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "end_date"
            ] = domain.end_date
            report_dict["infrastructure"]["domains"][domain.domain.id][
                "note"
            ] = domain.note
        for server in self.report_queryset.project.serverhistory_set.all():
            report_dict["infrastructure"]["servers"]["static"][server.server.id] = {}
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "id"
            ] = server.server.id
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "ip_address"
            ] = server.server.ip_address
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "activity"
            ] = server.activity_type.activity
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "role"
            ] = server.server_role.server_role
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "operator"
            ] = server.operator.username
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "start_date"
            ] = server.start_date
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "end_date"
            ] = server.end_date
            report_dict["infrastructure"]["servers"]["static"][server.server.id][
                "note"
            ] = server.note
        for server in self.report_queryset.project.transientserver_set.all():
            report_dict["infrastructure"]["servers"]["cloud"][server.id] = {}
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "id"
            ] = server.id
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "ip_address"
            ] = server.ip_address
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "activity"
            ] = server.activity_type.activity
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "role"
            ] = server.server_role.server_role
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "operator"
            ] = server.operator.username
            report_dict["infrastructure"]["servers"]["cloud"][server.id][
                "note"
            ] = server.note
        # Hold all domain/server associations in a temporary dictionary
        temp = {}
        for connection in self.report_queryset.project.domainserverconnection_set.all():
            # Handle one-to-many relationships by combining everything into
            # a domain and list of servers
            if connection.subdomain != "*":
                domain_name = connection.subdomain + "." + connection.domain.domain.name
            else:
                domain_name = connection.domain.domain.name
            report_dict["infrastructure"]["domains_and_servers"][connection.id] = {}
            report_dict["infrastructure"]["domains_and_servers"][connection.id][
                "domain"
            ] = domain_name
            if connection.static_server:
                server = connection.static_server.server.ip_address
            else:
                server = connection.transient_server.ip_address
            if domain_name in temp:
                server_list = [server]
                for val in temp[domain_name]:
                    server_list.append(val)
                # Remove any duplicates from server_list
                server = list(set(server_list))
            # Now add the temporary dictionary's data to the report JSON
            report_dict["infrastructure"]["domains_and_servers"][connection.id][
                "servers"
            ] = server
            if connection.endpoint:
                report_dict["infrastructure"]["domains_and_servers"][connection.id][
                    "cdn_endpoint"
                ] = connection.endpoint
            else:
                report_dict["infrastructure"]["domains_and_servers"][connection.id][
                    "cdn_endpoint"
                ] = "None"
        # Operator assignments
        report_dict["team"] = {}
        for operator in self.report_queryset.project.projectassignment_set.all():
            report_dict["team"][operator.operator.id] = {}
            report_dict["team"][operator.operator.id]["id"] = operator.operator.id
            report_dict["team"][operator.operator.id]["name"] = operator.operator.name
            report_dict["team"][operator.operator.id][
                "project_role"
            ] = operator.role.project_role
            report_dict["team"][operator.operator.id]["email"] = operator.operator.email
            report_dict["team"][operator.operator.id][
                "start_date"
            ] = operator.start_date
            report_dict["team"][operator.operator.id]["end_date"] = operator.end_date
            report_dict["team"][operator.operator.id]["note"] = operator.note
        return json.dumps(report_dict, indent=2, cls=DjangoJSONEncoder)

    def make_figure(self, par, ref=None):
        """
        Append a text run configured as an auto-incrementing figure to the provided
        paragraph. The label and number are wrapped in ``w:bookmarkStart`` and
        ``w:bookmarkEnd``.

        Source:
            https://github.com/python-openxml/python-docx/issues/359

        **Parameters**

        ``par`` : docx.paragraph.Paragraph
            Paragraph to alter
        ``ref`` : string
            String to use as the ``w:name`` value for the bookmark
        """

        def generate_ref():
            """Generate a random eight character reference ID."""
            return random.randint(10000000, 99999999)

        if ref:
            ref = f"_Ref{ref}"
        else:
            ref = f"_Ref{generate_ref()}"
        # Start a bookmark run with the figure label
        p = par._p
        bookmark_start = OxmlElement("w:bookmarkStart")
        bookmark_start.set(qn("w:name"), ref)
        bookmark_start.set(qn("w:id"), "0")
        p.append(bookmark_start)

        # Add the figure label
        run = par.add_run(self.label_figure)

        # Append XML for a new field character run
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "begin")
        r.append(fldChar)

        # Add field code instructions with ``instrText``
        run = par.add_run()
        r = run._r
        instrText = OxmlElement("w:instrText")
        # Sequential figure with arabic numbers
        instrText.text = " SEQ Figure \\* ARABIC"
        r.append(instrText)

        # An optional ``separate`` value to enforce a space between label and number
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "separate")
        r.append(fldChar)

        # Include ``#`` as a placeholder for the number when Word updates fields
        run = par.add_run("#")
        r = run._r
        # Close the field character run
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "end")
        r.append(fldChar)

        # End the bookmark after the number
        p = par._p
        bookmark_end = OxmlElement("w:bookmarkEnd")
        bookmark_end.set(qn("w:id"), "0")
        p.append(bookmark_end)

    def make_cross_ref(self, par, ref):
        """
        Append a text run configured as a cross-reference to the provided paragraph.

        **Parameters**

        ``par`` : docx.paragraph.Paragraph
            Paragraph to alter
        ``ref`` : string
            The ``w:name`` value of the target bookmark
        """
        # Start the field character run for the label and number
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "begin")
        r.append(fldChar)

        # Add field code instructions with ``instrText`` that points to the target bookmark
        run = par.add_run()
        r = run._r
        instrText = OxmlElement("w:instrText")
        instrText.text = f" REF _Ref{ref} \\h "
        r.append(instrText)

        # An optional ``separate`` value to enforce a space between label and number
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "separate")
        r.append(fldChar)

        # Add runs for the figure label and number
        run = par.add_run(self.label_figure)
        # This ``#`` is a placeholder Word will replace with the figure's number
        run = par.add_run("#")

        # Close the  field character run
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "end")
        r.append(fldChar)

        return par

    def list_number(self, par, prev=None, level=None, num=True):
        """
        Makes the specified paragraph a list item with a specific level and optional restart.

        An attempt will be made to retrieve an abstract numbering style that corresponds
        to the style of the paragraph. If that is not possible, the default numbering or
        bullet style will be used based on the ``num`` parameter.

        Source:
            https://github.com/python-openxml/python-docx/issues/25#issuecomment-400787031

        **Parameters**

        ``par`` : docx.paragraph.Paragraph
            The docx paragraph to turn into a list item.
        ``prev`` : docx.paragraph.Paragraph or None
            The previous paragraph in the list. If specified, the numbering and styles will
            be taken as a continuation of this paragraph. If omitted, a new numbering scheme
            will be started.
        ``level`` : int or None
            The level of the paragraph within the outline. If ``prev`` is set, defaults
            to the same level as in ``prev``. Otherwise, defaults to zero.
        ``num`` : bool
            If ``prev`` is :py:obj:`None` and the style of the paragraph does not correspond
            to an existing numbering style, this will determine wether or not the list will
            be numbered or bulleted. The result is not guaranteed, but is fairly safe for
            most Word templates.
        """
        xpath_options = {
            True: {"single": "count(w:lvl)=1 and ", "level": 0},
            False: {"single": "", "level": level},
        }

        def style_xpath(prefer_single=True):
            """
            The style comes from the outer-scope variable ``par.style.name``.
            """
            style = par.style.style_id
            return (
                "w:abstractNum["
                '{single}w:lvl[@w:ilvl="{level}"]/w:pStyle[@w:val="{style}"]'
                "]/@w:abstractNumId"
            ).format(style=style, **xpath_options[prefer_single])

        def type_xpath(prefer_single=True):
            """
            The type is from the outer-scope variable ``num``.
            """
            type = "decimal" if num else "bullet"
            return (
                "w:abstractNum["
                '{single}w:lvl[@w:ilvl="{level}"]/w:numFmt[@w:val="{type}"]'
                "]/@w:abstractNumId"
            ).format(type=type, **xpath_options[prefer_single])

        def get_abstract_id():
            """
            Select as follows:

            1. Match single-level by style (get min ID)
            2. Match exact style and level (get min ID)
            3. Match single-level decimal/bullet types (get min ID)
            4. Match decimal/bullet in requested level (get min ID)
            """
            for fn in (style_xpath, type_xpath):
                for prefer_single in (True, False):
                    xpath = fn(prefer_single)
                    ids = numbering.xpath(xpath)
                    if ids:
                        return min(int(x) for x in ids)
            return 0

        if (
            prev is None
            or prev._p.pPr is None
            or prev._p.pPr.numPr is None
            or prev._p.pPr.numPr.numId is None
        ):
            if level is None:
                level = 0
            numbering = (
                self.sacrificial_doc.part.numbering_part.numbering_definitions._numbering
            )
            # Compute the abstract ID first by style, then by ``num``
            abstract = get_abstract_id()
            # Set the concrete numbering based on the abstract numbering ID
            num = numbering.add_num(abstract)
            # Make sure to override the abstract continuation property
            num.add_lvlOverride(ilvl=level).add_startOverride(1)
            # Extract the newly-allocated concrete numbering ID
            num = num.numId
        else:
            if level is None:
                level = prev._p.pPr.numPr.ilvl.val
            # Get the previous concrete numbering ID
            num = prev._p.pPr.numPr.numId.val
        par._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = num
        par._p.get_or_add_pPr().get_or_add_numPr().get_or_add_ilvl().val = level

        return par

    def get_styles(self, tag):
        """
        Get styles from an BS4 ``Tag`` object's ``styles`` attribute and convert
        the string to a dictionary.

        **Parameters**

        ``tag`` : Tag
            BS4 ``Tag`` witth a ``styles`` attribute
        """
        tag_styles = {}
        style_str = tag.attrs["style"]
        # Filter any blanks from the split
        style_list = list(filter(None, style_str.split(";")))
        for style in style_list:
            temp = style.split(":")
            key = temp[0].strip()
            value = temp[1].strip()
            try:
                if key == "font-size":
                    # Remove the "pt" from the font size and convert it to a ``Pt`` object
                    value = value.replace("pt", "")
                    value = float(value)
                    value = Pt(value)
                if key == "font-family":
                    # Some fonts include a list of values – get just the first one
                    font_list = value.split(",")
                    priority_font = (
                        font_list[0].replace("'", "").replace('"', "").strip()
                    )
                    value = priority_font
                if key == "color":
                    # Convert the color hex value to an ``RGCBolor`` object
                    value = value.replace("#", "")
                    n = 2
                    hex_color = [
                        hex(int(value[i : i + n], 16)) for i in range(0, len(value), n)
                    ]
                    if self.report_type == "pptx":
                        value = PptxRGBColor(*map(lambda v: int(v, 16), hex_color))
                    else:
                        value = RGBColor(*map(lambda v: int(v, 16), hex_color))
                tag_styles[key] = value
            except Exception:
                logger.exception(
                    "Failed to convert one of the inline styles for a text run"
                )
        return tag_styles

    def process_evidence(self, finding, keyword, file_path, extension, par):
        """
        Process the specified evidence file for the named finding to add it to the Word document.

        **Parameters**

        ``finding`` : dict
            Finding currently being processed
        ``keyword`` : string
            Evidence keyword corresponding to the evidence attached to the finding
        ``file_path`` : string
            File path for the evidence file
        ``extension`` : string
            Evidence file's extension
        ``par`` : Paragraph
            Paragraph meant to hold the evidence
        """
        if extension in self.text_extensions:
            with open(file_path, "r") as evidence_contents:
                # Read in evidence text
                evidence_text = evidence_contents.read()
                if self.report_type == "pptx":
                    self.delete_paragraph(par)
                    top = Inches(1.65)
                    left = Inches(8)
                    width = Inches(4.5)
                    height = Inches(3)
                    # Create new textbox, textframe, paragraph, and run
                    textbox = self.finding_slide.shapes.add_textbox(
                        left, top, width, height
                    )
                    text_frame = textbox.text_frame
                    p = text_frame.paragraphs[0]
                    run = p.add_run()
                    # Insert evidence and apply formatting
                    run.text = evidence_text
                    font = run.font
                    font.size = Pt(11)
                    font.name = "Courier New"
                else:
                    # Drop in text evidence using the ``CodeBlock`` style
                    par.text = evidence_text
                    par.style = "CodeBlock"
                    par.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    # Add a caption paragraph below the evidence
                    p = self.sacrificial_doc.add_paragraph(style="Caption")
                    ref_name = re.sub(
                        "[^A-Za-z0-9]+",
                        "",
                        finding["evidence"][keyword]["friendly_name"],
                    )
                    self.make_figure(p, ref_name)
                    run = p.add_run(
                        self.prefix_figure + finding["evidence"][keyword]["caption"]
                    )
        elif extension in self.image_extensions:
            # Drop in the image at the full 6.5" width and add the caption
            if self.report_type == "pptx":
                self.delete_paragraph(par)
                # Place new textbox to the mid-right
                top = Inches(1.65)
                left = Inches(8)
                width = Inches(4.5)
                self.finding_slide.shapes.add_picture(file_path, left, top, width=width)
            else:
                par.alignment = WD_ALIGN_PARAGRAPH.CENTER
                run = par.add_run()
                # Add the picture to the document and then add a border
                run.add_picture(file_path, width=Inches(6.5))

                if self.enable_borders:
                    # Add the border – see Ghostwriter Wiki for documentation
                    inline_class = run._r.xpath("//wp:inline")[-1]
                    inline_class.attrib["distT"] = "0"
                    inline_class.attrib["distB"] = "0"
                    inline_class.attrib["distL"] = "0"
                    inline_class.attrib["distR"] = "0"

                    # Set the shape's "effect extent" attributes to the border weight
                    effect_extent = OxmlElement("wp:effectExtent")
                    effect_extent.set("l", str(self.border_weight))
                    effect_extent.set("t", str(self.border_weight))
                    effect_extent.set("r", str(self.border_weight))
                    effect_extent.set("b", str(self.border_weight))
                    # Insert just below ``<wp:extent>`` or it will not work
                    inline_class.insert(1, effect_extent)

                    # Find inline shape properties – ``pic:spPr``
                    pic_data = run._r.xpath("//pic:spPr")[-1]
                    # Assemble OXML for a solid border
                    ln_xml = OxmlElement("a:ln")
                    ln_xml.set("w", str(self.border_weight))
                    solidfill_xml = OxmlElement("a:solidFill")
                    color_xml = OxmlElement("a:srgbClr")
                    color_xml.set("val", self.border_color)
                    solidfill_xml.append(color_xml)
                    ln_xml.append(solidfill_xml)
                    pic_data.append(ln_xml)

                # Create the caption for the image
                p = self.sacrificial_doc.add_paragraph(style="Caption")
                ref_name = re.sub(
                    "[^A-Za-z0-9]+", "", finding["evidence"][keyword]["friendly_name"]
                )
                self.make_figure(p, ref_name)
                run = p.add_run(
                    self.prefix_figure + finding["evidence"][keyword]["caption"]
                )
        # Skip unapproved files
        else:
            par = None
            pass

    def delete_paragraph(self, par):
        """
        Delete the specified paragraph.

        **Parameter**

        ``par``
            Paragraph to delete from the document
        """
        p = par._p
        parent_element = p.getparent()
        parent_element.remove(p)

    def write_xml(self, text, par, styles):
        """
        Write the provided text to Office XML.

        **Parameters**

        ``text`` : string
            Text to check for keywords
        ``par`` : Paragraph
            Paragraph for the processed text
        ``styles`` : dict
            Copy of ``ReportConstants.DEFAULT_STYLE_VALUES`` with styles for the text
        """
        # Handle hyperlinks based on Office report type
        # Easy with ``python-pptx`` API, but custom work required for ``python-docx``
        if styles["hyperlink"] and styles["hyperlink_url"]:
            if self.report_type == "pptx":
                run = par.add_run()
                run.text = text
                run.hyperlink.address = styles["hyperlink_url"]
            else:
                logger.info("Text is: %s, styles: %s", text, styles)
                # For Word, this code is modified from this issue:
                #   https://github.com/python-openxml/python-docx/issues/384
                # Get an ID from the ``document.xml.rels`` file
                part = par.part
                r_id = part.relate_to(
                    styles["hyperlink_url"],
                    docx.opc.constants.RELATIONSHIP_TYPE.HYPERLINK,
                    is_external=True,
                )
                # Create the ``w:hyperlink`` tag and add needed values
                hyperlink = docx.oxml.shared.OxmlElement("w:hyperlink")
                hyperlink.set(
                    docx.oxml.shared.qn("r:id"),
                    r_id,
                )
                # Create the ``w:r`` and ``w:rPr`` elements
                new_run = docx.oxml.shared.OxmlElement("w:r")
                rPr = docx.oxml.shared.OxmlElement("w:rPr")
                new_run.append(rPr)
                new_run.text = text
                hyperlink.append(new_run)
                # Create a new Run object and add the hyperlink into it
                run = par.add_run()
                run._r.append(hyperlink)
                # A workaround for the lack of a hyperlink style
                if "Hyperlink" in self.sacrificial_doc.styles:
                    run.style = "Hyperlink"
                else:
                    run.font.color.theme_color = MSO_THEME_COLOR_INDEX.HYPERLINK
                    run.font.underline = True
        else:
            run = par.add_run()
            run.text = text

        # Apply font-based styles that work for both APIs
        font = run.font
        font.bold = styles["bold"]
        font.italic = styles["italic"]
        font.underline = styles["underline"]
        if styles["font_color"]:
            font.color.rgb = styles["font_color"]
        font.name = styles["font_family"]
        font.size = styles["font_size"]
        if styles["inline_code"]:
            if self.report_type == "pptx":
                font.name = "Courier New"
            else:
                run.style = "CodeInline"
                font.no_proof = True

        # These styles require extra work due to limitations of the ``python-pptx`` API
        if styles["highlight"]:
            if self.report_type == "pptx":
                rPr = run._r.get_or_add_rPr()
                highlight = OxmlElement("a:highlight")
                srgbClr = OxmlElement("a:srgbClr")
                srgbClr.set("val", "FFFF00")
                highlight.append(srgbClr)
                rPr.append(highlight)
            else:
                font.highlight_color = WD_COLOR_INDEX.YELLOW
        if styles["strikethrough"]:
            if self.report_type == "pptx":
                font._element.set("strike", "sngStrike")
            else:
                font.strike = styles["strikethrough"]
        if styles["subscript"]:
            if self.report_type == "pptx":
                font._element.set("baseline", "-25000")
            else:
                font.subscript = styles["subscript"]
        if styles["superscript"]:
            if self.report_type == "pptx":
                font._element.set("baseline", "30000")
            else:
                font.superscript = styles["superscript"]

    def replace_and_write(
        self, text, par, finding, styles=ReportConstants.DEFAULT_STYLE_VALUES.copy()
    ):
        """
        Find and replace template keywords in the provided text.

        **Parameters**

        ``text`` : string
            Text to check for keywords
        ``par`` : Paragraph
            Paragraph for the processed text
        ``styles`` : dict
            Copy of ``ReportConstants.DEFAULT_STYLE_VALUES`` with styles for the text
        """
        text = text.replace("\r\n", "")
        # Regex for searching for bracketed template placeholders, e.g. ``{{.client}}``
        keyword_regex = r"\{\{\.(.*?)\}\}"
        # Search for ``{{. }}`` keywords
        match = re.search(keyword_regex, text)
        if match:
            # Get just the first match, set it as the ``keyword``, and remove it from the line
            # There should never be - or need to be - multiple matches
            match = match[0]
            keyword = match.replace("}}", "").replace("{{.", "").strip()
        else:
            keyword = ""
        # Perform static client name replacement
        if "{{.client}}" in text:
            if self.report_json["client"]["short_name"]:
                text = text.replace(
                    "{{.client}}", self.report_json["client"]["short_name"]
                )
            else:
                text = text.replace(
                    "{{.client}}", self.report_json["client"]["full_name"]
                )
        # Perform replacement of project-related placeholders
        if "{{.project_start}}" in text:
            text = text.replace(
                "{{.project_start}}", self.report_json["project"]["start_date"]
            )
        if "{{.project_end}}" in text:
            text = text.replace(
                "{{.project_end}}", self.report_json["project"]["end_date"]
            )
        if "{{.project_start_uk}}" in text:
            text = text.replace(
                "{{.project_start_uk}}", self.report_json["project"]["start_date_uk"]
            )
        if "{{.project_end_uk}}" in text:
            text = text.replace(
                "{{.project_end_uk}}", self.report_json["project"]["end_date_uk"]
            )
        if "{{.project_type}}" in text:
            text = text.replace(
                "{{.project_type}}", self.report_json["project"]["project_type"].lower()
            )
        # Transform caption placeholders into figures
        if keyword.startswith("caption"):
            logger.info("GOT A CAPTION: %s", repr(keyword))
            ref_name = keyword.lstrip("caption ")
            ref_name = re.sub("[^A-Za-z0-9]+", "", ref_name)
            logger.info(text)
            text = text.replace("{{.%s}}" % keyword, "")
            logger.info(text)
            if self.report_type == "pptx":
                if ref_name:
                    run = par.add_run()
                    run.text = f"See {ref_name}"
                    font = run.font
                    font.italic = True
            else:
                par.style = "Caption"
                if ref_name:
                    self.make_figure(par, ref_name)
                else:
                    self.make_figure(par)
                par.add_run(self.prefix_figure + text)
            return par

        # Transform references into bookmarks
        if keyword and keyword.startswith("ref "):
            ref_keyword = keyword
            keyword = keyword.lstrip("ref ")
            ref_name = re.sub("[^A-Za-z0-9]+", "", keyword)
            ref_placeholder = "{{.%s}}" % ref_keyword
            exploded_text = re.split(f"({ref_placeholder})", text)
            for text in exploded_text:
                if text == ref_placeholder:
                    if self.report_type == "pptx":
                        run = par.add_run()
                        run.text = f"See {ref_name}"
                        font = run.font
                        font.italic = True
                    else:
                        self.make_cross_ref(
                            par,
                            ref_name,
                        )
                else:
                    self.write_xml(text, par, styles)
            return par

        # Handle evidence keywords
        if "evidence" in finding:
            if keyword and keyword in finding["evidence"].keys():
                file_path = (
                    settings.MEDIA_ROOT
                    + "/"
                    + finding["evidence"][keyword]["file_path"]
                )
                extension = finding["evidence"][keyword]["url"].split(".")[-1]
                if os.path.exists(file_path):
                    self.process_evidence(finding, keyword, file_path, extension, par)
                    return par
                else:
                    raise FileNotFoundError(file_path)

        # If nothing above triggers, write the text
        self.write_xml(text, par, styles)
        return par

    def process_nested_tags(self, contents, par, finding):
        """
        Process BeautifulSoup4 ``Tag`` objects containing nested HTML tags.

        **Parameters**

        ``contents`` : Tag.contents
            Contents of a BS4 ``Tag``
        ``par`` : Paragraph
            Word docx ``Paragraph`` object
        ``finding`` : dict
            The current finding (JSON) being processed
        """
        for part in contents:
            styles = ReportConstants.DEFAULT_STYLE_VALUES.copy()
            nested_styles = ReportConstants.DEFAULT_STYLE_VALUES.copy()
            # Get each part's name to check if it's a ``Tag`` object
            # A plain string will return ``None`` - no tag
            part_name = part.name
            if part_name:
                # Split part into list of plain text and tag objects
                part_contents = part.contents
                # Get the parent object's style info first as it applies to all future runs
                # A ``code`` tag here is inline code inside of a ``p`` tag
                if part_name == "code":
                    nested_styles["inline_code"] = True
                # An ``em`` tag designates italics and appears rarely
                elif part_name == "em":
                    nested_styles["italic_font"] = True
                # A ``strong`` or ``b`` tag designates bold/strong font style and appears rarely
                elif part_name == "strong" or part_name == "b":
                    nested_styles["bold"] = True
                # A ``u`` tag desingates underlined text
                elif part_name == "u":
                    nested_styles["underline"] = True
                elif part_name == "sub":
                    nested_styles["subscript"] = True
                elif part_name == "sup":
                    nested_styles["superscript"] = True
                elif part_name == "del":
                    nested_styles["strikethrough"] = True
                # A span tag will contain one or more classes for formatting
                elif part_name == "span":
                    if "class" in part.attrs:
                        part_attrs = part.attrs["class"]
                        # Check existence of supported classes
                        if "italic" in part_attrs:
                            nested_styles["italic"] = True
                        if "bold" in part_attrs:
                            nested_styles["bold"] = True
                        if "underline" in part_attrs:
                            nested_styles["underline"] = True
                        if "highlight" in part_attrs:
                            nested_styles["highlight"] = True
                    if "style" in part.attrs:
                        part_style = self.get_styles(part)
                        # Check existence of supported styles
                        if "font-size" in part_style:
                            nested_styles["font_size"] = part_style["font-size"]
                        if "font-family" in part_style:
                            nested_styles["font_family"] = part_style["font-family"]
                        if "color" in part_style:
                            nested_styles["font_color"] = part_style["color"]
                        if "background-color" in part_style:
                            nested_styles["highlight"] = part_style["background-color"]
                elif part_name == "a":
                    nested_styles["hyperlink"] = True
                    nested_styles["hyperlink_url"] = part["href"]
                # Any other tags are unexpected and ignored
                else:
                    if part_name not in self.tag_allowlist:
                        logger.warning(
                            "Encountered an unexpected nested HTML tag: %s", part_name
                        )
                # Loop over all items in the contents list
                for tag in part_contents:
                    # Same as above with the nested tags
                    tag_name = tag.name
                    if tag_name and tag_name in self.tag_allowlist:
                        tag_contents = tag.contents
                        content_text = ""
                        # Check for an additional tags in the contents
                        # This happens when a hyperlink is formatted with a font style
                        if tag_contents[0].name:
                            if tag_contents[0].name == "a":
                                styles["hyperlink"] = True
                                styles["hyperlink_url"] = tag_contents[0]["href"]
                                content_text = tag_contents[0].text
                        else:
                            content_text = " ".join(tag_contents)
                        if tag_name == "code":
                            styles["inline_code"] = True
                        elif tag_name == "em":
                            styles["italic"] = True
                        elif tag_name == "span":
                            if "class" in tag.attrs:
                                tag_attrs = tag.attrs["class"]
                                if "italic" in tag_attrs:
                                    styles["italic"] = True
                                if "bold" in tag_attrs:
                                    styles["bold"] = True
                                if "underline" in tag_attrs:
                                    styles["underline"] = True
                                if "highlight" in tag_attrs:
                                    styles["highlight"] = True
                            if "style" in part.attrs:
                                tag_style = self.get_styles(tag)
                                # Check existence of supported styles
                                if "font-size" in tag_style:
                                    styles["font_size"] = tag_style["font-size"]
                                if "font-family" in tag_style:
                                    styles["font_family"] = tag_style["font-family"]
                                if "color" in tag_style:
                                    styles["font_color"] = tag_style["color"]
                                if "background-color" in tag_style:
                                    styles["highlight"] = tag_style["background-color"]
                        elif tag_name == "a":
                            styles["hyperlink"] = True
                            styles["hyperlink_url"] = tag["href"]
                        else:
                            logger.warning(
                                "Encountered an unexpected nested HTML tag: %s",
                                tag_name,
                            )
                    elif tag_name:
                        logger.warning(
                            "Ignoring a nested HTML tag not in the allowlist: %s",
                            tag_name,
                        )
                        continue
                    else:
                        content_text = tag

                    # Conditionally set text styles
                    if styles["inline_code"] or nested_styles["inline_code"]:
                        styles["inline_code"] = True
                    if styles["underline"] or nested_styles["underline"]:
                        styles["underline"] = True
                    if styles["bold"] or nested_styles["bold"]:
                        styles["bold"] = True
                    if styles["italic"] or nested_styles["italic"]:
                        styles["italic"] = True
                    if styles["strikethrough"] or nested_styles["strikethrough"]:
                        styles["strikethrough"] = True
                    if styles["superscript"] or nested_styles["superscript"]:
                        styles["superscript"] = True
                    if styles["subscript"] or nested_styles["subscript"]:
                        styles["subscript"] = True
                    if styles["highlight"] or nested_styles["highlight"]:
                        styles["highlight"] = True
                    # These styles can be deeply nested, so we favor the run's style
                    # Take the nested style if the current run's style is ``None``
                    if styles["hyperlink"] or nested_styles["hyperlink"]:
                        styles["hyperlink"] = True
                        if not styles["hyperlink_url"]:
                            styles["hyperlink_url"] = nested_styles["hyperlink_url"]
                    if styles["font_size"] or nested_styles["font_size"]:
                        if not styles["font_size"]:
                            styles["font_size"] = nested_styles["font_size"]
                    if styles["font_family"] or nested_styles["font_family"]:
                        if not styles["font_family"]:
                            styles["font_family"] = nested_styles["font_family"]
                    if styles["font_color"] or nested_styles["font_color"]:
                        if not styles["font_color"]:
                            styles["font_color"] = nested_styles["font_color"]

                    # Write the text for this run
                    par = self.replace_and_write(content_text, par, finding, styles)
                    # Reset temporary run styles
                    styles = ReportConstants.DEFAULT_STYLE_VALUES.copy()
            # There are no tags to process, so write the string
            else:
                if isinstance(part, NavigableString):
                    par = self.replace_and_write(part, par, finding)
                else:
                    par = self.replace_and_write(part.text, par, finding)
        return par

    def create_list_paragraph(
        self, prev_p, level, num=False, alignment=WD_ALIGN_PARAGRAPH.LEFT
    ):
        """
        Create a new paragraph in the document for a list.

        **Parameters**

        ``prev_p``
            Previous paragraph to link the next list item
        ``level``
            Indentation level for the list item
        ``num``
            Boolean to determine if the line item will be numbered (Default: False)
        """
        if self.report_type == "pptx":
            # Move to new paragraph/line and indent bullets based on level
            p = self.finding_body_shape.text_frame.add_paragraph()
            p.level = level
        else:
            styles = self.sacrificial_doc.styles
            try:
                if num:
                    list_style = styles["Number List"]
                else:
                    list_style = styles["Bullet List"]
            except Exception:
                list_style = styles["List Paragraph"]
            p = self.sacrificial_doc.add_paragraph(style=list_style)
            p = self.list_number(p, prev=prev_p, level=level, num=num)
            p.alignment = alignment
        return p

    def parse_nested_html_lists(self, tag, prev_p, num, finding, level=0):
        """
        Recursively parse deeply nested lists. This checks for ``<ol>`` or ``<ul>`` tags
        and keeps parsing until all nested lists are found and processed.

        Returns the last paragraph object created.

        **Parameters**

        ``tag``
            BeautifulSoup 4 Tag object to parse
        ``prev_p``
            Previous paragraph to link the next list item
        ``num``
            Boolean to determine if the line item will be numbered
        ``finding``
            Report finding currently being processed
        ``level``
            Indentation level for the list item (Defaults to 0)
        """
        p = prev_p
        contents = tag.contents
        for part in contents:
            if part.name == "li":
                # Get the contents of li
                li_contents = part.contents
                # A length of one means no other tags to process
                if len(li_contents) == 1:
                    # Create the paragraph for this list item
                    p = self.create_list_paragraph(prev_p, level, num)
                    if li_contents[0].name:
                        self.process_nested_tags(li_contents, p, finding)
                    else:
                        self.replace_and_write(part.text, p, finding)
                # Bigger lists mean more tags, so process nested tags
                else:
                    # Find part with nested list
                    if part.ol or part.ul:
                        # Get everything between the <li> and the first nested list tag
                        temp = []
                        nested_list = None
                        for sub_part in part:
                            # Add everything NOT a nested list to temp
                            # This holds text and nested tags that come before the first list tag
                            if not sub_part.name == "ol" and not sub_part.name == "ul":
                                if sub_part != "\n":
                                    temp.append(sub_part)
                            elif sub_part.name == "ol" or sub_part.name == "ul":
                                if sub_part != "\n":
                                    nested_list = sub_part
                        # If temp isn't empty, process it like any other line
                        if temp:
                            p = self.create_list_paragraph(prev_p, level, num)
                            if len(temp) == 1:
                                if temp[0].name:
                                    self.process_nested_tags(temp, p, finding)
                                else:
                                    self.replace_and_write(temp[0], p, finding)
                            # Bigger lists mean more tags, so process nested tags
                            else:
                                self.process_nested_tags(temp, p, finding)
                        # Recursively process this list and any other nested lists inside of it
                        if nested_list:
                            # Increment the list level counter for this nested list
                            level += 1
                            p = self.parse_nested_html_lists(
                                nested_list, p, num, finding, level
                            )
                    else:
                        p = self.create_list_paragraph(prev_p, level, num)
                        self.process_nested_tags(part.contents, p, finding)
                prev_p = p
            # If ol tag encountered, increment level and switch to numbered list
            elif part.name == "ol":
                level += 1
                p = self.parse_nested_html_lists(part, prev_p, num, finding, level)
            # If ul tag encountered, increment level and switch to bulleted list
            elif part.name == "ul":
                level += 1
                p = self.parse_nested_html_lists(part, prev_p, num, finding, level)
            # No change in list type, so proceed with writing the line
            elif part.name:
                p = self.create_list_paragraph(prev_p, level, num)
                self.process_nested_tags(part, p, finding)
            else:
                if not isinstance(part, NavigableString):
                    logger.warning(
                        "Encountered an unknown tag for a list: %s", part.name
                    )
                else:
                    if part.strip() != "":
                        p = self.create_list_paragraph(prev_p, level, num)
                        self.replace_and_write(part.strip(), p, finding)

        # Return last paragraph created
        return p

    def process_text_xml(self, text, finding):
        """
        Process the provided text from the specified finding to parse keywords for
        evidence placement and formatting for Office XML.

        **Parameters**

        ``text``
            Text to convert to Office XML
        ``finding``
            Current report finding being processed
        """
        prev_p = None

        # Clean text to make it XML compatible for Office XML
        text = "".join(c for c in text if self.valid_xml_char_ordinal(c))

        if text:
            # Parse the HTML into a BS4 soup object
            soup = BeautifulSoup(text, "lxml")
            # Each WYSIWYG field begins with `<html><body>` so get the contents of body
            body = soup.find("body")
            contents_list = body.contents
            # Loop over all ``bs4.element.Tag`` objects in the body
            for tag in contents_list:
                tag_name = tag.name
                # Hn – Headings
                if tag_name in ["h1", "h2", "h3", "h4", "h5", "h6"]:
                    if self.report_type == "pptx":
                        # No headings in PPTX, so add a new line and bold it as a pseudo-heading
                        p = self.finding_body_shape.text_frame.add_paragraph()
                        run = p.add_run()
                        run.text = tag.text
                        font = run.font
                        font.bold = True
                    else:
                        heading_num = int(tag_name[1])
                        # Add the heading to the document
                        # This discards any inline formatting, but that should be managed
                        # by editing the style in the template
                        p = self.sacrificial_doc.add_heading(tag.text, heading_num)

                # P – Paragraphs
                elif tag_name == "p":
                    # Get the tag's contents to check for additional formatting
                    contents = tag.contents
                    if self.report_type == "pptx":
                        p = self.finding_body_shape.text_frame.add_paragraph()
                        ALIGNMENT = PP_ALIGN
                    else:
                        p = self.sacrificial_doc.add_paragraph()
                        ALIGNMENT = WD_ALIGN_PARAGRAPH
                    # Check for alignment classes
                    if "class" in tag.attrs:
                        tag_attrs = tag.attrs["class"]
                        if "left" in tag_attrs:
                            p.alignment = ALIGNMENT.LEFT
                        if "center" in tag_attrs:
                            p.alignment = ALIGNMENT.CENTER
                        if "right" in tag_attrs:
                            p.alignment = ALIGNMENT.RIGHT
                        if "justify" in tag_attrs:
                            p.alignment = ALIGNMENT.JUSTIFY
                    self.process_nested_tags(contents, p, finding)

                # PRE – Code Blocks
                elif tag_name == "pre":
                    # The WYSIWYG editor doesn't allow users to format text inside of a code block
                    # So, just insert the text without any further processing
                    contents = tag.contents
                    if self.report_type == "pptx":
                        # Place new textbox to the mid-right
                        if contents:
                            top = Inches(1.65)
                            left = Inches(8)
                            width = Inches(4.5)
                            height = Inches(3)
                            # Create new textbox, textframe, paragraph, and run
                            textbox = self.finding_slide.shapes.add_textbox(
                                left, top, width, height
                            )
                            text_frame = textbox.text_frame
                            # There should be just the one code tag inside any Ghostwriter code block
                            for content in contents:
                                # The only content should be a long line of text with `\r\n`
                                for code in content:
                                    # Split at the newlines to make a new list
                                    parts = code.split("\r\n")
                                    # Iterate over the list of code lines to make paragraphs
                                    for code_line in parts:
                                        p = text_frame.add_paragraph()
                                        p.alignment = PP_ALIGN.LEFT
                                        run = p.add_run()
                                        # Insert code block and apply formatting
                                        run.text = code_line
                                        font = run.font
                                        font.size = Pt(11)
                                        font.name = "Courier New"
                    else:
                        if contents:
                            # There should be just the one code tag inside any Ghostwriter code block
                            for content in contents:
                                # The only content should be a long line of text with `\r\n`
                                for code in content:
                                    # Split at the newlines to make a new list
                                    parts = code.split("\r\n")
                                    # Iterate over the list of code lines to make paragraphs
                                    for code_line in parts:
                                        # Create paragraph and apply 'CodeBlock' style
                                        # Style is managed in the docx template
                                        p = self.sacrificial_doc.add_paragraph(
                                            code_line
                                        )
                                        p.style = "CodeBlock"
                                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT

                # OL & UL – Ordered/Numbered & Unordered Lists
                elif tag_name == "ol" or tag_name == "ul":
                    # Ordered/numbered lists need numbers and linked paragraphs
                    p = None
                    prev_p = None
                    if tag_name == "ol":
                        num = True
                    else:
                        num = False

                    # Get the list tag's contents and check each item
                    contents = tag.contents
                    for part in contents:
                        # Reset list indentation level for each loop
                        level = 0
                        # Check if the tag is a list item, <li>
                        if part.name == "li":
                            # Get the contents of li
                            li_contents = part.contents
                            # A length of `1` means no other tags to process
                            if len(li_contents) == 1:
                                # Create the paragraph for this list item
                                p = self.create_list_paragraph(prev_p, level, num)
                                if li_contents[0].name:
                                    p = self.process_nested_tags(
                                        li_contents, p, finding
                                    )
                                else:
                                    p = self.replace_and_write(part.text, p, finding)
                            # Bigger lists mean more tags, so process nested tags
                            else:
                                # Identify a part with a nested list
                                if part.ol or part.ul:
                                    # Get everything between the <li> and the first nested <ol>
                                    temp = []
                                    nested_list = None
                                    for sub_part in part:
                                        # Add everything NOT a nested list to temp
                                        # This holds text and nested tags that come before the first list tag
                                        if (
                                            not sub_part.name == "ol"
                                            and not sub_part.name == "ul"
                                        ):
                                            if sub_part != "\n":
                                                temp.append(sub_part)
                                        elif (
                                            sub_part.name == "ol"
                                            or sub_part.name == "ul"
                                        ):
                                            if sub_part != "\n":
                                                nested_list = sub_part
                                    # If temp isn't empty, process it like any other line
                                    if temp:
                                        p = self.create_list_paragraph(
                                            prev_p, level, num
                                        )
                                        if len(temp) == 1:
                                            if temp[0].name:
                                                p = self.process_nested_tags(
                                                    temp, p, finding
                                                )
                                            else:
                                                p = self.replace_and_write(
                                                    temp[0], p, finding
                                                )
                                        # Bigger lists mean more tags, so process nested tags
                                        else:
                                            p = self.process_nested_tags(
                                                temp, p, finding
                                            )
                                    # Recursively process this list and any other nested lists inside of it
                                    if nested_list:
                                        # Increment the list level counter for this nested list
                                        level += 1
                                        p = self.parse_nested_html_lists(
                                            nested_list, p, num, finding, level
                                        )
                                # No nested list, proceed as normal
                                else:
                                    p = self.create_list_paragraph(prev_p, level, num)
                                    p = self.process_nested_tags(
                                        part.contents, p, finding
                                    )
                            # Track the paragraph used for this list item to link subsequent paragraphs
                            prev_p = p
                        else:
                            if not isinstance(part, NavigableString):
                                logger.warning(
                                    "Encountered an unknown tag inside of an ordered list: %s",
                                    part.name,
                                )
                else:
                    if not isinstance(tag, NavigableString):
                        logger.warning(
                            "Encountered an unknown tag inside of the finding HTML: %s",
                            tag_name,
                        )

    def generate_word_docx(self):
        """
        Generate a complete Word document for the current report.
        """
        # Generate the JSON for the report
        self.report_json = json.loads(self.generate_json())
        # Create Word document writer using the specified template file
        try:
            self.word_doc = DocxTemplate(self.template_loc)
        except DocxPackageNotFoundError:
            logger.exception(
                "Failed to load the provided template document because file could not be found: %s",
                self.template_loc,
            )
            raise DocxPackageNotFoundError
        except Exception:
            logger.exception(
                "Failed to load the provided template document: %s", self.template_loc
            )

        # Check for styles
        styles = self.word_doc.styles
        if "CodeBlock" not in styles:
            codeblock_style = styles.add_style("CodeBlock", WD_STYLE_TYPE.PARAGRAPH)
            codeblock_style.base_style = styles["Normal"]
            codeblock_style.hidden = False
            codeblock_style.quick_style = True
            codeblock_style.priority = 2
            # Set font and size
            codeblock_font = codeblock_style.font
            codeblock_font.name = "Courier New"
            codeblock_font.size = Pt(11)
            # Set alignment
            codeblock_par = codeblock_style.paragraph_format
            codeblock_par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            codeblock_par.line_spacing = 1
            codeblock_par.left_indent = Inches(0.2)
            codeblock_par.right_indent = Inches(0.2)

        if "CodeInline" not in styles:
            codeinline_style = styles.add_style("CodeInline", WD_STYLE_TYPE.PARAGRAPH)
            codeinline_style.hidden = False
            codeinline_style.quick_style = True
            codeinline_style.priority = 3
            # Set font and size
            codeblock_font = codeinline_style.font
            codeblock_font.name = "Courier New"
            codeblock_font.size = Pt(11)

        # Prepare the ``context`` dict for the Word template rendering
        context = {}
        context["report_date"] = datetime.now().strftime("%B %d, %Y")
        context["report_date_uk"] = datetime.now().strftime("%d %B %Y")

        # Client information
        context["client"] = self.report_json["client"]["full_name"]
        context["client_short"] = self.report_json["client"]["short_name"]
        context["client_pocs"] = self.report_json["client"]["poc"].values()

        # Assessment information
        context["assessment_name"] = self.report_json["project"]["name"]
        context["assessment_type"] = self.report_json["project"]["project_type"]
        context["project_type"] = context["assessment_type"]
        context["company"] = self.company_config.company_name
        context["company_pocs"] = self.report_json["team"].values()

        # Project dates
        context["project_start_date"] = self.report_json["project"]["start_date"]
        context["project_start_date_uk"] = self.report_json["project"]["start_date_uk"]
        context["project_end_date"] = self.report_json["project"]["end_date"]
        context["project_end_date_uk"] = self.report_json["project"]["end_date_uk"]

        context["execution_window"] = self.report_json["project"]["execution_window"]
        context["execution_window_uk"] = self.report_json["project"][
            "execution_window_uk"
        ]

        # Infrastructure information
        context["domains"] = self.report_json["infrastructure"]["domains"].values()
        context["static_servers"] = self.report_json["infrastructure"]["servers"][
            "static"
        ].values()
        context["cloud_servers"] = self.report_json["infrastructure"]["servers"][
            "cloud"
        ].values()
        context["domains_and_servers"] = self.report_json["infrastructure"][
            "domains_and_servers"
        ].values()

        # Findings information
        context["findings"] = self.report_json["findings"].values()
        context["total_findings"] = len(self.report_json["findings"].values())

        # Generate the XML for the styled findings
        context = self.process_findings(context)

        # Render the Word document + auto-escape any unsafe XML/HTML
        self.word_doc.render(context, self.jinja_env, autoescape=True)

        # Return the final rendered document
        return self.word_doc

    def process_findings(self, context: dict) -> dict:
        """
        Update the document context with ``RichText`` and ``Subdocument`` objects for
        each finding. This

        **Parameters**

        ``context``
            Pre-defined template context
        """

        def render_subdocument(section, finding):
            self.sacrificial_doc = self.word_doc.new_subdoc()
            self.process_text_xml(section, finding)
            return self.sacrificial_doc

        for finding in context["findings"]:
            logger.info("Processing %s", finding["title"])
            # Create ``RichText()`` object for a colored severity category
            finding["severity_rt"] = RichText(
                finding["severity"], color=finding["severity_color"]
            )
            # Create subdocuments for each finding section
            finding["affected_entities_rt"] = render_subdocument(
                finding["affected_entities"], finding
            )
            finding["description_rt"] = render_subdocument(
                finding["description"], finding
            )
            finding["impact_rt"] = render_subdocument(finding["impact"], finding)
            finding["recommendation_rt"] = render_subdocument(
                finding["recommendation"], finding
            )
            finding["replication_steps_rt"] = render_subdocument(
                finding["replication_steps"], finding
            )
            finding["host_detection_techniques_rt"] = render_subdocument(
                finding["host_detection_techniques"], finding
            )
            finding["network_detection_techniques_rt"] = render_subdocument(
                finding["network_detection_techniques"], finding
            )
            finding["references_rt"] = render_subdocument(
                finding["references"], finding
            )

        return context

    def process_text_xlsx(self, html, text_format, finding):
        """
        Process the provided text from the specified finding to parse keywords for
        evidence placement and formatting in xlsx documents.

        **Parameters**

        ``html``
            HTML content to parse with BeautifulSoup 4
        ``text_format``
            Format to apply to the Excel worksheet cell – defined in ``generate_excel_xlsx()``
        ``finding``
            Current report finding being processed
        """
        # Regex for searching for bracketed template placeholders, e.g. {{.client}}
        keyword_regex = r"\{\{\.(.*?)\}\}"
        # Strip out all HTML tags
        # This _could_ impact HTML strings a user has included as part of a finding but we can revisit this later
        text = BeautifulSoup(html, "lxml").text
        # Perform the necessary replacements
        if "{{.client}}" in text:
            if self.report_json["client"]["short_name"]:
                text = text.replace(
                    "{{.client}}", self.report_json["client"]["short_name"]
                )
            else:
                text = text.replace(
                    "{{.client}}", self.report_json["client"]["full_name"]
                )
        if "{{.project_start}}" in text:
            text = text.replace(
                "{{.project_start}}", self.report_json["project"]["start_date"]
            )
        if "{{.project_end}}" in text:
            text = text.replace(
                "{{.project_end}}", self.report_json["project"]["end_date"]
            )
        if "{{.project_start_uk}}" in text:
            text = text.replace(
                "{{.project_start_uk}}", self.report_json["project"]["start_date_uk"]
            )
        if "{{.project_end_uk}}" in text:
            text = text.replace(
                "{{.project_end_uk}}", self.report_json["project"]["end_date_uk"]
            )
        if "{{.project_type}}" in text:
            text = text.replace(
                "{{.project_type}}", self.report_json["project"]["project_type"].lower()
            )
        text = text.replace("{{.caption}}", "Caption \u2013 ")
        # Find/replace evidence keywords because they're ugly and don't make sense when read
        match = re.findall(keyword_regex, text)
        if match:
            for keyword in match:
                if keyword in finding["evidence"].keys():
                    # \u2013 is an em-dash
                    text = text.replace(
                        "{{." + keyword + "}}",
                        "\n<See Report for Evidence File: {}>\nCaption \u2013 {}".format(
                            finding["evidence"][keyword]["friendly_name"],
                            finding["evidence"][keyword]["caption"],
                        ),
                    )
                else:
                    # Some unrecognized strring inside braces so ignore it
                    pass
        self.worksheet.write(self.row, self.col, text, text_format)

    def generate_excel_xlsx(self, memory_object):
        """
        Generate a complete Excel spreadsheet for the current report.
        """
        from ghostwriter.reporting.models import Evidence

        # Generate the JSON for the report
        self.report_json = json.loads(self.generate_json())

        # Create xlsxwriter
        word_doc = memory_object
        self.worksheet = word_doc.add_worksheet("Findings")

        # Create some basic formats
        # Header format
        bold_format = word_doc.add_format({"bold": True})
        bold_format.set_text_wrap()
        bold_format.set_align("vcenter")
        # Affected assets format
        asset_format = word_doc.add_format()
        asset_format.set_text_wrap()
        asset_format.set_align("vcenter")
        asset_format.set_align("center")
        # Remaining cells
        wrap_format = word_doc.add_format()
        wrap_format.set_text_wrap()
        wrap_format.set_align("vcenter")
        # Create header row for findings
        self.col = 0
        headers = [
            "Finding",
            "Severity",
            "Affected Entities",
            "Description",
            "Impact",
            "Recommendation",
            "Replication Steps",
            "Host Detection Techniques",
            "Network Detection Techniques",
            "References",
            "Supporting Evidence",
        ]
        for header in headers:
            self.worksheet.write(0, self.col, header, bold_format)
            self.col += 1
        # Width of all columns set to 30
        self.worksheet.set_column(0, 10, 30)
        # Width of severity columns set to 10
        self.worksheet.set_column(1, 1, 10)
        # Loop through the dict of findings to create findings worksheet
        self.col = 0
        self.row = 1
        for finding in self.report_json["findings"].values():
            # Finding Name
            self.worksheet.write(self.row, self.col, finding["title"], wrap_format)
            self.col += 1
            # Severity
            severity_format = word_doc.add_format({"bold": True})
            severity_format.set_align("vcenter")
            severity_format.set_align("center")
            severity_format.set_font_color("black")
            # Color the cell based on corresponding severity color
            severity_format.set_bg_color(finding["severity_color"])
            self.worksheet.write(self.row, 1, finding["severity"], severity_format)
            self.col += 1

            # Affected Asset
            if finding["affected_entities"]:
                self.process_text_xlsx(
                    finding["affected_entities"], asset_format, finding
                )
            else:
                self.worksheet.write(self.row, self.col, "N/A", asset_format, finding)
            self.col += 1

            # Description
            self.process_text_xlsx(finding["description"], wrap_format, finding)
            self.col += 1

            # Impact
            self.process_text_xlsx(finding["impact"], wrap_format, finding)
            self.col += 1

            # Recommendation
            self.process_text_xlsx(finding["recommendation"], wrap_format, finding)
            self.col += 1

            # Replication
            self.process_text_xlsx(finding["replication_steps"], wrap_format, finding)
            self.col += 1

            # Detection
            self.process_text_xlsx(
                finding["host_detection_techniques"], wrap_format, finding
            )
            self.col += 1
            self.process_text_xlsx(
                finding["network_detection_techniques"], wrap_format, finding
            )
            self.col += 1

            # References
            self.process_text_xlsx(finding["references"], wrap_format, finding)
            self.col += 1

            # Collect the evidence, if any, from the finding's folder and insert inline with description
            try:
                evidence_queryset = Evidence.objects.filter(finding=finding["id"])
            except Exception:
                evidence_queryset = []
            # Loop through any evidence and add it to the evidence column
            evidence = [
                f.document.name
                for f in evidence_queryset
                if f in self.image_extensions or self.text_extensions
            ]
            finding_evidence_names = "\r\n".join(map(str, evidence))

            # Evidence List
            self.worksheet.write(
                self.row, self.col, finding_evidence_names, wrap_format
            )
            # Increment row counter and reset columns before moving on to next finding
            self.row += 1
            self.col = 0

        # Add a filter to the worksheet
        self.worksheet.autofilter(
            "A1:J{}".format(len(self.report_json["findings"]) + 1)
        )

        # Finalize document
        word_doc.close()
        return word_doc

    def generate_powerpoint_pptx(self):
        """
        Generate a complete PowerPoint slide deck for the current report.
        """
        self.report_type = "pptx"
        self.report_json = json.loads(self.generate_json())
        # Create document writer using the specified template
        try:
            self.ppt_presentation = Presentation(self.template_loc)
        except ValueError:
            logger.exception(
                "Failed to load the provided template document because it is not a PowerPoint file: %s",
                self.template_loc,
            )
            raise ValueError
        except PptxPackageNotFoundError:
            logger.exception(
                "Failed to load the provided template document because file could not be found: %s",
                self.template_loc,
            )
            raise PptxPackageNotFoundError
        except Exception:
            logger.exception(
                "Failed to load the provided template document for unknown reason: %s",
                self.template_loc,
            )

        # Loop through the dict of findings to create slides based on findings
        # Initialize findings stats dict
        findings_stats = {
            "Critical": 0,
            "High": 0,
            "Medium": 0,
            "Low": 0,
            "Informational": 0,
        }

        def get_textframe(shape):
            text_frame = shape.text_frame
            # Fits content to text frame, but only triggers on update after opening file
            text_frame.auto_size = MSO_AUTO_SIZE.TEXT_TO_FIT_SHAPE

            return text_frame

        # Calculate finding stats
        for finding in self.report_json["findings"].values():
            findings_stats[finding["severity"]] += 1
        # Slide styles (From Master Style counting top to bottom from 0..n)
        SLD_LAYOUT_TITLE = 0
        SLD_LAYOUT_TITLE_AND_CONTENT = 1
        SLD_LAYOUT_FINAL = 12

        # Add a title slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = self.company_config.company_name
        text_frame = get_textframe(body_shape)
        # Use ``text_frame.text`` for first line/paragraph or ``text_frame.paragraphs[0]``
        text_frame.text = "{} Debrief".format(
            self.report_json["project"]["project_type"]
        )
        p = text_frame.add_paragraph()
        p.text = self.report_json["client"]["full_name"]

        # Add Agenda slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = "Agenda"
        body_shape = shapes.placeholders[1]
        text_frame = get_textframe(body_shape)

        # Add Introduction slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = "Introduction"
        body_shape = shapes.placeholders[1]
        text_frame = get_textframe(body_shape)

        # Add Methodology slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = "Methodology"
        body_shape = shapes.placeholders[1]
        text_frame = get_textframe(body_shape)

        # Add Attack Path Overview slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = "Attack Path Overview"
        body_shape = shapes.placeholders[1]
        text_frame = get_textframe(body_shape)

        # Add Findings Overview Slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = "Findings Overview"
        text_frame = get_textframe(body_shape)
        for stat in findings_stats:
            p = text_frame.add_paragraph()
            p.text = "{} Findings".format(stat)
            p.level = 0
            p = text_frame.add_paragraph()
            p.text = str(findings_stats[stat])
            p.level = 1

        # Add Findings Overview Slide 2
        # If there are findings then write a table of findings and severity ratings
        if len(self.report_json["findings"]) > 0:
            # Delete the default text placeholder
            textbox = shapes[1]
            sp = textbox.element
            sp.getparent().remove(sp)
            # Add a table
            rows = len(self.report_json["findings"]) + 1
            columns = 2
            left = Inches(1.5)
            top = Inches(2)
            width = Inches(8)
            height = Inches(0.8)
            table = shapes.add_table(rows, columns, left, top, width, height).table
            # Set column width
            table.columns[0].width = Inches(8.5)
            table.columns[1].width = Inches(2.0)
            # Write table headers
            cell = table.cell(0, 0)
            cell.text = "Finding"
            cell.fill.solid()
            cell.fill.fore_color.rgb = pptx.dml.color.RGBColor(0x2D, 0x28, 0x69)
            cell = table.cell(0, 1)
            cell.text = "Severity"
            cell.fill.solid()
            cell.fill.fore_color.rgb = pptx.dml.color.RGBColor(0x2D, 0x28, 0x69)
            # Write findings rows
            row_iter = 1
            for finding in self.report_json["findings"].values():
                table.cell(row_iter, 0).text = finding["title"]
                risk_cell = table.cell(row_iter, 1)
                # Set risk rating
                risk_cell.text = finding["severity"]
                # Set cell color fill type to solid
                risk_cell.fill.solid()
                # Color the risk cell based on corresponding severity color
                cell_color = pptx.dml.color.RGBColor(
                    *map(lambda v: int(v, 16), finding["severity_color_hex"])
                )
                risk_cell.fill.fore_color.rgb = cell_color
                row_iter += 1
            # Set all cells alignment to center and vertical center
            for cell in table.iter_cells():
                cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        else:
            p = text_frame.add_paragraph()
            p.text = "No findings"
            p.level = 0

        # Create slide for each finding
        for finding in self.report_json["findings"].values():
            slide_layout = self.ppt_presentation.slide_layouts[
                SLD_LAYOUT_TITLE_AND_CONTENT
            ]
            self.finding_slide = self.ppt_presentation.slides.add_slide(slide_layout)
            shapes = self.finding_slide.shapes
            title_shape = shapes.title

            # Prepare text frame
            self.finding_body_shape = shapes.placeholders[1]
            if self.finding_body_shape.has_text_frame:
                text_frame = get_textframe(self.finding_body_shape)
                text_frame.clear()
                self.delete_paragraph(text_frame.paragraphs[0])

            title_shape.text = "{} [{}]".format(finding["title"], finding["severity"])
            if finding["description"]:
                self.process_text_xml(finding["description"], finding)
            else:
                self.process_text_xml("<p>No description provided</p>", finding)

            # Strip all HTML tags and replace any \x0D characters for pptx
            entities = BeautifulSoup(finding["affected_entities"], "lxml").text.replace(
                "\x0D", ""
            )
            impact = BeautifulSoup(finding["impact"], "lxml").text.replace("\x0D", "")
            recommendation = BeautifulSoup(
                finding["recommendation"], "lxml"
            ).text.replace("\x0D", "")
            replication = BeautifulSoup(
                finding["replication_steps"], "lxml"
            ).text.replace("\x0D", "")
            references = BeautifulSoup(finding["references"], "lxml").text.replace(
                "\x0D", ""
            )
            notes_slide = self.finding_slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            p = text_frame.add_paragraph()
            p.text = "{}: {}\n\nAFFECTED ENTITIES\n\n{}\n\nIMPACT\n\n{}\n\nMITIGATION\n\n{}\n\nREPLICATION\n\n{}\n\nREFERENCES\n\n{}".format(
                finding["severity"].capitalize(),
                finding["title"],
                entities,
                impact,
                recommendation,
                replication,
                references,
            )

        # Add Observations slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = "Positive Observations"
        text_frame = get_textframe(body_shape)

        # Add Recommendations slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = "Recommendations"
        text_frame = get_textframe(body_shape)

        # Add Conclusion slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = "Positive Observations"
        text_frame = get_textframe(body_shape)

        # Add final slide
        slide_layout = self.ppt_presentation.slide_layouts[SLD_LAYOUT_FINAL]
        slide = self.ppt_presentation.slides.add_slide(slide_layout)
        shapes = slide.shapes
        body_shape = shapes.placeholders[1]
        text_frame = get_textframe(body_shape)
        text_frame.clear()
        p = text_frame.paragraphs[0]
        p.line_spacing = 0.7
        p.text = self.company_config.company_name
        p = text_frame.add_paragraph()
        p.text = self.company_config.company_twitter
        p.line_spacing = 0.7
        p = text_frame.add_paragraph()
        p.text = self.company_config.company_email
        p.line_spacing = 0.7

        # Finalize document and return it for an HTTP response
        return self.ppt_presentation

    def generate_all_reports(self, docx_template, pptx_template):
        """
        Generate all availabe report types and return memory streams for each file.
        """
        # Generate the JSON report - it just needs to be a string object
        self.report_json = json.loads(self.generate_json())
        # Generate the docx report - save it in a memory stream
        try:
            self.template_loc = docx_template
            word_doc = self.generate_word_docx()
            word_stream = io.BytesIO()
            word_doc.save(word_stream)
        except Exception:
            raise
        # Generate the xlsx report - save it in a memory stream
        try:
            excel_stream = io.BytesIO()
            workbook = Workbook(excel_stream, {"in_memory": True})
            self.generate_excel_xlsx(workbook)
        except Exception:
            raise
        # Generate the pptx report - save it in a memory stream
        try:
            self.template_loc = pptx_template
            ppt_doc = self.generate_powerpoint_pptx()
            ppt_stream = io.BytesIO()
            ppt_doc.save(ppt_stream)
        except Exception:
            raise
        # Return each memory object
        return self.report_json, word_stream, excel_stream, ppt_stream


class TemplateLinter:
    """Lint template files to catch undefined variables and syntax errors."""

    def __init__(self, template_loc):
        self.template_loc = template_loc
        self.jinja_template_env = jinja2.Environment(
            undefined=jinja2.DebugUndefined, extensions=["jinja2.ext.debug"]
        )
        self.jinja_template_env.filters["filter_severity"] = self.dummy_filter_severity
        self.jinja_template_env.filters["strip_html"] = self.dummy_strip_html

    def dummy_filter_severity(self, value, allowlist):
        return []

    def dummy_strip_html(self, value):
        return []

    def lint_docx(self):
        """
        Lint the provided Word docx file from :model:`reporting.ReportTemplate`.
        """
        results = {"result": "success", "warnings": [], "errors": []}
        if self.template_loc:
            if os.path.exists(self.template_loc):
                logger.info("Found template file at %s", self.template_loc)
                try:
                    # Dummy context data to identify undefined custom variables in template
                    context = {}

                    context["report_date"] = datetime.now().strftime("%B %d, %Y")
                    context["report_date_uk"] = datetime.now().strftime("%d %B %Y")

                    # Client information
                    context["client"] = "Kabletown"
                    context["client_short"] = "Kabletown"
                    context["client_pocs"] = ""

                    # Assessment information
                    context["assessment_name"] = ""
                    context["assessment_type"] = ""
                    context["project_type"] = ""
                    context["company"] = ""
                    context["company_pocs"] = ""

                    # Project dates
                    context["project_start_date"] = ""
                    context["project_start_date_uk"] = ""
                    context["project_end_date"] = ""
                    context["project_end_date_uk"] = ""

                    context["execution_window"] = ""
                    context["execution_window_uk"] = ""

                    # Infrastructure information
                    context["domains"] = ""
                    context["static_servers"] = ""
                    context["cloud_servers"] = ""
                    context["domains_and_servers"] = ""

                    # Findings information
                    context["findings"] = ""
                    context["findings_subdoc"] = ""

                    # Step 1: Load the document as a template
                    template_document = DocxTemplate(self.template_loc)
                    logger.info("Template loaded for linting")

                    # Step 2: Check document's styles
                    document_styles = template_document.styles
                    if "Bullet List" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Bullet List"
                        )
                    if "Number List" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): Number List"
                        )
                    if "CodeBlock" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): CodeBlock"
                        )
                    if "CodeInline" not in document_styles:
                        results["warnings"].append(
                            "Template is missing a recommended style (see documentation): CodeInline"
                        )
                    logger.info("Completed Word style checks")

                    # Step 3: Test rendering the document
                    try:
                        template_document.render(
                            context, self.jinja_template_env, autoescape=True
                        )
                        undefined_vars = template_document.undeclared_template_variables
                        if undefined_vars:
                            for variable in undefined_vars:
                                results["warnings"].append(
                                    f"Undefined variable: {variable}"
                                )
                        if results["warnings"]:
                            results["result"] = "warning"
                        logger.info("Completed document rendering test")
                    except TemplateSyntaxError as error:
                        logger.error("Template syntax error: %s", error)
                        results = {
                            "result": "failed",
                            "errors": [
                                f"Jinja2 template syntax error: {error.message}"
                            ],
                        }
                except Exception:
                    logger.exception("Template failed rendering")
                    results = {
                        "result": "failed",
                        "errors": ["Template rendering failed unexpectedly"],
                    }
            else:
                logger.error("Template file path did not exist: %s", self.template_loc)
                results = {
                    "result": "failed",
                    "errors": ["Template file does not exist – upload it again"],
                }
        else:
            logger.error("Received a `None` value for template location")

        logger.info("Template linting completed")
        return json.dumps(results)

    def lint_pptx(self):
        """
        Lint the provided PowerPoint pptx file from :model:`reporting.ReportTemplate`.
        """
        results = {"result": "success", "warnings": [], "errors": []}
        if self.template_loc:
            if os.path.exists(self.template_loc):
                logger.info("Found template file at %s", self.template_loc)
                try:
                    # Test 1: Check if the document is a PPTX file
                    template_document = Presentation(self.template_loc)

                    # Test 2: Check for existing slides
                    slide_count = len(template_document.slides)
                    logger.warning("Slide count was %s", slide_count)
                    if slide_count > 0:
                        results["warnings"].append(
                            "Template can be used, but it has slides when it should be empty (see documentation)"
                        )
                except ValueError:
                    logger.exception(
                        "Failed to load the provided template document because it is not a PowerPoint file: %s",
                        self.template_loc,
                    )
                    results = {
                        "result": "failed",
                        "errors": ["Template file is not a PowerPoint presentation"],
                    }
                except Exception:
                    logger.exception("Template failed rendering")
                    results = {
                        "result": "failed",
                        "errors": ["Template rendering failed unexpectedly"],
                    }
            else:
                logger.error("Template file path did not exist: %s", self.template_loc)
                results = {
                    "result": "failed",
                    "errors": ["Template file does not exist – upload it again"],
                }
        else:
            logger.error("Received a `None` value for template location")

        logger.info("Template linting completed")
        return json.dumps(results)
