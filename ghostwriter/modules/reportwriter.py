#!/usr/bin/python3
# -*- coding: utf-8 -*-

"""This module contains the tools required for generating Microsoft Office
documents for reporting. The Reportwriter class accepts data and produces a
docx, xlsx, pptx, and json using the provided data.
"""

import re
import io
import os
import json

from PIL import Image
from PIL import ImageOps

from xlsxwriter.workbook import Workbook

from docx import Document
from docx.oxml import parse_xml
from docx.oxml.shared import OxmlElement, qn
from docx.oxml.ns import nsdecls
from docx.shared import RGBColor, Inches, Pt
from docx.enum.style import WD_STYLE_TYPE
from docx.enum.text import WD_ALIGN_PARAGRAPH

import pptx
from pptx import Presentation
from pptx.enum.text import PP_ALIGN
from pptx.enum.text import MSO_ANCHOR

from django.conf import settings
from django.core.serializers.json import DjangoJSONEncoder


class Reportwriter():
    """Class for generating documents for the provided findings."""
    # Color codes used for finding severity
    # Blue
    informational_color = '8eaadb'
    informational_color_hex = [0x83, 0xaa, 0xdb]
    # Green
    low_color = 'a8d08d'
    low_color_hex = [0xa8, 0xd0, 0x8d]
    # Orange
    medium_color = 'f4b083'
    medium_color_hex = [0xf4, 0xb0, 0x83]
    # Red
    high_color = 'ff7e79'
    high_color_hex = [0xff, 0x7e, 0x79]
    # Purple
    critical_color = '7030a0'
    critical_color_hex = [0x70, 0x30, 0xa0]
    # Picture border color - this one needs the # in front
    border_color = '#2d2b6b'
    border_color_hex = [0x45, 0x43, 0x107]
    # Extensions allowed for evidence
    image_extensions = ['png', 'jpeg', 'jpg']
    text_extensions = ['txt', 'ps1', 'py', 'md', 'log']

    def __init__(self, report_queryset, output_path, evidence_path,
                 template_loc=None):
        """Everything that must be initialized is setup here."""
        self.output_path = output_path
        self.template_loc = template_loc
        self.evidence_path = evidence_path
        self.report_queryset = report_queryset

    def generate_json(self):
        """Export report as a JSON dictionary."""
        project_name = str(self.report_queryset.project)
        # Client data
        report_dict = {}
        report_dict['client'] = {}
        report_dict['client']['id'] = self.report_queryset.project.client.id
        report_dict['client']['full_name'] = \
            self.report_queryset.project.client.name
        report_dict['client']['short_name'] = \
            self.report_queryset.project.client.short_name
        report_dict['client']['codename'] = \
            self.report_queryset.project.client.codename
        # Client points of contact data
        report_dict['client']['poc'] = {}
        for poc in self.report_queryset.project.client.clientcontact_set.all():
            report_dict['client']['poc'][poc.id] = {}
            report_dict['client']['poc'][poc.id]['id'] = poc.id
            report_dict['client']['poc'][poc.id]['name'] = poc.name
            report_dict['client']['poc'][poc.id]['job_title'] = poc.job_title
            report_dict['client']['poc'][poc.id]['email'] = poc.email
            report_dict['client']['poc'][poc.id]['phone'] = poc.phone
            report_dict['client']['poc'][poc.id]['note'] = poc.note
        # Project data
        report_dict['project'] = {}
        report_dict['project']['id'] = self.report_queryset.project.id
        report_dict['project']['name'] = project_name
        report_dict['project']['start_date'] = \
            self.report_queryset.project.start_date
        report_dict['project']['end_date'] = \
            self.report_queryset.project.end_date
        report_dict['project']['codename'] = \
            self.report_queryset.project.codename
        report_dict['project']['project_type'] = \
            self.report_queryset.project.project_type.project_type
        report_dict['project']['note'] = self.report_queryset.project.note
        # Finding data
        report_dict['findings'] = {}
        for finding in self.report_queryset.reportfindinglink_set.all():
            report_dict['findings'][finding.title] = {}
            report_dict['findings'][finding.title]['id'] = finding.id
            report_dict['findings'][finding.title]['title'] = finding.title
            report_dict['findings'][finding.title]['severity'] = \
                finding.severity.severity
            report_dict['findings'][finding.title]['affected_entities'] = \
                finding.affected_entities
            report_dict['findings'][finding.title]['description'] = \
                finding.description
            report_dict['findings'][finding.title]['impact'] = finding.impact
            report_dict['findings'][finding.title]['recommendation'] = \
                finding.mitigation
            report_dict['findings'][finding.title]['replication_steps'] = \
                finding.replication_steps
            report_dict['findings'][finding.title][
                'host_detection_techniques'] = \
                finding.host_detection_techniques
            report_dict['findings'][finding.title][
                'network_detection_techniques'] = \
                finding.network_detection_techniques
            report_dict['findings'][finding.title]['references'] = \
                finding.references
            # Get any evidence
            report_dict['findings'][finding.title]['evidence'] = {}
            for evidence_file in finding.evidence_set.all():
                evidence_name = evidence_file.friendly_name
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name] = {}
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['id'] = evidence_file.id
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['friendly_name'] = \
                    evidence_file.friendly_name
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['uploaded_by'] = \
                    evidence_file.uploaded_by.username
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['upload_date'] = \
                    evidence_file.upload_date
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['description'] = \
                    evidence_file.description
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['caption'] = \
                    evidence_file.caption
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['url'] = \
                    evidence_file.document.url
                report_dict['findings'][finding.title][
                    'evidence'][evidence_name]['file_path'] = \
                    str(evidence_file.document)
        # Infrastructure data
        report_dict['infrastructure'] = {}
        report_dict['infrastructure']['domains'] = {}
        report_dict['infrastructure']['servers'] = {}
        report_dict['infrastructure']['servers']['static'] = {}
        report_dict['infrastructure']['servers']['cloud'] = {}
        report_dict['infrastructure']['domains_and_servers'] = {}
        for domain in self.report_queryset.project.history_set.all():
            report_dict['infrastructure']['domains'][domain.domain.id] = {}
            report_dict['infrastructure']['domains'][domain.domain.id][
                'id'] = domain.domain.id
            report_dict['infrastructure']['domains'][domain.domain.id][
                'name'] = domain.domain.name
            report_dict['infrastructure']['domains'][domain.domain.id][
                'activity'] = domain.activity_type.activity
            report_dict['infrastructure']['domains'][domain.domain.id][
                'operator'] = domain.operator.username
            report_dict['infrastructure']['domains'][domain.domain.id][
                'start_date'] = domain.start_date
            report_dict['infrastructure']['domains'][domain.domain.id][
                'end_date'] = domain.end_date
            report_dict['infrastructure']['domains'][domain.domain.id][
                'note'] = domain.note
        for server in self.report_queryset.project.serverhistory_set.all():
            report_dict['infrastructure']['servers']['static'][
                server.server.id] = {}
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['id'] = server.server.id
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['ip_address'] = server.server.ip_address
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['activity'] = server.activity_type.activity
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['role'] = server.server_role.server_role
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['operator'] = server.operator.username
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['start_date'] = server.start_date
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['end_date'] = server.end_date
            report_dict['infrastructure']['servers']['static'][
                server.server.id]['note'] = server.note
        for server in self.report_queryset.project.transientserver_set.all():
            report_dict['infrastructure']['servers']['cloud'][server.id] = {}
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'id'] = server.id
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'ip_address'] = server.ip_address
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'activity'] = server.activity_type.activity
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'role'] = server.server_role.server_role
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'operator'] = server.operator.username
            report_dict['infrastructure']['servers']['cloud'][server.id][
                'note'] = server.note
        # Hold all domain/server associations in a temporary dictionary
        temp = {}
        for connection in self.report_queryset.project.domainserverconnection_set.all():
            # Handle one-to-many relationships by combining everything into
            # a domain and list of servers
            if connection.subdomain is not "*":
                domain_name = connection.subdomain + "." + connection.domain.domain.name
            else:
                domain_name = connection.domain.domain.name
            report_dict['infrastructure']['domains_and_servers'][connection.id] = {}
            report_dict['infrastructure']['domains_and_servers'][
                connection.id]['domain'] = domain_name
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
            report_dict['infrastructure']['domains_and_servers'][
                connection.id]['servers'] = server
            if connection.endpoint:
                report_dict['infrastructure']['domains_and_servers'][
                    connection.id]['cdn_endpoint'] = connection.endpoint
            else:
                report_dict['infrastructure']['domains_and_servers'][
                    connection.id]['cdn_endpoint'] = "None"
        # Operator assignments
        report_dict['team'] = {}
        for operator in self.report_queryset.project.projectassignment_set.all():
            report_dict['team'][operator.operator.id] = {}
            report_dict['team'][operator.operator.id][
                'id'] = operator.operator.id
            report_dict['team'][operator.operator.id][
                'name'] = operator.operator.name
            report_dict['team'][operator.operator.id][
                'project_role'] = operator.role.project_role
            report_dict['team'][operator.operator.id][
                'email'] = operator.operator.email
            report_dict['team'][operator.operator.id][
                'start_date'] = operator.start_date
            report_dict['team'][operator.operator.id][
                'end_date'] = operator.end_date
            report_dict['team'][operator.operator.id][
                'note'] = operator.note
        return json.dumps(report_dict, indent=2, cls=DjangoJSONEncoder)

    def create_newline(self):
        """Create a blank line to act as a separator between document elements.
        A paragraph must be added and then a run in order to use an
        `add_break()`. This creates the appropriate <w:r> in the docx
        document's XML.
        """
        p = self.spenny_doc.add_paragraph()
        run = p.add_run()
        run.add_break()

    def make_figure(self, paragraph):
        """Make the specified paragraph an auto-incrementing Figure in the
        Word document.

        Code from: https://github.com/python-openxml/python-docx/issues/359
        """
        run = run = paragraph.add_run()
        r = run._r
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'begin')
        r.append(fldChar)
        instrText = OxmlElement('w:instrText')
        instrText.text = ' SEQ Figure \\* ARABIC'
        r.append(instrText)
        fldChar = OxmlElement('w:fldChar')
        fldChar.set(qn('w:fldCharType'), 'end')
        r.append(fldChar)

    def list_number(self, par, prev=None, level=None, num=True):
        """Makes the specified paragraph a list item with a specific level and
        optional restart.

        An attempt will be made to retrieve an abstract numbering style that
        corresponds to the style of the paragraph. If that is not possible,
        the default numbering or bullet style will be used based on the
        ``num`` parameter.

        Parameters
        ----------
        par : docx.paragraph.Paragraph
            The paragraph to turn into a list item.
        prev : docx.paragraph.Paragraph or None
            The previous paragraph in the list. If specified, the numbering
            and styles will be taken as a continuation of this paragraph.
            If omitted, a new numbering scheme will be started.
        level : int or None
            The level of the paragraph within the outline. If ``prev`` is
            set, defaults to the same level as in ``prev``. Otherwise,
            defaults to zero.
        num : bool
            If ``prev`` is :py:obj:`None` and the style of the paragraph
            does not correspond to an existing numbering style, this will
            determine wether or not the list will be numbered or bulleted.
            The result is not guaranteed, but is fairly safe for most Word
            templates.

        Code from:
        https://github.com/python-openxml/python-docx/issues/25#issuecomment-400787031
        """
        xpath_options = {
            True: {'single': 'count(w:lvl)=1 and ', 'level': 0},
            False: {'single': '', 'level': level},
        }

        def style_xpath(prefer_single=True):
            """
            The style comes from the outer-scope variable ``par.style.name``.
            """
            style = par.style.style_id
            return (
                'w:abstractNum['
                '{single}w:lvl[@w:ilvl="{level}"]/w:pStyle[@w:val="{style}"]'
                ']/@w:abstractNumId'
            ).format(style=style, **xpath_options[prefer_single])

        def type_xpath(prefer_single=True):
            """
            The type is from the outer-scope variable ``num``.
            """
            type = 'decimal' if num else 'bullet'
            return (
                'w:abstractNum['
                '{single}w:lvl[@w:ilvl="{level}"]/w:numFmt[@w:val="{type}"]'
                ']/@w:abstractNumId'
            ).format(type=type, **xpath_options[prefer_single])

        def get_abstract_id():
            """Select as follows:
                1. Match single-level by style (get min ID)
                2. Match exact style and level (get min ID)
                3. Match single-level decimal/bullet types (get min ID)
                4. Match decimal/bullet in requested level (get min ID)
                3. 0
            """
            for fn in (style_xpath, type_xpath):
                for prefer_single in (True, False):
                    xpath = fn(prefer_single)
                    ids = numbering.xpath(xpath)
                    if ids:
                        return min(int(x) for x in ids)
            return 0

        if (prev is None or
                prev._p.pPr is None or
                prev._p.pPr.numPr is None or
                prev._p.pPr.numPr.numId is None):
            if level is None:
                level = 0
            numbering = self.spenny_doc.part.numbering_part.\
                numbering_definitions._numbering
            # Compute the abstract ID first by style, then by num
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
        par._p.get_or_add_pPr().get_or_add_numPr().\
            get_or_add_numId().val = num
        par._p.get_or_add_pPr().get_or_add_numPr().\
            get_or_add_ilvl().val = level

    def process_text(self, text, finding, report_json):
        """Process the provided text from the specified finding to parse
        keywords for evidence placement and formatting.
        """
        numbered_list = False
        bulleted_list = False
        code_block = False
        inline_code = False
        italic_text = False
        bold_text = False
        p = None
        prev_p = None
        regex = r'\{\{\.(.*?)\}\}'
        for line in text.split('\n'):
            line = line.strip()
            # Perform static replacements
            if '{{.client}}' in line:
                if report_json['client']['short_name']:
                    line = line.replace(
                        '{{.client}}',
                        report_json['client']['short_name'])
                else:
                    line = line.replace(
                        '{{.client}}',
                        report_json['client']['full_name'])
            # Handle keywords that affect whole paragraphs, allowing for spaces
            if (
                line.startswith('{{.code_block') or
                line.startswith('{{ .code_block') or
                line.startswith('{{.end_code_block') or
                line.startswith('{{ .end_code_block') or
                line.startswith('{{.numbered_list') or
                line.startswith('{{ .numbered_list') or
                line.startswith('{{.end_numbered_list') or
                line.startswith('{{ .end_numbered_list') or
                line.startswith('{{.bulleted_list') or
                line.startswith('{{ .bulleted_list') or
                line.startswith('{{.end_bulleted_list') or
                line.startswith('{{ .end_bulleted_list') or
                line.startswith('{{.caption') or
                line.startswith('{{ .caption')
              ):
                # Search for something wrapped in `{{. }}``
                match = re.search(regex, line)
                if match:
                    # Get just the first match, set it as the keyword, and
                    # remove it from the line
                    match = match[0]
                    keyword = match.\
                        replace('{', '').\
                        replace('}', '').\
                        replace('.', '').\
                        strip()
                    line = line.replace(match, '')
                    # Handle code blocks
                    if keyword == 'code_block':
                        code_block = True
                        if line:
                            p = self.spenny_doc.add_paragraph(line)
                            p.style = 'CodeBlock'
                            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                    if keyword == 'end_code_block':
                        if line:
                            p = self.spenny_doc.add_paragraph(line)
                            p.style = 'CodeBlock'
                            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        code_block = False
                        continue
                    # Handle captions - intended to follow code blocks
                    if keyword == 'caption':
                        numbered_list = False
                        bulleted_list = False
                        p = self.spenny_doc.add_paragraph(
                            'Figure ',
                            style='Caption')
                        self.make_figure(p)
                        run = p.add_run(' - ' + line)
                    # Handle lists
                    if keyword == 'numbered_list':
                        if line:
                            p = self.spenny_doc.add_paragraph(
                                line,
                                style='Normal')
                            self.list_number(p, level=0, num=True)
                            p.paragraph_format.left_indent = Inches(0.5)
                        numbered_list = True
                    if keyword == 'end_numbered_list':
                        if line:
                            p = self.spenny_doc.add_paragraph(
                                line,
                                style='Normal')
                            self.list_number(p, level=0, num=True)
                            p.paragraph_format.left_indent = Inches(0.5)
                        numbered_list = False
                        continue
                    if keyword == 'bulleted_list':
                        if line:
                            p = self.spenny_doc.add_paragraph(
                                line,
                                style='Normal')
                            self.list_number(p, level=0, num=False)
                            p.paragraph_format.left_indent = Inches(0.5)
                        bulleted_list = True
                    if keyword == 'end_bulleted_list':
                        if line:
                            p = self.spenny_doc.add_paragraph(
                                line,
                                style='Normal')
                            self.list_number(p, level=0, num=False)
                            p.paragraph_format.left_indent = Inches(0.5)
                        bulleted_list = False
                        continue
            # Continue handling paragraph formatting if active
            elif code_block:
                p = self.spenny_doc.add_paragraph(line)
                p.style = 'CodeBlock'
                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
            elif numbered_list:
                p = self.spenny_doc.add_paragraph(line, style='Normal')
                self.list_number(p, prev=prev_p, level=0, num=True)
                p.paragraph_format.left_indent = Inches(0.5)
            elif bulleted_list:
                p = self.spenny_doc.add_paragraph(line, style='Normal')
                self.list_number(p, level=0, num=False)
                p.paragraph_format.left_indent = Inches(0.5)
            # Handle keywords wrapped around runs of text inside paragraphs
            # and evidence files
            else:
                if '{{.' in line:
                    match = re.search(regex, line)
                    if match:
                        match = match[0]
                        keyword = match.\
                            replace('{{.', '').\
                            replace('}}', '').strip()
                        # line = line.replace(match, '')
                    # Check if the keyword references evidence
                    evidence = False
                    if 'evidence' in finding:
                        if keyword in finding['evidence'].keys():
                            evidence = True
                    if evidence:
                        file_path = settings.MEDIA_ROOT + \
                                   '/' + \
                                   finding['evidence'][keyword]['file_path']
                        extension = finding['evidence'][keyword]['url'].\
                            split('.')[-1]
                        if extension in self.text_extensions:
                            with open(file_path, 'r') as evidence_contents:
                                # Read in evidence text
                                evidence_text = evidence_contents.read()
                                # Drop in text evidence using the
                                # Code Block style
                                p = self.spenny_doc.add_paragraph(
                                    evidence_text)
                                p.style = 'CodeBlock'
                                p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                                p = self.spenny_doc.add_paragraph(
                                    'Figure ',
                                    style='Caption')
                                self.make_figure(p)
                                run = p.add_run(
                                    ' - ' +
                                    finding['evidence'][keyword]['caption'])
                        elif extension in self.image_extensions:
                            # Add a border to the image - this is not ideal
                            img = Image.open(file_path)
                            file_path_parts = os.path.split(file_path)
                            image_directory = file_path_parts[0]
                            image_name = file_path_parts[1]
                            new_file = os.path.join(
                                image_directory,
                                'border_' + image_name)
                            img_with_border = ImageOps.expand(
                                img,
                                border=1,
                                fill=self.border_color)
                            img_with_border = img_with_border.convert('RGB')
                            # Save the new copy to the evidence folder with
                            # a`border_` prefix
                            img_with_border.save(new_file)
                            # Drop in the image at the full 6.5" width and add
                            # the caption
                            p = self.spenny_doc.add_paragraph()
                            run = p.add_run()
                            run.add_picture(new_file, width=Inches(6.5))
                            p = self.spenny_doc.add_paragraph(
                                'Figure ',
                                style='Caption')
                            self.make_figure(p)
                            run = p.add_run(
                                ' - ' +
                                finding['evidence'][keyword]['caption'])
                        # This skips unapproved files
                        else:
                            p = None
                            pass
                    else:
                        # Handle keywords that require managing runs
                        p = self.spenny_doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        all_words = line.split(' ')
                        for word in all_words:
                            prepared_text = word.strip() + ' '
                            # Determine styling
                            if (
                                'inline_code' in word and
                                'end_inline_code' not in word
                              ):
                                inline_code = True
                                continue
                            if 'end_inline_code' in word:
                                inline_code = False
                                continue
                            if 'italic' in word and 'end_italic' not in word:
                                italic_text = True
                                continue
                            if 'end_italic' in word:
                                italic_text = False
                                continue
                            if 'bold' in word and 'end_bold' not in word:
                                bold_text = True
                                continue
                            if 'end_bold' in word:
                                bold_text = False
                                continue
                            # Write the content
                            if inline_code:
                                run = p.add_run(prepared_text)
                                run.style = 'Code (inline)'
                            else:
                                run = p.add_run(prepared_text)
                            if italic_text:
                                font = run.font
                                font.italic = True
                            if bold_text:
                                font = run.font
                                font.bold = True
                else:
                    p = self.spenny_doc.add_paragraph(line, style='Normal')
            # Save the current paragraph for next iteration - needed for lists
            prev_p = p

    def generate_word_docx(self):
        """Generate a Word document for the current report."""
        # Generate the JSON for the report
        report_json = json.loads(self.generate_json())
        # Create Word document writer using the specified template file and
        # a style editor
        if self.template_loc:
            try:
                self.spenny_doc = Document(self.template_loc)
            except Exception:
                # TODO: Return error on webpage
                pass
        else:
            # TODO: Return error on webpage
            pass
        # Create a custom style for table cells named 'Headers'
        # The following makes the header cell text white, bold, and
        # 12pt Calibri
        styles = self.spenny_doc.styles
        styles.add_style('Headers', WD_STYLE_TYPE.CHARACTER)
        cell_text = self.spenny_doc.styles['Headers']
        cell_text_font = cell_text.font
        cell_text_font.name = 'Calibri'
        cell_text_font.size = Pt(12)
        cell_text_font.bold = True
        cell_text_font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)

        ################################################
        # Create the Team and Points of Contact Tables #
        ################################################

        # If the style needs to be updated, update it in template.docx
        poc_table = self.spenny_doc.add_table(
            rows=1,
            cols=3,
            style='Ghostwriter Table')
        name_header = poc_table.cell(0, 0)
        name_header.text = ""
        name_header.paragraphs[0].add_run('Name').bold = True
        name_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        role_header = poc_table.cell(0, 1)
        role_header.text = ''
        role_header.paragraphs[0].add_run('Role').bold = True
        role_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        email_header = poc_table.cell(0, 2)
        email_header.text = ''
        email_header.paragraphs[0].add_run('Email').bold = True
        email_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Re-size table headers
        widths = (Inches(5.4), Inches(1.1))
        for row in poc_table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
        poc_table.allow_autofit = True
        poc_table.autofit = True
        # Loop through the individuals to create rows
        counter = 1
        for contact in report_json['client']['poc'].values():
            poc_table.add_row()
            name_cell = poc_table.cell(counter, 0)
            name_cell.text = "{}".format(contact['name'])
            name_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            role_cell = poc_table.cell(counter, 1)
            role_cell.text = "{}".format(contact['job_title'])
            role_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            email_cell = poc_table.cell(counter, 2)
            email_cell.text = "{}".format(contact['email'])
            email_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1
        self.create_newline()

        # If the style needs to be updated, update it in template.docx
        team_table = self.spenny_doc.add_table(
            rows=1,
            cols=3,
            style='Ghostwriter Table')
        name_header = team_table.cell(0, 0)
        name_header.text = ''
        name_header.paragraphs[0].add_run('Name').bold = True
        name_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        role_header = team_table.cell(0, 1)
        role_header.text = ''
        role_header.paragraphs[0].add_run('Role').bold = True
        role_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        email_header = team_table.cell(0, 2)
        email_header.text = ''
        email_header.paragraphs[0].add_run('Email').bold = True
        email_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Re-size table headers
        widths = (Inches(5.4), Inches(1.1))
        for row in team_table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
        team_table.allow_autofit = True
        team_table.autofit = True
        # Loop through the team members to create rows
        counter = 1
        for operator in report_json['team'].values():
            team_table.add_row()
            name_cell = team_table.cell(counter, 0)
            name_cell.text = '{}'.format(operator['name'])
            name_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            role_cell = team_table.cell(counter, 1)
            role_cell.text = '{}'.format(operator['project_role'])
            role_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            email_cell = team_table.cell(counter, 2)
            email_cell.text = '{}'.format(operator['email'])
            email_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1

        self.spenny_doc.add_page_break()

        ################################################
        # Create the Infrastructure Information Tables #
        ################################################

        # If the style needs to be updated, update it in template.docx
        domain_table = self.spenny_doc.add_table(
            rows=1,
            cols=3,
            style='Ghostwriter Table')
        domain_table.allow_autofit = True
        domain_table.autofit = True
        domain_header = domain_table.cell(0, 0)
        domain_header.text = ''
        domain_header.paragraphs[0].add_run("Domain").bold = True
        domain_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        role_header = domain_table.cell(0, 1)
        role_header.text = ''
        role_header.paragraphs[0].add_run("Purpose").bold = True
        role_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        note_header = domain_table.cell(0, 2)
        note_header.text = ''
        note_header.paragraphs[0].add_run("Note").bold = True
        note_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Loop through the domains to create rows
        counter = 1
        for domain in report_json['infrastructure']['domains'].values():
            domain_table.add_row()
            name_cell = domain_table.cell(counter, 0)
            name_cell.text = '{}'.format(domain['name'])
            name_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            role_cell = domain_table.cell(counter, 1)
            role_cell.text = '{}'.format(domain['activity'])
            role_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            note_cell = domain_table.cell(counter, 2)
            note_cell.text = '{}'.format(domain['note'])
            note_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1
        self.create_newline()

        # If the style needs to be updated, update it in template.docx
        server_table = self.spenny_doc.add_table(
            rows=1,
            cols=3,
            style='Ghostwriter Table')
        server_table.allow_autofit = True
        server_table.autofit = True
        server_header = server_table.cell(0, 0)
        server_header.text = ''
        server_header.paragraphs[0].add_run("IP Address").bold = True
        server_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        activity_header = server_table.cell(0, 1)
        activity_header.text = ''
        activity_header.paragraphs[0].add_run("Purpose").bold = True
        activity_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        role_header = server_table.cell(0, 2)
        role_header.text = ''
        role_header.paragraphs[0].add_run("Role").bold = True
        role_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Loop through the domains to create rows
        counter = 1
        for server in report_json['infrastructure']['servers']['static'].values():
            server_table.add_row()
            name_cell = server_table.cell(counter, 0)
            name_cell.text = "{}".format(server['ip_address'])
            name_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            activity_cell = server_table.cell(counter, 1)
            activity_cell.text = "{}".format(server['activity'])
            activity_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            role_cell = server_table.cell(counter, 2)
            role_cell.text = "{}".format(server['role'])
            role_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1
        for server in report_json['infrastructure']['servers']['cloud'].values():
            server_table.add_row()
            name_cell = server_table.cell(counter, 0)
            name_cell.text = "{}".format(server['ip_address'])
            name_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            activity_cell = server_table.cell(counter, 1)
            activity_cell.text = "{}".format(server['activity'])
            activity_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            role_cell = server_table.cell(counter, 2)
            role_cell.text = "{}".format(server['role'])
            role_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1            
        self.create_newline()

        # If the style needs to be updated, update it in template.docx
        connection_table = self.spenny_doc.add_table(
            rows=1,
            cols=3,
            style='Ghostwriter Table')
        connection_table.allow_autofit = True
        connection_table.autofit = True
        server_header = connection_table.cell(0, 0)
        server_header.text = ""
        server_header.paragraphs[0].add_run("Domain").bold = True
        server_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        domain_header = connection_table.cell(0, 1)
        domain_header.text = ""
        domain_header.paragraphs[0].add_run("Server").bold = True
        domain_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        domain_header = connection_table.cell(0, 2)
        domain_header.text = ""
        domain_header.paragraphs[0].add_run("CDN Endpoint").bold = True
        domain_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Loop through the domains to create rows
        counter = 1
        for connection in report_json[
          'infrastructure']['domains_and_servers'].values():
            connection_table.add_row()
            server_cell = connection_table.cell(counter, 0)
            server_cell.text = "{}".format(connection['domain'])
            server_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            domain_cell = connection_table.cell(counter, 1)
            domain_cell.text = "{}".format(connection['servers'])
            domain_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            domain_cell = connection_table.cell(counter, 2)
            domain_cell.text = "{}".format(connection['cdn_endpoint'])
            domain_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Increase counter for the next row
            counter += 1

        self.spenny_doc.add_page_break()

        #####################################
        # Create the Findings Summary Table #
        #####################################

        # If the style needs to be updated, update it in template.docx
        finding_table = self.spenny_doc.add_table(
            rows=1,
            cols=2,
            style='Ghostwriter Table')
        finding_header = finding_table.cell(0, 0)
        finding_header.text = ""
        finding_header.paragraphs[0].add_run("Finding").bold = True
        finding_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        severity_header = finding_table.cell(0, 1)
        severity_header.text = ""
        severity_header.paragraphs[0].add_run("Severity").bold = True
        severity_header.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
        # Re-size table headers to provide space for finding name
        widths = (Inches(5.4), Inches(1.1))
        for row in finding_table.rows:
            for idx, width in enumerate(widths):
                row.cells[idx].width = width
        finding_table.allow_autofit = True
        finding_table.autofit = True
        # Loop through the findings to create rows
        counter = 1
        for finding in report_json['findings'].values():
            finding_table.add_row()
            finding_cell = finding_table.cell(counter, 0)
            finding_cell.text = "{}".format(finding['title'])
            finding_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            severity_cell = finding_table.cell(counter, 1)
            severity_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = severity_cell.paragraphs[0].add_run(
                '{}'.format(finding['severity']))
            font = run.font
            font.color.rgb = RGBColor(0x00, 0x00, 0x00)
            run.bold = False
            severity_cell.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.CENTER
            # Shading a table cell requires parsing some XML and then editing
            # the cell to be shaded
            if finding['severity'].lower() == 'informational':
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.
                                    format(nsdecls('w'),
                                           self.informational_color))
            elif finding['severity'].lower() == 'low':
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.
                                    format(nsdecls('w'),
                                           self.low_color))
            elif finding['severity'].lower() == 'medium':
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.
                                    format(nsdecls('w'),
                                           self.medium_color))
            elif finding['severity'].lower() == 'high':
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.
                                    format(nsdecls('w'),
                                           self.high_color))
            else:
                shading = parse_xml(r'<w:shd {} w:fill="{}"/>'.
                                    format(nsdecls('w'),
                                           self.critical_color))
            # Modify font to white so it contrasts better against dark cell
            font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
            # Manually append the appropriate shading to the risk rating cell
            finding_table.rows[counter].cells[1]._tc.get_or_add_tcPr().\
                append(shading)
            # Increase counter for the next row
            counter += 1

        ########################################
        # Create the Individual Findings Pages #
        ########################################

        # Add a page break and create each finding's page
        self.spenny_doc.add_page_break()
        for finding in report_json['findings'].values():
            # There's a special Heading 3 for the finding title so we don't
            # use `add_heading()` here
            p = self.spenny_doc.add_paragraph(finding['title'])
            p.style = 'Heading 3 - Finding'
            # This is Heading 4 but we want to make severity a run to color it
            # so we don't use `add_heading()` here
            p = self.spenny_doc.add_paragraph()
            p.style = 'Heading 4'
            run = p.add_run('Severity – ')
            run = p.add_run('{}'.format(finding['severity']))
            font = run.font
            if finding['severity'].lower() == 'informational':
                font.color.rgb = RGBColor(
                    self.informational_color_hex[0],
                    self.informational_color_hex[1],
                    self.informational_color_hex[2])
            elif finding['severity'].lower() == 'low':
                font.color.rgb = RGBColor(
                    self.low_color_hex[0],
                    self.low_color_hex[1],
                    self.low_color_hex[2])
            elif finding['severity'].lower() == 'medium':
                font.color.rgb = RGBColor(
                    self.medium_color_hex[0],
                    self.medium_color_hex[1],
                    self.medium_color_hex[2])
            elif finding['severity'].lower() == 'high':
                font.color.rgb = RGBColor(
                    self.high_color_hex[0],
                    self.high_color_hex[1],
                    self.high_color_hex[2])
            else:
                font.color.rgb = RGBColor(
                    self.critical_color_hex[0],
                    self.critical_color_hex[2],
                    self.critical_color_hex[2])
            # Add an Affected Entities section
            self.spenny_doc.add_heading('Affected Entities', 4)
            if not finding['affected_entities']:
                finding['affected_entities'] = 'Must Be Provided'
            all_entities = finding['affected_entities'].split('\n')
            for entity in all_entities:
                entity = entity.strip()
                p = self.spenny_doc.add_paragraph(entity, style='Normal')
                self.list_number(p, level=0, num=False)
                p.paragraph_format.left_indent = Inches(0.5)
            # Add a Description section that may also include evidence figures
            self.spenny_doc.add_heading('Description', 4)
            self.process_text(finding['description'], finding, report_json)
            # Create Impact section
            self.spenny_doc.add_heading('Impact', 4)
            self.process_text(
                finding['impact'],
                finding,
                report_json)
            # Create Recommendations section
            self.spenny_doc.add_heading('Recommendation', 4)
            self.process_text(
                finding['recommendation'],
                finding,
                report_json)
            # Create Replication section
            self.spenny_doc.add_heading('Replication Steps', 4)
            self.process_text(
                finding['replication_steps'],
                finding,
                report_json)
            # Check if techniques are provided before creating a host
            # detection section
            if finding['host_detection_techniques']:
                self.spenny_doc.add_heading(
                    'Adversary Detection Techniques – Host', 4)
                self.process_text(
                    finding['host_detection_techniques'],
                    finding,
                    report_json)
            # Check if techniques are provided before creating a network
            # detection section
            if finding['network_detection_techniques']:
                self.spenny_doc.add_heading(
                    'Adversary Detection Techniques – Network', 4)
                self.process_text(
                    finding['network_detection_techniques'],
                    finding,
                    report_json)
            # Create References section
            self.spenny_doc.add_heading('References', 4)
            self.process_text(finding['references'], finding, report_json)
            # On to the next finding
            self.spenny_doc.add_page_break()
        # Finalize document and return it for an HTTP response
        return self.spenny_doc

    def generate_excel_xlsx(self, memory_object):
        """Generate the finding rows and save the document."""
        from ghostwriter.reporting.models import Evidence
        # Generate the JSON for the report
        report_json = json.loads(self.generate_json())
        # Create xlsxwriter
        spenny_doc = memory_object
        worksheet = spenny_doc.add_worksheet('Findings')
        # Create some basic formats
        # Header format
        bold_format = spenny_doc.add_format({'bold': True})
        bold_format.set_text_wrap()
        bold_format.set_align('vcenter')
        # Affected assets format
        asset_format = spenny_doc.add_format()
        asset_format.set_text_wrap()
        asset_format.set_align('vcenter')
        asset_format.set_align('center')
        # Remaining cells
        wrap_format = spenny_doc.add_format()
        wrap_format.set_text_wrap()
        wrap_format.set_align('vcenter')
        # Create header row for findings
        col = 0
        headers = ['Finding', 'Severity', 'Affected Entities', 'Description',
                   'Impact', 'Recommendation', 'Replication Steps',
                   'Host Detection Techniques', 'Network Detection Techniques',
                   'References', 'Supporting Evidence']
        for header in headers:
            worksheet.write(0, col, header, bold_format)
            col = col + 1
        # Width of all columns set to 30
        worksheet.set_column(0, 10, 30)
        # Width of severity columns set to 10
        worksheet.set_column(1, 1, 10)
        # Loop through the dict of findings to create findings worksheet
        col = 0
        row = 1
        for finding in report_json['findings'].values():
            # Finding Name
            worksheet.write(row, 0, finding['title'], wrap_format)
            # Severity
            severity_format = spenny_doc.add_format()
            severity_format.set_align('vcenter')
            severity_format.set_align('center')
            # Color the cell based on corresponding severity color
            if finding['severity'].lower() == 'informational':
                severity_format.set_bg_color(self.informational_color)
            elif finding['severity'].lower() == "low":
                severity_format.set_bg_color(self.low_color)
            elif finding['severity'].lower() == "medium":
                severity_format.set_bg_color(self.medium_color)
            elif finding['severity'].lower() == "high":
                severity_format.set_bg_color(self.high_color)
            elif finding['severity'].lower() == "critical":
                severity_format.set_bg_color(self.critical_color)
            worksheet.write(row, 1, finding['severity'], severity_format)
            # Affected Asset
            if finding['affected_entities']:
                worksheet.write(
                    row, 2, finding['affected_entities'], asset_format)
            else:
                worksheet.write(
                    row, 2, 'N/A', asset_format)
            # Description
            worksheet.write(
                row, 3, finding['description'], wrap_format)
            # Impact
            worksheet.write(
                row, 4, finding['impact'], wrap_format)
            # Recommendation
            worksheet.write(
                row, 5, finding['recommendation'], wrap_format)
            # Replication
            worksheet.write(
                row, 6, finding['replication_steps'], wrap_format)
            # Detection
            worksheet.write(
                row, 7, finding['host_detection_techniques'], wrap_format)
            worksheet.write(
                row, 8, finding['network_detection_techniques'], wrap_format)
            # References
            worksheet.write(
                row, 9, finding['references'], wrap_format)
            # Collect the evidence, if any, from the finding's folder and
            # insert inline with description
            try:
                evidence_queryset = Evidence.objects.\
                    filter(finding=finding['id'])
            except Exception:
                evidence_queryset = []
            # Loop through any evidence and add it to the evidence column
            evidence = [f.document.name for f in evidence_queryset
                        if f in self.image_extensions or self.text_extensions]
            finding_evidence_names = '\r\n'.join(map(str, evidence))
            # Evidence List
            worksheet.write(row, 10, finding_evidence_names, wrap_format)
            # Increment row counter before moving on to next finding
            row += 1
        # Add a filter to the worksheet
        worksheet.autofilter('A1:J{}'.format(len(report_json['findings'])+1))
        # Finalize document
        spenny_doc.close()
        return(spenny_doc)

    def insert_slide(self):
        """Shortcut for inserting new ppt slides"""
        # TO-DO

    def generate_powerpoint_pptx(self):
        """Generate the tables and save the PowerPoint presentation."""
        # Generate the JSON for the report
        report_json = json.loads(self.generate_json())
        # Create document writer using the specified template
        if self.template_loc:
            try:
                self.spenny_ppt = Presentation(self.template_loc)
            except Exception:
                # TODO: Return error on webpage
                pass
        else:
            # TODO: Return error on webpage
            pass
        self.ppt_color_info = pptx.dml.color.RGBColor(
            self.informational_color_hex[0],
            self.informational_color_hex[1],
            self.informational_color_hex[2])
        self.ppt_color_low = pptx.dml.color.RGBColor(
            self.low_color_hex[0],
            self.low_color_hex[1],
            self.low_color_hex[2])
        self.ppt_color_medium = pptx.dml.color.RGBColor(
            self.medium_color_hex[0],
            self.medium_color_hex[1],
            self.medium_color_hex[2])
        self.ppt_color_high = pptx.dml.color.RGBColor(
            self.high_color_hex[0],
            self.high_color_hex[1],
            self.high_color_hex[2])
        self.ppt_color_critical = pptx.dml.color.RGBColor(
            self.critical_color_hex[0],
            self.critical_color_hex[1],
            self.critical_color_hex[2])
        # Loop through the dict of findings to create slides based on findings
        # Initialize findings stats dict
        findings_stats = {
            'Critical': 0,
            'High': 0,
            'Medium': 0,
            'Low': 0,
            'Informational': 0
        }
        # Calculate finding stats
        for finding in report_json['findings'].values():
            findings_stats[finding['severity']] += 1
        # Slide styles (From Master Style counting top to bottom from 0..n)
        SLD_LAYOUT_TITLE = 0
        SLD_LAYOUT_TITLE_AND_CONTENT = 1
        SLD_LAYOUT_FINAL = 12
        # Add title slide
        slide_layout = self.spenny_ppt.slide_layouts[SLD_LAYOUT_TITLE]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = 'Ghostwriter'
        text_frame = body_shape.text_frame
        # Use text_frame.text for first line/paragraph or
        # text_frame.paragraphs[0]
        text_frame.text = report_json['client']['full_name']
        p = text_frame.add_paragraph()
        p.text = report_json['client']['full_name']
        # Add Agenda slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = 'Agenda'
        body_shape = shapes.placeholders[1]
        text_frame = body_shape.text_frame
        # Add Introduction slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = 'Introduction'
        body_shape = shapes.placeholders[1]
        text_frame = body_shape.text_frame
        # Add Methodology slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = 'Methodology'
        body_shape = shapes.placeholders[1]
        text_frame = body_shape.text_frame
        # Add Attack Path Overview slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        title_shape.text = 'Attack Path Overview'
        body_shape = shapes.placeholders[1]
        text_frame = body_shape.text_frame
        # Add Findings Overview Slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = 'Findings Overview'
        text_frame = body_shape.text_frame
        for stat in findings_stats:
            p = text_frame.add_paragraph()
            p.text = '{} Findings'.format(stat)
            p.level = 0
            p = text_frame.add_paragraph()
            p.text = str(findings_stats[stat])
            p.level = 1
        # Add Findings Overview Slide 2
        # If there are findings then write a table of findings and
        # severity ratings
        if len(report_json['findings']) > 0:
            # Delete the default text placeholder
            textbox = shapes[1]
            sp = textbox.element
            sp.getparent().remove(sp)
            # Add a table
            rows = len(report_json['findings']) + 1
            columns = 2
            left = Inches(1.5)
            top = Inches(2)
            width = Inches(8)
            height = Inches(0.8)
            table = shapes.add_table(
                rows,
                columns,
                left,
                top,
                width,
                height).table
            # Set column width
            table.columns[0].width = Inches(9.0)
            table.columns[1].width = Inches(1.5)
            # Write table headers
            cell = table.cell(0, 0)
            cell.text = 'Finding'
            cell.fill.solid()
            cell.fill.fore_color.rgb = pptx.dml.color.\
                RGBColor(0x2D, 0x28, 0x69)
            cell = table.cell(0, 1)
            cell.text = 'Severity'
            cell.fill.solid()
            cell.fill.fore_color.rgb = pptx.dml.color.\
                RGBColor(0x2D, 0x28, 0x69)
            # Write findings rows
            row_iter = 1
            for finding in report_json['findings'].values():
                table.cell(row_iter, 0).text = finding['title']
                risk_cell = table.cell(row_iter, 1)
                # Set risk rating
                risk_cell.text = finding['severity']
                # Set cell color fill type to solid
                risk_cell.fill.solid()
                # Color the risk cell based on corresponding severity color
                if finding['severity'].lower() == "informational":
                    risk_cell.fill.fore_color.rgb = self.ppt_color_info
                elif finding['severity'].lower() == "low":
                    risk_cell.fill.fore_color.rgb = self.ppt_color_low
                elif finding['severity'].lower() == "medium":
                    risk_cell.fill.fore_color.rgb = self.ppt_color_medium
                elif finding['severity'].lower() == "high":
                    risk_cell.fill.fore_color.rgb = self.ppt_color_high
                elif finding['severity'].lower() == "critical":
                    risk_cell.fill.fore_color.rgb = self.ppt_color_critical
                    # Set cell's font color to white for better contrast with
                    # dark background
                    paragraph = risk_cell.text_frame.paragraphs[0]
                    paragraph.font.color.rgb = pptx.dml.color.\
                        RGBColor(0xFF, 0xFF, 0xFF)
                row_iter += 1
            # Set all cells alignment to center and vertical center
            for cell in table.iter_cells():
                cell.text_frame.paragraphs[0].alignment = PP_ALIGN.CENTER
                cell.vertical_anchor = MSO_ANCHOR.MIDDLE
        else:
            p = text_frame.add_paragraph()
            p.text = 'No findings'
            p.level = 0
        # Create slide for each finding
        for finding in report_json['findings'].values():
            slide_layout = self.spenny_ppt.slide_layouts[
                SLD_LAYOUT_TITLE_AND_CONTENT]
            slide = self.spenny_ppt.slides.add_slide(slide_layout)
            shapes = slide.shapes
            title_shape = shapes.title
            body_shape = shapes.placeholders[1]
            title_shape.text = "{} [{}]".format(
                finding['title'],
                finding['severity'])
            text_frame = body_shape.text_frame
            text_frame.text = '{}'.format(finding['description'])
            bullets = finding['description'].splitlines()
            first_bullet = True
            for bullet in bullets:
                if first_bullet:
                    text_frame.text = bullet
                    first_bullet = False
                else:
                    p = text_frame.add_paragraph()
                    p.text = bullet
                    p.level = 0
            # Add some detailed notes
            notes_slide = slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            p = text_frame.add_paragraph()
            p.text = '{}: {}\n'.format(
                finding['severity'].capitalize(),
                finding['title'])
        # Add observations slide
        # Observation 1
        #  Bullet detail
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = 'Positive Observations'
        text_frame = body_shape.text_frame
        # Add recommendations slide
        # Recommendation 1
        # Bullet detail
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = "Recommendations"
        text_frame = body_shape.text_frame
        # Add Conclusion slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = 'Control Observations'
        text_frame = body_shape.text_frame
        # Add final slide
        slide_layout = self.spenny_ppt.slide_layouts[SLD_LAYOUT_FINAL]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        # title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        text_frame = body_shape.text_frame
        text_frame.clear()
        p = text_frame.paragraphs[0]
        p.line_spacing = 0.7
        p.text = settings.COMPANY_NAME
        p = text_frame.add_paragraph()
        p.text = settings.COMPANY_TWITTER
        p.line_spacing = 0.7
        p = text_frame.add_paragraph()
        p.text = settings.COMPANY_EMAIL
        p.line_spacing = 0.7
        # Finalize document and return it for an HTTP response
        return self.spenny_ppt

    def generate_all_reports(self, docx_template, pptx_template):
        """Generate all availabe report types and retturn memory streams for
        each file.
        """
        # Generate the JSON report - it just needs to be a string object
        report_json = self.generate_json()
        # Generate the docx report - save it in a memory stream
        self.template_loc = docx_template
        word_doc = self.generate_word_docx()
        word_stream = io.BytesIO()
        word_doc.save(word_stream)
        # Generate the xlsx report - save it in a memory stream
        excel_stream = io.BytesIO()
        workbook = Workbook(excel_stream, {'in_memory': True})
        self.generate_excel_xlsx(workbook)
        # Generate the pptx report - save it in a memory stream
        self.template_loc = pptx_template
        ppt_doc = self.generate_powerpoint_pptx()
        ppt_stream = io.BytesIO()
        ppt_doc.save(ppt_stream)
        # Return each memory object
        return report_json, word_stream, excel_stream, ppt_stream
