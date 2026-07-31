"""
This module contains the tools required for generating Microsoft Office documents for
reporting.
"""

# Standard Libraries
import logging
import types
from datetime import date, datetime, time, timedelta

# 3rd Party Libraries
import jinja2
import jinja2.environment
import jinja2.ext
import jinja2.nodes
import jinja2.runtime
import jinja2.sandbox

from ghostwriter.modules.reportwriter import jinja_funcs

logger = logging.getLogger(__name__)


def jinja_string_literal(value: str) -> str:
    """
    Encode a value, including quotes, without Jinja template delimiters.

    Every code point is escaped so HTML parsing and sanitizer normalization cannot
    turn data into Jinja syntax before the template is compiled.
    """
    return '"' + "".join(f"\\U{ord(character):08x}" for character in value) + '"'


class ReportSandboxedEnvironment(jinja2.sandbox.ImmutableSandboxedEnvironment):
    """
    Immutable Jinja environment for all report-controlled template source.

    Compiler, template, and extension objects are capabilities rather than report
    data. Templates must never inspect or call through them, even if a future
    context accidentally exposes one.
    """

    _blocked_attribute_types = (
        jinja2.environment.Environment,
        jinja2.environment.Template,
        jinja2.environment.TemplateStream,
        jinja2.ext.Extension,
        jinja2.nodes.Node,
        jinja2.runtime.Context,
        types.ModuleType,
    )

    _blocked_callable_attribute_types = (
        types.FunctionType,
        types.BuiltinFunctionType,
        types.MethodType,
        types.BuiltinMethodType,
    )

    _blocked_object_module_prefixes = (
        "docx.",
        "docxtpl.",
    )

    _safe_builtin_method_owner_types = (
        bool,
        bytes,
        date,
        datetime,
        dict,
        float,
        frozenset,
        int,
        list,
        range,
        set,
        str,
        time,
        timedelta,
        tuple,
    )

    _safe_jinja_method_owner_types = (
        jinja2.runtime.AsyncLoopContext,
        jinja2.runtime.LoopContext,
        jinja2.utils.Cycler,
    )

    _safe_jinja_callable_types = (
        jinja2.runtime.BlockReference,
        jinja2.runtime.Macro,
        jinja2.utils.Joiner,
    )

    @classmethod
    def _is_blocked_class(cls, obj):
        """Return whether obj is a class for one of the blocked capability types."""
        return isinstance(obj, type) and issubclass(obj, cls._blocked_attribute_types)

    @classmethod
    def _is_blocked_object(cls, obj):
        """Return whether an object must expose no template capabilities."""
        if obj is None:
            return False
        return (
            getattr(type(obj), "_jinja_block_all_attributes", False)
            or isinstance(obj, cls._blocked_attribute_types)
            or cls._is_blocked_class(obj)
            or type(obj).__module__.startswith(cls._blocked_object_module_prefixes)
        )

    def _is_registered_callable(self, obj):
        """Return whether a callable was explicitly registered with the environment."""
        return any(
            obj is candidate
            for registry in (self.globals, self.filters, self.tests)
            for candidate in registry.values()
        ) or any(
            obj is candidate
            for candidate in (
                jinja_funcs.caption,
                jinja_funcs.ref,
                jinja_funcs.mk_evidence,
            )
        )

    @classmethod
    def _is_safe_builtin_method(cls, obj):
        """
        Return whether obj is an inherited method of a known data-only type.

        Looking up the defining class prevents a dict or string subclass from
        introducing an executable method and inheriting trust from its base type.
        """
        if not isinstance(obj, types.BuiltinMethodType):
            return False
        owner = obj.__self__
        method_name = getattr(obj, "__name__", None)
        if owner is None or method_name is None:
            return False
        for base in type(owner).__mro__:
            if method_name in base.__dict__:
                return base in cls._safe_builtin_method_owner_types
        return False

    def is_safe_attribute(self, obj, attr, value):
        """Deny access to application-marked objects and Jinja internals."""
        if self._is_blocked_object(obj) or isinstance(
            obj,
            self._blocked_callable_attribute_types,
        ):
            return False
        return super().is_safe_attribute(obj, attr, value)

    def is_safe_callable(self, obj):
        """Permit only registered functions and explicitly data-only call targets."""
        owner = (
            obj.__self__
            if isinstance(
                obj,
                (
                    types.MethodType,
                    types.BuiltinMethodType,
                ),
            )
            else None
        )
        if self._is_blocked_object(obj) or self._is_blocked_object(owner):
            return False
        if self._is_registered_callable(obj):
            return super().is_safe_callable(obj)
        if self._is_safe_builtin_method(obj):
            return super().is_safe_callable(obj)
        if (
            isinstance(obj, types.MethodType)
            and type(owner) in self._safe_jinja_method_owner_types
        ):
            return super().is_safe_callable(obj)
        if type(obj) in self._safe_jinja_callable_types:
            return super().is_safe_callable(obj)
        return False


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

    env = ReportSandboxedEnvironment(undefined=undefined, autoescape=True)
    env.filters["filter_severity"] = jinja_funcs.filter_severity
    env.filters["filter_type"] = jinja_funcs.filter_type
    env.filters["strip_html"] = jinja_funcs.strip_html
    env.filters["compromised"] = jinja_funcs.compromised
    env.filters["add_days"] = jinja_funcs.add_days
    env.filters["format_datetime"] = jinja_funcs.format_datetime
    env.filters["to_datetime"] = jinja_funcs.to_datetime
    env.filters["business_days"] = jinja_funcs.business_days
    env.filters["get_item"] = jinja_funcs.get_item
    env.filters["regex_search"] = jinja_funcs.regex_search
    env.filters["filter_tags"] = jinja_funcs.filter_tags
    env.filters["replace_blanks"] = jinja_funcs.replace_blanks
    env.filters[
        "filter_bhe_findings_by_domain"
    ] = jinja_funcs.filter_bhe_findings_by_domain
    env.filters["translate_domain_sid"] = jinja_funcs.translate_domain_sid

    if debug:
        return env, undefined_vars
    return env


def report_generation_queryset():
    """
    Gets a queryset of Reports with `select_related` and `prefetch_related` options optimal for report generation.
    """
    from ghostwriter.reporting.models import (  # pylint: disable=import-outside-toplevel
        Report,
    )

    return (
        Report.objects.all()
        .prefetch_related(
            "tags",
            "reportfindinglink_set",
            "reportobservationlink_set",
            "evidence_set",
            "project__oplog_set",
            "project__oplog_set__entries",
            "project__oplog_set__entries__tags",
        )
        .select_related()
    )
