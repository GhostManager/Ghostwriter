"""Custom template tags for the shepherd app."""

# Django Imports
from django import template

register = template.Library()


@register.filter
def category_value(value):
    """
    Render domain category JSON values as text.

    VirusTotal normally returns categories as ``{"source": "category"}``, but
    stored JSON may contain lists or nested values. Templates should still
    render the page instead of passing non-text values to text-only filters.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value
    if isinstance(value, dict):
        rendered_categories = []
        for key, category in value.items():
            rendered_category = category_value(category)
            if rendered_category:
                rendered_categories.append(f"{key}: {rendered_category}")
        return ", ".join(rendered_categories)
    if isinstance(value, set):
        rendered_categories = sorted(category_value(category) for category in value)
        return ", ".join(category for category in rendered_categories if category)
    if isinstance(value, (list, tuple)):
        rendered_categories = [category_value(category) for category in value]
        return ", ".join(category for category in rendered_categories if category)
    return str(value)
