
import json

# Django Imports
import bleach
import bs4
from bleach.css_sanitizer import CSSSanitizer
from django import template
from django.conf import settings
from django.template.loader import render_to_string
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


@register.filter
def rich_text_preview(value, report=None):
    html = _coerce_rich_text_value(value)
    if not report:
        return mark_safe(_sanitize_rich_text(html))

    soup = bs4.BeautifulSoup(html, "html.parser")
    evidence_nodes = soup.select(
        ".richtext-evidence[data-evidence-id], [data-gw-evidence]"
    )
    if not evidence_nodes:
        return mark_safe(_sanitize_rich_text(html))

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
    report_config = ReportConfiguration.get_solo()
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

    placeholders = {}
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

    sanitized = _sanitize_rich_text(str(soup))
    for placeholder, rendered in placeholders.items():
        sanitized = sanitized.replace(placeholder, rendered)
    return mark_safe(sanitized)


@register.filter
def json_pretty(obj):
    return json.dumps(obj, indent="\t")
