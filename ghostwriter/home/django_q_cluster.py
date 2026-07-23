"""Restricted Django Q scheduler and worker implementations.

These functions preserve the scheduler and worker contracts from the pinned
django-q2 1.10.0 dependency while inserting policy checks before imports and
execution. Review them whenever that dependency is upgraded.
"""

# Standard Libraries
import pydoc
import traceback

# Django Imports
from django.utils import timezone

# 3rd Party Libraries
import django_q.scheduler as q_scheduler
import django_q.worker as q_worker

# Ghostwriter Libraries
from ghostwriter.home.django_q_policy import (
    TaskPolicyError,
    validate_schedule,
    validate_task,
)


def restricted_scheduler(broker=None):
    """Create tasks from due schedules after applying server policy."""
    if not broker:
        broker = q_scheduler.get_broker()
    q_scheduler.close_old_django_connections()

    default_cluster = (
        q_scheduler.db.models.Q(cluster__isnull=True)
        if q_scheduler.Conf.CLUSTER_NAME == q_scheduler.Conf.PREFIX
        else q_scheduler.db.models.Q(pk__in=[])
    )
    try:
        with q_scheduler.db.transaction.atomic(
            using=q_scheduler.db.router.db_for_write(q_scheduler.Schedule)
        ):
            schedules = (
                q_scheduler.Schedule.objects.select_for_update()
                .exclude(repeats=0)
                .filter(next_run__lt=timezone.now())
                .filter(
                    default_cluster
                    | q_scheduler.db.models.Q(cluster=q_scheduler.Conf.CLUSTER_NAME)
                )
            )
            for schedule in schedules:
                try:
                    with q_scheduler.db.transaction.atomic(
                        using=q_scheduler.db.router.db_for_write(q_scheduler.Schedule)
                    ):
                        _enqueue_schedule(schedule, broker)
                except TaskPolicyError as error:
                    q_scheduler.Schedule.objects.filter(pk=schedule.pk).update(
                        repeats=0
                    )
                    q_scheduler.logger.error(
                        "Paused Django Q schedule %s because server policy denied it: %s",
                        schedule.pk,
                        error,
                    )
                except Exception:
                    q_scheduler.logger.exception(
                        "Could not create a task from Django Q schedule %s",
                        schedule.pk,
                    )
    except Exception:
        q_scheduler.logger.exception("Could not inspect Django Q schedules")


def _enqueue_schedule(schedule, broker):
    """Enqueue one locked schedule and calculate its following run."""
    args, kwargs = validate_schedule(schedule)
    q_options = {}
    if schedule.hook:
        q_options["hook"] = schedule.hook

    if schedule.schedule_type != schedule.ONCE:
        next_run = schedule.next_run
        while True:
            next_run = schedule.calculate_next_run(next_run)
            if q_scheduler.Conf.CATCH_UP or next_run > q_scheduler.localtime():
                break
        schedule.next_run = next_run
        if schedule.repeats < -1:
            schedule.repeats = -1
        if schedule.repeats > 0:
            schedule.repeats -= 1

    q_options["cluster"] = schedule.cluster
    if (
        q_options["cluster"] is None
        or q_options["cluster"] == q_scheduler.Conf.CLUSTER_NAME
    ):
        q_options["broker"] = broker
    q_options["group"] = schedule.name or schedule.id
    kwargs["q_options"] = q_options
    schedule.task = q_scheduler.async_task(schedule.func, *args, **kwargs)
    if not schedule.task:
        q_scheduler.logger.error(
            "%s failed to create a task from schedule %s",
            q_scheduler.current_process().name,
            schedule.name or schedule.id,
        )
    else:
        q_scheduler.logger.info(
            "%s created task %s from schedule %s",
            q_scheduler.current_process().name,
            q_scheduler.humanize(schedule.task),
            schedule.name or schedule.id,
        )

    if schedule.schedule_type == schedule.ONCE:
        if schedule.repeats < 0:
            schedule.delete()
            return
        schedule.repeats = 0
    schedule.save()


def restricted_worker(task_queue, result_queue, timer, timeout=q_worker.Conf.TIMEOUT):
    """Execute queued tasks only after validating them against server policy."""
    proc_name = q_worker.current_process().name
    q_worker.logger.info(
        "%s ready for work at %s", proc_name, q_worker.current_process().pid
    )
    q_worker.post_spawn.send(sender="django_q", proc_name=proc_name)
    if q_worker.setproctitle:
        q_worker.setproctitle.setproctitle(f"qcluster {proc_name} idle")
    task_count = 0
    if timeout is None:
        timeout = -1

    for task in iter(task_queue.get, "STOP"):
        timer.value = -1
        task_count += 1
        func = task["func"]
        func_name = q_worker.get_func_repr(func)
        task_name = task["name"]
        q_worker.logger.info("%s processing %s '%s'", proc_name, task_name, func_name)
        if q_worker.setproctitle:
            q_worker.setproctitle.setproctitle(
                f"qcluster {proc_name} processing {task_name} '{func_name}'"
            )
        if not task.get("sync", False):
            q_worker.close_old_django_connections()
        timer_value = task.pop("timeout", timeout)
        timeout_error = False
        policy_denied = False

        try:
            validate_task(
                func,
                args=task.get("args", ()),
                kwargs=task.get("kwargs", {}),
                hook=task.get("hook"),
            )
            if not callable(func):
                func = pydoc.locate(func)
            if func is None:
                raise ValueError(f"Function {task['func']} is not defined")
            q_worker.pre_execute.send(sender="django_q", func=func, task=task)
            timer.value = timer_value
            if timer.value != -1:
                timer.value += 3
            with q_worker.TimeoutHandler(timer_value):
                response = func(*task["args"], **task["kwargs"])
            result = (response, True)
        except TaskPolicyError as error:
            policy_denied = True
            task["ack_failure"] = True
            result = (f"Task blocked by server policy: {error}", False)
            q_worker.logger.error(
                "Blocked Django Q task %s (%s): %s",
                task_name,
                func_name,
                error,
            )
        except (Exception, q_worker.TimeoutException) as error:
            if isinstance(error, q_worker.TimeoutException):
                timeout_error = True
            result = (f"{error} : {traceback.format_exc()}", False)
            if q_worker.error_reporter:
                q_worker.error_reporter.report()
            if task.get("sync", False):
                q_worker.post_execute_in_worker.send(
                    sender="django_q", func=func, task=task
                )
                raise

        with timer.get_lock():
            task["result"] = result[0]
            task["success"] = result[1]
            task["stopped"] = timezone.now()
            if not policy_denied:
                q_worker.post_execute_in_worker.send(
                    sender="django_q", func=func, task=task
                )
            result_queue.put(task)
            if timeout_error:
                timer.value = 0
                break
            timer.value = -1
            if q_worker.setproctitle:
                q_worker.setproctitle.setproctitle(f"qcluster {proc_name} idle")
            if task_count == q_worker.Conf.RECYCLE or q_worker.rss_check():
                timer.value = -2
                break
    q_worker.logger.info("%s stopped doing work", proc_name)
