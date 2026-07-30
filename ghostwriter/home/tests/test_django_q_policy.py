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
from django.core.exceptions import ImproperlyConfigured, ValidationError
from django.core.management import call_command
from django.core.management.base import CommandError
from django.db.models.signals import post_save
from django.test import SimpleTestCase, TestCase, override_settings
from django.utils import timezone

# 3rd Party Libraries
from django_q.conf import Conf
from django_q.exceptions import TimeoutException
from django_q.models import Failure, Schedule, Success, Task
from django_q.signals import call_hook
from django_q.tasks import async_task

# Ghostwriter Libraries
from ghostwriter.home import django_q_tasks
from ghostwriter.home.admin import RestrictedScheduleAdmin, RestrictedScheduleForm
from ghostwriter.home.django_q_cluster import restricted_scheduler, restricted_worker
from ghostwriter.home.django_q_integration import (
    call_allowed_hook,
    install_django_q_restrictions,
    validate_schedule_on_save,
)
from ghostwriter.home.django_q_policy import (
    COMMAND_RUNNER,
    TaskPolicyError,
    callable_path,
    get_schedule_policy,
    parse_schedule_arguments,
    validate_policy_configuration,
    validate_schedule,
    validate_task,
)


def allowed_test_task(value):
    """Return a value for restricted-worker tests."""
    return value


def failing_test_task():
    """Raise an ordinary task exception for restricted-worker tests."""
    raise RuntimeError("expected task failure")


def allowed_test_hook(task):
    """Mark a task when an approved test hook is called."""
    task.hook_called = True


def failing_test_hook(task):
    """Raise an ordinary hook exception for hook-isolation tests."""
    raise RuntimeError(f"expected hook failure for {task.pk}")


TEST_TASK_PATH = "ghostwriter.home.tests.test_django_q_policy.allowed_test_task"
FAILING_TEST_TASK_PATH = "ghostwriter.home.tests.test_django_q_policy.failing_test_task"
TEST_HOOK_PATH = "ghostwriter.home.tests.test_django_q_policy.allowed_test_hook"
FAILING_TEST_HOOK_PATH = "ghostwriter.home.tests.test_django_q_policy.failing_test_hook"
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
    def test_callable_path_accepts_function(self):
        self.assertEqual(callable_path(allowed_test_task), TEST_TASK_PATH)

    def test_callable_path_rejects_non_callable_and_malformed_values(self):
        for value in (object(), "not-a-dotted-path"):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TaskPolicyError, "exact dotted path"):
                    callable_path(value)

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

    def test_builtin_argument_constraints_are_enforced(self):
        path = "ghostwriter.modules.oplog_monitors.review_active_logs"
        for value, message in (
            (True, "must be a int"),
            (0, "below the allowed minimum"),
            (8761, "exceeds the allowed maximum"),
        ):
            with self.subTest(value=value):
                with self.assertRaisesRegex(TaskPolicyError, message):
                    validate_task(path, args=(value,), schedule_only=True)

        validate_task(
            "ghostwriter.shepherd.tasks.check_domains",
            args=(None,),
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

    def test_schedule_arguments_accept_single_values_and_mapping_syntax(self):
        args, kwargs = parse_schedule_arguments("1", "{'enabled': True}")

        self.assertEqual(args, (1,))
        self.assertEqual(kwargs, {"enabled": True})

    def test_schedule_arguments_accept_python_values(self):
        args, kwargs = parse_schedule_arguments((1, 2), {"enabled": True})

        self.assertEqual(args, (1, 2))
        self.assertEqual(kwargs, {"enabled": True})

    def test_schedule_arguments_reject_code(self):
        with self.assertRaises(TaskPolicyError):
            parse_schedule_arguments("__import__('os').system('id')", "")

    def test_schedule_arguments_reject_kwargs_expansion_and_duplicates(self):
        for kwargs in (
            "1",
            "**{'enabled': True}",
            "enabled=True, enabled=False",
        ):
            with self.subTest(kwargs=kwargs):
                with self.assertRaisesRegex(
                    TaskPolicyError,
                    "Keyword arguments must contain Python literals",
                ):
                    parse_schedule_arguments("", kwargs)

    def test_schedule_arguments_reject_non_mapping_kwargs(self):
        with self.assertRaisesRegex(TaskPolicyError, "must be a mapping"):
            parse_schedule_arguments("", object())

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

        result = django_q_tasks.run_configured_command("backup")

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

    @override_settings(
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={
            "not a dotted path": {},
            TEST_TASK_PATH: {
                "args": [{"type": "int", "min": "1"}],
                "kwargs": {},
            },
        }
    )
    def test_policy_configuration_reports_multiple_errors(self):
        errors = validate_policy_configuration()

        self.assertGreaterEqual(len(errors), 2)
        self.assertTrue(
            any("exact dotted path" in error for error in errors),
            errors,
        )
        self.assertTrue(
            any("Policy min" in error for error in errors),
            errors,
        )

    @override_settings(
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={
            TEST_TASK_PATH: {
                "args": [{"type": "int", "min": "1"}],
                "kwargs": {},
            }
        }
    )
    def test_invalid_policy_bound_fails_closed_at_runtime(self):
        with self.assertRaisesRegex(TaskPolicyError, "Policy min"):
            validate_task(TEST_TASK_PATH, args=(1,), schedule_only=True)

    @override_settings(
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={
            TEST_TASK_PATH: {
                "args": [{"type": "int", "min": 5, "max": 1}],
                "kwargs": {},
            }
        }
    )
    def test_policy_configuration_rejects_inverted_bounds(self):
        self.assertTrue(
            any(
                "minimum greater than its maximum" in error
                for error in validate_policy_configuration()
            )
        )

    def test_command_policy_reports_each_invalid_definition(self):
        invalid_commands = (
            {1: {"argv": ["/bin/true"]}},
            {"bad": "not-a-mapping"},
            {"bad": {"argv": []}},
            {"bad": {"argv": ["/bin/true"], "shell": False}},
            {"bad": {"argv": ["/bin/true"], "cwd": "relative"}},
            {"bad": {"argv": ["/bin/true"], "timeout": 0}},
            {"bad": {"argv": ["/bin/true"], "env": {"KEY": 1}}},
        )
        for commands in invalid_commands:
            with self.subTest(commands=commands):
                with override_settings(GHOSTWRITER_DJANGO_Q_COMMANDS=commands):
                    self.assertTrue(validate_policy_configuration())

    def test_policy_configuration_validates_each_schema_shape(self):
        invalid_specifications = (
            "not-a-mapping",
            {"args": "not-a-list", "kwargs": {}},
            {"args": [], "kwargs": "not-a-mapping"},
            {"args": ["not-a-mapping"], "kwargs": {}},
            {"args": [{"type": "unsupported"}], "kwargs": {}},
            {
                "args": [{"name": "", "type": "int"}],
                "kwargs": {},
            },
            {
                "args": [
                    {"name": "first", "type": "int", "required": False},
                    {"name": "second", "type": "int"},
                ],
                "kwargs": {},
            },
            {
                "args": [{"type": "int", "choices": "not-a-list"}],
                "kwargs": {},
            },
            {
                "args": [],
                "kwargs": {},
                "required_parameters": ["missing"],
            },
        )
        for specification in invalid_specifications:
            with self.subTest(specification=specification):
                with override_settings(
                    GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={TEST_TASK_PATH: specification}
                ):
                    self.assertTrue(validate_policy_configuration())

    @override_settings(
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS=[],
        GHOSTWRITER_DJANGO_Q_SCHEDULE_HOOKS=[],
        GHOSTWRITER_DJANGO_Q_COMMANDS=[],
    )
    def test_policy_configuration_aggregates_invalid_mapping_settings(self):
        errors = validate_policy_configuration()

        self.assertEqual(len(errors), 3)

    @override_settings(
        GHOSTWRITER_DJANGO_Q_SCHEDULE_HOOKS={TEST_HOOK_PATH: "not-a-mapping"}
    )
    def test_policy_configuration_rejects_invalid_hook_schema(self):
        self.assertTrue(validate_policy_configuration())

    @override_settings(GHOSTWRITER_DJANGO_Q_COMMANDS={1: {"argv": ["/bin/true"]}})
    def test_schedule_policy_rejects_invalid_command_name(self):
        with self.assertRaisesRegex(TaskPolicyError, "Command names"):
            get_schedule_policy()

    @override_settings(GHOSTWRITER_DJANGO_Q_COMMANDS={})
    @patch("ghostwriter.home.django_q_tasks.call_command")
    def test_clear_expired_sessions_uses_narrow_management_command(
        self, call_command_mock
    ):
        django_q_tasks.clear_expired_sessions()

        call_command_mock.assert_called_once_with("clear_expired_sessions")

    def test_command_runner_rejects_unknown_command(self):
        with self.assertRaisesRegex(TaskPolicyError, "not approved"):
            django_q_tasks.run_configured_command("missing")

    def test_schedule_rejects_intended_date_keyword(self):
        schedule = Schedule(
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            intended_date_kwarg="run_at",
        )

        with self.assertRaisesRegex(TaskPolicyError, "intended-date"):
            validate_schedule(schedule)

    def test_task_rejects_unapproved_hook(self):
        with self.assertRaisesRegex(TaskPolicyError, "hook policy"):
            validate_task(
                "ghostwriter.home.django_q_tasks.clear_expired_sessions",
                hook="os.system",
                schedule_only=True,
            )


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

    def test_schedule_admin_allows_cluster_routing_only(self):
        model_admin = admin.site._registry[Schedule]

        self.assertNotIn("cluster", model_admin.readonly_fields)
        self.assertIn("cluster", RestrictedScheduleForm().fields)
        self.assertIn("intended_date_kwarg", model_admin.readonly_fields)

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
        with self.assertRaises(ValidationError) as raised:
            Schedule.objects.create(
                name="Malicious",
                func="os.system",
                args="'id'",
                schedule_type=Schedule.DAILY,
            )

        self.assertFalse(hasattr(raised.exception, "error_dict"))
        self.assertIn("os.system is not permitted", raised.exception.messages[0])

    def test_audit_command_reports_clean_policy(self):
        stdout = StringIO()

        call_command("audit_django_q_policy", "--check", stdout=stdout)

        self.assertIn("All Django Q schedules satisfy", stdout.getvalue())

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
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.get_broker")
    def test_scheduler_uses_configured_broker(
        self, get_broker_mock, _close_connections
    ):
        get_broker_mock.return_value = Mock()

        restricted_scheduler()

        get_broker_mock.assert_called_once_with()

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

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.logger")
    @patch("ghostwriter.home.django_q_cluster._enqueue_schedule")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    def test_scheduler_isolates_unexpected_schedule_failure(
        self, _close_connections, enqueue_mock, logger_mock
    ):
        for name in ("First", "Second"):
            Schedule.objects.create(
                name=name,
                func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
                schedule_type=Schedule.DAILY,
                repeats=-1,
                next_run=timezone.now(),
                cluster=Conf.CLUSTER_NAME,
            )
        enqueue_mock.side_effect = [RuntimeError("expected failure"), None]

        restricted_scheduler(broker=Mock())

        self.assertEqual(enqueue_mock.call_count, 2)
        logger_mock.exception.assert_called_once()

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.logger")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.db.transaction.atomic",
        side_effect=RuntimeError("database unavailable"),
    )
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    def test_scheduler_logs_backend_failure(
        self, _close_connections, _atomic, logger_mock
    ):
        restricted_scheduler(broker=Mock())

        logger_mock.exception.assert_called_once_with(
            "Could not inspect Django Q schedules"
        )

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.async_task")
    def test_scheduler_advances_recurring_schedule(
        self, async_task_mock, _close_connections
    ):
        async_task_mock.return_value = "0123456789abcdef0123456789abcdef"
        original_next_run = timezone.now()
        schedule = Schedule.objects.create(
            name="Recurring cleanup",
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            schedule_type=Schedule.DAILY,
            repeats=2,
            next_run=original_next_run,
            cluster=Conf.CLUSTER_NAME,
        )

        restricted_scheduler(broker=Mock())

        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 1)
        self.assertGreater(schedule.next_run, original_next_run)

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.async_task")
    def test_scheduler_preserves_approved_hook_and_normalizes_repeats(
        self, async_task_mock, _close_connections
    ):
        async_task_mock.return_value = "0123456789abcdef0123456789abcdef"
        schedule = Schedule.objects.create(
            name="Hooked cleanup",
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            hook="ghostwriter.modules.notifications_slack.send_slack_complete_msg",
            schedule_type=Schedule.DAILY,
            repeats=-2,
            next_run=timezone.now(),
            cluster=Conf.CLUSTER_NAME,
        )

        restricted_scheduler(broker=Mock())

        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, -1)
        q_options = async_task_mock.call_args.kwargs["q_options"]
        self.assertEqual(q_options["hook"], schedule.hook)

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.logger")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.async_task",
        return_value=None,
    )
    def test_scheduler_records_enqueue_failure(
        self, _async_task, _close_connections, logger_mock
    ):
        schedule = Schedule.objects.create(
            name="Failed enqueue",
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            schedule_type=Schedule.ONCE,
            repeats=1,
            next_run=timezone.now(),
            cluster=Conf.CLUSTER_NAME,
        )

        restricted_scheduler(broker=Mock())

        logger_mock.error.assert_called_once()
        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 0)

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.async_task")
    def test_scheduler_deletes_completed_one_time_schedule(
        self, async_task_mock, _close_connections
    ):
        async_task_mock.return_value = "0123456789abcdef0123456789abcdef"
        schedule = Schedule.objects.create(
            name="One time cleanup",
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions",
            schedule_type=Schedule.ONCE,
            repeats=-1,
            next_run=timezone.now(),
            cluster=Conf.CLUSTER_NAME,
        )

        restricted_scheduler(broker=Mock())

        self.assertFalse(Schedule.objects.filter(pk=schedule.pk).exists())


class WorkerPolicyTests(SimpleTestCase):
    def test_raw_schedule_save_skips_policy_validation(self):
        validate_schedule_on_save(
            Schedule,
            Schedule(func="os.system"),
            raw=True,
        )

    def test_result_without_hook_needs_no_policy_check(self):
        call_allowed_hook(None, SimpleNamespace(pk="task-id", hook=None))

    @override_settings(GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS=[])
    def test_install_restrictions_rejects_invalid_policy(self):
        with self.assertRaisesRegex(ImproperlyConfigured, "server policy"):
            install_django_q_restrictions()

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

    @override_settings(
        GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS={
            FAILING_TEST_TASK_PATH: {"args": [], "kwargs": {}}
        },
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={},
    )
    @patch("ghostwriter.home.django_q_cluster.q_worker.rss_check", return_value=False)
    @patch("ghostwriter.home.django_q_cluster.q_worker.setproctitle", None)
    def test_worker_records_approved_task_exception(self, _rss_check):
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        task_queue.put(
            {
                "id": "failure-id",
                "name": "failure",
                "func": FAILING_TEST_TASK_PATH,
                "args": (),
                "kwargs": {},
                "started": timezone.now(),
            }
        )
        task_queue.put("STOP")

        restricted_worker(task_queue, result_queue, FakeTimer())

        result = result_queue.get_nowait()
        self.assertFalse(result["success"])
        self.assertIn("expected task failure", result["result"])

    @override_settings(
        GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS=TEST_TASK_POLICY,
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={},
    )
    @patch(
        "ghostwriter.home.django_q_cluster.q_worker.TimeoutHandler",
        side_effect=TimeoutException,
    )
    @patch("ghostwriter.home.django_q_cluster.q_worker.setproctitle", None)
    def test_worker_records_timeout_and_stops(self, _timeout_handler):
        task_queue = queue.Queue()
        result_queue = queue.Queue()
        timer = FakeTimer()
        task_queue.put(
            {
                "id": "timeout-id",
                "name": "timeout",
                "func": TEST_TASK_PATH,
                "args": (7,),
                "kwargs": {},
                "started": timezone.now(),
            }
        )

        restricted_worker(task_queue, result_queue, timer)

        result = result_queue.get_nowait()
        self.assertFalse(result["success"])
        self.assertEqual(timer.value, 0)

    @override_settings(
        GHOSTWRITER_DJANGO_Q_INTERNAL_TASKS={
            FAILING_TEST_TASK_PATH: {"args": [], "kwargs": {}}
        },
        GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={},
    )
    @patch("ghostwriter.home.django_q_cluster.q_worker.setproctitle", None)
    def test_synchronous_worker_reraises_task_exception(self):
        task_queue = queue.Queue()
        task_queue.put(
            {
                "id": "sync-failure-id",
                "name": "sync failure",
                "func": FAILING_TEST_TASK_PATH,
                "args": (),
                "kwargs": {},
                "sync": True,
                "started": timezone.now(),
            }
        )

        with self.assertRaisesRegex(RuntimeError, "expected task failure"):
            restricted_worker(task_queue, queue.Queue(), FakeTimer())

    @patch("ghostwriter.home.django_q_integration.pydoc.locate")
    def test_result_hook_is_denied_before_import(self, locate_mock):
        task = SimpleNamespace(pk="task-id", hook="os.system")

        call_allowed_hook(None, task)

        locate_mock.assert_not_called()

    @override_settings(GHOSTWRITER_DJANGO_Q_INTERNAL_HOOKS={TEST_HOOK_PATH: {}})
    @patch("ghostwriter.home.django_q_integration.logger")
    @patch("ghostwriter.home.django_q_integration.pydoc.locate", return_value=None)
    def test_missing_approved_result_hook_is_blocked(self, _locate, logger_mock):
        task = SimpleNamespace(pk="task-id", hook=TEST_HOOK_PATH)

        call_allowed_hook(None, task)

        logger_mock.error.assert_called_once()

    @override_settings(GHOSTWRITER_DJANGO_Q_INTERNAL_HOOKS={TEST_HOOK_PATH: {}})
    def test_approved_result_hook_runs(self):
        task = SimpleNamespace(pk="task-id", hook=TEST_HOOK_PATH)

        call_allowed_hook(None, task)

        self.assertTrue(task.hook_called)

    @override_settings(GHOSTWRITER_DJANGO_Q_INTERNAL_HOOKS={FAILING_TEST_HOOK_PATH: {}})
    @patch("ghostwriter.home.django_q_integration.logger")
    def test_approved_result_hook_failure_is_isolated(self, logger_mock):
        task = SimpleNamespace(pk="task-id", hook=FAILING_TEST_HOOK_PATH)

        call_allowed_hook(None, task)

        logger_mock.exception.assert_called_once_with(
            "Approved Django Q result hook failed for task %s",
            "task-id",
        )
