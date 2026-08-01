# Standard Libraries
import io
import json
import logging
import re
from datetime import datetime
from typing import Any, Callable, Iterable

# Django Imports
from django.core.serializers.json import DjangoJSONEncoder
from django.db.models import Model
from django.forms import ValidationError

# 3rd Party Libraries
import jinja2

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import CompanyInformation, ExtraFieldSpec
from ghostwriter.modules.reportwriter import prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import (
    ReportExportError,
    ReportExportTemplateError,
)
from ghostwriter.modules.reportwriter.base.html_rich_text import (
    HtmlRichText,
    LazilyRenderedTemplate,
    rich_text_template,
)

logger = logging.getLogger(__name__)


def materialize_jinja_context(value: Any) -> Any:
    """Return a detached context containing only exact JSON primitive types."""
    try:
        return json.loads(json.dumps(value, cls=DjangoJSONEncoder))
    except (TypeError, ValueError) as exc:
        raise TypeError(
            "Jinja export contexts must contain only JSON-serializable values"
        ) from exc


class ExportBase:
    """
    Base class for exporting things.

    # Fields

    * `input_object`: The object passed into `__init__`, unchanged
    * `data`: The object passed into `__init__` run through the supplied serializer,
      usually a dict, for passing into a Jinja environment
    * `jinja_env`: Jinja2 environment for templating
    """
    input_object: Any
    data: Any
    jinja_env: jinja2.Environment
    jinja_undefined_variables: set[str] | None
    extra_fields_spec_cache: dict[str, Iterable[ExtraFieldSpec]]
    evidences_by_id: dict
    preview_extra_field_model_label: str | None
    preview_extra_field_name: str | None

    def __init__(
        self,
        input_object: Any,
        *,
        is_raw: bool = False,
        jinja_debug: bool = False,
        object_serializer: Callable[[Any], Any] | None = None,
    ):
        self.evidences_by_id = {}
        self.extra_fields_spec_cache = {}
        self.preview_extra_field_model_label = None
        self.preview_extra_field_name = None

        if jinja_debug:
            self.jinja_env, self.jinja_undefined_variables = prepare_jinja2_env(debug=True)
        else:
            self.jinja_env = prepare_jinja2_env(debug=False)
            self.jinja_undefined_variables = None
        if is_raw:
            self.input_object = None
            serialized_data = input_object
        else:
            self.input_object = input_object
            serialized_data = (
                object_serializer(input_object)
                if object_serializer is not None
                else input_object
            )
        self.data = materialize_jinja_context(serialized_data)

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

    def create_evidences_lookup(self, evidence_list, inherit_from: dict = None) -> dict:
        """
        Creates a dict that should be set to the rich text context's `"_evidences"` field.

        Adds the evidences in the `evidence_list` iter to the `evidences_by_id` map to
        allow later access.

        If `inherit_from` is not None, it's copied, and the evidences are placed into the copy.
        """
        out = inherit_from.copy() if inherit_from is not None else {}
        for evi in evidence_list:
            out[evi["friendly_name"]] = evi["id"]
            self.evidences_by_id[evi["id"]] = evi
        return out

    def create_lazy_template(
        self, location: str | None, text: str | None, context: dict, **kwargs
    ) -> LazilyRenderedTemplate:
        """
        Creates a `LazilyRenderedTemplate` that will `text` as a jinja template when needed.

        Implementations of `map_rich_texts` should call this on rich text fields, replacing the rich text field
        with its return value.
        """
        return LazilyRenderedTemplate(
            ReportExportTemplateError.map_errors(
                lambda: rich_text_template(self.jinja_env, text or "", **kwargs),
                location,
            ),
            location,
            context,
        )

    def process_extra_fields(self, location: str, extra_fields: dict, model, context: dict):
        """
        Process the `extra_fields` dict, filling missing extra fields with empty values and replacing
        rich texts with a `LazyRenderedTemplate`.
        """
        specs = self.extra_field_specs_for(model)
        for field in specs:
            if field.internal_name not in extra_fields:
                extra_fields[field.internal_name] = field.empty_value()
            if field.type == "rich_text":
                if (
                    self.preview_extra_field_model_label
                    and (
                        model._meta.label != self.preview_extra_field_model_label
                        or field.internal_name != self.preview_extra_field_name
                    )
                ):
                    continue
                extra_fields[field.internal_name] = self.create_lazy_template(
                    f"extra field {field.internal_name} of {location}",
                    str(extra_fields[field.internal_name]),
                    context,
                )

    def process_literal_extra_fields(
        self,
        location: str,
        extra_fields: dict,
        model,
    ):
        """
        Fill extra-field defaults without treating rich-text values as templates.

        This is used for data sources such as operation logs, whose values may
        contain Jinja payloads recorded during an assessment.
        """
        for field in self.extra_field_specs_for(model):
            if field.internal_name not in extra_fields:
                extra_fields[field.internal_name] = field.empty_value()
            if field.type == "rich_text":
                extra_fields[field.internal_name] = HtmlRichText(
                    str(extra_fields[field.internal_name]),
                    f"extra field {field.internal_name} of {location}",
                )

    def map_rich_texts(self):
        """
        Replaces rich text entries in `self.data` with `LazilyRenderedTemplate` or `HtmlAndRich` instances.
        """
        raise NotImplementedError()

    def run(self) -> io.BytesIO:
        raise NotImplementedError()

    @classmethod
    def mime_type(cls) -> str:
        """Gets the mime type of the result from `run`"""
        raise NotImplementedError()

    @classmethod
    def extension(cls) -> str:
        """Gets the file extension of the result from `run`, without the dot"""
        raise NotImplementedError()

    @classmethod
    def generate_lint_data(cls):
        """Gets the data to use for linting"""
        raise NotImplementedError()

    @classmethod
    def check_filename_template(cls, filename_template: str):
        """Checks if the filename Jinja template string can be formatted OK"""
        exporter = cls(
            cls.generate_lint_data(),
            is_raw=True,
            jinja_debug=True,
        )
        try:
            exporter.render_filename(filename_template, ext="test")
        except (jinja2.TemplateError, ReportExportError) as e:
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

        report_name = ReportExportTemplateError.map_errors(
            lambda: self.jinja_env.from_string(filename_template).render(data),
            "the template filename",
        )

        report_name = _replace_filename_chars(report_name)
        if ext is None:
            ext = self.extension()
        return report_name.strip() + "." + ext

    def bloodhound_heading_offset(self) -> int:
        """
        Number of levels to offset headers in the descriptions from BloodHound data. Default is zero.
        """
        return 0


def _replace_filename_chars(name):
    """Remove illegal characters from the report name."""
    name = name.replace("–", "-")
    return re.sub(r"[<>:;\"'/\\|?*.,{}\[\]]", "", name)
