"""Summarize artifacts from an ALAS observation run.

This is repo-side analysis tooling. It reads the artifacts emitted by
`scripts/alas_observe_runner.py`:

- meta.json
- events.jsonl (NDJSON)
- observations.jsonl (NDJSON)
- session.json
- screenshots/*.png

and produces a compact JSON or text summary suitable for CI logs or quick triage.
Vendor code is not touched.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Iterable


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _parse_iso_ts(value: str) -> datetime | None:
    # Runner uses datetime.now(UTC).isoformat() which is parseable by fromisoformat.
    # Some external tools may emit a trailing "Z"; handle that too.
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except Exception:
        return None


@dataclass(frozen=True)
class NdjsonLoadResult:
    records: list[dict[str, Any]]
    invalid_lines: int


def _load_ndjson(path: Path) -> NdjsonLoadResult:
    records: list[dict[str, Any]] = []
    invalid = 0
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return NdjsonLoadResult(records=[], invalid_lines=0)

    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            invalid += 1
            continue
        if not isinstance(obj, dict):
            invalid += 1
            continue
        records.append(obj)
    return NdjsonLoadResult(records=records, invalid_lines=invalid)


def _load_graph_state_ids(graph_path: Path) -> set[str]:
    graph = _load_json(graph_path)
    if not graph:
        return set()
    states = graph.get("states")
    if isinstance(states, dict):
        return {str(k) for k in states.keys()}
    if isinstance(states, list):
        ids = set()
        for item in states:
            if isinstance(item, dict) and "id" in item:
                ids.add(str(item["id"]))
        return ids
    return set()


def _coerce_screenshot_path(run_dir: Path, value: str | None) -> Path | None:
    if not value:
        return None
    translated = _translate_windows_drive_path(value)
    p = Path(translated)
    if p.is_absolute():
        return p
    return (run_dir / p).resolve()


def _translate_windows_drive_path(value: str) -> str:
    """Translate a Windows drive path (e.g. D:\\foo\\bar) into a WSL path if possible.

    Observation artifacts may be produced by Windows Python and embedded as raw
    Windows paths, even when analysis is running under WSL.
    """

    if len(value) < 3:
        return value
    drive = value[0]
    if not drive.isalpha() or value[1] != ":":
        return value
    sep = value[2]
    if sep not in ("\\", "/"):
        return value

    # Normalize: "D:\a\b" -> "/mnt/d/a/b"
    drive_lower = drive.lower()
    rest = value[3:].replace("\\", "/").lstrip("/")
    return f"/mnt/{drive_lower}/{rest}"


def _count_screenshots_on_disk(screenshots_dir: Path) -> int:
    if not screenshots_dir.exists():
        return 0
    count = 0
    for p in screenshots_dir.iterdir():
        if p.is_file() and p.suffix.lower() == ".png":
            count += 1
    return count


def _top(counter: Counter[str], limit: int) -> list[dict[str, Any]]:
    return [{"key": k, "count": int(v)} for k, v in counter.most_common(limit)]


def summarize_run(run_dir: Path, *, graph_path: Path | None = None, top_n: int = 15) -> dict[str, Any]:
    run_dir = run_dir.resolve()
    meta = _load_json(run_dir / "meta.json") or {}

    effective_graph_path: Path | None = None
    if graph_path is not None:
        effective_graph_path = graph_path.resolve()
    else:
        meta_graph = meta.get("graph_path")
        if isinstance(meta_graph, str) and meta_graph:
            effective_graph_path = Path(meta_graph)

    graph_state_ids: set[str] = set()
    if effective_graph_path and effective_graph_path.exists():
        graph_state_ids = _load_graph_state_ids(effective_graph_path)

    events_res = _load_ndjson(run_dir / "events.jsonl")
    obs_res = _load_ndjson(run_dir / "observations.jsonl")
    session = _load_json(run_dir / "session.json") or {}

    screenshots_dir = run_dir / "screenshots"
    screenshots_on_disk = _count_screenshots_on_disk(screenshots_dir)

    by_locate_state: Counter[str] = Counter()
    observations_by_assignment: Counter[str] = Counter()
    unknown_by_assignment: Counter[str] = Counter()
    inconsistent_current_state = 0
    missing_screenshots = 0
    duplicate_screenshot_refs = 0
    screenshot_ref_counts: Counter[str] = Counter()
    observed_states: set[str] = set()

    for rec in obs_res.records:
        assignment_value = rec.get("assignment")
        assignment_key = str(assignment_value) if assignment_value else "unknown"
        observations_by_assignment[assignment_key] += 1

        locate_result = rec.get("locate_result") if isinstance(rec.get("locate_result"), dict) else {}
        state = locate_result.get("state")
        state_key = "unknown" if not state else str(state)
        by_locate_state[state_key] += 1
        observed_states.add(state_key)
        if state_key == "unknown":
            unknown_by_assignment[assignment_key] += 1

        current_state = rec.get("current_state")
        if state_key not in ("unknown", "none") and current_state is not None and str(current_state) != state_key:
            inconsistent_current_state += 1

        screenshot_value = rec.get("screenshot")
        if isinstance(screenshot_value, str):
            screenshot_ref_counts[screenshot_value] += 1
            screenshot_path = _coerce_screenshot_path(run_dir, screenshot_value)
            if screenshot_path and not screenshot_path.exists():
                missing_screenshots += 1

    for path_str, c in screenshot_ref_counts.items():
        if c > 1:
            duplicate_screenshot_refs += int(c - 1)

    # Session-derived states (confirmed).
    confirmed_states: Counter[str] = Counter()
    for item in session.get("history", []) if isinstance(session.get("history"), list) else []:
        if not isinstance(item, dict):
            continue
        if item.get("type") == "confirmed_state" and item.get("state_id") is not None:
            confirmed_states[str(item["state_id"])] += 1
            observed_states.add(str(item["state_id"]))

    # Event-derived assignments and actions.
    assignment_starts: Counter[str] = Counter()
    assignment_ends: Counter[str] = Counter()
    assignment_events: Counter[str] = Counter()
    primitive_actions: Counter[str] = Counter()
    semantic_actions: Counter[str] = Counter()
    event_states: set[str] = set()

    first_ts: datetime | None = None
    last_ts: datetime | None = None

    def _ingest_ts(ts: str | None) -> None:
        nonlocal first_ts, last_ts
        if not ts:
            return
        parsed = _parse_iso_ts(ts)
        if not parsed:
            return
        if first_ts is None or parsed < first_ts:
            first_ts = parsed
        if last_ts is None or parsed > last_ts:
            last_ts = parsed

    for ev in events_res.records:
        _ingest_ts(ev.get("ts") if isinstance(ev.get("ts"), str) else None)

        assignment = ev.get("assignment")
        if assignment is not None:
            assignment_events[str(assignment)] += 1

        if ev.get("event_type") == "assignment" and ev.get("semantic_action") == "assignment_start":
            # Prefer the command target if present; it is stable across config naming.
            target = ev.get("target")
            assignment_key = str(target) if target else str(assignment) if assignment else "unknown"
            assignment_starts[assignment_key] += 1
        if ev.get("event_type") == "assignment" and ev.get("semantic_action") == "assignment_end":
            target = ev.get("target")
            assignment_key = str(target) if target else str(assignment) if assignment else "unknown"
            assignment_ends[assignment_key] += 1

        prim = ev.get("primitive_action")
        if prim is not None:
            primitive_actions[str(prim)] += 1

        sem = ev.get("semantic_action")
        if sem is not None:
            semantic_actions[str(sem)] += 1

        state_after = ev.get("state_after")
        if isinstance(state_after, str) and state_after:
            event_states.add(state_after)
            observed_states.add(state_after)

    # Include timestamps from observations as well.
    for rec in obs_res.records:
        _ingest_ts(rec.get("timestamp") if isinstance(rec.get("timestamp"), str) else None)

    total_obs = sum(by_locate_state.values())
    unknown_obs = int(by_locate_state.get("unknown", 0))
    unknown_rate = (unknown_obs / total_obs) if total_obs else None

    states_not_in_graph: list[str] = []
    if graph_state_ids:
        for s in sorted(observed_states):
            if s in ("unknown", "none"):
                continue
            if s not in graph_state_ids:
                states_not_in_graph.append(s)

    duration_s: float | None = None
    if first_ts and last_ts:
        duration_s = max(0.0, (last_ts - first_ts).total_seconds())

    unbalanced_assignments: dict[str, int] = {}
    for key in sorted(set(assignment_starts) | set(assignment_ends)):
        delta = int(assignment_starts.get(key, 0) - assignment_ends.get(key, 0))
        if delta != 0:
            unbalanced_assignments[key] = delta

    unknown_rate_by_assignment: dict[str, float] = {}
    for key, total in observations_by_assignment.items():
        if total:
            unknown_rate_by_assignment[key] = float(unknown_by_assignment.get(key, 0) / total)

    warnings: list[str] = []
    if unknown_rate is not None and unknown_rate > 0.30 and total_obs >= 20:
        warnings.append(f"High unknown rate: {unknown_rate:.1%} ({unknown_obs}/{total_obs})")
    if missing_screenshots:
        warnings.append(f"Missing screenshot files referenced by observations: {missing_screenshots}")
    if states_not_in_graph:
        warnings.append(f"Observed states not present in graph: {len(states_not_in_graph)}")
    if unbalanced_assignments:
        warnings.append(f"Unbalanced assignment start/end pairs: {len(unbalanced_assignments)}")

    return {
        "run_dir": str(run_dir),
        "run_id": str(meta.get("run_id") or run_dir.name),
        "graph_path": str(effective_graph_path) if effective_graph_path else None,
        "created_at": meta.get("created_at"),
        "counts": {
            "events": len(events_res.records),
            "events_invalid_lines": events_res.invalid_lines,
            "observations": len(obs_res.records),
            "observations_invalid_lines": obs_res.invalid_lines,
            "screenshots_on_disk": screenshots_on_disk,
            "screenshots_referenced": int(sum(screenshot_ref_counts.values())),
        },
        "time": {
            "first_ts": first_ts.isoformat() if first_ts else None,
            "last_ts": last_ts.isoformat() if last_ts else None,
            "duration_s": duration_s,
        },
        "states": {
            "total_observations": total_obs,
            "unknown_observations": unknown_obs,
            "unknown_rate": unknown_rate,
            "by_locate_state": dict(by_locate_state),
            "top_locate_states": _top(by_locate_state, top_n),
            "confirmed_state_counts": dict(confirmed_states),
            "states_not_in_graph": states_not_in_graph,
        },
        "assignments": {
            "starts": dict(assignment_starts),
            "ends": dict(assignment_ends),
            "top_starts": _top(assignment_starts, top_n),
            "top_ends": _top(assignment_ends, top_n),
            "events_by_assignment": dict(assignment_events),
            "top_events_by_assignment": _top(assignment_events, top_n),
            "observations_by_assignment": dict(observations_by_assignment),
            "top_observations_by_assignment": _top(observations_by_assignment, top_n),
            "unknown_rate_by_assignment": unknown_rate_by_assignment,
            "unbalanced_start_end": unbalanced_assignments,
        },
        "actions": {
            "by_primitive_action": dict(primitive_actions),
            "top_primitive_actions": _top(primitive_actions, top_n),
            "by_semantic_action": dict(semantic_actions),
            "top_semantic_actions": _top(semantic_actions, top_n),
        },
        "mismatches": {
            "inconsistent_current_state": inconsistent_current_state,
            "missing_screenshot_files": missing_screenshots,
            "duplicate_screenshot_refs": duplicate_screenshot_refs,
            "event_states_not_in_graph": sorted(
                s for s in event_states if graph_state_ids and s not in graph_state_ids
            ),
        },
        "warnings": warnings,
    }


def _format_text(summary: dict[str, Any]) -> str:
    counts = summary.get("counts", {})
    states = summary.get("states", {})
    assigns = summary.get("assignments", {})
    mismatches = summary.get("mismatches", {})
    warnings = summary.get("warnings", [])

    lines: list[str] = []
    lines.append(f"run_id: {summary.get('run_id')}")
    lines.append(f"run_dir: {summary.get('run_dir')}")
    if summary.get("graph_path"):
        lines.append(f"graph: {summary.get('graph_path')}")

    lines.append(
        f"events: {counts.get('events', 0)} (invalid_lines={counts.get('events_invalid_lines', 0)})"
    )
    lines.append(
        "observations: "
        f"{counts.get('observations', 0)} (invalid_lines={counts.get('observations_invalid_lines', 0)})"
    )
    lines.append(
        f"screenshots: on_disk={counts.get('screenshots_on_disk', 0)} "
        f"referenced={counts.get('screenshots_referenced', 0)}"
    )

    total_obs = states.get("total_observations", 0) or 0
    unknown_obs = states.get("unknown_observations", 0) or 0
    unknown_rate = states.get("unknown_rate")
    if unknown_rate is None:
        lines.append("unknown_rate: n/a")
    else:
        lines.append(f"unknown_rate: {unknown_rate:.1%} ({unknown_obs}/{total_obs})")

    top_states = states.get("top_locate_states") or []
    if top_states:
        lines.append("top_states:")
        for item in top_states[:10]:
            lines.append(f"  {item.get('key')}: {item.get('count')}")

    top_assigns = assigns.get("top_starts") or []
    if top_assigns:
        lines.append("top_assignments:")
        for item in top_assigns[:10]:
            lines.append(f"  {item.get('key')}: {item.get('count')}")

    if mismatches:
        lines.append(
            "mismatches: "
            f"inconsistent_current_state={mismatches.get('inconsistent_current_state', 0)} "
            f"missing_screenshot_files={mismatches.get('missing_screenshot_files', 0)} "
            f"duplicate_screenshot_refs={mismatches.get('duplicate_screenshot_refs', 0)}"
        )

    if warnings:
        lines.append("warnings:")
        for w in warnings:
            lines.append(f"  - {w}")

    return "\n".join(lines) + "\n"


def _pick_latest_run_dir(runs_root: Path) -> Path | None:
    if not runs_root.exists():
        return None
    candidates = [p for p in runs_root.iterdir() if p.is_dir()]
    if not candidates:
        return None
    # Run dirs are timestamp-prefixed; lexicographic sort is acceptable.
    candidates.sort(key=lambda p: p.name)
    return candidates[-1]


def parse_args(argv: Iterable[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Summarize ALAS observation corpus artifacts")
    parser.add_argument("--run-dir", help="Path to a single run directory")
    parser.add_argument(
        "--runs-root",
        default=None,
        help="Root containing multiple runs (default: data/alas-observe). Use with --latest.",
    )
    parser.add_argument("--latest", action="store_true", help="Use the latest run under --runs-root")
    parser.add_argument("--graph", default=None, help="Optional graph.json override")
    parser.add_argument("--format", choices=["json", "text"], default="text")
    parser.add_argument("--top", type=int, default=15, help="Top-N entries to include for counters")
    parser.add_argument("--output", default=None, help="Write output to a file instead of stdout")
    return parser.parse_args(list(argv) if argv is not None else None)


def main(argv: Iterable[str] | None = None) -> int:
    args = parse_args(argv)

    run_dir: Path | None = Path(args.run_dir).resolve() if args.run_dir else None
    if args.latest:
        root = Path(args.runs_root) if args.runs_root else (Path(__file__).resolve().parents[1] / "data" / "alas-observe")
        run_dir = _pick_latest_run_dir(root)
        if run_dir is None:
            sys.stderr.write(f"No runs found under {root}\n")
            return 2

    if run_dir is None:
        sys.stderr.write("Provide --run-dir or (--runs-root/--latest)\n")
        return 2

    graph_path = Path(args.graph).resolve() if args.graph else None
    summary = summarize_run(run_dir, graph_path=graph_path, top_n=int(args.top))

    if args.format == "json":
        out = json.dumps(summary, indent=2, sort_keys=True) + "\n"
    else:
        out = _format_text(summary)

    if args.output:
        Path(args.output).write_text(out, encoding="utf-8")
    else:
        sys.stdout.write(out)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
