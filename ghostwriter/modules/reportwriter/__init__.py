"""
This module contains the tools required for generating Microsoft Office documents for
reporting.
"""

# Standard Libraries
import logging

# 3rd Party Libraries
import jinja2
import jinja2.sandbox

from ghostwriter.modules.reportwriter import jinja_funcs

logger = logging.getLogger(__name__)


def prepare_jinja2_env(debug=False):
    """Prepare a Jinja2 environment with all custom filters."""
    if debug:
        undefined_vars = set()

        class RecordUndefined(jinja2.DebugUndefined):
            __slots__ = ()

            def _record(self):
                undefined_vars.add(self._undefined_name)

            def _fail_with_undefined_error(self, *args, **kwargs):
                self._record()
                return super()._fail_with_undefined_error(*args, **kwargs)

            def __str__(self) -> str:
                self._record()
                return super().__str__()

            def __iter__(self):
                self._record()
                return super().__iter__()

            def __bool__(self):
                self._record()
                return super().__bool__()

        undefined = RecordUndefined
    else:
        undefined = jinja2.make_logging_undefined(logger=logger, base=jinja2.Undefined)

    env = jinja2.sandbox.SandboxedEnvironment(undefined=undefined, extensions=["jinja2.ext.debug"], autoescape=True)
    env.filters["filter_severity"] = jinja_funcs.filter_severity
    env.filters["filter_type"] = jinja_funcs.filter_type
    env.filters["strip_html"] = jinja_funcs.strip_html
    env.filters["compromised"] = jinja_funcs.compromised
    env.filters["add_days"] = jinja_funcs.add_days
    env.filters["format_datetime"] = jinja_funcs.format_datetime
    env.filters["get_item"] = jinja_funcs.get_item
    env.filters["regex_search"] = jinja_funcs.regex_search
    env.filters["filter_tags"] = jinja_funcs.filter_tags
    env.filters["replace_blanks"] = jinja_funcs.replace_blanks
    env.filters["filter_bhe_findings_by_domain"] = jinja_funcs.filter_bhe_findings_by_domain
    env.filters["translate_domain_sid"] = jinja_funcs.translate_domain_sid

    if debug:
        return env, undefined_vars
    return env

def report_generation_queryset():
    """
    Gets a queryset of Reports with `select_related` and `prefetch_related` options optimal for report generation.
    """
    from ghostwriter.reporting.models import Report # pylint: disable=import-outside-toplevel
    return Report.objects.all().prefetch_related(
        "tags",
        "reportfindinglink_set",
        "reportfindinglink_set__evidence_set",
        "reportobservationlink_set",
        "evidence_set",
        "project__oplog_set",
        "project__oplog_set__entries",
        "project__oplog_set__entries__tags",
    ).select_related()
