"""Tests for scheduler.py — priority ordering, NextRun logic, resource gating."""

from __future__ import annotations

import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from scheduler import (
    compute_next_run,
    format_schedule,
    get_ready_tasks,
    get_waiting_tasks,
    next_wakeup,
    pick_next,
)

# --- Fixtures ---

NOW = datetime(2026, 3, 16, 12, 0, 0, tzinfo=UTC)
PAST = "2020-01-01T00:00:00"
FUTURE = "2030-01-01T00:00:00"


def make_manifest(*tasks):
    """Helper to build a task manifest from (id, next_run, enabled) tuples."""
    manifest = {"tasks": {}}
    for t in tasks:
        task_id = t[0]
        next_run = t[1] if len(t) > 1 else None
        enabled = t[2] if len(t) > 2 else True
        manifest["tasks"][task_id] = {
            "entry_state": f"page_{task_id}",
            "schedule": {"type": "interval", "interval_minutes": 60},
            "enabled": enabled,
            "next_run": next_run,
            "actions": [],
        }
    return manifest


# --- Ready tasks ---


class TestGetReadyTasks:
    def test_past_next_run_is_ready(self):
        m = make_manifest(("commission", PAST))
        ready = get_ready_tasks(m, NOW)
        assert len(ready) == 1
        assert ready[0]["task_id"] == "commission"

    def test_future_next_run_is_not_ready(self):
        m = make_manifest(("commission", FUTURE))
        ready = get_ready_tasks(m, NOW)
        assert len(ready) == 0

    def test_null_next_run_is_ready(self):
        m = make_manifest(("commission", None))
        ready = get_ready_tasks(m, NOW)
        assert len(ready) == 1

    def test_disabled_task_not_ready(self):
        m = make_manifest(("commission", PAST, False))
        ready = get_ready_tasks(m, NOW)
        assert len(ready) == 0

    def test_multiple_ready(self):
        m = make_manifest(("reward", PAST), ("commission", PAST))
        ready = get_ready_tasks(m, NOW)
        assert len(ready) == 2

    def test_resource_gating_blocks(self):
        m = make_manifest(("daily", PAST))
        m["tasks"]["daily"]["resource_requirements"] = {"oil": {"min": 500}}
        resources = {"resources": {"oil": {"value": 100}}}
        ready = get_ready_tasks(m, NOW, resources)
        assert len(ready) == 0

    def test_resource_gating_passes(self):
        m = make_manifest(("daily", PAST))
        m["tasks"]["daily"]["resource_requirements"] = {"oil": {"min": 100}}
        resources = {"resources": {"oil": {"value": 500}}}
        ready = get_ready_tasks(m, NOW, resources)
        assert len(ready) == 1


# --- Waiting tasks ---


class TestGetWaitingTasks:
    def test_future_task_is_waiting(self):
        m = make_manifest(("commission", FUTURE))
        waiting = get_waiting_tasks(m, NOW)
        assert len(waiting) == 1
        assert waiting[0]["task_id"] == "commission"

    def test_past_task_not_waiting(self):
        m = make_manifest(("commission", PAST))
        waiting = get_waiting_tasks(m, NOW)
        assert len(waiting) == 0

    def test_sorted_by_next_run(self):
        m = make_manifest(
            ("later", "2028-01-01T00:00:00"),
            ("sooner", "2027-01-01T00:00:00"),
        )
        waiting = get_waiting_tasks(m, NOW)
        assert waiting[0]["task_id"] == "sooner"
        assert waiting[1]["task_id"] == "later"


# --- Pick next ---


class TestPickNext:
    def test_picks_highest_priority(self):
        m = make_manifest(("commission", PAST), ("reward", PAST))
        pick = pick_next(m, NOW)
        assert pick is not None
        # reward is higher priority than commission in DEFAULT_PRIORITY
        assert pick["task_id"] == "reward"

    def test_returns_none_when_nothing_ready(self):
        m = make_manifest(("commission", FUTURE))
        pick = pick_next(m, NOW)
        assert pick is None

    def test_custom_priority_order(self):
        m = make_manifest(("commission", PAST), ("reward", PAST))
        pick = pick_next(m, NOW, priority_order=["commission", "reward"])
        assert pick["task_id"] == "commission"

    def test_unknown_tasks_sort_last(self):
        m = make_manifest(("custom_task", PAST), ("reward", PAST))
        pick = pick_next(m, NOW)
        assert pick["task_id"] == "reward"


# --- Next wakeup ---


class TestNextWakeup:
    def test_returns_earliest_waiting(self):
        m = make_manifest(
            ("later", "2028-01-01T00:00:00"),
            ("sooner", "2027-01-01T00:00:00"),
        )
        wake = next_wakeup(m, NOW)
        assert wake is not None
        assert wake.year == 2027

    def test_none_when_all_ready(self):
        m = make_manifest(("commission", PAST))
        assert next_wakeup(m, NOW) is None

    def test_none_when_empty(self):
        assert next_wakeup({"tasks": {}}, NOW) is None


# --- Compute next run ---


class TestComputeNextRun:
    def test_interval(self):
        task = {"schedule": {"type": "interval", "interval_minutes": 60}}
        nr = compute_next_run(task, NOW)
        assert nr == NOW + timedelta(minutes=60)

    def test_server_reset_same_day(self):
        # NOW is 12:00 UTC — reset at hour 0 should be tomorrow
        task = {"schedule": {"type": "server_reset", "reset_hour": 0}}
        nr = compute_next_run(task, NOW)
        assert nr.day == NOW.day + 1
        assert nr.hour == 0

    def test_server_reset_later_today(self):
        # NOW is 12:00 UTC — reset at hour 18 should be today
        task = {"schedule": {"type": "server_reset", "reset_hour": 18}}
        nr = compute_next_run(task, NOW)
        assert nr.day == NOW.day
        assert nr.hour == 18

    def test_one_shot(self):
        task = {"schedule": {"type": "one_shot"}}
        nr = compute_next_run(task, NOW)
        assert nr > NOW + timedelta(days=365)

    def test_manual(self):
        task = {"schedule": {"type": "manual"}}
        nr = compute_next_run(task, NOW)
        assert nr > NOW + timedelta(days=365)


# --- Format schedule ---


class TestFormatSchedule:
    def test_shows_ready_and_waiting(self):
        m = make_manifest(("reward", PAST), ("commission", FUTURE))
        schedule = format_schedule(m, NOW)
        assert len(schedule) == 2

        by_id = {s["task_id"]: s for s in schedule}
        assert by_id["reward"]["status"] == "ready"
        assert by_id["commission"]["status"] == "waiting"

    def test_shows_disabled(self):
        m = make_manifest(("reward", PAST, False))
        schedule = format_schedule(m, NOW)
        assert schedule[0]["status"] == "disabled"
