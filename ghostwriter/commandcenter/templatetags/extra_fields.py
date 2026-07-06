
import html as html_module
import json

# Django Imports
import bleach
import bs4
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils.encoding import force_str
from django.utils.html import mark_safe

from ghostwriter.commandcenter.models import ExtraFieldSpec, ReportConfiguration
from ghostwriter.reporting.models import Evidence

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


def _sanitize_rich_text(value):
    css_sanitizer = CSSSanitizer(allowed_css_properties=settings.BLEACH_ALLOWED_STYLES)
    return bleach.clean(
        value,
        tags=settings.BLEACH_ALLOWED_TAGS,
        attributes=settings.BLEACH_ALLOWED_ATTRIBUTES,
        css_sanitizer=css_sanitizer,
        protocols=settings.BLEACH_ALLOWED_PROTOCOLS,
        strip=settings.BLEACH_STRIP_TAGS,
        strip_comments=settings.BLEACH_STRIP_COMMENTS,
    )


def _expand_evidence_and_sanitize(html, report, *, client=None):
    """
    Expand Ghostwriter marker spans in *html* and sanitize the result.

    Handles four kinds of markers produced by the Jinja2 export pipeline:

    * ``data-gw-evidence`` / ``.richtext-evidence[data-evidence-id]`` –
      replaced with the rendered evidence image/text plus caption.
    * ``data-gw-ref`` – cross-reference to a captioned figure, rendered as
      *"Figure #"* in the preview.
    * ``data-gw-caption`` – figure caption prefix, rendered as
      *"Figure #<prefix>"* using the global report configuration.
    * ``data-gw-image`` – named image placeholder (e.g. ``CLIENT_LOGO``),
      rendered as an ``<img>`` tag when the asset is available.

    If *report* is falsy, evidence expansion is skipped but ref/caption/image
    markers are still expanded.

    Returns a safe HTML string (not yet wrapped in ``mark_safe``).
    """
    report_config = ReportConfiguration.get_solo()

    soup = bs4.BeautifulSoup(html, "html.parser")

    label = report_config.label_figure
    prefix = report_config.prefix_figure

    # --- Expand data-gw-ref spans → "Figure #" ---
    for node in soup.select("[data-gw-ref]"):
        node.replace_with(f"{label} #")

    # --- Expand data-gw-caption spans/divs → "Figure # – <caption text>" ---
    for node in soup.select("[data-gw-caption]"):
        inner_text = node.get_text()
        caption_text = f"{label} #{prefix}{inner_text}"
        if node.name in ("div", "section", "article"):
            # Block-level caption objects need a <p> wrapper to match the
            # rendering of inline ``{{.caption}}`` keywords (which already
            # sit inside a <p> from the editor).
            new_tag = soup.new_tag("p")
            new_tag.string = caption_text
            node.replace_with(new_tag)
        else:
            node.replace_with(caption_text)

    # --- Expand data-gw-image divs (e.g. CLIENT_LOGO) → <img> or placeholder ---
    _image_placeholders = {}
    for idx, node in enumerate(soup.select("[data-gw-image]")):
        image_name = node.get("data-gw-image", "")
        rendered_img = None
        if image_name == "CLIENT_LOGO" and client and client.logo:
            logo_url = reverse("rolodex:client_logo_download", kwargs={"pk": client.pk}) + "?view=true"
            alt = html_module.escape(client.name) + " logo"
            rendered_img = (
                f'<div style="text-align: center;">'
                f'<img class="mb-3" src="{logo_url}" alt="{alt}" '
                f'style="max-width: 6.5in; height: auto;" />'
                f'</div>'
            )
        if rendered_img:
            placeholder = f"__GW_IMAGE_PREVIEW_{idx}__"
            _image_placeholders[placeholder] = rendered_img
            node.replace_with(placeholder)
        else:
            node.decompose()

    # --- Expand evidence markers ---
    evidence_nodes = soup.select(
        ".richtext-evidence[data-evidence-id], [data-gw-evidence]"
    )
    placeholders = {}

    if evidence_nodes and report:
        evidence_ids = set()
        for node in evidence_nodes:
            evidence_id = node.get("data-evidence-id") or node.get("data-gw-evidence")
            try:
                evidence_ids.add(int(evidence_id))
            except (TypeError, ValueError):
                continue

        evidences = {
            evidence.pk: evidence
            for evidence in Evidence.objects.filter(pk__in=evidence_ids, report=report)
        }
        report_template = getattr(report, "docx_template", None)
        evidence_image_alignment = report_config.evidence_image_alignment
        evidence_image_width = report_config.evidence_image_width or 6.5
        if report_template is not None:
            evidence_image_alignment = report_template.get_effective_evidence_image_alignment(
                report_config
            )
            evidence_image_width = report_template.get_effective_evidence_image_width(
                report_config
            )
        rendered_evidence = {}
        for evidence in evidences.values():
            rendered_evidence[evidence.pk] = render_to_string(
                "snippets/evidence_display.html",
                {
                    "evidence": evidence,
                    "report_config": report_config,
                    "evidence_image_alignment": evidence_image_alignment,
                    "evidence_image_width": evidence_image_width,
                    "clickable": True,
                    "rich_text_preview": True,
                },
            )

        for index, node in enumerate(evidence_nodes):
            evidence_id = node.get("data-evidence-id") or node.get("data-gw-evidence")
            try:
                rendered = rendered_evidence[int(evidence_id)]
            except (KeyError, TypeError, ValueError):
                node.decompose()
                continue

            placeholder = f"__GW_EVIDENCE_PREVIEW_{index}__"
            placeholders[placeholder] = rendered
            node.replace_with(placeholder)
    elif evidence_nodes:
        # No report context – remove unresolvable evidence markers
        for node in evidence_nodes:
            node.decompose()

    sanitized = _sanitize_rich_text(str(soup))
    for placeholder, rendered in placeholders.items():
        sanitized = sanitized.replace(placeholder, rendered)
    for placeholder, rendered in _image_placeholders.items():
        sanitized = sanitized.replace(placeholder, rendered)
    return sanitized


@register.filter
def rich_text_preview(value, report=None):
    html = _coerce_rich_text_value(value)
    return mark_safe(_expand_evidence_and_sanitize(html, report))


@register.filter
def json_pretty(obj):
    return json.dumps(obj, indent="\t")
