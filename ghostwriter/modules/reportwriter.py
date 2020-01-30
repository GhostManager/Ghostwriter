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

from bs4 import BeautifulSoup


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
    critical_color = '966FD6'
    critical_color_hex = [0x96, 0x6f, 0xd6]
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

    def valid_xml_char_ordinal(self, c):
        """Clean string to make all characters XML compatible for Word documents.

        https://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python
        """
        codepoint = ord(c)
        # Conditions ordered by presumed frequency
        return (
            0x20 <= codepoint <= 0xD7FF or
            codepoint in (0x9, 0xA, 0xD) or
            0xE000 <= codepoint <= 0xFFFD or
            0x10000 <= codepoint <= 0x10FFFF
            )

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
            if finding.affected_entities:
                report_dict['findings'][finding.title]['affected_entities'] = \
                    finding.affected_entities
            else:
                report_dict['findings'][finding.title]['affected_entities'] = \
                    '<p>Must Be Provided</p>'
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

    def set_contextual_spacing(self, par):
        """Enable Word's "Don't add spaces between paragraphs of the same style"
        option to remove extra spacing around list items.
        """
        styling = par.style._element.xpath("//w:pPr")[0]
        contextual_spacing = OxmlElement('w:contextualSpacing')
        styling.append(contextual_spacing)
        print(par.style._element.xml)
        return par

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

    def process_inline_text(self, line, p, report_type=None):
        """Process the provided line for the provided paragraph to handle
        nested inline text formatting.
        """
        # Split line on spaces and curly brackets
        all_words = re.split('<', line)
        all_words = [all_words[0]] + ['<' + l for l in all_words[1:]]
        for word in all_words:
            write_line = True
            prepared_text = word.replace('&nbsp;', '').strip() + ' '
            # Check if word is blank
            if not word:
                continue
            # Determine styling
            if (
                '<code' in word and
                '</code' not in word and
                not self.code_block
                ):
                self.inline_code = True
                prepared_text = prepared_text.replace('<code>', '')
            if '</code' in word:
                self.inline_code = False
                continue
            if '<span' in word and '</span' not in word:
                # When two or more styles are applied, TinyMCE uses a span:
                # e.g., <span class="bold italic">
                regex = r'(?<=class=").*?(?=">)'
                match = re.search(regex, word)
                self.span_classes = match[0].split(' ')
                if 'italic' in self.span_classes:
                    self.italic_text = True
                if 'bold' in self.span_classes:
                    self.bold_text = True
                prepared_text = prepared_text.replace('<span class="{}">'.format(' '.join(self.span_classes)), '')
            if '</span' in word:
                prepared_text = prepared_text.replace('</span>', '')
                if 'italic' in self.span_classes:
                    self.italic_text = False
                if 'bold' in self.span_classes:
                    self.bold_text = False
            if '<em' in word and '</em' not in word:
                prepared_text = prepared_text.replace('<em>', '')
                self.italic_text = True
            if '</em' in word:
                prepared_text = prepared_text.replace('</em>', '')
                self.italic_text = False
            if '<strong' in word and '</strong' not in word:
                prepared_text = prepared_text.replace('<strong>', '')
                self.bold_text = True
            if '</strong' in word:
                prepared_text = prepared_text.replace('</strong>', '')
                self.bold_text = False
            # Write the content
            if self.inline_code:
                if report_type == 'pptx':
                    if self.first_bullet:
                        run = p.add_run()
                        run.text = prepared_text
                        self.first_bullet = False
                    else:
                        text_frame = self.finding_body_shape.text_frame
                        run = p.add_run()
                        run.text = prepared_text
                else:
                    run = p.add_run()
                    run.text = prepared_text
                    run.style = 'Code (inline)'
            else:
                if report_type == 'pptx':
                    if self.first_bullet:
                        run = p.add_run()
                        run.text = prepared_text
                        self.first_bullet = False
                    else:
                        text_frame = self.finding_body_shape.text_frame
                        run = p.add_run()
                        run.text = prepared_text
                else:
                    run = p.add_run()
                    run.text = prepared_text
            if self.italic_text:
                    font = run.font
                    font.italic = True
            if self.bold_text:
                    font = run.font
                    font.bold = True

    def search_evidence(self, finding, search):
        """Search the provided finding JSON for the specified search term."""
        for key, value in finding.items():
            if search in finding[key]['url']:
                return key
        return None

    def process_evidence(self, finding, keyword, file_path, extension, report_type=None):
        """Process the specified evidence file for the named finding to
        add it to the Word document.
        """
        if extension in self.text_extensions:
            with open(file_path, 'r') as evidence_contents:
                # Read in evidence text
                evidence_text = evidence_contents.read()
                if report_type == 'pptx':
                    # Place new textbox to the mid-right
                    top = Inches(1.65)
                    left = Inches(6)
                    width = Inches(4.5)
                    height = Inches(3)
                    # Create new textbox, textframe, paragraph, and run
                    textbox = self.finding_slide.shapes.add_textbox(
                        left, top, width, height)
                    text_frame = textbox.text_frame
                    p = text_frame.paragraphs[0]
                    run = p.add_run()
                    # Insert evidence and apply formatting
                    run.text = evidence_text
                    font = run.font
                    font.size = Pt(11)
                    font.name = 'Courier New'
                else:
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
                        u' \u2013 ' +
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
            if report_type == 'pptx':
                top = Inches(1.65)
                left = Inches(8)
                width = Inches(4.5)
                image = self.finding_slide.shapes.add_picture(new_file, left, top, width=width)
            else:
                p = self.spenny_doc.add_paragraph()
                run = p.add_run()
                run.add_picture(new_file, width=Inches(6.5))
                p = self.spenny_doc.add_paragraph(
                    'Figure ',
                    style='Caption')
                self.make_figure(p)
                run = p.add_run(
                    u' \u2013 ' +
                    finding['evidence'][keyword]['caption'])
        # This skips unapproved files
        else:
            p = None
            pass

    def delete_paragraph(self, paragraph):
        """Function to delete the specified paragraph."""
        p = paragraph._p
        parent_element = p.getparent()
        parent_element.remove(p)

    def process_text_xml(self, text, finding, report_json, report_type=None):
        """Process the provided text from the specified finding to parse
        keywords for evidence placement and formatting for Office XML.
        """
        if report_type == 'pptx':
            if self.finding_body_shape.has_text_frame:
                self.finding_body_shape.text_frame.clear()
                self.delete_paragraph(self.finding_body_shape.text_frame.paragraphs[0])
        # Track paragraphs for docx lists
        p = None
        prev_p = None
        # Track formatting options
        self.bold_text = False
        self.code_block = False
        self.inline_code = False
        self.italic_text = False
        self.numbered_list = False
        self.bulleted_list = False
        # Track bullets for pptx slides
        self.first_bullet = True
        # Regex for searching for bracketed template placeholders, e.g. {{.client}}
        keyword_regex = r'\{\{\.(.*?)\}\}'
        # Clean text to make it XML compatible for Office XML
        text = ''.join(c for c in text if self.valid_xml_char_ordinal(c))
        # Split the text by HTML tags
        # We do not use BS4 here because we don't need searchable strings
        # We want to be able to manipulate the HTML as basic strings
        html = text.split('<')
        # Now make a list and restore the removed '<' characters
        html = [html[0]] + ['<' + l for l in html[1:]]
        # Go line by line to strip and process each piece of the text
        for line in html:
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
            # Handle keywords that affect whole paragraphs
            if (
                line.startswith('<pre class="language-') or
                line.startswith('</pre>') or
                line.startswith('<code>') or
                line.startswith('</code>') or
                line.startswith('<ol>') or
                line.startswith('</ol>') or
                line.startswith('<ul>') or
                line.startswith('</ul>') or
                line.startswith('<li>') or
                line.startswith('</li>') or
                line.startswith('<p>') or
                line.startswith('</p>') or
                line.startswith('<img')
              ):
                if line.startswith('<p>'):
                    line = line.lstrip('<p>')
                    # Check for any template keywords in need of processing
                    match = re.search(keyword_regex, line)
                    if match:
                        # Get just the first match, set it as the "keyword," and  
                        # remove it from the line
                        # There should never be - or need to be - multiple matches
                        match = match[0]
                        keyword = match.\
                            replace('{', '').\
                            replace('}', '').\
                            replace('.', '').\
                            strip()
                        line = line.replace(match, '')
                    else:
                        keyword = ''
                    # Handle caption keywords following <p>
                    if keyword == 'caption':
                        if report_type == 'pptx':
                            # Only option would be to make the caption a slide
                            # bullet and that would be weird - so just pass
                            pass
                        else:
                            # This is a caption so turn off any list formatting
                            self.numbered_list = False
                            self.bulleted_list = False
                            p = self.spenny_doc.add_paragraph(
                                'Figure ',
                                style='Caption')
                            self.make_figure(p)
                            run = p.add_run(u' \u2013 ' + line)
                    # Handle evidence keywords following <p>
                    elif keyword in finding['evidence'].keys():
                        file_path = settings.MEDIA_ROOT + \
                                   '/' + \
                                   finding['evidence'][keyword]['file_path']
                        extension = finding['evidence'][keyword]['url'].\
                            split('.')[-1]
                        self.process_evidence(finding, keyword, file_path, extension, report_type)
                    else:
                        if line:
                            if report_type == 'pptx':
                                p = self.finding_body_shape.text_frame.add_paragraph()
                                self.process_inline_text(line, p, 'pptx')
                            else:
                                p = self.spenny_doc.add_paragraph()
                                self.process_inline_text(line, p)
                # Lines starting with a closing </p> are usually just that
                # tag and nothing else so strip and move on
                if line.startswith('</p>'):
                    line = line.lstrip('</p>')
                    if line:
                        if report_type == 'pptx':
                            self.process_inline_text(line, p, 'pptx')
                        else:
                            self.process_inline_text(line, p)
                # Handle code blocks
                if line.startswith('<pre class="language-'):
                    self.code_block = True
                if line.startswith('</pre>'):
                    self.code_block = False
                    continue
                if line.startswith('<code>'):
                    if self.code_block:
                        line = line.strip('<code>')
                        if report_type == 'pptx':
                            # Place new textbox to the mid-right
                            if line:
                                top = Inches(1.65)
                                left = Inches(6)
                                width = Inches(4.5)
                                height = Inches(3)
                                # Create new textbox, textframe, paragraph, and run
                                textbox = self.finding_slide.shapes.add_textbox(
                                    left, top, width, height)
                                text_frame = textbox.text_frame
                                p = text_frame.paragraphs[0]
                                run = p.add_run()
                                # Insert code block and apply formatting
                                run.text = line.replace('\x0D', '')
                                font = run.font
                                font.size = Pt(11)
                                font.name = 'Courier New'
                        else:
                            # Create paragraph and apply 'CodeBlock' style
                            # Style is managed in the docx template
                            p = self.spenny_doc.add_paragraph()
                            p.style = 'CodeBlock'
                            p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                            if line:
                                for code in line.split('\n'):
                                    p.add_run(code)
                    else:
                        self.process_inline_text(line, p)
                if line.startswith('</code>'):
                    line = line.lstrip('</code>')
                    if self.inline_code:
                        self.inline_code = False
                    if line:
                        if report_type == 'pptx':
                            self.process_inline_text(line, p, 'pptx')
                        else:
                            self.process_inline_text(line, p)
                # Check for ordered lists (numbered)
                if line.startswith('<ol>'):
                    self.numbered_list = True
                    line = line.replace('<ol>', '')
                    if line:
                        if report_type == 'pptx':
                            # Nothing to do here (for now) for pptx
                            pass
                        else:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            p = self.set_contextual_spacing(p)
                            self.process_inline_text(line, p)
                            self.list_number(p, level=0, num=True)
                            p.paragraph_format.left_indent = Inches(0.5)
                if line.startswith('</ol>'):
                    self.numbered_list = False
                    line = line.replace('</ol>', '')
                    if line:
                        if report_type == 'pptx':
                            # Nothing to do here (for now) for pptx
                            pass
                        else:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            self.process_inline_text(line, p)
                            self.list_number(p, level=0, num=True)
                            p.paragraph_format.left_indent = Inches(0.5)
                    continue
                # Check for unordered lists (bulleted)
                if line.startswith('<ul>'):
                    self.bulleted_list = True
                    line = line.replace('<ul>', '')
                    if line:
                        if report_type == 'pptx':
                            # Nothing to do here (for now) for pptx
                            pass
                        else:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            p = self.set_contextual_spacing(p)
                            self.process_inline_text(line, p)
                            self.list_number(p, level=0, num=False)
                            p.paragraph_format.left_indent = Inches(0.5)
                if line.startswith('</ul>'):
                    self.bulleted_list = False
                    line = line.replace('</ul>', '')
                    if line:
                        if report_type == 'pptx':
                            # Nothing to do here (for now) for pptx
                            pass
                        else:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            p = self.set_contextual_spacing(p)
                            self.process_inline_text(line, p)
                            self.list_number(p, level=0, num=False)
                            p.paragraph_format.left_indent = Inches(0.5)
                    continue
                # Handle list items
                if line.startswith('<li>'):
                    line = line.replace('<li>', '')
                    if report_type == 'pptx':
                        # Move to new paragraph/line and indent bullets one tab
                        p = self.finding_body_shape.text_frame.add_paragraph()
                        p.level = 1
                        self.process_inline_text(line, p, 'pptx')
                    else:
                        if self.numbered_list:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            p = self.set_contextual_spacing(p)
                            self.process_inline_text(line, p)
                            self.list_number(p, prev=prev_p, level=0, num=True)
                            p.paragraph_format.left_indent = Inches(0.5)
                        elif self.bulleted_list:
                            p = self.spenny_doc.add_paragraph(style='Normal')
                            p = self.set_contextual_spacing(p)
                            self.process_inline_text(line, p)
                            self.list_number(p, level=0, num=False)
                            p.paragraph_format.left_indent = Inches(0.5)
                        else:
                            continue
                if line.startswith('</li>'):
                    continue
                # Handle inserted evidence images
                if line.startswith('<img'):
                    # Check if the img src references evidence
                    evidence = False
                    if 'evidence' in finding:
                        # Check if the src attribute is in evidence
                        try:
                            regex = r'(?<=src="..\/..\/..\/..)(.*?)(?=")'
                            match = re.search(regex, line)
                            keyword = self.search_evidence(finding['evidence'], match[0])
                            if keyword:
                                evidence = True
                        except:
                            print("[!] No match for image source in evidence: {}".format(line))
                        if evidence:
                            file_path = settings.MEDIA_ROOT + \
                                    '/' + \
                                    finding['evidence'][keyword]['file_path']
                            extension = finding['evidence'][keyword]['url'].\
                                split('.')[-1]
                            self.process_evidence(finding, keyword, file_path, extension, report_type)
            # Continue handling paragraph formatting if active
            elif self.code_block:
                self.process_inline_text(line, p, report_type)
            elif self.numbered_list:
                self.process_inline_text(line, p, report_type)
                if report_type == 'pptx':
                    pass
                else:
                    self.list_number(p, prev=prev_p, level=0, num=True)
                    p.paragraph_format.left_indent = Inches(0.5)
            elif self.bulleted_list:
                self.process_inline_text(line, p, report_type)
                if report_type == 'pptx':
                    pass
                else:
                    self.list_number(p, level=0, num=False)
                    p.paragraph_format.left_indent = Inches(0.5)
            # Handle keywords wrapped around runs of text inside paragraphs
            # and evidence files
            else:
                if '<img' in line:
                    # Check if the keyword references evidence
                    evidence = False
                    if 'evidence' in finding:
                        regex = r'src="..\/..\/..\/..(.*?)"'
                        match = re.search(regex, line)
                        if match[0] in finding['evidence'].values():
                            evidence = True
                    if evidence:
                        file_path = settings.MEDIA_ROOT + \
                                   '/' + \
                                   finding['evidence'][keyword]['file_path']
                        extension = finding['evidence'][keyword]['url'].\
                            split('.')[-1]
                        self.process_evidence(finding, keyword, file_path, extension, report_type)
                    else:
                        # Handle keywords that require managing runs
                        p = self.spenny_doc.add_paragraph()
                        p.alignment = WD_ALIGN_PARAGRAPH.LEFT
                        self.process_inline_text(line, p, report_type)
                else:
                    if line:
                        self.process_inline_text(line, p, report_type)
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
                raise
        else:
            raise
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

        if report_json['client']['poc'].values():
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

        if report_json['team'].values():
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

        if report_json['team'].values() or report_json['client']['poc'].values():
            self.spenny_doc.add_page_break()

        ################################################
        # Create the Infrastructure Information Tables #
        ################################################

        if report_json['infrastructure']['domains'].values():
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

        if report_json['infrastructure']['servers']['static'].values() or report_json['infrastructure']['servers']['cloud'].values():
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

        if report_json['infrastructure']['domains_and_servers'].values():
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

        if report_json['infrastructure']['domains'].values() or report_json['infrastructure']['servers']['static'].values() or report_json['infrastructure']['servers']['cloud'].values() or report_json['infrastructure']['domains_and_servers'].values():
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
                    self.critical_color_hex[1],
                    self.critical_color_hex[2])
            # Add an Affected Entities section
            self.spenny_doc.add_heading('Affected Entities', 4)
            self.process_text_xml(finding['affected_entities'], finding, report_json)
            # Add a Description section that may also include evidence figures
            self.spenny_doc.add_heading('Description', 4)
            self.process_text_xml(finding['description'], finding, report_json)
            # Create Impact section
            self.spenny_doc.add_heading('Impact', 4)
            self.process_text_xml(
                finding['impact'],
                finding,
                report_json)
            # Create Recommendations section
            self.spenny_doc.add_heading('Recommendation', 4)
            self.process_text_xml(
                finding['recommendation'],
                finding,
                report_json)
            # Create Replication section
            self.spenny_doc.add_heading('Replication Steps', 4)
            self.process_text_xml(
                finding['replication_steps'],
                finding,
                report_json)
            # Check if techniques are provided before creating a host
            # detection section
            if finding['host_detection_techniques']:
                # \u2013 is an em-dash
                self.spenny_doc.add_heading(
                    u'Adversary Detection Techniques \u2013 Host', 4)
                self.process_text_xml(
                    finding['host_detection_techniques'],
                    finding,
                    report_json)
            # Check if techniques are provided before creating a network
            # detection section
            if finding['network_detection_techniques']:
                # \u2013 is an em-dash
                self.spenny_doc.add_heading(
                    u'Adversary Detection Techniques \u2013 Network', 4)
                self.process_text_xml(
                    finding['network_detection_techniques'],
                    finding,
                    report_json)
            # Create References section
            if finding['references']:
                self.spenny_doc.add_heading('References', 4)
                self.process_text_xml(finding['references'], finding, report_json)
            # On to the next finding
            self.spenny_doc.add_page_break()
        # Finalize document and return it for an HTTP response
        return self.spenny_doc

    def process_text_xlsx(self, html, text_format, finding, report_json):
        """Process the provided text from the specified finding to parse
        keywords for evidence placement and formatting in xlsx documents.
        """
        # Regex for searching for bracketed template placeholders, e.g. {{.client}}
        keyword_regex = r'\{\{\.(.*?)\}\}'
        # Strip out all HTML tags
        # This _could_ impact HTML strings a user has included as part of a finding
        # but we can revisit this later
        text = BeautifulSoup(html, 'lxml').text
        # Perform the necessary replacements
        if '{{.client}}' in text:
            if report_json['client']['short_name']:
                text = text.replace(
                    '{{.client}}',
                    report_json['client']['short_name'])
            else:
                text = text.replace(
                    '{{.client}}',
                    report_json['client']['full_name'])
        text = text.replace('{{.caption}}', u'Caption \u2013 ')
        # Find/replace evidence keywords because they're ugly and don't make sense when read
        match = re.findall(keyword_regex, text)
        if match:
            for keyword in match:
                if keyword in finding['evidence'].keys():
                    # \u2013 is an em-dash
                    text = text.replace(
                        "{{." + keyword + "}}",
                        u'\n<See Report for Evidence File: {}>\nCaption \u2013 {}'.format(
                            finding['evidence'][keyword]['friendly_name'],
                            finding['evidence'][keyword]['caption'])
                            )
                else:
                    # Some unrecognized strring inside braces so ignore it
                    pass
        self.worksheet.write(self.row, self.col, text, text_format)

    def generate_excel_xlsx(self, memory_object):
        """Generate the finding rows and save the document."""
        from ghostwriter.reporting.models import Evidence
        # Generate the JSON for the report
        report_json = json.loads(self.generate_json())
        # Create xlsxwriter
        spenny_doc = memory_object
        self.worksheet = spenny_doc.add_worksheet('Findings')
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
        self.col = 0
        headers = ['Finding', 'Severity', 'Affected Entities', 'Description',
                   'Impact', 'Recommendation', 'Replication Steps',
                   'Host Detection Techniques', 'Network Detection Techniques',
                   'References', 'Supporting Evidence']
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
        for finding in report_json['findings'].values():
            # Finding Name
            self.worksheet.write(self.row, self.col, finding['title'], wrap_format)
            self.col += 1
            # Severity
            severity_format = spenny_doc.add_format({'bold': True})
            severity_format.set_align('vcenter')
            severity_format.set_align('center')
            severity_format.set_font_color('black')
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
            self.worksheet.write(self.row, 1, finding['severity'], severity_format)
            self.col += 1
            # Affected Asset
            if finding['affected_entities']:
                self.process_text_xlsx(
                    finding['affected_entities'], asset_format, finding, report_json)
            else:
                self.worksheet.write(
                    self.row, self.col, 'N/A', asset_format, finding, report_json)
            self.col += 1
            # Description
            self.process_text_xlsx(
                finding['description'], wrap_format, finding, report_json)
            self.col += 1
            # Impact
            self.process_text_xlsx(
                finding['impact'], wrap_format, finding, report_json)
            self.col += 1
            # Recommendation
            self.process_text_xlsx(
                finding['recommendation'], wrap_format, finding, report_json)
            self.col += 1
            # Replication
            self.process_text_xlsx(
                finding['replication_steps'], wrap_format, finding, report_json)
            self.col += 1
            # Detection
            self.process_text_xlsx(
                finding['host_detection_techniques'], wrap_format, finding, report_json)
            self.col += 1
            self.process_text_xlsx(
                finding['network_detection_techniques'], wrap_format, finding, report_json)
            self.col += 1
            # References
            self.process_text_xlsx(
                finding['references'], wrap_format, finding, report_json)
            self.col += 1
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
            self.worksheet.write(self.row, self.col, finding_evidence_names, wrap_format)
            # Increment row counter and reset columns before moving on to next finding
            self.row += 1
            self.col = 0
        # Add a filter to the worksheet
        self.worksheet.autofilter('A1:J{}'.format(len(report_json['findings'])+1))
        # Finalize document
        spenny_doc.close()
        return(spenny_doc)

    def process_text_pptx(self, html, text_frame, finding, report_json):
        """Process the provided text from the specified finding to parse
        keywords for evidence placement and formatting in pptx decks.
        """
        # Regex for searching for bracketed template placeholders, e.g. {{.client}}
        keyword_regex = r'\{\{\.(.*?)\}\}'
        # Strip out all HTML tags
        # This _could_ impact HTML strings a user has included as part of a finding
        # but we can revsit this later
        text = BeautifulSoup(html, 'lxml').text
        # Perform the necessary replacements
        if '{{.client}}' in text:
            if report_json['client']['short_name']:
                text = text.replace(
                    '{{.client}}',
                    report_json['client']['short_name'])
            else:
                text = text.replace(
                    '{{.client}}',
                    report_json['client']['full_name'])
        text = text.replace('{{.caption}}', u'Caption \u2013 ')
        # Find/replace evidence keywords because they're ugly and don't make sense when read
        match = re.findall(keyword_regex, text)
        if match:
            for keyword in match:
                if keyword in finding['evidence'].keys():
                    # \u2013 is an em-dash
                    text = text.replace(
                        "{{." + keyword + "}}",
                        u'\n<See Report for Evidence File: {}>\nCaption \u2013 {}'.format(
                            finding['evidence'][keyword]['friendly_name'],
                            finding['evidence'][keyword]['caption'])
                            )
                else:
                    # Some unrecognized strring inside braces so ignore it
                    pass
        bullets = text.splitlines()
        first_bullet = True
        for bullet in bullets:
            if bullet:
                if first_bullet:
                    text_frame.text = bullet
                    first_bullet = False
                else:
                    p = text_frame.add_paragraph()
                    p.text = bullet
                    p.level = 0

    def generate_powerpoint_pptx(self):
        """Generate the tables and save the PowerPoint presentation."""
        # Generate the JSON for the report
        report_json = json.loads(self.generate_json())
        # Create document writer using the specified template
        if self.template_loc:
            try:
                self.spenny_ppt = Presentation(self.template_loc)
            except Exception:
                raise
        else:
            raise
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
        # Add a title slide
        slide_layout = self.spenny_ppt.slide_layouts[SLD_LAYOUT_TITLE]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = settings.COMPANY_NAME
        text_frame = body_shape.text_frame
        # Use text_frame.text for first line/paragraph or
        # text_frame.paragraphs[0]
        text_frame.text = '{} Debrief'.format(report_json['project']['project_type'])
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
            table.columns[0].width = Inches(8.5)
            table.columns[1].width = Inches(2.0)
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
            self.finding_slide = self.spenny_ppt.slides.add_slide(slide_layout)
            shapes = self.finding_slide.shapes
            title_shape = shapes.title
            self.finding_body_shape = shapes.placeholders[1]
            title_shape.text = "{} [{}]".format(
                finding['title'],
                finding['severity'])
            self.process_text_xml(finding['description'], finding, report_json, 'pptx')
            # Add some detailed notes
            # Strip all HTML tags and replace any \x0D characters for pptx
            entities = BeautifulSoup(finding['affected_entities'], 'lxml').text.replace('\x0D', '')
            impact = BeautifulSoup(finding['impact'], 'lxml').text.replace('\x0D', '')
            recommendation = BeautifulSoup(finding['recommendation'], 'lxml').text.replace('\x0D', '')
            replication = BeautifulSoup(finding['replication_steps'], 'lxml').text.replace('\x0D', '')
            references = BeautifulSoup(finding['references'], 'lxml').text.replace('\x0D', '')
            notes_slide = self.finding_slide.notes_slide
            text_frame = notes_slide.notes_text_frame
            p = text_frame.add_paragraph()
            p.text = '{}: {}\n\nAFFECTED ENTITIES\n\n{}\n\nIMPACT\n\n{}\n\n\
MITIGATION\n\n{}\n\nREPLICATION\n\n{}\n\nREFERENCES\n\n{}'.format(
                    finding['severity'].capitalize(), finding['title'],
                    entities, impact, recommendation, replication,
                    references
                )
        # Add Observations slide
        slide_layout = self.spenny_ppt.slide_layouts[
            SLD_LAYOUT_TITLE_AND_CONTENT]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
        title_shape = shapes.title
        body_shape = shapes.placeholders[1]
        title_shape.text = 'Positive Observations'
        text_frame = body_shape.text_frame
        # Add Recommendations slide
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
        title_shape.text = 'Positive Observations'
        text_frame = body_shape.text_frame
        # Add final slide
        slide_layout = self.spenny_ppt.slide_layouts[SLD_LAYOUT_FINAL]
        slide = self.spenny_ppt.slides.add_slide(slide_layout)
        shapes = slide.shapes
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
        try:
            self.template_loc = docx_template
            word_doc = self.generate_word_docx()
            word_stream = io.BytesIO()
            word_doc.save(word_stream)
        except:
            raise
        # Generate the xlsx report - save it in a memory stream
        try:
            excel_stream = io.BytesIO()
            workbook = Workbook(excel_stream, {'in_memory': True})
            self.generate_excel_xlsx(workbook)
        except:
            raise
        # Generate the pptx report - save it in a memory stream
        try:
            self.template_loc = pptx_template
            ppt_doc = self.generate_powerpoint_pptx()
            ppt_stream = io.BytesIO()
            ppt_doc.save(ppt_stream)
        except:
            raise
        # Return each memory object
        return report_json, word_stream, excel_stream, ppt_stream
