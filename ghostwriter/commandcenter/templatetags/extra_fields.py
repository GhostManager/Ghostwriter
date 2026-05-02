
import json

# Django Imports
from django import template
from django.utils.encoding import force_str

from ghostwriter.commandcenter.models import ExtraFieldSpec

register = template.Library()


def _coerce_rich_text_value(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    try:
        return json.dumps(value, indent="\t")
    except (TypeError, ValueError):
        return force_str(value)


@register.filter
def get_extra_field(extra_fields: dict, spec: ExtraFieldSpec):
    value = spec.value_of(extra_fields)
    if spec.type == "rich_text":
        return _coerce_rich_text_value(value)
    return value


@register.filter
def json_pretty(obj):
    return json.dumps(obj, indent="\t")
