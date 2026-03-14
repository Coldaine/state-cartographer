"""Append-only NDJSON event log for assignment/action execution."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

VALID_EVENT_TYPES = {"assignment", "observation", "execution", "recovery"}
REQUIRED_FIELDS = {"ts", "run_id", "serial", "event_type", "ok"}


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat()


def validate_event(event: dict[str, Any]) -> None:
    missing = sorted(REQUIRED_FIELDS - set(event))
    if missing:
        raise ValueError(f"Missing required event fields: {missing}")
    if event["event_type"] not in VALID_EVENT_TYPES:
        raise ValueError(f"Invalid event_type {event['event_type']!r}. Valid: {sorted(VALID_EVENT_TYPES)}")
    if not isinstance(event["ok"], bool):
        raise ValueError("Event field 'ok' must be boolean")


def make_event(
    *,
    run_id: str,
    serial: str,
    event_type: str,
    ok: bool,
    session_id: str | None = None,
    assignment: str | None = None,
    semantic_action: str | None = None,
    primitive_action: str | None = None,
    target: str | None = None,
    coords: list[int] | None = None,
    gesture: dict[str, Any] | None = None,
    package: str | None = None,
    state_before: str | None = None,
    state_after: str | None = None,
    screen_before: str | None = None,
    screen_after: str | None = None,
    duration_ms: int | None = None,
    error: str | None = None,
    notes: str | None = None,
    ts: str | None = None,
) -> dict[str, Any]:
    event = {
        "ts": ts or utc_now_iso(),
        "run_id": run_id,
        "session_id": session_id,
        "serial": serial,
        "assignment": assignment,
        "event_type": event_type,
        "semantic_action": semantic_action,
        "primitive_action": primitive_action,
        "target": target,
        "coords": coords,
        "gesture": gesture,
        "package": package,
        "state_before": state_before,
        "state_after": state_after,
        "screen_before": screen_before,
        "screen_after": screen_after,
        "ok": ok,
        "duration_ms": duration_ms,
        "error": error,
        "notes": notes,
    }
    validate_event(event)
    return event


def append_event(path: Path, event: dict[str, Any]) -> None:
    validate_event(event)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(event, separators=(",", ":")) + "\n")


def load_events(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    events = []
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        events.append(json.loads(line))
    return events


def main() -> int:
    parser = argparse.ArgumentParser(description="Execution event log utility")
    sub = parser.add_subparsers(dest="command", required=True)

    validate_parser = sub.add_parser("validate")
    validate_parser.add_argument("--file", required=True, help="NDJSON event log path")

    args = parser.parse_args()

    if args.command == "validate":
        try:
            for event in load_events(Path(args.file)):
                validate_event(event)
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            sys.stderr.write(f"Invalid event log: {exc}\n")
            return 1
        json.dump({"ok": True}, sys.stdout)
        sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
