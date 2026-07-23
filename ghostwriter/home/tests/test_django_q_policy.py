"""Tests for Ghostwriter's Django Q task policy."""

# Standard Libraries
import inspect
import pydoc
import queue
from contextlib import nullcontext
from io import StringIO
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django Imports
from django.contrib import admin
from django.core.exceptions import ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

# 3rd Party Libraries
from django_q.conf import Conf
from django_q.models import Failure, Schedule, Success, Task
from django_q.signals import call_hook
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.home.admin import RestrictedScheduleAdmin, RestrictedScheduleForm
from ghostwriter.home.django_q_cluster import restricted_scheduler, restricted_worker
from ghostwriter.home.django_q_integration import call_allowed_hook
from ghostwriter.home.django_q_policy import (
    COMMAND_RUNNER,
    TaskPolicyError,
    get_schedule_policy,
    parse_schedule_arguments,
    validate_policy_configuration,
    validate_task,
)
from ghostwriter.home.django_q_tasks import run_configured_command


def allowed_test_task(value):
    """Return a value for restricted-worker tests."""
    return value


TEST_TASK_PATH = "ghostwriter.home.tests.test_django_q_policy.allowed_test_task"
TEST_TASK_POLICY = {
    TEST_TASK_PATH: {
        "label": "Allowed Test Task",
        "args": [{"type": "int"}],
        "kwargs": {},
    }
}


class FakeTimer:
    """Provide the small multiprocessing.Value interface used by workers."""

    def __init__(self):
        self.value = -1

    def get_lock(self):
        return nullcontext()


class TaskPolicyTests(SimpleTestCase):
    def test_builtin_task_is_allowed_with_approved_arguments(self):
        path = validate_task(
            "ghostwriter.shepherd.tasks.release_domains",
            kwargs={"no_action": True},
            schedule_only=True,
        )

        self.assertEqual(path, "ghostwriter.shepherd.tasks.release_domains")

    def test_builtin_policy_exposes_every_callable_parameter(self):
        for path, specification in get_schedule_policy().items():
            function = pydoc.locate(path)
            parameters = [
                parameter.name
                for parameter in inspect.signature(function).parameters.values()
                if parameter.kind
                in (parameter.POSITIONAL_ONLY, parameter.POSITIONAL_OR_KEYWORD)
            ]
            positional_names = [item.get("name") for item in specification["args"]]

            self.assertEqual(positional_names, parameters, path)
            self.assertEqual(set(specification["kwargs"]), set(parameters), path)

    def test_all_builtin_parameters_are_allowed_positionally(self):
        sample_values = {"bool": True, "int": 1, "float": 1.0, "str": "value"}
        for path, specification in get_schedule_policy().items():
            args = tuple(
                sample_values[item["type"]] for item in specification.get("args", [])
            )

            validate_task(path, args=args, schedule_only=True)

    def test_parameter_cannot_be_supplied_positionally_and_by_name(self):
        with self.assertRaisesRegex(TaskPolicyError, "more than once"):
            validate_task(
                "ghostwriter.shepherd.tasks.release_domains",
                args=(True,),
                kwargs={"no_action": False},
                schedule_only=True,
            )

    def test_arbitrary_callable_is_denied(self):
        with self.assertRaises(TaskPolicyError):
            validate_task("os.system", args=("id",), schedule_only=True)

    @patch("django_q.tasks.get_broker")
    def test_arbitrary_callable_is_denied_before_enqueue(self, get_broker_mock):
        get_broker_mock.return_value = Mock(list_key="test")

        with self.assertRaises(TaskPolicyError):
            async_task("os.system", "id")

        get_broker_mock.return_value.enqueue.assert_not_called()

    def test_allowed_callable_rejects_unapproved_arguments(self):
        with self.assertRaisesRegex(TaskPolicyError, "unapproved keyword"):
            validate_task(
                "ghostwriter.shepherd.tasks.release_domains",
                kwargs={"command": "id"},
                schedule_only=True,
            )

    def test_django_q_options_are_always_denied(self):
        with override_settings(
            GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS={
                TEST_TASK_PATH: {"allow_any_arguments": True}
            }
        ):
            with self.assertRaisesRegex(TaskPolicyError, "may not override"):
                validate_task(TEST_TASK_PATH, kwargs={"q_options": {"timeout": 0}})

    def test_schedule_arguments_use_literal_parsing(self):
        args, kwargs = parse_schedule_arguments("1, 'two'", "enabled=True, count=3")

        self.assertEqual(args, (1, "two"))
        self.assertEqual(kwargs, {"enabled": True, "count": 3})

    def test_schedule_arguments_reject_code(self):
        with self.assertRaises(TaskPolicyError):
            parse_schedule_arguments("__import__('os').system('id')", "")

    def test_schedule_arguments_reject_excessive_input(self):
        with self.assertRaisesRegex(TaskPolicyError, "maximum length"):
            parse_schedule_arguments("'" + ("a" * 10000) + "'", "")

    @override_settings(
        GHOSTWRITER_DJANGO_Q_COMMANDS={
            "backup": {
                "argv": ["/usr/local/bin/ghostwriter-backup"],
                "timeout": 30,
            }
        }
    )
    def test_fixed_commands_add_restricted_runner_to_schedule_policy(self):
        policy = get_schedule_policy()

        self.assertIn(COMMAND_RUNNER, policy)
        validate_task(
            COMMAND_RUNNER,
            kwargs={"command_name": "backup"},
            schedule_only=True,
        )
        validate_task(COMMAND_RUNNER, args=("backup",), schedule_only=True)
        with self.assertRaisesRegex(TaskPolicyError, "requires parameters"):
            validate_task(COMMAND_RUNNER, schedule_only=True)
        with self.assertRaises(TaskPolicyError):
            validate_task(
                COMMAND_RUNNER,
                kwargs={"command_name": "shell"},
                schedule_only=True,
            )

    @override_settings(
        GHOSTWRITER_DJANGO_Q_COMMANDS={
            "backup": {
                "argv": ["/usr/local/bin/ghostwriter-backup", "--quiet"],
                "timeout": 30,
            }
        }
    )
    @patch("ghostwriter.home.django_q_tasks.subprocess.run")
    def test_command_runner_uses_fixed_argv_without_shell(self, run_mock):
        run_mock.return_value = SimpleNamespace(returncode=0)

        result = run_configured_command("backup")

        self.assertEqual(result, {"returncode": 0})
        run_mock.assert_called_once_with(
            ["/usr/local/bin/ghostwriter-backup", "--quiet"],
            cwd=None,
            env={},
            shell=False,
            check=True,
            timeout=30,
            stdout=-3,
            stderr=-3,
        )

    @override_settings(
        GHOSTWRITER_DJANGO_Q_COMMANDS={"bad": {"argv": ["sh", "-c", "id"]}}
    )
    def test_relative_command_policy_fails_system_check(self):
        self.assertTrue(validate_policy_configuration())


class RestrictedAdminTests(SimpleTestCase):
    def test_django_q_models_use_restricted_admins(self):
        self.assertIsInstance(admin.site._registry[Schedule], RestrictedScheduleAdmin)
        self.assertNotEqual(
            admin.site._registry[Success].actions[0].__name__,
            "resubmit_task",
        )
        self.assertNotEqual(
            admin.site._registry[Failure].actions[0].__name__,
            "resubmit_task",
        )

    def test_schedule_form_rejects_forged_callable(self):
        form = RestrictedScheduleForm(
            data={
                "name": "Malicious",
                "func": "os.system",
                "hook": "",
                "args": "'id'",
                "kwargs": "",
                "schedule_type": Schedule.DAILY,
                "minutes": "",
                "repeats": -1,
                "next_run": timezone.now(),
                "cron": "",
                "cluster": "",
                "intended_date_kwarg": "",
            }
        )

        self.assertFalse(form.is_valid())
        self.assertIn("func", form.errors)

    def test_schedule_form_exposes_builtin_slack_hook(self):
        form = RestrictedScheduleForm()

        self.assertIn(
            (
                "ghostwriter.modules.notifications_slack.send_slack_complete_msg",
                "Send Slack Completion Message",
            ),
            list(form.fields["hook"].choices),
        )

    def test_schedule_form_accepts_approved_callable(self):
        form = RestrictedScheduleForm(
            data={
                "name": "Release Domains",
                "func": "ghostwriter.shepherd.tasks.release_domains",
                "hook": "",
                "args": "",
                "kwargs": "no_action=True",
                "schedule_type": Schedule.DAILY,
                "minutes": "",
                "repeats": -1,
                "next_run": timezone.now(),
                "cron": "",
                "cluster": "",
                "intended_date_kwarg": "",
            }
        )

        self.assertTrue(form.is_valid(), form.errors.as_json())


class SchedulePolicyIntegrationTests(TestCase):
    def test_model_save_signal_rejects_disallowed_schedule(self):
        with self.assertRaises(ValidationError):
            Schedule.objects.create(
                name="Malicious",
                func="os.system",
                args="'id'",
                schedule_type=Schedule.DAILY,
            )

    def test_audit_command_reports_and_pauses_bulk_inserted_schedule(self):
        schedule = Schedule(
            name="Malicious",
            func="os.system",
            args="'id'",
            schedule_type=Schedule.DAILY,
            repeats=-1,
        )
        Schedule.objects.bulk_create([schedule])
        stdout = StringIO()

        with self.assertRaises(CommandError):
            call_command("audit_django_q_policy", "--check", stdout=stdout)
        self.assertIn("DISALLOWED", stdout.getvalue())

        call_command("audit_django_q_policy", "--pause-disallowed", stdout=StringIO())
        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 0)

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.async_task")
    def test_scheduler_pauses_denied_row_and_continues_allowed_rows(
        self, async_task_mock, _close_connections
    ):
        async_task_mock.return_value = "0123456789abcdef0123456789abcdef"
        invalid = Schedule(
            name="Malicious",
            func="os.system",
            args="'id'",
            schedule_type=Schedule.DAILY,
            repeats=-1,
            next_run=timezone.now(),
            cluster=Conf.CLUSTER_NAME,
        )
        Schedule.objects.bulk_create([invalid])
        valid = Schedule.objects.create(
            name="Cleanup",
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            schedule_type=Schedule.ONCE,
            repeats=1,
            next_run=timezone.now(),
            cluster=Conf.CLUSTER_NAME,
        )

        restricted_scheduler(broker=Mock())

        invalid.refresh_from_db()
        valid.refresh_from_db()
        self.assertEqual(invalid.repeats, 0)
        self.assertEqual(valid.repeats, 0)
        async_task_mock.assert_called_once()


class WorkerPolicyTests(SimpleTestCase):
    def test_unrestricted_django_q_hook_receiver_is_disconnected(self):
        synchronous, asynchronous = post_save._live_receivers(Task)

        self.assertNotIn(call_hook, [*synchronous, *asynchronous])

    @override_settings(
        GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS=TEST_TASK_POLICY,
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={},
    )
    @patch("ghostwriter.home.django_q_cluster.q_worker.rss_check", return_value=False)
    @patch("ghostwriter.home.django_q_cluster.q_worker.setproctitle", None)
    def test_worker_executes_approved_task(self, _rss_check):
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        task_queue.put(
            {
                "id": "allowed-id",
                "name": "allowed",
                "func": TEST_TASK_PATH,
                "args": (7,),
                "kwargs": {},
                "started": timezone.now(),
            }
        )
        task_queue.put("STOP")

        restricted_worker(task_queue, result_queue, FakeTimer())

        result = result_queue.get_nowait()
        self.assertTrue(result["success"])
        self.assertEqual(result["result"], 7)

    @patch("ghostwriter.home.django_q_cluster.pydoc.locate")
    @patch("ghostwriter.home.django_q_cluster.q_worker.rss_check", return_value=False)
    @patch("ghostwriter.home.django_q_cluster.q_worker.setproctitle", None)
    def test_worker_denies_task_before_import_and_acknowledges_failure(
        self, _rss_check, locate_mock
    ):
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        task_queue.put(
            {
                "id": "blocked-id",
                "name": "blocked",
                "func": "os.system",
                "args": ("id",),
                "kwargs": {},
                "started": timezone.now(),
            }
        )
        task_queue.put("STOP")

        restricted_worker(task_queue, result_queue, FakeTimer())

        result = result_queue.get_nowait()
        self.assertFalse(result["success"])
        self.assertTrue(result["ack_failure"])
        self.assertIn("blocked by server policy", result["result"])
        locate_mock.assert_not_called()

    @patch("ghostwriter.home.django_q_integration.pydoc.locate")
    def test_result_hook_is_denied_before_import(self, locate_mock):
        task = SimpleNamespace(pk="task-id", hook="os.system")

        call_allowed_hook(None, task)

        locate_mock.assert_not_called()
