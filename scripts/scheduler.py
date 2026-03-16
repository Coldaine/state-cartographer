"""Scheduler — picks the next task to run based on priority, time, and resources.

The scheduler is the runtime heart. It inspects the task manifest and resource
store, determines which tasks are ready to run, and returns them in priority
order.

This module provides the decision logic. The actual execution loop lives in
executor.py. Keeping them separate means the scheduler can be tested without
needing ADB or any live system.
"""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON file as a dict."""
    with open(path) as f:
        return json.load(f)


# Default priority order — lower index = higher priority.
# Recovery tasks always run first, then collection tasks, then farming.
DEFAULT_PRIORITY = [
    "restart",
    "login",
    "reward",
    "commission",
    "research",
    "dorm",
    "meowfficer",
    "guild",
    "daily",
    "hard",
    "exercise",
    "event",
    "campaign",
    "retire",
    "shop",
]


def get_ready_tasks(
    manifest: dict[str, Any],
    now: datetime,
    resources: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    """Return all tasks that are enabled and due to run.

    A task is "ready" if:
      1. enabled is not False
      2. next_run is None (never been scheduled) or next_run <= now
      3. All resource_requirements (if any) are met

    Returns a list of dicts: [{"task_id": str, "task": dict, "next_run": datetime|None}, ...]
    """
    ready = []
    tasks = manifest.get("tasks", {})

    for task_id, task_def in tasks.items():
        if not task_def.get("enabled", True):
            continue

        next_run = _parse_next_run(task_def.get("next_run"))
        if next_run is not None and next_run > now:
            continue

        if resources and not _check_resource_requirements(task_def, resources):
            continue

        ready.append(
            {
                "task_id": task_id,
                "task": task_def,
                "next_run": next_run,
            }
        )

    return ready


def get_waiting_tasks(
    manifest: dict[str, Any],
    now: datetime,
) -> list[dict[str, Any]]:
    """Return all enabled tasks that are not yet due, sorted by next_run asc.

    These are tasks the scheduler would pick up once their time comes.
    """
    waiting = []
    tasks = manifest.get("tasks", {})

    for task_id, task_def in tasks.items():
        if not task_def.get("enabled", True):
            continue

        next_run = _parse_next_run(task_def.get("next_run"))
        if next_run is None or next_run <= now:
            continue

        waiting.append(
            {
                "task_id": task_id,
                "task": task_def,
                "next_run": next_run,
            }
        )

    waiting.sort(key=lambda t: t["next_run"])
    return waiting


def pick_next(
    manifest: dict[str, Any],
    now: datetime,
    resources: dict[str, Any] | None = None,
    priority_order: list[str] | None = None,
) -> dict[str, Any] | None:
    """Pick the single highest-priority ready task.

    Returns {"task_id": str, "task": dict, "next_run": datetime|None}
    or None if no tasks are ready.

    Priority is determined by position in priority_order (lower index = higher).
    Tasks not in the priority list sort after those that are.
    """
    ready = get_ready_tasks(manifest, now, resources)
    if not ready:
        return None

    order = priority_order or DEFAULT_PRIORITY

    def sort_key(entry: dict[str, Any]) -> tuple[int, str]:
        task_id = entry["task_id"]
        try:
            idx = order.index(task_id)
        except ValueError:
            idx = len(order)
        return (idx, task_id)

    ready.sort(key=sort_key)
    return ready[0]


def next_wakeup(
    manifest: dict[str, Any],
    now: datetime,
) -> datetime | None:
    """Return the datetime when the next waiting task becomes due.

    Returns None if there are no waiting tasks (everything is ready or disabled).
    """
    waiting = get_waiting_tasks(manifest, now)
    if not waiting:
        return None
    return waiting[0]["next_run"]


def compute_next_run(
    task_def: dict[str, Any],
    now: datetime,
) -> datetime:
    """Compute the next_run for a task after it completes.

    Based on the task's schedule definition:
      - "interval": now + interval_minutes
      - "server_reset": next server reset time
      - "one_shot": far future (effectively disabled after running)
      - "manual": far future (agent must re-enable)
    """
    from datetime import timedelta

    schedule = task_def.get("schedule", {})
    stype = schedule.get("type", "manual")

    if stype == "interval":
        minutes = schedule.get("interval_minutes", 60)
        return now + timedelta(minutes=minutes)

    if stype == "server_reset":
        reset_hour = schedule.get("reset_hour", 0)
        # Next reset is tomorrow at reset_hour if we're past it today
        candidate = now.replace(hour=reset_hour, minute=0, second=1, microsecond=0)
        if candidate <= now:
            candidate += timedelta(days=1)
        return candidate

    if stype in ("one_shot", "manual"):
        # Set far future — task won't run again until manually rescheduled
        return now + timedelta(days=365 * 10)

    # Unknown schedule type — default to 1 hour
    return now + timedelta(hours=1)


def format_schedule(
    manifest: dict[str, Any],
    now: datetime,
) -> list[dict[str, str]]:
    """Return a human-readable schedule summary for display.

    Returns a list of dicts with task_id, status, next_run_str, schedule_type.
    """
    result = []
    tasks = manifest.get("tasks", {})

    for task_id, task_def in tasks.items():
        enabled = task_def.get("enabled", True)
        next_run = _parse_next_run(task_def.get("next_run"))
        schedule = task_def.get("schedule", {})
        stype = schedule.get("type", "manual")

        if not enabled:
            status = "disabled"
        elif next_run is None or next_run <= now:
            status = "ready"
        else:
            status = "waiting"

        result.append(
            {
                "task_id": task_id,
                "status": status,
                "next_run": next_run.isoformat() if next_run else "now",
                "schedule_type": stype,
            }
        )

    return result


def _parse_next_run(value: Any) -> datetime | None:
    """Parse a next_run value into a datetime or None."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=UTC)
        return dt
    return None


def _check_resource_requirements(
    task_def: dict[str, Any],
    resources: dict[str, Any],
) -> bool:
    """Check if all resource requirements for a task are met."""
    reqs = task_def.get("resource_requirements", {})
    res_store = resources.get("resources", {})

    for res_name, constraint in reqs.items():
        entry = res_store.get(res_name)
        if entry is None:
            continue  # Unknown resources don't block

        value = entry.get("value")
        if not isinstance(value, (int, float)):
            continue

        min_val = constraint.get("min")
        if min_val is not None and value < min_val:
            return False

        max_val = constraint.get("max")
        if max_val is not None and value > max_val:
            return False

    return True


def main() -> None:
    """CLI entry point for scheduler — shows schedule status."""
    parser = argparse.ArgumentParser(description="Task scheduler — show what runs next")
    parser.add_argument("--tasks", required=True, help="Path to tasks.json")
    parser.add_argument("--resources", help="Path to resource store JSON")
    parser.add_argument("--dry-run", action="store_true", help="Show the schedule without executing anything")

    args = parser.parse_args()

    manifest = load_json(Path(args.tasks))
    resources = load_json(Path(args.resources)) if args.resources else None
    now = datetime.now(tz=UTC)

    if args.dry_run:
        schedule = format_schedule(manifest, now)
        print(json.dumps(schedule, indent=2))

        pick = pick_next(manifest, now, resources)
        if pick:
            print(f"\nNext task: {pick['task_id']}")
        else:
            wake = next_wakeup(manifest, now)
            if wake:
                delta = wake - now
                mins = int(delta.total_seconds() / 60)
                print(f"\nNo tasks ready. Next wakeup in {mins} minutes.")
            else:
                print("\nNo tasks scheduled.")
    else:
        pick = pick_next(manifest, now, resources)
        if pick:
            print(json.dumps({"next": pick["task_id"]}, indent=2))
        else:
            print(json.dumps({"next": None}, indent=2))


if __name__ == "__main__":
    main()
