import json
from django.template import Library

register = Library()

@register.filter
def json_enc(value):
    return json.dumps(value, indent="\t")
