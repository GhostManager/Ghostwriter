
import logging
import re

import jinja2

from ghostwriter.modules.exceptions import InvalidFilterValue

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
        super().__init__(display_text)
        self.display_text = display_text
        self.location = location
        self.code_context = code_context

    def __str__(self) -> str:
        if not self.location and not self.code_context:
            return self.display_text

        text = self.display_text.rstrip()
        if text.endswith((".", "!", "?")):
            text += " The error occurred"

        if self.location:
            text += f" in {self.location}"

        if self.code_context:
            if self.location:
                text += ","
            text += f" near `{self.code_context}`"

        return f"{text}."

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
        except jinja2.exceptions.SecurityError as err:
            message = str(err)
            # Jinja reports a rejected call using the callable's repr. Its
            # wrappers for string format methods include a Python address.
            formatter = re.fullmatch(r"<function str\.(format(?:_map)?) at 0x[0-9a-fA-F]+> is not safely callable", message)
            if formatter:
                method = formatter[1]
                message = (
                    f"String method .{method}() is unavailable in report templates. "
                    f"Search for .{method} in the template. For simple substitutions, "
                    'use the Jinja |format filter with % placeholders, such as {{ "%s"|format(value) }}.'
                )
            elif message.endswith(" is not safely callable"):
                message = (
                    "A template expression calls an unsupported function or method. "
                    "Use a supported Ghostwriter template helper or Jinja filter."
                )
            elif message.startswith("access to attribute "):
                message = f"Template error: {message}"
            else:
                message = (
                    "The template uses an unsupported operation. "
                    "Review the template expressions and use supported Ghostwriter helpers or Jinja filters."
                )
            raise ReportExportTemplateError(message, location) from err
        except jinja2.TemplateError as err:
            raise ReportExportTemplateError(f"Template error: {err}", location) from err
        except ZeroDivisionError as err:
            raise ReportExportTemplateError("Template attempted to divide by zero", location) from err
        except TypeError as err:
            logger.exception("Template TypeError, may be a bug or an issue with the template")
            raise ReportExportTemplateError(f"Invalid template operation: {err}", location) from err
        except Exception as err:
            raise ReportExportError(str(err), location) from err
