
from django import forms

import jinja2

from ghostwriter.modules.reportwriter import prepare_jinja2_env


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
            env.from_string(value)
        except jinja2.TemplateSyntaxError as e:
            line = value.splitlines()[e.lineno - 1]
            raise forms.ValidationError(f"{e} at `{line}`") from e
