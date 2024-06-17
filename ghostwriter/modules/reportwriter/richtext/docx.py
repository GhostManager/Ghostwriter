# Standard Libraries
import logging
import os
import random
import re

# Django Imports
from django.conf import settings

# 3rd Party Libraries
import docx
from docx.enum.dml import MSO_THEME_COLOR_INDEX
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX
from docx.image.exceptions import UnrecognizedImageError
from docx.oxml.shared import OxmlElement, qn
from docx.shared import Inches, Pt
from docx.shared import RGBColor as DocxRgbColor
from lxml import etree

# Ghostwriter Libraries
from ghostwriter.modules.reportwriter.extensions import IMAGE_EXTENSIONS, TEXT_EXTENSIONS
from ghostwriter.modules.reportwriter.richtext.ooxml import BaseHtmlToOOXML, parse_styles

logger = logging.getLogger(__name__)


class HtmlToDocx(BaseHtmlToOOXML):
    """
    Converts HTML to a word document
    """

    def __init__(self, doc, p_style):
        super().__init__()
        self.doc = doc
        self.p_style = p_style
        self.list_styles_cache = {}

    def text(self, el, *, par=None, style={}, **kwargs):
        # Process hyperlinks on top of the usual text rules
        if par is not None and style.get("hyperlink_url"):
            # For Word, this code is modified from this issue:
            #   https://github.com/python-openxml/python-docx/issues/384
            # Get an ID from the ``document.xml.rels`` file
            part = par.part
            r_id = part.relate_to(
                style["hyperlink_url"],
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
            self.text_tracking.append_text_to_run(new_run, str(el))
            hyperlink.append(new_run)
            # Create a new Run object and add the hyperlink into it
            run = par.add_run()
            run._r.append(hyperlink)
            # A workaround for the lack of a hyperlink style
            if "Hyperlink" in self.doc.styles:
                run.style = "Hyperlink"
            else:
                run.font.color.theme_color = MSO_THEME_COLOR_INDEX.HYPERLINK
                run.font.underline = True
        else:
            super().text(el, par=par, style=style, **kwargs)

    def style_run(self, run, style):
        super().style_run(run, style)
        if style.get("inline_code"):
            run.style = "CodeInline"
            run.font.no_proof = True
        if style.get("highlight"):
            run.font.highlight_color = WD_COLOR_INDEX.YELLOW
        if style.get("strikethrough"):
            run.font.strike = True
        if style.get("subscript"):
            run.font.subscript = True
        if style.get("superscript"):
            run.font.superscript = True
        if style.get("font_size"):
            run.font.size = Pt(style["font_size"])
        if "font_color" in style:
            run.font.color.rgb = DocxRgbColor(*style["font_color"])

    def tag_br(self, el, *, par=None, **kwargs):
        self.text_tracking.new_block()
        if "data-gw-pagebreak" in el.attrs:
            self.doc.add_page_break()
        else:
            run = par.add_run()
            run.add_break()

    def _tag_h(self, el, **kwargs):
        heading_num = int(el.name[1:])
        self.text_tracking.new_block()
        self.doc.add_heading(el.text, heading_num)

    tag_h1 = _tag_h
    tag_h2 = _tag_h
    tag_h3 = _tag_h
    tag_h4 = _tag_h
    tag_h5 = _tag_h
    tag_h6 = _tag_h

    def tag_p(self, el, *, par=None, **kwargs):
        self.text_tracking.new_block()
        if par is not None:
            # <p> nested in another block element like blockquote, use or copy the paragraph object
            if any(run.text for run in par.runs):
                # Paragraph has things in it already, make a new one but copy the style
                par = self.doc.add_paragraph(style=par.style)
        else:
            # Top level <p>
            par = self.doc.add_paragraph()
            try:
                par.style = self.p_style
            except KeyError:
                pass

        par_classes = set(el.attrs.get("class", []))
        if "left" in par_classes:
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        if "center" in par_classes:
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
        if "right" in par_classes:
            par.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        if "justify" in par_classes:
            par.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY

        self.process_children(el, par=par, **kwargs)

    def tag_pre(self, el, *, par=None, **kwargs):
        if par is None:
            par = self.doc.add_paragraph()

        par.alignment = WD_ALIGN_PARAGRAPH.LEFT
        run = par.add_run(el.get_text())
        try:
            par.style = "CodeBlock"
        except KeyError:
            font = run.font
            font.name = "Courier New"

    def tag_ul(self, el, *, par=None, list_level=None, list_tracking=None, **kwargs):
        if list_tracking is None:
            list_tracking = ListTracking()
            assert list_level is None
            this_list_level = 0
        else:
            assert list_level is not None
            this_list_level = list_level + 1

        is_ordered = el.name == "ol"

        # Create paragraphs for each list item
        for child in el.children:
            if child.name != "li":
                # TODO: log
                continue
            par = self.doc.add_paragraph()
            self.text_tracking.new_block()
            list_tracking.add_paragraph(par, this_list_level, is_ordered)
            self.process_children(
                child.children, par=par, list_level=this_list_level, list_tracking=list_tracking, **kwargs
            )

        if this_list_level == 0:
            list_tracking.create(self.doc, self.list_styles_cache)

    tag_ol = tag_ul

    def tag_blockquote(self, el, **kwargs):
        # TODO: if done in a list, this won't preserve the level.
        # Not sure how to do that, since this requires a new paragraph.
        par = self.doc.add_paragraph()
        self.text_tracking.new_block()
        try:
            par.style = "Blockquote"
        except KeyError:
            pass
        self.process_children(el.children, par=par, **kwargs)

    def create_table(self, rows, cols, **kwargs):
        table = self.doc.add_table(rows=rows, cols=cols, style="Table Grid")
        self.set_autofit()

        return table

    def paragraph_for_table_cell(self, cell, td_el):
        def handle_style(key, value):
            if key == "background-color":
                shade = OxmlElement("w:shd")
                shade.set(qn("w:fill"), value.replace("#", ""))
                cell._tc.get_or_add_tcPr().append(shade)

        parse_styles(td_el.attrs.get("style", ""), handle_style)

        return next(iter(cell.paragraphs))

    def set_autofit(self):
        """
        Hotfix for lack of full autofit support for tables in `python-docx`.

        Ref: https://github.com/python-openxml/python-docx/issues/209
        """
        for t_idx, _ in enumerate(self.doc.tables):
            self.doc.tables[t_idx].autofit = True
            self.doc.tables[t_idx].allow_autofit = True
            self.doc.tables[t_idx]._tblPr.xpath("./w:tblW")[0].attrib[
                "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}type"
            ] = "auto"
            for row_idx, _ in enumerate(self.doc.tables[t_idx].rows):
                for cell_idx, _ in enumerate(self.doc.tables[t_idx].rows[row_idx].cells):
                    self.doc.tables[t_idx].rows[row_idx].cells[cell_idx]._tc.tcPr.tcW.type = "auto"
                    self.doc.tables[t_idx].rows[row_idx].cells[cell_idx]._tc.tcPr.tcW.w = 0
        return self.doc


class HtmlToDocxWithEvidence(HtmlToDocx):
    """
    Augments `HtmlToDocx`, replacing marked spans with evidence figures, captions,
    and references.
    """

    def __init__(
        self,
        doc,
        p_style,
        evidences,
        figure_label: str,
        figure_prefix: str,
        title_case_captions: bool,
        title_case_exceptions: list[str],
        border_color_width: tuple[str, float] | None,
    ):
        super().__init__(doc, p_style)
        self.evidences = evidences
        self.figure_label = figure_label
        self.figure_prefix = figure_prefix
        self.title_case_captions = title_case_captions
        self.title_case_exceptions = title_case_exceptions
        self.border_color_width = border_color_width

    def text(self, el, *, par=None, **kwargs):
        if par is not None and getattr(par, "_gw_is_caption", False):
            el = self.title_except(el)
        return super().text(el, par=par, **kwargs)

    def tag_span(self, el, *, par, **kwargs):
        if "data-gw-evidence" in el.attrs:
            try:
                evidence = self.evidences[int(el.attrs["data-gw-evidence"])]
            except (KeyError, ValueError):
                return
            self.make_evidence(par, evidence)
        elif "data-gw-caption" in el.attrs:
            ref_name = el.attrs["data-gw-caption"]
            par.style = "Caption"
            par._gw_is_caption = True
            self.make_figure(par, ref_name or None)
        elif "data-gw-ref" in el.attrs:
            ref_name = el.attrs["data-gw-ref"]
            self.text_tracking.force_emit_pending_segment_break()
            self.make_cross_ref(par, ref_name)
        else:
            super().tag_span(el, par=par, **kwargs)

    def title_except(self, s):
        """
        Title case the given string except for articles and words in the provided exceptions list.

        Ref: https://stackoverflow.com/a/3729957
        """
        if self.title_case_captions:
            word_list = re.split(" ", s)  # re.split behaves as expected
            final = [word_list[0].capitalize()]
            for word in word_list[1:]:
                final.append(word if word in self.title_case_exceptions else word.capitalize())
            s = " ".join(final)
        return s

    def make_figure(self, par, ref: str | None = None):
        if ref:
            ref = f"_Ref{ref}"
        else:
            ref = f"_Ref{random.randint(10000000, 99999999)}"

        # Start a bookmark run with the figure label
        p = par._p
        bookmark_start = OxmlElement("w:bookmarkStart")
        bookmark_start.set(qn("w:name"), ref)
        bookmark_start.set(qn("w:id"), "0")
        p.append(bookmark_start)

        # Add the figure label
        run = par.add_run(self.figure_label)

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

        # Add prefix
        par.add_run(self.figure_prefix)

    def make_evidence(self, par, evidence):
        file_path = settings.MEDIA_ROOT + "/" + evidence["path"]
        if not os.path.exists(file_path):
            raise FileNotFoundError(file_path)

        extension = file_path.split(".")[-1].lower()
        if extension in TEXT_EXTENSIONS:
            with open(file_path, "r", encoding="utf-8") as evidence_file:
                evidence_text = evidence_file.read()
            par.text = evidence_text
            par.alignment = WD_ALIGN_PARAGRAPH.LEFT
            try:
                par.style = "CodeBlock"
            except KeyError:
                pass
            par_caption = self.doc.add_paragraph(style="Caption")
            self.make_figure(par_caption, evidence["friendly_name"])
            par_caption.add_run(self.title_except(evidence["caption"]))
        elif extension in IMAGE_EXTENSIONS:
            par.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = par.add_run()
            try:
                run.add_picture(file_path, width=Inches(6.5))
            except UnrecognizedImageError as e:
                logger.exception(
                    "Evidence file known as %s (%s) was not recognized as a %s file.",
                    evidence["friendly_name"],
                    file_path,
                    extension,
                )
                error_msg = (
                    f'The evidence file, `{evidence["friendly_name"]},` was not recognized as a {extension} file. '
                    "Try opening it, exporting as desired type, and re-uploading it."
                )
                raise UnrecognizedImageError(error_msg) from e

            if self.border_color_width is not None:
                border_color, border_width = self.border_color_width
                # Add the border – see Ghostwriter Wiki for documentation
                inline_class = run._r.xpath("//wp:inline")[-1]
                inline_class.attrib["distT"] = "0"
                inline_class.attrib["distB"] = "0"
                inline_class.attrib["distL"] = "0"
                inline_class.attrib["distR"] = "0"

                # Set the shape's "effect extent" attributes to the border weight
                effect_extent = OxmlElement("wp:effectExtent")
                effect_extent.set("l", str(border_width))
                effect_extent.set("t", str(border_width))
                effect_extent.set("r", str(border_width))
                effect_extent.set("b", str(border_width))
                # Insert just below ``<wp:extent>`` or it will not work
                inline_class.insert(1, effect_extent)

                # Find inline shape properties – ``pic:spPr``
                pic_data = run._r.xpath("//pic:spPr")[-1]
                # Assemble OXML for a solid border
                ln_xml = OxmlElement("a:ln")
                ln_xml.set("w", str(border_width))
                solidfill_xml = OxmlElement("a:solidFill")
                color_xml = OxmlElement("a:srgbClr")
                color_xml.set("val", border_color)
                solidfill_xml.append(color_xml)
                ln_xml.append(solidfill_xml)
                pic_data.append(ln_xml)

            # Create the caption for the image
            p = self.doc.add_paragraph(style="Caption")
            self.make_figure(p, evidence["friendly_name"])
            run = p.add_run(self.title_except(evidence["caption"]))

    def make_cross_ref(self, par, ref: str):
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
        instrText.text = " REF \"_Ref{}\" \\h ".format(ref.replace('\\', '\\\\').replace('"', '\\"'))
        r.append(instrText)

        # An optional ``separate`` value to enforce a space between label and number
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "separate")
        r.append(fldChar)

        # Add runs for the figure label and number
        run = par.add_run(self.figure_label)
        # This ``#`` is a placeholder Word will replace with the figure's number
        run = par.add_run("#")

        # Close the  field character run
        run = par.add_run()
        r = run._r
        fldChar = OxmlElement("w:fldChar")
        fldChar.set(qn("w:fldCharType"), "end")
        r.append(fldChar)


class ListTracking:
    """
    Tracks a list being created, and creates the abstract and concrete ooxml numbering for it
    """

    def __init__(self):
        self.paragraphs = []
        self.level_list_is_ordered = []

    @staticmethod
    def q_w(tag):
        return etree.QName("http://schemas.openxmlformats.org/wordprocessingml/2006/main", tag)

    def add_paragraph(self, pg, level: int, is_ordered: bool):
        """
        Adds a paragraph to the list, tracking the list level and ordered/unordered type
        """
        if level > len(self.level_list_is_ordered):
            raise Exception(
                "Tried to add level {} to a list with {} existing levels".format(level, len(self.level_list_is_ordered))
            )
        if level == len(self.level_list_is_ordered):
            self.level_list_is_ordered.append(is_ordered)
        self.paragraphs.append((pg, level))

    def create(self, doc, cache):
        """
        Creates the numbering, if needed, and assigns it to each of the paragraphs registered by `add_paragraph`.
        """
        # Finalize the list into a tuple, which is hashable.
        # Technically an abuse of a tuple, but Python has no built-in immutable sequence types
        level_list_is_ordered = tuple(self.level_list_is_ordered)
        if level_list_is_ordered in cache:
            # Re-use the numbering
            numbering_id = cache[level_list_is_ordered]
        else:
            # Create a new numbering
            numbering = doc.part.numbering_part.numbering_definitions._numbering
            last_used_id = max((int(id) for id in numbering.xpath("w:abstractNum/@w:abstractNumId")), default=-1)
            abstract_numbering_id = last_used_id + 1

            abstract_numbering = numbering.makeelement(self.q_w("abstractNum"))
            abstract_numbering.set(self.q_w("abstractNumId"), str(abstract_numbering_id))

            multi_level_type = abstract_numbering.makeelement(self.q_w("multiLevelType"))
            multi_level_type.set(self.q_w("val"), "hybridMultilevel")
            abstract_numbering.append(multi_level_type)

            for level_num, is_ordered in enumerate(level_list_is_ordered):
                # TODO: vary bullets or numbers based on level
                level = abstract_numbering.makeelement(self.q_w("lvl"))
                level.set(self.q_w("ilvl"), str(level_num))

                start = level.makeelement(self.q_w("start"))
                start.set(self.q_w("val"), "1")
                level.append(start)

                num_fmt = level.makeelement(self.q_w("numFmt"))
                lvl_text = level.makeelement(self.q_w("lvlText"))
                if is_ordered:
                    num_fmt.set(self.q_w("val"), "decimal")
                    lvl_text.set(self.q_w("val"), "%{}.".format(level_num + 1))
                else:
                    num_fmt.set(self.q_w("val"), "bullet")
                    lvl_text.set(self.q_w("val"), "")
                    # lvl_text.set(self.q_w("val"), "X")
                level.append(num_fmt)
                level.append(lvl_text)

                prp = level.makeelement(self.q_w("pPr"))
                ind = prp.makeelement(self.q_w("ind"))
                ind.set(self.q_w("left"), str((level_num + 1) * 720))
                ind.set(self.q_w("hanging"), "360")
                prp.append(ind)
                level.append(prp)

                if not is_ordered:
                    rpr = level.makeelement(self.q_w("rPr"))
                    fonts = rpr.makeelement(self.q_w("rFonts"))
                    fonts.set(self.q_w("ascii"), "Symbol")
                    fonts.set(self.q_w("hAnsi"), "Symbol")
                    fonts.set(self.q_w("hint"), "default")
                    rpr.append(fonts)
                    level.append(rpr)

                abstract_numbering.append(level)

            numbering.insert(0, abstract_numbering)
            numbering_id = numbering.add_num(abstract_numbering_id).numId
            cache[level_list_is_ordered] = numbering_id

        for par, level in self.paragraphs:
            par._p.get_or_add_pPr().get_or_add_numPr().get_or_add_numId().val = numbering_id
            par._p.get_or_add_pPr().get_or_add_numPr().get_or_add_ilvl().val = level
