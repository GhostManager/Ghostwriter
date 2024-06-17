# Django Imports
from django import template

from ghostwriter.commandcenter.models import ExtraFieldSpec

register = template.Library()


@register.filter
def get_extra_field(extra_fields: dict, spec: ExtraFieldSpec):
    return spec.value_of(extra_fields)
