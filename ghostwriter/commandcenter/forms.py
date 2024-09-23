"""This contains all the forms used by the CommandCenter application."""

import logging

# Django Imports
from typing import Iterable, Iterator, Tuple
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

from crispy_forms.helper import FormHelper
from crispy_forms.layout import Layout, Field, ButtonHolder, Submit, HTML

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import ReportConfiguration, ExtraFieldSpec
from ghostwriter.modules.reportwriter.project.base import ExportProjectBase
from ghostwriter.modules.reportwriter.report.base import ExportReportBase

logger = logging.getLogger(__name__)


class ReportConfigurationForm(forms.ModelForm):
    """Save settings in :model:`commandcenter.ReportConfiguration`."""

    class Meta:
        model = ReportConfiguration
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Set `strip=False` for all fields to preserve whitespace so values like " — " for prefixes are not trimmed
        self.fields["prefix_figure"].strip = False
        self.fields["label_figure"].strip = False
        self.fields["prefix_table"].strip = False
        self.fields["label_table"].strip = False

    def clean_default_docx_template(self):
        docx_template = self.cleaned_data["default_docx_template"]
        if docx_template:
            docx_template_status = docx_template.get_status()
            if docx_template_status in ("error", "failed"):
                raise ValidationError(
                    _("Your selected Word template failed linting and cannot be used as a default template"),
                    "invalid",
                )
        return docx_template

    def clean_default_pptx_template(self):
        pptx_template = self.cleaned_data["default_pptx_template"]
        if pptx_template:
            pptx_template_status = pptx_template.get_status()
            if pptx_template_status in ("error", "failed"):
                raise ValidationError(
                    _("Your selected PowerPoint template failed linting and cannot be used as a default template"),
                    "invalid",
                )
        return pptx_template

    def clean_report_filename(self):
        name_template = self.cleaned_data["report_filename"]
        ExportReportBase.check_filename_template(name_template)
        return name_template

    def clean_project_filename(self):
        name_template = self.cleaned_data["project_filename"]
        ExportProjectBase.check_filename_template(name_template)
        return name_template


# Marker object to signal ExtraFieldsWidget to use the admin-configured defaults in the DB rather than loading from a value.
#
# Ideally, we'd load those and set them as the field's initial value. But Django throws an error if we try to access the DB
# in the field's __init__ method. So instead, pass this object as initial - if the form is unbound, Django will pass this
# to the widget's get_context method and the widget detects that.
EXTRA_FIELDS_USE_DB_INITIAL = object()


class ExtraFieldsWidget(forms.Widget):
    template_name = "user_extra_fields/widget.html"
    use_fieldset = True

    model_label: str
    _fields_specs_cache: Iterable[ExtraFieldSpec] | None

    def __init__(self, model_label: str, attrs=None):
        super().__init__(attrs)
        self.model_label = model_label
        self._fields_specs_cache = None

    def _field_specs(self) -> Iterable[ExtraFieldSpec]:
        """
        Gets and caches the field specifications for the field
        """
        if self._fields_specs_cache is not None:
            return self._fields_specs_cache
        fields_spec = ExtraFieldSpec.objects.filter(target_model=self.model_label)
        self._fields_specs_cache = fields_spec
        return fields_spec

    def _widgets(self, name: str) -> Iterator[Tuple[str, forms.Widget, ExtraFieldSpec]]:
        """
        Creates widgets for the field
        """
        for spec in self._field_specs():
            widget = spec.form_widget()
            widget_name = "{}_{}".format(name, spec.internal_name)
            yield (widget_name, widget, spec)

    @property
    def is_hidden(self):
        # Hide field if there are no extra fields
        fields = self._field_specs()
        return not fields

    def get_context(self, name, value, attrs):
        context = super().get_context(name, value, attrs)
        if value is None:
            value = {}

        subwidgets = []
        final_attrs = context["widget"]["attrs"]
        id_ = final_attrs.get("id")

        for widget_name, widget, spec in self._widgets(name):
            if value is EXTRA_FIELDS_USE_DB_INITIAL:
                widget_value = spec.initial_value()
            else:
                widget_value = value.get(spec.internal_name)
            if id_:
                widget_attrs = final_attrs.copy()
                widget_attrs["id"] = "{}_{}".format(id_, spec.internal_name)
            else:
                widget_attrs = final_attrs

            widget_attrs.setdefault("class", "")
            # Append `mb3` to the class list to add a margin below the field
            widget_attrs["class"] += " mb-3"
            # Add any classes from the widget
            if "class" in widget.attrs:
                widget_attrs["class"] += " " + widget.attrs["class"]

            widget_ctx = widget.get_context(widget_name, widget_value, widget_attrs)["widget"]

            subwidgets.append(
                {
                    "label": spec.display_name,
                    "description": spec.description,
                    "widget": widget_ctx,
                }
            )

        context["widget"]["subwidgets"] = subwidgets
        return context

    def value_from_datadict(self, data, files, name):
        value = {}
        for widget_name, widget, spec in self._widgets(name):
            value[spec.internal_name] = widget.value_from_datadict(data, files, widget_name)
        return value

    def value_omitted_from_data(self, data, files, name):
        for widget_name, widget, _spec in self._widgets(name):
            if not widget.value_omitted_from_data(data, files, widget_name):
                return False
        return True


class ExtraFieldsField(forms.Field):
    widget = ExtraFieldsWidget

    model_label: str
    _field_spec_cache: Iterable[ExtraFieldSpec] | None

    def __init__(self, model_label: str, *args, **kwargs) -> None:
        if "widget" not in kwargs:
            kwargs["widget"] = ExtraFieldsWidget(model_label)
        if "required" not in kwargs:
            kwargs["required"] = False
        if "initial" not in kwargs:
            kwargs["initial"] = EXTRA_FIELDS_USE_DB_INITIAL
        super().__init__(*args, **kwargs)
        self.model_label = model_label
        self._field_spec_cache = None

    @property
    def specs(self):
        if self._field_spec_cache is None:
            self._field_spec_cache = ExtraFieldSpec.objects.filter(target_model=self.model_label)
        return self._field_spec_cache

    def validate(self, value):
        # Done in clean
        pass

    def prepare_value(self, value):
        if not isinstance(value, dict):
            return value
        new_value = {}
        for field_spec in self.specs:
            field_obj = field_spec.form_field()
            field_value = value.get(field_spec.internal_name)
            new_value[field_spec.internal_name] = field_obj.prepare_value(field_value)
        return new_value

    def clean(self, value):
        if value is None:
            value = {}

        errors = []
        clean_data = {}
        for field_spec in self.specs:
            field_obj = field_spec.form_field()
            try:
                clean_data[field_spec.internal_name] = field_obj.clean(value.get(field_spec.internal_name))
            except ValidationError as e:
                errors.extend(m for m in e.error_list if m not in errors)
        if errors:
            raise ValidationError(errors)

        self.validate(clean_data)
        self.run_validators(clean_data)
        return clean_data


class SingleExtraFieldForm(forms.Form):
    extra_field_spec: ExtraFieldSpec

    def __init__(self, field_spec: ExtraFieldSpec, *args, create_crispy_field=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.extra_field_spec = field_spec

        field = field_spec.form_field(initial=field_spec.initial_value())
        field.widget = field_spec.form_widget()
        self.fields[field_spec.internal_name] = field

        self.helper = FormHelper()
        self.helper.form_show_labels = True
        self.helper.form_method = "post"

        if create_crispy_field is not None:
            crispy_field = create_crispy_field(field_spec)
        else:
            crispy_field = Field(field_spec.internal_name)

        self.helper.layout = Layout(
            crispy_field,
            ButtonHolder(
                Submit("submit_btn", "Submit", css_class="btn btn-primary col-md-4"),
                HTML(
                    """
                    <button onclick="window.location.href='{{ cancel_link }}'" class="btn btn-outline-secondary col-md-4" type="button">Cancel</button>
                    """
                ),
            ),
        )
