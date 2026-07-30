"""Install Ghostwriter's Django Q security controls."""

# Standard Libraries
import logging
import pydoc

# Django Imports
from django.core.checks import Error, Tags, register
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.db.models.signals import post_save, pre_save

# 3rd Party Libraries
import django_q.cluster
from django_q.models import Schedule, Task
from django_q.signals import call_hook, pre_enqueue

# Ghostwriter Libraries
from ghostwriter.home.django_q_cluster import restricted_scheduler, restricted_worker
from ghostwriter.home.django_q_policy import (
    TaskPolicyError,
    callable_path,
    get_hook_policy,
    validate_policy_configuration,
    validate_schedule,
    validate_task,
)

logger = logging.getLogger(__name__)


def validate_schedule_on_save(sender, instance, raw=False, **kwargs):
    """Reject Schedule writes that do not satisfy server policy."""
    if raw:
        return
    try:
        validate_schedule(instance)
    except TaskPolicyError as error:
        raise ValidationError(str(error)) from error


def validate_task_before_enqueue(sender, task, **kwargs):
    """Reject every disallowed task before Django Q signs or enqueues it."""
    validate_task(
        task.get("func"),
        args=task.get("args", ()),
        kwargs=task.get("kwargs", {}),
        hook=task.get("hook"),
    )


def call_allowed_hook(sender, instance, **kwargs):
    """Call a result hook only when its exact path is server-approved."""
    if not instance.hook:
        return
    try:
        hook_path = callable_path(instance.hook)
        if hook_path not in get_hook_policy():
            raise TaskPolicyError(
                f"{hook_path} is not permitted by the server hook policy"
            )
        hook = pydoc.locate(hook_path)
        if not callable(hook):
            raise TaskPolicyError(f"Approved hook {hook_path} could not be loaded")
        hook(instance)
    except TaskPolicyError as error:
        logger.error("Blocked Django Q result hook for task %s: %s", instance.pk, error)
    except Exception:  # pylint: disable=broad-exception-caught
        # Hooks are best-effort and must not disrupt task-result persistence.
        logger.exception(
            "Approved Django Q result hook failed for task %s", instance.pk
        )


@register(Tags.security)
def check_django_q_policy(app_configs, **kwargs):
    """Report malformed server policy through Django's system checks."""
    return [
        Error(message, id="ghostwriter.EQ001")
        for message in validate_policy_configuration()
    ]


def install_django_q_restrictions():
    """Connect validation signals and replace Django Q execution functions."""
    policy_errors = validate_policy_configuration()
    if policy_errors:
        raise ImproperlyConfigured(
            f"Invalid Django Q server policy: {'; '.join(policy_errors)}"
        )
    pre_save.connect(
        validate_schedule_on_save,
        sender=Schedule,
        dispatch_uid="ghostwriter.django_q.validate_schedule",
    )
    pre_enqueue.connect(
        validate_task_before_enqueue,
        dispatch_uid="ghostwriter.django_q.validate_enqueue",
    )
    post_save.disconnect(call_hook, sender=Task)
    post_save.connect(
        call_allowed_hook,
        sender=Task,
        dispatch_uid="ghostwriter.django_q.call_allowed_hook",
    )
    django_q.cluster.worker = restricted_worker
    django_q.cluster.scheduler = restricted_scheduler
