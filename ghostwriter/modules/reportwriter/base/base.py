
from datetime import datetime
import io
from typing import Any, Iterable
import re
from venv import logger

from django.forms import ValidationError
import jinja2
from django.db.models import Model

from ghostwriter.commandcenter.models import CompanyInformation, ExtraFieldSpec
from ghostwriter.modules.exceptions import InvalidFilterValue
from ghostwriter.modules.reportwriter import prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import rich_text_template


class ExportBase:
    """
    Base class for exporting things.

    Subclasses should prove a `run` method, and optionally `serialize_object`.

    Users should instantiate the object then call `run` to generate a `BytesIO` containing the exported
    file. Instances should not be re-used.

    Fields:

    * `input_object`: The object passed into `__init__`, unchanged
    * `data`: The object passed into `__init__` ran through `serialize_object`, usually a dict, for passing into a Jinja env
    * `jinja_env`: Jinja2 environment for templating
    """
    input_object: Any
    data: Any
    jinja_env: jinja2.Environment
    jinja_undefined_variables: set[str] | None
    extra_fields_spec_cache: dict[str, Iterable[ExtraFieldSpec]]

    def __init__(self, input_object: Any, *, is_raw=False, jinja_debug=False):
        if jinja_debug:
            self.jinja_env, self.jinja_undefined_variables = prepare_jinja2_env(debug=True)
        else:
            self.jinja_env = prepare_jinja2_env(debug=False)
            self.jinja_undefined_variables = None
        if is_raw:
            self.input_object = None
            self.data = input_object
        else:
            self.input_object = input_object
            self.data = self.serialize_object(input_object)
        self.extra_fields_spec_cache = {}

    def serialize_object(self, object: Any) -> Any:
        """
        Called by __init__ to serialize the input object to a format appropriate for use in a jinja environment.

        By default does nothing and returns `object` unchanged.
        """
        return object

    def extra_field_specs_for(self, model: Model) -> Iterable[ExtraFieldSpec]:
        """
        Gets (and caches) the set of extra fields for a model class.
        """
        label = model._meta.label
        if label in self.extra_fields_spec_cache:
            return self.extra_fields_spec_cache[label]
        specs = ExtraFieldSpec.objects.filter(target_model=label)
        self.extra_fields_spec_cache[label] = specs
        return specs

    def preprocess_rich_text(self, text: str, template_vars: Any):
        """
        Does jinja and `{{.item}}` substitutions on rich text, in preparation for feeding into the
        `BaseHtmlToOOXML` subclass.
        """
        text_rendered = rich_text_template(self.jinja_env, text).render(template_vars)
        # Filter out XML-incompatible characters
        text_char_filtered = "".join(c for c in text_rendered if _valid_xml_char_ordinal(c))
        return text_char_filtered

    def run(self) -> io.BytesIO:
        raise NotImplementedError()

    @classmethod
    def mime_type(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def extension(cls) -> str:
        raise NotImplementedError()

    @classmethod
    def generate_lint_data(cls):
        raise NotImplementedError()

    @classmethod
    def check_filename_template(cls, filename_template: str):
        exporter = cls(
            cls.generate_lint_data(),
            is_raw=True,
            jinja_debug=True,
        )
        try:
            exporter.render_filename(filename_template, ext="test")
        except jinja2.TemplateError as e:
            raise ValidationError(str(e)) from e
        except TypeError as e:
            logger.exception("TypeError while validating report filename. May be a syntax error or an actual error.")
            raise ValidationError(str(e)) from e

    def render_filename(self, filename_template, ext=None):
        """
        Generate a filename for an export, rendering the `filename_template` with
        the jinja data and appending the extension.
        """

        data = self.data.copy()
        data["company_name"] = CompanyInformation.get_solo().company_name
        data["now"] = datetime.now()

        report_name = ReportExportError.map_jinja2_render_errors(
            lambda: self.jinja_env.from_string(filename_template).render(data),
            "the template filename"
        )

        report_name = _replace_filename_chars(report_name)
        if ext is None:
            ext = self.extension()
        return report_name.strip() + "." + ext


def _valid_xml_char_ordinal(c):
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


def _replace_filename_chars(name):
    """Remove illegal characters from the report name."""
    name = name.replace("–", "-")
    return re.sub(r"[<>:;\"'/\\|?*.,{}\[\]]", "", name)


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
