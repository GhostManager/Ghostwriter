"""This contains all the forms used by the CommandCenter application."""

# Django Imports
from django import forms
from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _

# Ghostwriter Libraries
from ghostwriter.commandcenter.models import ReportConfiguration, ExtraFieldSpec


class ReportConfigurationForm(forms.ModelForm):
    """Save settings in :model:`commandcenter.ReportConfiguration`."""

    class Meta:
        model = ReportConfiguration
        fields = "__all__"

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


class ExtraFieldsWidget(forms.Widget):
    template_name = "user_extra_fields/widget.html"
    use_fieldset = True

    def __init__(self, model_label: str, attrs=None):
        super().__init__(attrs)
        self.model_label = model_label
        self._fields_spec_var = None

    def _field_specs(self):
        if self._fields_spec_var is not None:
            return self._fields_spec_var
        fields_spec = ExtraFieldSpec.objects.filter(target_model=self.model_label)
        self._fields_spec_var = fields_spec
        return fields_spec

    def _widgets(self, name):
        for spec in self._field_specs():
            widget = spec.form_widget()
            widget_name = "{}_{}".format(name, spec.internal_name)
            yield (widget_name, widget, spec)

    @property
    def is_hidden(self):
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
            widget_value = value.get(spec.internal_name)
            if id_:
                widget_attrs = final_attrs.copy()
                widget_attrs["id"] = "{}_{}".format(id_, spec.internal_name)
            else:
                widget_attrs = final_attrs

            widget_ctx = widget.get_context(widget_name, widget_value, widget_attrs)["widget"]

            subwidgets.append({
                "label": spec.display_name,
                "widget": widget_ctx,
            })

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

    def __init__(self, model_label: str, *args, **kwargs) -> None:
        if "widget" not in kwargs:
            kwargs["widget"] = ExtraFieldsWidget(model_label)
        if "required" not in kwargs:
            kwargs["required"] = False
        super().__init__(*args, **kwargs)
        self.model_label = model_label

    def validate(self, value):
        pass

    def clean(self, value):
        if value is None:
            value = {}

        field_specs = ExtraFieldSpec.objects.filter(target_model=self.model_label)
        errors = []
        clean_data = {}
        for field_spec in field_specs:
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
