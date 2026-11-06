"""Tests for shared background dashboard monitoring."""

# Standard Libraries
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from importlib import import_module
from threading import Barrier
from types import SimpleNamespace
from unittest.mock import Mock, patch

# Django Imports
from django.apps import apps
from django.core.management import call_command
from django.db import connections
from django.db.models.query import QuerySet
from django.test import TestCase, TransactionTestCase, override_settings
from django.utils import timezone

# 3rd Party Libraries
from django_q.conf import Conf
from django_q.models import Schedule

# Ghostwriter Libraries
from ghostwriter.home.django_q_cluster import restricted_scheduler
from ghostwriter.status.health import (
    DASHBOARD_HEALTH_MAX_AGE,
    HEALTH_SCHEDULE_NAME,
    HEALTH_TASK,
    ensure_dashboard_health_schedule,
    get_dashboard_health_summary,
)
from ghostwriter.status.models import DashboardHealthSnapshot

migration = import_module("ghostwriter.status.migrations.0002_dashboardhealthsnapshot")


class DashboardHealthSnapshotTests(TestCase):
    def setUp(self):
        DashboardHealthSnapshot.objects.all().delete()

    def test_snapshot_age_boundaries_do_not_probe_or_return_outdated_health(self):
        now = timezone.now()
        for state in ("OK", "WARNING", "ERROR"):
            for age, expected in (
                (timedelta(0), state),
                (DASHBOARD_HEALTH_MAX_AGE, state),
                (DASHBOARD_HEALTH_MAX_AGE + timedelta(seconds=1), "UNKNOWN"),
                (timedelta(seconds=-1), "UNKNOWN"),
            ):
                with self.subTest(state=state, age=age):
                    DashboardHealthSnapshot.objects.update_or_create(
                        pk=1,
                        defaults={
                            "checked_at": now - age,
                            "summary": {"state": state, "issues": []},
                        },
                    )
                    with patch(
                        "ghostwriter.status.health.timezone.now", return_value=now
                    ):
                        self.assertEqual(
                            get_dashboard_health_summary()["state"], expected
                        )

    def test_missing_snapshot_is_unknown(self):
        self.assertEqual(
            get_dashboard_health_summary(), {"state": "UNKNOWN", "issues": []}
        )


class DashboardHealthScheduleTests(TestCase):
    def setUp(self):
        Schedule.objects.all().delete()
        DashboardHealthSnapshot.objects.all().delete()
        self.schema_editor = SimpleNamespace(
            connection=SimpleNamespace(alias="default")
        )

    def test_restoration_preserves_renamed_customized_and_paused_monitor(self):
        schedule = ensure_dashboard_health_schedule()
        schedule.name = "Custom monitor name"
        schedule.minutes = 5
        schedule.repeats = 0
        schedule.save()

        with self.assertNumQueries(1):
            restored = ensure_dashboard_health_schedule()

        self.assertEqual(restored.pk, schedule.pk)
        self.assertEqual(restored.name, "Custom monitor name")
        self.assertEqual(restored.minutes, 5)
        self.assertEqual(restored.repeats, 0)
        self.assertEqual(Schedule.objects.count(), 1)

    def test_restoration_preserves_existing_health_result(self):
        now = timezone.now()
        summary = {"state": "ERROR", "issues": []}
        snapshot = DashboardHealthSnapshot.objects.create(
            checked_at=now, summary=summary
        )

        ensure_dashboard_health_schedule()

        snapshot.refresh_from_db()
        self.assertEqual(snapshot.checked_at, now)
        self.assertEqual(snapshot.summary, summary)

    @override_settings(GHOSTWRITER_DJANGO_Q_SCHEDULE_TASKS={})
    def test_restoration_respects_server_policy_without_database_queries(self):
        with self.assertNumQueries(0):
            self.assertIsNone(ensure_dashboard_health_schedule())

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.async_task",
        return_value="0123456789abcdef0123456789abcdef",
    )
    def test_scheduler_restores_deleted_monitor(self, enqueue, _close_connections):
        migration.create_health_schedule(apps, self.schema_editor)
        Schedule.objects.filter(func=HEALTH_TASK).delete()

        restricted_scheduler(broker=Mock())

        schedule = Schedule.objects.get(func=HEALTH_TASK)
        self.assertEqual(schedule.name, HEALTH_SCHEDULE_NAME)
        self.assertEqual(schedule.minutes, 1)
        self.assertEqual(schedule.repeats, -1)
        self.assertEqual(get_dashboard_health_summary()["state"], "UNKNOWN")
        enqueue.assert_called_once()

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.async_task")
    def test_scheduler_preserves_paused_monitor(self, enqueue, _close_connections):
        schedule = ensure_dashboard_health_schedule()
        schedule.repeats = 0
        schedule.minutes = 5
        schedule.save()

        restricted_scheduler(broker=Mock())

        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 0)
        self.assertEqual(schedule.minutes, 5)
        self.assertEqual(Schedule.objects.count(), 1)
        enqueue.assert_not_called()

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.async_task",
        return_value="0123456789abcdef0123456789abcdef",
    )
    def test_monitor_skips_downtime_even_when_cluster_catches_up(
        self, enqueue, _close_connections
    ):
        now = timezone.now()
        schedule = Schedule.objects.create(
            func=HEALTH_TASK,
            name=HEALTH_SCHEDULE_NAME,
            schedule_type=Schedule.MINUTES,
            minutes=1,
            repeats=-1,
            next_run=now - timedelta(days=365),
            cluster=Conf.CLUSTER_NAME,
        )
        original_calculate = Schedule.calculate_next_run
        with patch.object(Conf, "CATCH_UP", True), patch(
            "ghostwriter.home.django_q_cluster.q_scheduler.localtime", return_value=now
        ), patch.object(
            Schedule,
            "calculate_next_run",
            autospec=True,
            side_effect=original_calculate,
        ) as calculate:
            restricted_scheduler(broker=Mock())
            restricted_scheduler(broker=Mock())

        schedule.refresh_from_db()
        self.assertEqual(schedule.next_run, now + timedelta(minutes=1))
        enqueue.assert_called_once()
        calculate.assert_called_once()

    def test_migration_installs_one_schedule_without_overwriting_admin_changes(self):
        migration.create_health_schedule(apps, self.schema_editor)
        schedule = Schedule.objects.get(func=migration.HEALTH_TASK)
        self.assertEqual(schedule.schedule_type, Schedule.MINUTES)
        self.assertEqual(schedule.minutes, 1)
        self.assertEqual(schedule.repeats, -1)
        schedule.repeats = 0
        schedule.minutes = 5
        schedule.save()

        migration.create_health_schedule(apps, self.schema_editor)

        self.assertEqual(Schedule.objects.count(), 1)
        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 0)
        self.assertEqual(schedule.minutes, 5)

    def test_reverse_migration_removes_only_its_monitor(self):
        migration.create_health_schedule(apps, self.schema_editor)
        other = Schedule.objects.create(
            func="ghostwriter.home.django_q_tasks.clear_expired_sessions"
        )

        migration.remove_health_schedule(apps, self.schema_editor)

        self.assertEqual(
            list(Schedule.objects.values_list("pk", flat=True)), [other.pk]
        )

    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.async_task",
        return_value="0123456789abcdef0123456789abcdef",
    )
    def test_scheduler_uses_bounded_monitor_options_from_server_policy(
        self, enqueue, _close_connections
    ):
        migration.create_health_schedule(apps, self.schema_editor)
        schedule = Schedule.objects.get(func=migration.HEALTH_TASK)
        schedule.cluster = Conf.CLUSTER_NAME
        schedule.next_run = timezone.now() - timedelta(seconds=1)
        schedule.save()
        broker = Mock()

        restricted_scheduler(broker=broker)

        enqueue.assert_called_once_with(
            migration.HEALTH_TASK,
            q_options={
                "timeout": 30,
                "save": False,
                "ack_failure": True,
                "cluster": Conf.CLUSTER_NAME,
                "broker": broker,
                "group": schedule.name,
            },
        )
        schedule.refresh_from_db()
        self.assertEqual(schedule.task, "0123456789abcdef0123456789abcdef")
        self.assertGreater(schedule.next_run, timezone.now())


class DashboardHealthRecoveryTests(TransactionTestCase):
    @patch("ghostwriter.home.django_q_cluster.q_scheduler.close_old_django_connections")
    @patch(
        "ghostwriter.home.django_q_cluster.q_scheduler.async_task",
        return_value="0123456789abcdef0123456789abcdef",
    )
    def test_scheduler_restores_monitor_after_database_reset(
        self, enqueue, _close_connections
    ):
        Schedule.objects.all().delete()
        call_command("flush", interactive=False, verbosity=0)
        call_command("migrate", verbosity=0)
        self.assertFalse(Schedule.objects.filter(func=HEALTH_TASK).exists())
        self.assertEqual(get_dashboard_health_summary()["state"], "UNKNOWN")

        restricted_scheduler(broker=Mock())

        schedule = Schedule.objects.get(func=HEALTH_TASK)
        self.assertEqual(schedule.minutes, 1)
        self.assertEqual(get_dashboard_health_summary()["state"], "UNKNOWN")
        enqueue.assert_called_once()
        schedule.repeats = 0
        schedule.save()
        restricted_scheduler(broker=Mock())
        schedule.refresh_from_db()
        self.assertEqual(schedule.repeats, 0)
        enqueue.assert_called_once()

    def test_concurrent_restoration_creates_one_schedule(self):
        Schedule.objects.all().delete()
        DashboardHealthSnapshot.objects.all().delete()
        barrier = Barrier(3)
        original_first = QuerySet.first

        def synchronize_missing_schedule(queryset):
            result = original_first(queryset)
            if queryset.model is Schedule and result is None:
                barrier.wait(timeout=10)
            return result

        def restore(_index):
            try:
                return ensure_dashboard_health_schedule().pk
            finally:
                connections.close_all()

        with patch.object(QuerySet, "first", synchronize_missing_schedule):
            with ThreadPoolExecutor(max_workers=3) as executor:
                schedule_ids = list(executor.map(restore, range(3)))

        self.assertEqual(len(set(schedule_ids)), 1)
        self.assertEqual(Schedule.objects.filter(func=HEALTH_TASK).count(), 1)
        self.assertEqual(DashboardHealthSnapshot.objects.count(), 1)
