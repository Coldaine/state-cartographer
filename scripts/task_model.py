"""Task model — data structures for schedulable automation tasks.

A Task is a named, schedulable unit of work with an entry state (which screen
to navigate to), an action sequence (what to do once there), an exit condition,
scheduling rules, and an error strategy.

Tasks are loaded from a tasks.json file that sits alongside graph.json.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load and return a JSON file as a dict."""
    with open(path) as f:
        return json.load(f)


def load_tasks(path: Path) -> dict[str, Any]:
    """Load a tasks.json file and return the full task manifest.

    The manifest has:
      - "meta": metadata (version, description, etc.)
      - "tasks": dict of task_id -> task definition
    """
    raw = load_json(path)
    errors = validate_task_manifest(raw)
    if errors:
        raise ValueError(f"Invalid task manifest: {'; '.join(errors)}")
    return raw


def validate_task_manifest(manifest: dict[str, Any]) -> list[str]:
    """Validate a task manifest and return a list of errors (empty = valid)."""
    errors: list[str] = []

    if "tasks" not in manifest:
        errors.append("Missing required key: 'tasks'")
        return errors

    tasks = manifest["tasks"]
    if not isinstance(tasks, dict):
        errors.append("'tasks' must be a dict")
        return errors

    for task_id, task_def in tasks.items():
        errors.extend(_validate_task(task_id, task_def))

    return errors


def _validate_task(task_id: str, task_def: dict[str, Any]) -> list[str]:
    """Validate a single task definition."""
    errors: list[str] = []

    required = ["entry_state", "schedule"]
    for key in required:
        if key not in task_def:
            errors.append(f"Task '{task_id}': missing required key '{key}'")

    schedule = task_def.get("schedule", {})
    if schedule:
        errors.extend(_validate_schedule(task_id, schedule))

    actions = task_def.get("actions", [])
    for i, action in enumerate(actions):
        errors.extend(_validate_action(task_id, i, action))

    return errors


def _validate_schedule(task_id: str, schedule: dict[str, Any]) -> list[str]:
    """Validate a task's schedule definition."""
    errors: list[str] = []

    valid_types = {"interval", "server_reset", "one_shot", "manual"}
    stype = schedule.get("type")
    if stype and stype not in valid_types:
        errors.append(f"Task '{task_id}': schedule type '{stype}' not in {valid_types}")

    if stype == "interval" and "interval_minutes" not in schedule:
        errors.append(f"Task '{task_id}': interval schedule requires 'interval_minutes'")

    return errors


def _validate_action(task_id: str, index: int, action: dict[str, Any]) -> list[str]:
    """Validate a single action step."""
    errors: list[str] = []

    valid_types = {
        "navigate",
        "tap",
        "swipe",
        "wait",
        "wait_until",
        "assert_state",
        "read_resource",
        "conditional",
        "repeat",
    }

    atype = action.get("type")
    if not atype:
        errors.append(f"Task '{task_id}', action {index}: missing 'type'")
    elif atype not in valid_types:
        errors.append(f"Task '{task_id}', action {index}: type '{atype}' not in {valid_types}")

    if atype == "navigate" and "target_state" not in action:
        errors.append(f"Task '{task_id}', action {index}: 'navigate' requires 'target_state'")

    if atype == "tap" and "coords" not in action:
        errors.append(f"Task '{task_id}', action {index}: 'tap' requires 'coords'")

    return errors


def get_task(manifest: dict[str, Any], task_id: str) -> dict[str, Any] | None:
    """Get a task definition by ID, or None if not found."""
    return manifest.get("tasks", {}).get(task_id)


def is_task_enabled(task_def: dict[str, Any]) -> bool:
    """Check if a task is enabled (defaults to True if not specified)."""
    return task_def.get("enabled", True)


def get_next_run(task_def: dict[str, Any]) -> datetime | None:
    """Get the next_run datetime for a task, or None if not set."""
    nr = task_def.get("next_run")
    if nr is None:
        return None
    if isinstance(nr, datetime):
        return nr
    return datetime.fromisoformat(nr).replace(tzinfo=UTC)


def set_next_run(task_def: dict[str, Any], next_run: datetime) -> dict[str, Any]:
    """Set the next_run for a task. Returns the modified task_def."""
    task_def["next_run"] = next_run.isoformat()
    return task_def


def save_tasks(manifest: dict[str, Any], path: Path) -> None:
    """Write the task manifest back to disk."""
    with open(path, "w") as f:
        json.dump(manifest, f, indent=2, default=str)
        f.write("\n")
