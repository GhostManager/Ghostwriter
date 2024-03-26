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

    if debug:
        return env, undefined_vars
    else:
        return env
