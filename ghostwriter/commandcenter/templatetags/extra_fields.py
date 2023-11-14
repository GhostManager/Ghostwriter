# Django Imports
from django import template

from ghostwriter.commandcenter.models import ExtraFieldSpec

register = template.Library()


@register.filter
def get_extra_field(extra_fields: dict, spec: ExtraFieldSpec):
    return extra_fields.get(spec.internal_name, None) if extra_fields is not None else None
