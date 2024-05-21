
import re
import bs4
import jinja2

from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter import jinja_funcs


class ReportExportError(Exception):
    """
    User-facing error related to report generation
    """
    def __init__(self, display_text: str, location: str | None = None):
        self.display_text = display_text
        self.location = location

    def __str__(self) -> str:
        return self.display_text

    def at_error(self) -> str:
        """
        If the error has a `location` field, returns a string `" at {the_location}"`, else returns the empty string.
        """
        if self.location is None:
            return ""
        return f" at {self.location}"

    @classmethod
    def map_jinja2_render_errors(cls, callback, location: str | None = None):
        """
        Runs `callback` with no arguments, catching any Jinja-related exceptions and translating them to `ReportSyntaxError`s
        while noting the `location`.
        """
        try:
            return callback()
        except jinja2.TemplateSyntaxError as err:
            raise ReportExportError(f"Template syntax error: {err}", location) from err
        except jinja2.UndefinedError as err:
            raise ReportExportError(f"Template syntax error: {err}", location) from err
        except InvalidFilterValue as err:
            raise ReportExportError(f"Invalid filter value: {err.message}", location) from err
        except jinja2.TemplateError as err:
            raise ReportExportError(f"Template error: {err}", location) from err
        except ZeroDivisionError as err:
            raise ReportExportError("Template attempted to divide by zero", location) from err
        except TypeError as err:
            raise ReportExportError(f"Invalid template operation: {err}", location) from err


def _process_prefix(input_str: str, soup: bs4.BeautifulSoup, prefix: str):
    """
    Converts text nodes of the form `{%prefix someop %}` and replaces its parent `prefix` tag with `{% someop %}`
    in the passed-in soup.
    """

    regex = re.compile(r"^\s*(\{%|\{\{)\s*" + re.escape(prefix) + r"\b(.*)(%\}|\}\})\s*$")
    # Store in list since we mutate the nodes
    matching_strings = list(soup.find_all(string=regex))
    for node in matching_strings:
        # Find parent to strip out
        parent_tag = None
        for parent in node.parents:
            if parent.name == prefix:
                parent_tag = parent
                break
        if parent_tag is None:
            line = input_str.splitlines()[node.parent.sourceline - 1]
            raise ReportExportError(f"Jinja tag prefixed with '{prefix}' was not a descendant of a {prefix} tag, in line `{line}`")

        capture = regex.search(node)
        parent_tag.replace_with(capture.group(1) + capture.group(2) + capture.group(3))


def rich_text_template(env: jinja2.Environment, text: str) -> jinja2.Template:
    """
    Converts rich text `text` to a Jinja template. This does some additional Ghostwriter-specific
    processing.
    """
    # Replace old `{{.item}}`` syntax with jinja templates or elements to replace
    def replace_old_tag(match: re.Match):
        contents = match.group(1).strip()
        # These will be swapped out when parsing the HTML
        if contents.startswith("ref "):
            return jinja_funcs.ref(contents[4:].strip())
        elif contents == "caption":
            return jinja_funcs.caption("")
        elif contents.startswith("caption "):
            return jinja_funcs.caption(contents[8:].strip())
        return "{{ _old_dot_vars[" + repr(contents.strip()) + "]}}"

    text = re.sub(r"\{\{\.(.*?)\}\}", replace_old_tag, text)

    # Replace page breaks with something that the parser can easily pick up
    text = text.replace(
        "<p><!-- pagebreak --></p>", '<br data-gw-pagebreak="true" />'
    )

    # Replace `{%li foreach %}`-esque prefixes. This is similar to what python-docx-template does.
    soup = bs4.BeautifulSoup(text, "html.parser")
    _process_prefix(text, soup, "li")
    _process_prefix(text, soup, "p")
    _process_prefix(text, soup, "tr")
    _process_prefix(text, soup, "td")
    text = str(soup)

    # Compile
    return env.from_string(text)
