
import logging
import re
import bs4
import jinja2

from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter import jinja_funcs

logger = logging.getLogger(__name__)


class ReportExportError(Exception):
    """
    Error related to report generation.

    Usually wraps another error (via `raise ReportExportError() from exc`), annotating where the error occurred
    during report generation.

    Generally you should catch `ReportExportTemplateError` instead.
    """

    # Error message
    display_text: str
    # Description of the object where the error occurred, such as "the finding's description", if known
    location: str | None
    # The code near the source of the error, if known
    code_context: str | None

    def __init__(self, display_text: str, location: str | None = None, code_context: str | None = None):
        self.display_text = display_text
        self.location = location
        self.code_context = code_context

    def __str__(self) -> str:
        text = self.display_text
        ends_with_period = text.rstrip()[-1:] == "."

        if self.location:
            if ends_with_period:
                text += " Occurred in "
            else:
                text += " in "
            text += self.location

        if self.code_context:
            if self.location:
                text += ", near `"
            elif ends_with_period:
                text += " Occurred near `"
            else:
                text += " near `"
            text += self.code_context
            text += "`"

        return text

class ReportExportTemplateError(ReportExportError):
    """
    User-facing error related to report generation
    """

    @classmethod
    def map_errors(cls, callback, location: str | None = None):
        """
        Runs `callback` with no arguments, translating errors to `ReportTemplateError`s.

        Catches some Jinja-related errors and translates them to user-facing `ReportExportTemplateError`s.
        Other errors are translated to `ReportExportError`. Adds `location` info to any raised `ReportExportError`s
        that don't have it.
        """
        try:
            return callback()
        except ReportExportError as err:
            if location and not err.location:
                err.location = location
            raise
        except jinja2.TemplateSyntaxError as err:
            raise ReportExportTemplateError(f"Template syntax error: {err}", location) from err
        except jinja2.UndefinedError as err:
            raise ReportExportTemplateError(f"Template syntax error: {err}", location) from err
        except InvalidFilterValue as err:
            raise ReportExportTemplateError(f"Invalid filter value: {err.message}", location) from err
        except jinja2.TemplateError as err:
            raise ReportExportTemplateError(f"Template error: {err}", location) from err
        except ZeroDivisionError as err:
            raise ReportExportTemplateError("Template attempted to divide by zero", location) from err
        except TypeError as err:
            logger.exception("Template TypeError, may be a bug or an issue with the template")
            raise ReportExportTemplateError(f"Invalid template operation: {err}", location) from err
        except Exception as err:
            raise ReportExportError(str(err), location) from err

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
            raise ReportExportTemplateError(f"Jinja tag prefixed with '{prefix}' was not a descendant of a {prefix} tag", code_context=line)

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

    text = re.sub(r"\{\{\.([^\{\}]*)\}\}", replace_old_tag, text)

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
    try:
        return env.from_string(text)
    except jinja2.TemplateSyntaxError as err:
        line = text.splitlines()[err.lineno - 1]
        raise ReportExportTemplateError(str(err), code_context=line) from err
