
from typing import Any, Iterable
import re

import jinja2
from django.db.models import Model

from ghostwriter.commandcenter.models import ExtraFieldSpec
from ghostwriter.modules.reportwriter import jinja_funcs, prepare_jinja2_env


class ExportBase:
    data: Any
    jinja_env: jinja2.Environment
    extra_fields_spec_cache: dict[str, Iterable[ExtraFieldSpec]]

    def __init__(self, data: Any):
        self.jinja_env = prepare_jinja2_env(debug=False)
        self.data = data
        self.extra_fields_spec_cache = {}

    def extra_field_specs_for(self, model: Model) -> Iterable[ExtraFieldSpec]:
        """
        Gets (and caches) the set of extra fields for a model class.
        """
        label = model._meta.label
        if label in self.extra_fields_spec_cache:
            return self.extra_fields_spec_cache[label]
        else:
            specs = ExtraFieldSpec.objects.filter(target_model=label)
            self.extra_fields_spec_cache[label] = specs
            return specs

    def preprocess_rich_text(self, text: str, template_vars: Any):
        """
        Does jinja and `{{.item}}` substitutions on rich text, in preparation for feeding into the
        `BaseHtmlToOOXML` subclass.
        """

        if not text:
            return ""

        # Replace old `{{.item}}`` syntax with jinja templates or elements to replace
        def replace_old_tag(match: re.Match):
            contents = match.group(1).strip()
            # These will be swapped out when parsing the HTML
            if contents.startswith("ref "):
                return jinja_funcs.ref(contents[4:].strip())
            elif contents == "caption":
                return jinja_funcs.caption("")
            elif contents.startswith("caption "):
                return jinja_funcs.caption(contents[8:].strip())
            else:
                return "{{ _old_dot_vars[" + repr(contents.strip()) + "]}}"

        text_old_dot_subbed = re.sub(r"\{\{\.(.*?)\}\}", replace_old_tag, text)

        text_pagebrea_subbed = text_old_dot_subbed.replace(
            "<p><!-- pagebreak --></p>", '<br data-gw-pagebreak="true" />'
        )

        # Run template
        template = self.jinja_env.from_string(text_pagebrea_subbed)
        text_rendered = template.render(template_vars)

        # Filter out XML-incompatible characters
        text_char_filtered = "".join(c for c in text_rendered if _valid_xml_char_ordinal(c))
        return text_char_filtered


def _valid_xml_char_ordinal(c):
    """
    Clean string to make all characters XML compatible for Word documents.

    Source:
        https://stackoverflow.com/questions/8733233/filtering-out-certain-bytes-in-python

    **Parameters**

    ``c`` : string
        String of characters to validate
    """
    codepoint = ord(c)
    # Conditions ordered by presumed frequency
    return (
        0x20 <= codepoint <= 0xD7FF
        or codepoint in (0x9, 0xA, 0xD)
        or 0xE000 <= codepoint <= 0xFFFD
        or 0x10000 <= codepoint <= 0x10FFFF
    )
