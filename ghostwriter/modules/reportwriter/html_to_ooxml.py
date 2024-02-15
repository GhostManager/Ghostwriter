# Standard Libraries
import logging
import re

# 3rd Party Libraries
import bs4

logger = logging.getLogger(__name__)


def set_style_method(tag_name, style_key, style_value=True):
    """
    Creates and returns a `tag_*` method that sets a value in the `styles` dict
    and then recurses into its children.
    """

    def tag_style(self, el, style={}, **kwargs):
        style = style.copy()
        style[style_key] = style_value
        self.process_children(el.children, style=style, **kwargs)

    tag_style.__name__ = "tag_" + tag_name
    return tag_style


class BaseHtmlToOOXML:
    """
    Base HTML to OpenOffice XML converter. Converts HTML from the TinyMCE rich
    text to various types of OpenXML documents.

    Use a subclass that matches the desired document type.
    """

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

    def text(self, el, par=None, style=None, **kwargs):
        if par is None:
            # Text without a paragraph. If this is just some trailing whitespace, ignore it, otherwise
            # report an error.
            if el.text.strip():
                raise ValueError(
                    "found text node that was not enclosed in a paragraph or other block item: {!r}".format(el.text)
                )
            else:
                return
        text = self.strip_text_whitespace(el.text)
        if not text:
            return
        run = par.add_run()
        run.text = text
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
            run.font.size = "font_size"

    def strip_text_whitespace(self, text):
        """
        Consolidates adjacent whitespace into one space, similar to how browsers display it
        """
        return re.sub(r"\s+", " ", text)

    tag_code = set_style_method("code", "inline_code")
    tag_b = set_style_method("b", "bold")
    tag_strong = set_style_method("strong", "bold")
    tag_i = set_style_method("i", "italic")
    tag_em = set_style_method("em", "italic")
    tag_u = set_style_method("u", "underline")
    tag_sub = set_style_method("sub", "subscript")
    tag_sup = set_style_method("sup", "superscript")
    tag_del = set_style_method("del", "strikethrough")

    def tag_a(self, el, style={}, **kwargs):
        style = style | {"hyperlink_url": el.attrs.get("href")}
        self.process_children(el.children, style=style, **kwargs)

    def tag_span(self, el, style={}, **kwargs):
        style = style.copy()

        # Parse and check classes
        classes = el.attrs.get("class", [])
        for cls in ["italic", "bold", "underline", "highlight"]:
            if cls in classes:
                style[cls] = True

        # Parse and check styles
        for style_line in el.attrs.get("style", "").split(";"):
            if not style_line.strip():
                continue
            try:
                key, value = style_line.split(":")
                key = key.strip()
                value = value.strip()

                if key == "font-size":
                    style["font_size"] = float(value.replace("pt", ""))
                elif key == "font-family":
                    font_list = value.split(",")
                    priority_font = font_list[0].replace("'", "").replace('"', "").strip()
                    style["font_family"] = priority_font
                elif key == "color" or key == "background-color":
                    value = value.replace("#", "")
                    r, g, b = (int(value[i * 2 : i * 2 + 2], 16) for i in range(3))
                    if key == "color":
                        style["font_color"] = (r, g, b)
                    else:
                        style["background_color"] = (r, g, b)

            except (ValueError, IndexError):
                # Invalid input
                pass

        self.process_children(el.children, style=style, **kwargs)

    def tag_table(self, el, **kwargs):
        table_width, table_height = self._table_size(el)
        ooxml_table = self.create_table(rows=table_height, cols=table_width, **kwargs)

        ooxml_table.autofit = True
        for row in ooxml_table.rows:
            for cell in row.cells:
                tc = cell._tc
                tcPr = tc.get_or_add_tcPr()
                tcW = tcPr.get_or_add_tcW()
                tcW.type = "auto"

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

                par = self.paragraph_for_table_cell(cell)
                self.process_children(cell_el.children, par=par, **kwargs)

    @staticmethod
    def _table_rows(table_el):
        for item in table_el.children:
            if item.name == "tr":
                yield item
            elif item.name is not None:
                # thead, tbody, tfoot
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
        raise NotImplementedError()

    def paragraph_for_table_cell(self, cell):
        raise NotImplementedError()
