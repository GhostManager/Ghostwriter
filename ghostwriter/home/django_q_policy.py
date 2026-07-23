"""Server-side policy enforcement for Django Q tasks and schedules."""

# Standard Libraries
import ast
import inspect
import re
from collections.abc import Mapping, Sequence

# Django Imports
from django.conf import settings

COMMAND_RUNNER = "ghostwriter.home.django_q_tasks.run_configured_command"
MAX_SCHEDULE_ARGUMENT_LENGTH = 10000
RESERVED_KWARGS = {"q_options"}
SUPPORTED_TYPES = {"bool", "float", "int", "str"}
DOTTED_PATH_PATTERN = re.compile(r"^[A-Za-z_]\w*(?:\.[A-Za-z_]\w*)+$")


class TaskPolicyError(Exception):
    """Raised when a task, hook, command, or argument violates policy."""


def callable_path(value):
    """Return a stable dotted path without importing an untrusted string."""
    if isinstance(value, str):
        path = value
    elif (
        inspect.isfunction(value) or inspect.ismethod(value) or inspect.isbuiltin(value)
    ):
        module = getattr(value, "__module__", None)
        name = getattr(value, "__qualname__", None) or getattr(value, "__name__", None)
        path = f"{module}.{name}" if module and name else ""
    else:
        path = ""
    if not path or not DOTTED_PATH_PATTERN.fullmatch(path) or "<locals>" in path:
        raise TaskPolicyError("Task callable must be an exact dotted path")
    return path


def parse_schedule_arguments(args_value, kwargs_value):
    """Parse Django Q's literal args and kwargs formats without evaluating code."""
    args = ()
    kwargs = {}

    for label, value in (
        ("Arguments", args_value),
        ("Keyword arguments", kwargs_value),
    ):
        if isinstance(value, str) and len(value) > MAX_SCHEDULE_ARGUMENT_LENGTH:
            raise TaskPolicyError(
                f"{label} exceed the maximum length of {MAX_SCHEDULE_ARGUMENT_LENGTH} characters"
            )

    if args_value:
        if isinstance(args_value, str):
            try:
                args = ast.literal_eval(args_value)
            except (RecursionError, SyntaxError, ValueError, TypeError) as error:
                raise TaskPolicyError(
                    "Arguments must contain Python literals"
                ) from error
        else:
            args = args_value
        if not isinstance(args, tuple):
            args = (args,)

    if kwargs_value:
        if isinstance(kwargs_value, Mapping):
            kwargs = dict(kwargs_value)
        elif isinstance(kwargs_value, str):
            try:
                parsed = ast.literal_eval(kwargs_value)
                if not isinstance(parsed, Mapping):
                    raise ValueError
                kwargs = dict(parsed)
            except (
                RecursionError,
                SyntaxError,
                ValueError,
                TypeError,
            ) as literal_error:
                try:
                    keywords = ast.parse(
                        f"f({kwargs_value})", mode="eval"
                    ).body.keywords
                    if any(keyword.arg is None for keyword in keywords):
                        raise ValueError from literal_error
                    names = [keyword.arg for keyword in keywords]
                    if len(names) != len(set(names)):
                        raise ValueError from literal_error
                    kwargs = {
                        keyword.arg: ast.literal_eval(keyword.value)
                        for keyword in keywords
                    }
                except (RecursionError, SyntaxError, ValueError, TypeError) as error:
                    raise TaskPolicyError(
                        "Keyword arguments must contain Python literals"
                    ) from error
        else:
            raise TaskPolicyError("Keyword arguments must be a mapping")

    return args, kwargs


def get_command_policy():
    """Return a copy of the configured fixed-command mapping."""
    commands = getattr(settings, "GHOSTWRITER_DJANGO_Q_COMMANDS", {})
    if not isinstance(commands, Mapping):
        raise TaskPolicyError("GHOSTWRITER_DJANGO_Q_COMMANDS must be a mapping")
    return dict(commands)


def get_schedule_policy():
    """Return configured schedule tasks, adding the command runner when needed."""
    configured = getattr(settings, "GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS", {})
    if not isinstance(configured, Mapping):
        raise TaskPolicyError("GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS must be a mapping")
    policy = dict(configured)
    commands = get_command_policy()
    if commands:
        policy[COMMAND_RUNNER] = {
            "label": "Run Approved System Command",
            "args": [
                {
                    "name": "command_name",
                    "type": "str",
                    "required": False,
                    "choices": sorted(commands),
                }
            ],
            "kwargs": {
                "command_name": {
                    "type": "str",
                    "choices": sorted(commands),
                }
            },
            "required_parameters": ["command_name"],
        }
    return policy


def get_queue_policy():
    """Return the union of internal and administrator-schedulable tasks."""
    configured = getattr(settings, "GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS", {})
    if not isinstance(configured, Mapping):
        raise TaskPolicyError("GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS must be a mapping")
    policy = dict(configured)
    policy.update(get_schedule_policy())
    return policy


def get_hook_policy(schedule_only=False):
    """Return hooks permitted for schedules or for the complete queue."""
    schedule_hooks = getattr(settings, "GHOSTWRITER_DJANGO_Q_SCHEDULE_HOOKS", {})
    if not isinstance(schedule_hooks, Mapping):
        raise TaskPolicyError("GHOSTWRITER_DJANGO_Q_SCHEDULE_HOOKS must be a mapping")
    policy = dict(schedule_hooks)
    if not schedule_only:
        internal_hooks = getattr(settings, "GHOSTWRITER_DJANGO_Q_INTERNAL_HOOKS", {})
        if not isinstance(internal_hooks, Mapping):
            raise TaskPolicyError(
                "GHOSTWRITER_DJANGO_Q_INTERNAL_HOOKS must be a mapping"
            )
        policy = dict(internal_hooks) | policy
    return policy


def _validate_value(name, value, specification):
    if not isinstance(specification, Mapping):
        raise TaskPolicyError(f"Policy for {name} must be a mapping")
    if value is None:
        if specification.get("nullable", False):
            return
        raise TaskPolicyError(f"{name} may not be null")

    expected = specification.get("type")
    if expected not in SUPPORTED_TYPES:
        raise TaskPolicyError(f"Policy for {name} has an unsupported type")
    expected_type = {"bool": bool, "float": float, "int": int, "str": str}[expected]
    if expected == "float":
        valid_type = type(value) in (float, int)
    else:
        valid_type = type(value) is expected_type
    if not valid_type:
        raise TaskPolicyError(f"{name} must be a {expected}")

    if "choices" in specification and value not in specification["choices"]:
        raise TaskPolicyError(f"{name} is not an approved value")
    if "min" in specification and value < specification["min"]:
        raise TaskPolicyError(f"{name} is below the allowed minimum")
    if "max" in specification and value > specification["max"]:
        raise TaskPolicyError(f"{name} exceeds the allowed maximum")


def validate_arguments(task_path, args, kwargs, task_policy):
    """Validate arguments for one exact task policy entry."""
    task_specification = task_policy[task_path]
    if not isinstance(task_specification, Mapping):
        raise TaskPolicyError(f"Policy for {task_path} must be a mapping")
    if RESERVED_KWARGS.intersection(kwargs):
        raise TaskPolicyError(f"{task_path} may not override Django Q options")
    if task_specification.get("allow_any_arguments", False):
        return

    positional_specs = task_specification.get("args", [])
    keyword_specs = task_specification.get("kwargs", {})
    if not isinstance(positional_specs, Sequence) or isinstance(positional_specs, str):
        raise TaskPolicyError(
            f"Positional argument policy for {task_path} must be a list"
        )
    if not isinstance(keyword_specs, Mapping):
        raise TaskPolicyError(
            f"Keyword argument policy for {task_path} must be a mapping"
        )

    required_args = sum(1 for item in positional_specs if item.get("required", True))
    if len(args) < required_args or len(args) > len(positional_specs):
        raise TaskPolicyError(
            f"{task_path} received an unapproved number of positional arguments"
        )
    for index, value in enumerate(args):
        _validate_value(f"argument {index + 1}", value, positional_specs[index])

    positional_names = {
        specification.get("name")
        for specification in positional_specs[: len(args)]
        if specification.get("name")
    }
    duplicated = positional_names.intersection(kwargs)
    if duplicated:
        raise TaskPolicyError(
            f"{task_path} received arguments more than once: {', '.join(sorted(duplicated))}"
        )

    unexpected = set(kwargs) - set(keyword_specs)
    if unexpected:
        raise TaskPolicyError(
            f"{task_path} received unapproved keyword arguments: {', '.join(sorted(unexpected))}"
        )
    for name, value_specification in keyword_specs.items():
        if value_specification.get("required", False) and name not in kwargs:
            raise TaskPolicyError(f"{task_path} requires keyword argument {name}")
        if name in kwargs:
            _validate_value(name, kwargs[name], value_specification)

    provided_parameters = positional_names | set(kwargs)
    missing_parameters = (
        set(task_specification.get("required_parameters", [])) - provided_parameters
    )
    if missing_parameters:
        raise TaskPolicyError(
            f"{task_path} requires parameters: {', '.join(sorted(missing_parameters))}"
        )


def validate_task(func, args=(), kwargs=None, hook=None, schedule_only=False):
    """Validate a task package without importing its callable or hook."""
    task_path = callable_path(func)
    policy = get_schedule_policy() if schedule_only else get_queue_policy()
    if task_path not in policy:
        raise TaskPolicyError(f"{task_path} is not permitted by the server task policy")
    validate_arguments(task_path, tuple(args or ()), dict(kwargs or {}), policy)
    if hook:
        hook_path = callable_path(hook)
        hook_policy = get_hook_policy(schedule_only=schedule_only)
        if hook_path not in hook_policy:
            raise TaskPolicyError(
                f"{hook_path} is not permitted by the server hook policy"
            )
    return task_path


def validate_schedule(schedule):
    """Parse and validate a Django Q Schedule instance."""
    if schedule.intended_date_kwarg:
        raise TaskPolicyError("Scheduled tasks may not inject an intended-date keyword")
    args, kwargs = parse_schedule_arguments(schedule.args, schedule.kwargs)
    validate_task(
        schedule.func,
        args=args,
        kwargs=kwargs,
        hook=schedule.hook,
        schedule_only=True,
    )
    return args, kwargs


def validate_command_policy():
    """Validate fixed command definitions without executing them."""
    for name, command in get_command_policy().items():
        if not isinstance(name, str) or not name:
            raise TaskPolicyError("Command names must be non-empty strings")
        if not isinstance(command, Mapping):
            raise TaskPolicyError(f"Command {name} must be a mapping")
        argv = command.get("argv")
        if (
            not isinstance(argv, (list, tuple))
            or not argv
            or not all(isinstance(item, str) and item for item in argv)
        ):
            raise TaskPolicyError(f"Command {name} must define a non-empty string argv")
        if not argv[0].startswith("/"):
            raise TaskPolicyError(
                f"Command {name} must use an absolute executable path"
            )
        if "shell" in command:
            raise TaskPolicyError(f"Command {name} may not configure a shell")
        if "cwd" in command and (
            not isinstance(command["cwd"], str) or not command["cwd"].startswith("/")
        ):
            raise TaskPolicyError(f"Command {name} working directory must be absolute")
        if "timeout" in command and (
            type(command["timeout"]) not in (float, int) or command["timeout"] <= 0
        ):
            raise TaskPolicyError(f"Command {name} timeout must be positive")
        if "env" in command:
            environment = command["env"]
            if not isinstance(environment, Mapping) or not all(
                isinstance(key, str) and isinstance(value, str)
                for key, value in environment.items()
            ):
                raise TaskPolicyError(
                    f"Command {name} environment must contain only strings"
                )


def _validate_policy_schema(path, specification):
    """Validate the declarative structure of one task policy entry."""
    if not isinstance(specification, Mapping):
        raise TaskPolicyError(f"Policy for {path} must be a mapping")
    if specification.get("allow_any_arguments", False):
        return
    positional = specification.get("args", [])
    keywords = specification.get("kwargs", {})
    if not isinstance(positional, Sequence) or isinstance(positional, str):
        raise TaskPolicyError(f"Positional argument policy for {path} must be a list")
    if not isinstance(keywords, Mapping):
        raise TaskPolicyError(f"Keyword argument policy for {path} must be a mapping")
    optional_seen = False
    positional_names = []
    for name, value_specification in [
        *((f"argument {index + 1}", item) for index, item in enumerate(positional)),
        *keywords.items(),
    ]:
        if not isinstance(value_specification, Mapping):
            raise TaskPolicyError(f"Policy for {path} {name} must be a mapping")
        if value_specification.get("type") not in SUPPORTED_TYPES:
            raise TaskPolicyError(f"Policy for {path} {name} has an unsupported type")
        if name.startswith("argument "):
            parameter_name = value_specification.get("name")
            if parameter_name is not None and (
                not isinstance(parameter_name, str)
                or not parameter_name
                or parameter_name in positional_names
            ):
                raise TaskPolicyError(
                    f"Policy for {path} has an invalid or duplicate positional argument name"
                )
            if parameter_name:
                positional_names.append(parameter_name)
            required = value_specification.get("required", True)
            if not required:
                optional_seen = True
            elif optional_seen:
                raise TaskPolicyError(
                    f"Policy for {path} has a required argument after an optional one"
                )
        if "choices" in value_specification and (
            not isinstance(value_specification["choices"], Sequence)
            or isinstance(value_specification["choices"], str)
        ):
            raise TaskPolicyError(f"Policy choices for {path} {name} must be a list")

    required_parameters = specification.get("required_parameters", [])
    if (
        not isinstance(required_parameters, Sequence)
        or isinstance(required_parameters, str)
        or not all(isinstance(name, str) for name in required_parameters)
        or not set(required_parameters).issubset(set(positional_names) | set(keywords))
    ):
        raise TaskPolicyError(f"Policy for {path} has invalid required parameters")


def validate_policy_configuration():
    """Validate every configured policy entry and return any errors."""
    errors = []
    try:
        task_policies = (get_schedule_policy(), get_queue_policy())
        for policy in task_policies:
            for path, specification in policy.items():
                callable_path(path)
                _validate_policy_schema(path, specification)
        for path, specification in get_hook_policy().items():
            callable_path(path)
            if not isinstance(specification, Mapping):
                raise TaskPolicyError(f"Hook policy for {path} must be a mapping")
        validate_command_policy()
    except TaskPolicyError as error:
        errors.append(str(error))
    return errors
