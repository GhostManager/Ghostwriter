"""Determine which activity-log data an export needs before loading entries."""

from django.db.models import prefetch_related_objects
from jinja2 import meta

from ghostwriter.modules.reportwriter.querysets import oplog_entries_prefetch
from ghostwriter.oplog.models import OplogEntry

LOG_KEYS = ("logs", "tools")


def template_variables(env, source):
    """Find context keys, keeping the full log context for template references."""
    tree = env.parse(source)
    if list(meta.find_referenced_templates(tree)):
        return set(LOG_KEYS)
    return meta.find_undeclared_variables(tree)


def preview_template_variables(_env):
    """Previews have no outer document template."""
    return set()


def serialize_with_log_dependencies(serializer, project, inspect_context):
    """Serialize the light context first, then add only the required log data."""
    if inspect_context is None:
        return serializer.data

    log_fields = {key: serializer.fields.pop(key) for key in LOG_KEYS}
    data = serializer.to_representation(serializer.instance)
    try:
        required = inspect_context(data)
    except Exception:
        # Analysis is an optimization. Let the normal renderer handle errors.
        required = set(LOG_KEYS)

    if "logs" in required:
        prefetch_related_objects([project], oplog_entries_prefetch())
        for key, field in log_fields.items():
            data[key] = field.to_representation(field.get_attribute(serializer.instance))
    else:
        data["logs"] = []
        data["tools"] = _project_tool_names(project) if "tools" in required else []
    return data


def _project_tool_names(project):
    """Preserve the serializer's first-seen, lowercased tool ordering."""
    values = (
        OplogEntry.objects.filter(oplog_id__project=project)
        .exclude(tool__isnull=True)
        .exclude(tool="")
        .order_by("oplog_id_id", "-start_date", "-end_date")
        .values_list("tool", flat=True)
        .iterator()
    )
    return list(dict.fromkeys(tool.lower() for tool in values))
