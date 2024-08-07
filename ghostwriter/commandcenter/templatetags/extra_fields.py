
import json

# Django Imports
from django import template

from ghostwriter.commandcenter.models import ExtraFieldSpec

register = template.Library()


@register.filter
def get_extra_field(extra_fields: dict, spec: ExtraFieldSpec):
    return spec.value_of(extra_fields)


@register.filter
def json_pretty(obj):
    return json.dumps(obj, indent="\t")
