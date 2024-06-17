
from django import forms

from ghostwriter.modules.reportwriter import prepare_jinja2_env
from ghostwriter.modules.reportwriter.base import ReportExportError, rich_text_template


class JinjaRichTextField(forms.CharField):
    """
    CharField that checks its contents to see if it's a valid Jinja2 filter.
    """
    def __init__(self, *args, **kwargs):
        if "widget" not in kwargs:
            kwargs["widget"] = forms.Textarea
        super().__init__(*args, **kwargs)

    def validate(self, value: str):
        super().validate(value)
        env, _ = prepare_jinja2_env(debug=True)
        try:
            ReportExportError.map_jinja2_render_errors(lambda: rich_text_template(env, value))
        except ReportExportError as e:
            raise forms.ValidationError(str(e)) from e
