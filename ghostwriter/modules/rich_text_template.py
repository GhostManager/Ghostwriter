
import jinja2


class RichTextTemplate:
    source: str
    _template: jinja2.Template
    _model_location: str

    def __init__(self, source: str, template: jinja2.Template, model_location: str):
        self.source = source
        self._template = template
        self._model_location = model_location


