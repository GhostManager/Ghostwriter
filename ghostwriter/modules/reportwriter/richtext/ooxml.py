# Standard Libraries
import logging
import re
import typing

# 3rd Party Libraries
import bs4

logger = logging.getLogger(__name__)


def set_style_method(tag_name, style_key, style_value=True):
    """
    Creates and returns a `tag_*` method that sets a value in the `styles` dict
    and then recurses into its children.
    """

    def tag_style(self, el, *, style={}, **kwargs):
        style = style.copy()
        style[style_key] = style_value
        self.process_children(el.children, style=style, **kwargs)

    tag_style.__name__ = "tag_" + tag_name
    return tag_style

class TextTracking:
    """
    Processes raw text nodes, stripping whitespaces and keeping track of segment breaks (runs of whitespace in the source
    text that may be translated to one whitespace during rendering).

    Ref: https://www.w3.org/TR/css-text-3/#white-space-processing
    """

    is_block_start: bool
    segment_break_run: typing.Any | None
    in_pre: bool

    RE_PART = re.compile(r"^\s+|^[^\s]+")

    def __init__(self) -> None:
        self.is_block_start = True
        self.segment_break_run = None
        self.in_pre = False

    def new_block(self):
        """
        Starts a new block. Whitespace between calling this and the first non-whitespace characters will be dropped,
        and any pending segment break will be canceled.
        """
        self.is_block_start = True
        self.segment_break_run = None

    def append_text_to_run(self, run, text: str):
        """
        Parses the source text and appends it with collapsed spaces to the passed in run.

        If the passed in source text ends in whitespace, the tracker will store the run, as it
        may need to append a space if later text contains non-space characters.
        """
        if self.in_pre:
            run.text = run.text + remove_invalid_xml_chars(text)
            return

        while text:
            match = self.RE_PART.search(text)
            if match[0].isspace():
                # Setup segment break
                if not self.is_block_start:
                    self.segment_break_run = run
            else:
                # Non-space text
                self.is_block_start = False
                self.force_emit_pending_segment_break()
                run.text = run.text + remove_invalid_xml_chars(match[0])
            text = text[match.end() :]

    def force_emit_pending_segment_break(self):
        """
        If there is a pending segment break, forcibly emits it as a space.

        Use this before adding inline content to a paragraph, so that a space between it and the previous text is properly inserted.
        """
        self.is_block_start = False
        if self.segment_break_run is not None:
            self.segment_break_run.text = self.segment_break_run.text + " "
            self.segment_break_run = None


class BaseHtmlToOOXML:
    """
    Base HTML to OpenOffice XML converter. Converts HTML from the TinyMCE rich
    text to various types of OpenXML documents.

    Use a subclass that matches the desired document type.
    """

    text_tracking: TextTracking

    def __init__(self):
        self.text_tracking = TextTracking()

    @classmethod
    def run(cls, text: str, *args, **kwargs):
        """
        Parses the `text` as HTML and runs the class over the tree.
        Extra parameters are passed to the class's `__init__`.
        """
        soup = bs4.BeautifulSoup(text, "lxml")
        tag = soup.find("body")
        instance = cls(*args, **kwargs)
        if tag is not None:
            instance.process_children(tag.children)
        return instance

    def process(self, el, **kwargs):
        if el.name:
            if hasattr(self, "tag_" + el.name):
                getattr(self, "tag_" + el.name)(el, **kwargs)
            else:
                logger.warning("Unimplemented tag: %s, skipping", el.name)
        else:
            self.text(el, **kwargs)

    def process_children(self, children_iterable, **kwargs):
        for ch in children_iterable:
            self.process(ch, **kwargs)

    def text(self, el, *, par=None, style=None, **kwargs):
        if par is None:
            # Text without a paragraph. If this is just some trailing whitespace, ignore it, otherwise
            # report an error.
            if el.strip():
                raise ValueError(
                    "found text node that was not enclosed in a paragraph or other block item: {!r}".format(el.text)
                )
            return
        run = par.add_run()
        self.text_tracking.append_text_to_run(run, el)
        self.style_run(run, style or {})

    def style_run(self, run, style):
        """
        Called by the default `text` method to style a run. Overridable to
        extend with additional styles.
        """
        if style.get("bold"):
            run.font.bold = True
        if style.get("italic"):
            run.font.italic = True
        if style.get("underline"):
            run.font.underline = True
        if style.get("font_family"):
            run.font.name = style["font_family"]
        if style.get("font_size"):
            try:
                run.font.size = int(style["font_size"])
            except ValueError:
                pass

    tag_code = set_style_method("code", "inline_code")
    tag_b = set_style_method("b", "bold")
    tag_strong = set_style_method("strong", "bold")
    tag_i = set_style_method("i", "italic")
    tag_em = set_style_method("em", "italic")
    tag_u = set_style_method("u", "underline")
    tag_sub = set_style_method("sub", "subscript")
    tag_sup = set_style_method("sup", "superscript")
    tag_del = set_style_method("del", "strikethrough")

    def tag_a(self, el, *, style={}, **kwargs):
        style = style | {"hyperlink_url": el.attrs.get("href")}
        self.process_children(el.children, style=style, **kwargs)

    def tag_span(self, el, *, style={}, **kwargs):
        style = style.copy()

        # Parse and check classes
        classes = el.attrs.get("class", [])
        for cls in ["italic", "bold", "underline", "highlight"]:
            if cls in classes:
                style[cls] = True

        def handle_style(key, value):
            if key == "font-size":
                style["font_size"] = float(value.replace("pt", ""))
            elif key == "font-family":
                font_list = value.split(",")
                priority_font = font_list[0].replace("'", "").replace('"', "").strip()
                style["font_family"] = priority_font
            elif key in ("color", "background-color"):
                value = value.replace("#", "")
                r, g, b = (int(value[i * 2 : i * 2 + 2], 16) for i in range(3))
                if key == "color":
                    style["font_color"] = (r, g, b)
                else:
                    style["background_color"] = (r, g, b)

        parse_styles(el.attrs.get("style", ""), handle_style)

        self.process_children(el.children, style=style, **kwargs)

    def tag_mark(self, el, *, style={}, **kwargs):
        style = style.copy()
        style["highlight"] = True
        self.process_children(el.children, style=style, **kwargs)

    def tag_table(self, el, **kwargs):
        self.text_tracking.new_block()
        table_width, table_height = self._table_size(el)
        ooxml_table = self.create_table(rows=table_height, cols=table_width, **kwargs)

        merged_cells = set()
        row_el_iter = self._table_rows(el)
        for row_i in range(table_height):
            # Get next row, if any. May not have any if the rowspan of a cell exceeds the number of specified rows.
            row_el = next(row_el_iter, None)
            col_el_iter = self._table_row_columns(row_el) if row_el is not None else iter([])

            for col_i in range(table_width):
                if (row_i, col_i) in merged_cells:
                    # Part of another cell, skip
                    continue

                cell_el = next(col_el_iter, None)
                if cell_el is None:
                    # No td for this cell, ignore
                    continue

                cell = ooxml_table.cell(row_i, col_i)

                rowspan = max(1, int(cell_el.attrs.get("rowspan", 1)))
                colspan = max(1, int(cell_el.attrs.get("colspan", 1)))

                if rowspan > 1 or colspan > 1:
                    # Merged cell, merge it in the document and mark that those cells have been merged
                    corner_cell = ooxml_table.cell(row_i + rowspan - 1, col_i + colspan - 1)
                    cell.merge(corner_cell)
                    for row_j in range(rowspan):
                        for col_j in range(colspan):
                            merged_cells.add((row_i + row_j, col_i + col_j))

                self.text_tracking.new_block()
                par = self.paragraph_for_table_cell(cell, cell_el)
                self.process_children(cell_el.children, par=par, **kwargs)

    def tag_div(self, el, **kwargs):
        classes = el.attrs.get("class", [])
        if "collab-table-wrapper" in classes:
            table = el.find("table")
            caption_el = el.find(class_="collab-table-caption-content")
            caption_bookmark_el = el.find(class_="collab-table-caption")
            caption_bookmark = caption_bookmark_el.attrs.get("data-bookmark") if caption_bookmark_el is not None else None
            self.tag_table(
                table,
                caption_el=caption_el,
                caption_bookmark=caption_bookmark,
                **kwargs,
            )
        else:
            logger.warning("Don't know how to handle div: %s", el)

    @staticmethod
    def _table_rows(table_el):
        for item in table_el.children:
            if item.name == "tr":
                yield item
            elif item.name in ("thead", "tbody", "tfoot"):
                for subitem in item:
                    if subitem.name == "tr":
                        yield subitem

    @staticmethod
    def _table_row_columns(table_el):
        return (item for item in table_el.children if item.name in ("td", "th"))

    @staticmethod
    def _table_size(table_el):
        max_width = 0
        max_height = 0
        for row_i, row in enumerate(BaseHtmlToOOXML._table_rows(table_el)):
            row_width = 0
            row_height = 1
            for col in BaseHtmlToOOXML._table_row_columns(row):
                row_width += max(1, int(col.attrs.get("colspan", "1")))
                row_height = max(row_height, int(col.attrs.get("rowspan", "1")))
            max_width = max(max_width, row_width)
            max_height = max(max_height, row_i + row_height)
        return (max_width, max_height)

    def create_table(self, rows, cols, **kwargs):
        """
        Creates a table with the specified number of rows and columns. Additional arguments passed to `tag_table` are also passed here.
        """
        raise NotImplementedError()

    def paragraph_for_table_cell(self, cell, td_el):
        """
        Gets the ooxml paragraph for a table cell to add contents to.

        This may also style the cell's paragraph if desired, using the passed in `td_el` item.
        """
        raise NotImplementedError()


def strip_text_whitespace(text: str):
    """
    Consolidates adjacent whitespace into one space, similar to how browsers display it
    """
    return re.sub(r"\s+", " ", text)


def parse_styles(style: str, handle):
    """
    Does rough parsing of a `style` attribute, calling `handle(key,value)` and catching/ignoring any `ValueError` it throws.
    """
    for style_line in style.split(";"):
        if not style_line.strip():
            continue
        try:
            key, value = style_line.split(":")
            key = key.strip()
            value = value.strip()
        except IndexError:
            # Invalid input
            pass
        try:
            handle(key, value)
        except ValueError:
            # Invalid input
            pass

def remove_invalid_xml_chars(text: str) -> str:
    return "".join(c for c in text if _valid_xml_char_ordinal(c))

def _valid_xml_char_ordinal(c: str):
    """
    Checks if the character is valid to include in XML.

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
