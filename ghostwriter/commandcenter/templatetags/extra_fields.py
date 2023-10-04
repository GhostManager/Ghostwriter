# Django Imports
from django import template

from ghostwriter.commandcenter.models import ExtraFieldSpec

register = template.Library()


@register.filter
def display_extra_field(extra_fields: dict, spec: ExtraFieldSpec):
    value = extra_fields.get(spec.internal_name, None)
    return spec.value_to_html_context(value)
