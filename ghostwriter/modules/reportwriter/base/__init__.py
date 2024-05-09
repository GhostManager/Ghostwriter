
import re
import jinja2

from ghostwriter.modules.reportwriter import jinja_funcs


def rich_text_template(env: jinja2.Environment, text: str) -> jinja2.Template:
    """
    Converts rich text `text` to a Jinja template. This does some additional Ghostwriter-specific
    processing.
    """
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
        return "{{ _old_dot_vars[" + repr(contents.strip()) + "]}}"

    text_old_dot_subbed = re.sub(r"\{\{\.(.*?)\}\}", replace_old_tag, text)

    text_pagebrea_subbed = text_old_dot_subbed.replace(
        "<p><!-- pagebreak --></p>", '<br data-gw-pagebreak="true" />'
    )

    # Compile
    return env.from_string(text_pagebrea_subbed)
