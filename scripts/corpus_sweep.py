#!/usr/bin/env python3
"""VLM corpus sweep — multi-pass labeling pipeline.

Implements Passes 1-4 from docs/plans/vlm-corpus-sweep-plan.md:

  Pass 1 — Bulk VLM label every screenshot in the corpus.
  Pass 2 — Align VLM labels with ALAS log events by timestamp.
  Pass 3 — Adjudicate disagreements using a second model (Kimi).
  Pass 4 — Extract (source_page, action, target_page) transition triples.

Each pass writes a JSONL artefact to data/sweep/.  Later passes read
earlier pass artefacts, so they can be run independently or chained.

Usage examples:

  # Run all passes
  python scripts/corpus_sweep.py all

  # Run only Pass 1 (bulk label)
  python scripts/corpus_sweep.py pass1

  # Show what labels would be used without calling the VLM
  python scripts/corpus_sweep.py labels

  # Run Pass 4 (triples) from existing Pass 2/3 output
  python scripts/corpus_sweep.py pass4
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from state_cartographer.run_recording import RunRecorder

# ---------------------------------------------------------------------------
# Path constants
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parent.parent
ALAS_ROOT = Path(os.getenv("SC_ALAS_ROOT", r"D:\_projects\ALAS_original"))
CORPUS_DIR = REPO_ROOT / "data" / "raw_stream"
ALAS_LOG_DIR = ALAS_ROOT / "log"
SWEEP_OUT_DIR = REPO_ROOT / "data" / "sweep"
ALAS_PAGE_FILE = ALAS_ROOT / "module" / "ui" / "page.py"

PASS1_OUT = SWEEP_OUT_DIR / "pass1_labels.jsonl"
PASS2_OUT = SWEEP_OUT_DIR / "pass2_merged.jsonl"
PASS3_OUT = SWEEP_OUT_DIR / "pass3_adjudicated.jsonl"
PASS4_OUT = SWEEP_OUT_DIR / "pass4_triples.jsonl"

DISAGREEMENT_OUT = SWEEP_OUT_DIR / "disagreements.jsonl"

# ---------------------------------------------------------------------------
# Candidate label derivation from ALAS page definitions
# ---------------------------------------------------------------------------

# These are the current fallback page labels when ALAS page.py is unavailable.
# Re-derive at runtime if the file changes.
_FALLBACK_PAGE_LABELS: list[str] = [
    "page_main",
    "page_campaign_menu",
    "page_campaign",
    "page_fleet",
    "page_main_white",
    "page_unknown",
    "page_exercise",
    "page_daily",
    "page_event",
    "page_sp",
    "page_coalition",
    "page_os",
    "page_archives",
    "page_reward",
    "page_mission",
    "page_guild",
    "page_commission",
    "page_tactical",
    "page_battle_pass",
    "page_event_list",
    "page_raid",
    "page_dock",
    "page_dock_grid",
    "page_ship_detail",
    "page_ship_gear",
    "page_dock_sort",
    "page_research",
    "page_shipyard",
    "page_meta",
    "page_storage",
    "page_reshmenu",
    "page_dormmenu",
    "page_dorm",
    "page_meowfficer",
    "page_academy",
    "page_private_quarters",
    "page_game_room",
    "page_shop",
    "page_munitions",
    "page_supply_pack",
    "page_build",
    "page_mail",
    "page_channel",
    "page_rpg_stage",
    "page_rpg_story",
    "page_rpg_city",
    "page_hospital",
]


def derive_candidate_labels(page_file: Path = ALAS_PAGE_FILE) -> list[str]:
    """Extract page names from ALAS page.py without importing it.

    Falls back to the hardcoded list if the file is unavailable.
    """
    if not page_file.exists():
        return list(_FALLBACK_PAGE_LABELS)
    content = page_file.read_text(encoding="utf-8", errors="ignore")
    pages = re.findall(r"^(page_\w+)\s*=\s*Page\b", content, re.MULTILINE)
    if not pages:
        return list(_FALLBACK_PAGE_LABELS)
    return pages


# ---------------------------------------------------------------------------
# Frame timestamp parsing
# ---------------------------------------------------------------------------

# Corpus screenshots are named: YYYYMMdd_HHmmss_mmm.png  (e.g. 20260320_002241_384.png)
_FRAME_TS_RE = re.compile(r"^(\d{8})_(\d{6})_(\d+)")


def frame_timestamp(path: Path) -> datetime | None:
    """Parse the capture timestamp out of a corpus filename.

    Returns None if the filename does not match the expected pattern.
    """
    m = _FRAME_TS_RE.match(path.stem)
    if not m:
        return None
    date_part, time_part, ms_part = m.groups()
    ts_str = f"{date_part[:4]}-{date_part[4:6]}-{date_part[6:8]} "
    ts_str += f"{time_part[:2]}:{time_part[2:4]}:{time_part[4:6]}.{ms_part.zfill(3)}"
    try:
        return datetime.fromisoformat(ts_str)
    except ValueError:
        return None


def collect_corpus_frames(corpus_dir: Path = CORPUS_DIR) -> list[Path]:
    """Return all PNG frames in the corpus directory, sorted by filename."""
    if not corpus_dir.exists():
        return []
    return sorted(corpus_dir.glob("*.png"))


# ---------------------------------------------------------------------------
# ALAS log parser (Pass 2 dependency)
# ---------------------------------------------------------------------------

# ALAS task execution log line format:
#   2026-03-25 12:46:12.873 | INFO | <message>
_LOG_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\.\d+)\s*\|\s*(\w+)\s*\|\s*(.+)$")

# Patterns inside the message field
_PAGE_ARRIVE_RE = re.compile(r"UI get to (page_\w+)", re.IGNORECASE)
_PAGE_LABEL_RE = re.compile(r"Page[:\s]+(page_\w+)", re.IGNORECASE)
_PAGE_APPEAR_RE = re.compile(r"(page_\w+)\s+appear", re.IGNORECASE)
_CLICK_RE = re.compile(r"Click\s+(\S+)\s+at\s+\((\d+),\s*(\d+)\)", re.IGNORECASE)
_TASK_RE = re.compile(r"<<<\s*(\w+)\s*>>>")


class ALASLogEvent:
    """A single parsed event from an ALAS task execution log."""

    __slots__ = ("action", "button", "event_type", "level", "page", "raw_message", "task", "timestamp", "x", "y")

    def __init__(
        self,
        timestamp: datetime,
        level: str,
        raw_message: str,
        event_type: str,
        page: str | None = None,
        action: str | None = None,
        button: str | None = None,
        x: int | None = None,
        y: int | None = None,
        task: str | None = None,
    ):
        self.timestamp = timestamp
        self.level = level
        self.raw_message = raw_message
        self.event_type = event_type
        self.page = page
        self.action = action
        self.button = button
        self.x = x
        self.y = y
        self.task = task

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp.isoformat(),
            "level": self.level,
            "event_type": self.event_type,
            "page": self.page,
            "action": self.action,
            "button": self.button,
            "x": self.x,
            "y": self.y,
            "task": self.task,
            "raw_message": self.raw_message,
        }


def parse_alas_log(log_path: Path) -> list[ALASLogEvent]:
    """Parse an ALAS task execution log and return structured events.

    Only events that carry page or action information are returned.
    GUI launcher logs (which contain only startup configs) will produce
    an empty list.
    """
    events: list[ALASLogEvent] = []
    current_task: str | None = None

    for line in log_path.read_text(encoding="utf-8", errors="ignore").splitlines():
        line = line.strip()
        m = _LOG_LINE_RE.match(line)
        if not m:
            continue

        ts_str, level, message = m.groups()
        try:
            ts = datetime.fromisoformat(ts_str)
        except ValueError:
            continue

        # Track active task context
        task_m = _TASK_RE.search(message)
        if task_m:
            current_task = task_m.group(1)

        # Page arrival
        page_arrive = _PAGE_ARRIVE_RE.search(message)
        if page_arrive:
            events.append(
                ALASLogEvent(
                    timestamp=ts,
                    level=level,
                    raw_message=message,
                    event_type="page_arrive",
                    page=page_arrive.group(1),
                    task=current_task,
                )
            )
            continue

        # Page appear
        page_appear = _PAGE_APPEAR_RE.search(message)
        if page_appear:
            events.append(
                ALASLogEvent(
                    timestamp=ts,
                    level=level,
                    raw_message=message,
                    event_type="page_appear",
                    page=page_appear.group(1),
                    task=current_task,
                )
            )
            continue

        # Page label
        page_label = _PAGE_LABEL_RE.search(message)
        if page_label:
            events.append(
                ALASLogEvent(
                    timestamp=ts,
                    level=level,
                    raw_message=message,
                    event_type="page_label",
                    page=page_label.group(1),
                    task=current_task,
                )
            )
            continue

        # Click/tap action
        click_m = _CLICK_RE.search(message)
        if click_m:
            button, x_str, y_str = click_m.groups()
            events.append(
                ALASLogEvent(
                    timestamp=ts,
                    level=level,
                    raw_message=message,
                    event_type="tap",
                    action="tap",
                    button=button,
                    x=int(x_str),
                    y=int(y_str),
                    task=current_task,
                )
            )

    return events


def load_all_alas_events(log_dir: Path = ALAS_LOG_DIR) -> list[ALASLogEvent]:
    """Load and merge events from all ALAS task execution logs in the log dir.

    GUI logs are skipped (they match *_gui.txt and contain no events of interest).
    """
    all_events: list[ALASLogEvent] = []
    if not log_dir.exists():
        return all_events
    for log_file in sorted(log_dir.glob("*.txt")):
        if log_file.name.endswith("_gui.txt") or log_file.name.endswith("_-c.txt"):
            continue
        all_events.extend(parse_alas_log(log_file))
    all_events.sort(key=lambda e: e.timestamp)
    return all_events


# ---------------------------------------------------------------------------
# Pass 1 — Bulk VLM label
# ---------------------------------------------------------------------------


def run_pass1(
    corpus_dir: Path = CORPUS_DIR,
    out_file: Path = PASS1_OUT,
    candidate_labels: list[str] | None = None,
    vlm_base_url: str = "http://localhost:18900/v1",
    vlm_model: str = "local-vlm",
    batch_size: int = 1,
    limit: int | None = None,
    dry_run: bool = False,
) -> list[dict[str, Any]]:
    """Pass 1: run every corpus frame through the local VLM.

    Writes one JSON object per line to out_file.
    Returns the list of result dicts.
    """
    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from vlm_detector import VLMClient, detect_page

    frames = collect_corpus_frames(corpus_dir)
    if not frames:
        print(f"[pass1] No frames found in {corpus_dir}. Run ALAS first to populate the corpus.")
        return []

    if limit:
        frames = frames[:limit]

    labels = candidate_labels or derive_candidate_labels()
    print(f"[pass1] {len(frames)} frames, {len(labels)} candidate labels")

    if dry_run:
        print(f"[pass1] dry-run: would call VLM for {len(frames)} frames")
        return []

    client = VLMClient(base_url=vlm_base_url, model=vlm_model)
    out_file.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    with out_file.open("w", encoding="utf-8") as fh:
        for i, frame in enumerate(frames, 1):
            ts = frame_timestamp(frame)
            try:
                result = detect_page(frame, labels, task_context="corpus_pass1", client=client)
                row = {
                    "file": frame.name,
                    "timestamp": ts.isoformat() if ts else None,
                    "label": result.get("primary", {}).get("label"),
                    "confidence": result.get("primary", {}).get("confidence"),
                    "rationale": result.get("primary", {}).get("rationale"),
                    "uncertainty_flags": result.get("primary", {}).get("uncertainty_flags", []),
                    "pass": 1,
                }
            except Exception as exc:
                row = {
                    "file": frame.name,
                    "timestamp": ts.isoformat() if ts else None,
                    "label": None,
                    "confidence": None,
                    "error": str(exc),
                    "pass": 1,
                }
            fh.write(json.dumps(row) + "\n")
            results.append(row)

            if i % 50 == 0:
                print(f"[pass1] {i}/{len(frames)} frames labeled")

    print(f"[pass1] done — {len(results)} rows → {out_file}")
    return results


# ---------------------------------------------------------------------------
# Pass 2 — Timeline merge
# ---------------------------------------------------------------------------


def _nearest_event(ts: datetime, events: list[ALASLogEvent], window_s: float = 2.0) -> ALASLogEvent | None:
    """Return the closest event within window_s seconds of ts, or None."""
    best: ALASLogEvent | None = None
    best_delta = float("inf")
    for event in events:
        delta = abs((event.timestamp - ts).total_seconds())
        if delta < best_delta and delta <= window_s:
            best_delta = delta
            best = event
    return best


def run_pass2(
    pass1_file: Path = PASS1_OUT,
    out_file: Path = PASS2_OUT,
    alas_log_dir: Path = ALAS_LOG_DIR,
    window_s: float = 2.0,
) -> list[dict[str, Any]]:
    """Pass 2: join VLM labels with ALAS log events by timestamp proximity.

    For each labeled frame, finds the nearest ALAS event within window_s seconds
    and attaches ALAS page context and task label.
    """
    if not pass1_file.exists():
        print(f"[pass2] Pass 1 output not found: {pass1_file}. Run pass1 first.")
        return []

    alas_events = load_all_alas_events(alas_log_dir)
    if not alas_events:
        print(
            "[pass2] No ALAS task execution events found. "
            "Run ALAS tasks and confirm logs are in vendor/AzurLaneAutoScript/log/."
        )

    rows = [json.loads(line) for line in pass1_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    out_file.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []

    with out_file.open("w", encoding="utf-8") as fh:
        for row in rows:
            ts_str = row.get("timestamp")
            nearest_event = None
            if ts_str and alas_events:
                try:
                    ts = datetime.fromisoformat(ts_str)
                    nearest_event = _nearest_event(ts, alas_events, window_s)
                except ValueError:
                    pass

            merged = dict(row)
            merged["alas_page"] = nearest_event.page if nearest_event else None
            merged["alas_task"] = nearest_event.task if nearest_event else None
            merged["alas_action"] = nearest_event.action if nearest_event else None
            merged["alas_button"] = nearest_event.button if nearest_event else None
            merged["alas_x"] = nearest_event.x if nearest_event else None
            merged["alas_y"] = nearest_event.y if nearest_event else None
            merged["alas_event_type"] = nearest_event.event_type if nearest_event else None
            merged["pass"] = 2

            fh.write(json.dumps(merged) + "\n")
            results.append(merged)

    print(f"[pass2] done — {len(results)} rows merged → {out_file}")
    return results


# ---------------------------------------------------------------------------
# Pass 3 — Disagreement adjudication
# ---------------------------------------------------------------------------


def run_pass3(
    pass2_file: Path = PASS2_OUT,
    out_file: Path = PASS3_OUT,
    disagreement_file: Path = DISAGREEMENT_OUT,
    corpus_dir: Path = CORPUS_DIR,
    confidence_threshold: float = 0.6,
) -> list[dict[str, Any]]:
    """Pass 3: adjudicate disagreements between VLM and ALAS labels.

    Disagreement means: VLM label != ALAS page label, OR VLM confidence < threshold.
    Sends disagreement frames to Kimi for a second opinion.
    Writes the full timeline (with adjudication where applied) to out_file.
    """
    if not pass2_file.exists():
        print(f"[pass3] Pass 2 output not found: {pass2_file}. Run pass2 first.")
        return []

    _scripts_dir = str(Path(__file__).resolve().parent)
    if _scripts_dir not in sys.path:
        sys.path.insert(0, _scripts_dir)
    from kimi_review import build_prompt as _kimi_build_prompt
    from kimi_review import run_kimi as _run_kimi

    rows = [json.loads(line) for line in pass2_file.read_text(encoding="utf-8").splitlines() if line.strip()]
    labels = derive_candidate_labels()

    disagreements: list[dict[str, Any]] = []
    for row in rows:
        vlm_label = row.get("label")
        alas_page = row.get("alas_page")
        confidence = row.get("confidence") or 0.0
        low_confidence = confidence < confidence_threshold
        label_mismatch = alas_page and vlm_label and vlm_label != alas_page

        if low_confidence or label_mismatch:
            row["disagreement_reason"] = "low_confidence" if low_confidence else "label_mismatch"
            disagreements.append(row)

    print(f"[pass3] {len(disagreements)}/{len(rows)} frames flagged as disagreements")

    # Write disagreements for inspection before adjudication
    disagreement_file.parent.mkdir(parents=True, exist_ok=True)
    with disagreement_file.open("w", encoding="utf-8") as fh:
        for row in disagreements:
            fh.write(json.dumps(row) + "\n")

    # Adjudicate each disagreement with Kimi
    adjudicated: dict[str, dict[str, Any]] = {}
    for row in disagreements:
        frame_path = corpus_dir / row["file"]
        if not frame_path.exists():
            continue
        try:
            prompt = _kimi_build_prompt(
                [frame_path],
                task_context=row.get("alas_task") or "unknown",
                allowed_labels=labels,
            )
            raw = _run_kimi(prompt, workdir=frame_path.parent)
            kimi_result: dict[str, Any] = json.loads(raw) if raw.strip().startswith("{") else {}
            adjudicated[row["file"]] = {
                "kimi_label": kimi_result.get("best_label"),
                "kimi_confidence": kimi_result.get("confidence"),
                "kimi_visible_text": kimi_result.get("visible_text", []),
                "kimi_ambiguity_notes": kimi_result.get("ambiguity_notes", []),
            }
        except Exception as exc:
            adjudicated[row["file"]] = {"kimi_error": str(exc)}

    # Merge adjudication results and determine resolved label
    out_file.parent.mkdir(parents=True, exist_ok=True)
    results: list[dict[str, Any]] = []
    with out_file.open("w", encoding="utf-8") as fh:
        for row in rows:
            merged = dict(row)
            merged["pass"] = 3
            if row["file"] in adjudicated:
                merged.update(adjudicated[row["file"]])
                kimi_label = adjudicated[row["file"]].get("kimi_label")
                vlm_label = row.get("label")
                # If both agree, use that label. If they disagree, keep VLM but note it.
                if kimi_label and kimi_label == vlm_label:
                    merged["resolved_label"] = vlm_label
                    merged["resolution_method"] = "agreement"
                elif kimi_label and kimi_label != vlm_label:
                    merged["resolved_label"] = kimi_label
                    merged["resolution_method"] = "kimi_override"
                else:
                    merged["resolved_label"] = vlm_label
                    merged["resolution_method"] = "vlm_only"
            else:
                merged["resolved_label"] = row.get("label")
                merged["resolution_method"] = "no_disagreement"
            fh.write(json.dumps(merged) + "\n")
            results.append(merged)

    print(f"[pass3] done — {len(adjudicated)} adjudicated → {out_file}")
    return results


# ---------------------------------------------------------------------------
# Pass 4 — Triple extraction
# ---------------------------------------------------------------------------


def run_pass4(
    pass3_file: Path = PASS3_OUT,
    pass2_file: Path = PASS2_OUT,
    out_file: Path = PASS4_OUT,
    min_confidence: float = 0.6,
) -> list[dict[str, Any]]:
    """Pass 4: extract (source_page, action, target_page) transition triples.

    Looks for consecutive frames where the resolved label changes.
    Uses ALAS action context to populate the action field when available.
    Writes one triple per state transition detected.
    """
    # Prefer adjudicated output; fall back to merged output if pass3 wasn't run
    source_file = pass3_file if pass3_file.exists() else pass2_file
    if not source_file.exists():
        print(f"[pass4] No merged timeline found ({pass3_file} or {pass2_file}). Run pass2 or pass3 first.")
        return []

    rows = [json.loads(line) for line in source_file.read_text(encoding="utf-8").splitlines() if line.strip()]

    # Sort by timestamp to ensure correct sequencing
    def _ts(row: dict[str, Any]) -> str:
        return row.get("timestamp") or ""

    rows.sort(key=_ts)

    triples: list[dict[str, Any]] = []
    prev_row: dict[str, Any] | None = None

    for row in rows:
        label_key = "resolved_label" if "resolved_label" in row else "label"
        current_label = row.get(label_key)
        confidence = row.get("confidence") or 0.0

        if current_label is None or confidence < min_confidence:
            prev_row = None  # break the chain on low confidence
            continue

        if prev_row is not None:
            prev_label_key = "resolved_label" if "resolved_label" in prev_row else "label"
            prev_label = prev_row.get(prev_label_key)
            if prev_label and current_label != prev_label:
                triple = {
                    "source_page": prev_label,
                    "target_page": current_label,
                    "action": prev_row.get("alas_action"),
                    "button": prev_row.get("alas_button"),
                    "x": prev_row.get("alas_x"),
                    "y": prev_row.get("alas_y"),
                    "task": prev_row.get("alas_task"),
                    "source_frame": prev_row.get("file"),
                    "target_frame": row.get("file"),
                    "source_timestamp": prev_row.get("timestamp"),
                    "target_timestamp": row.get("timestamp"),
                    "source_confidence": prev_row.get("confidence"),
                    "target_confidence": row.get("confidence"),
                }
                triples.append(triple)

        prev_row = row

    out_file.parent.mkdir(parents=True, exist_ok=True)
    with out_file.open("w", encoding="utf-8") as fh:
        for triple in triples:
            fh.write(json.dumps(triple) + "\n")

    print(f"[pass4] done — {len(triples)} triples extracted → {out_file}")
    return triples


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def cmd_labels(args: argparse.Namespace) -> None:
    labels = derive_candidate_labels()
    print(f"{len(labels)} candidate labels:")
    for label in labels:
        print(f"  {label}")


def cmd_pass1(args: argparse.Namespace) -> None:
    run_pass1(
        corpus_dir=Path(args.corpus_dir),
        out_file=Path(args.out) if args.out else PASS1_OUT,
        vlm_base_url=args.vlm_url,
        vlm_model=args.vlm_model,
        limit=args.limit,
        dry_run=args.dry_run,
    )


def cmd_pass2(args: argparse.Namespace) -> None:
    run_pass2(
        pass1_file=Path(args.pass1) if args.pass1 else PASS1_OUT,
        out_file=Path(args.out) if args.out else PASS2_OUT,
        window_s=args.window,
    )


def cmd_pass3(args: argparse.Namespace) -> None:
    run_pass3(
        pass2_file=Path(args.pass2) if args.pass2 else PASS2_OUT,
        out_file=Path(args.out) if args.out else PASS3_OUT,
        corpus_dir=Path(args.corpus_dir),
        confidence_threshold=args.confidence,
    )


def cmd_pass4(args: argparse.Namespace) -> None:
    run_pass4(
        pass3_file=Path(args.pass3) if args.pass3 else PASS3_OUT,
        pass2_file=Path(args.pass2) if args.pass2 else PASS2_OUT,
        out_file=Path(args.out) if args.out else PASS4_OUT,
        min_confidence=args.confidence,
    )


def cmd_all(args: argparse.Namespace) -> None:
    run_pass1(
        corpus_dir=Path(args.corpus_dir),
        vlm_base_url=args.vlm_url,
        vlm_model=args.vlm_model,
        limit=args.limit,
        dry_run=args.dry_run,
    )
    run_pass2(window_s=args.window)
    run_pass3(corpus_dir=Path(args.corpus_dir), confidence_threshold=args.confidence)
    run_pass4(min_confidence=args.confidence)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--run-id", default=None, help="Optional explicit run id for provenance output.")
    sub = parser.add_subparsers(dest="command", required=True)

    # Shared arguments
    shared = argparse.ArgumentParser(add_help=False)
    shared.add_argument("--corpus-dir", default=str(CORPUS_DIR), help="Path to screenshot corpus dir")
    shared.add_argument("--out", default=None, help="Override output JSONL path")
    shared.add_argument("--confidence", type=float, default=0.6, help="Confidence threshold")

    # labels
    sub.add_parser("labels", parents=[shared], help="Print candidate label set and exit")

    # pass1
    p1 = sub.add_parser("pass1", parents=[shared], help="Bulk VLM label (requires local VLM at localhost:18900)")
    p1.add_argument("--vlm-url", default="http://localhost:18900/v1")
    p1.add_argument("--vlm-model", default="local-vlm")
    p1.add_argument("--limit", type=int, default=None, help="Label only the first N frames")
    p1.add_argument("--dry-run", action="store_true", help="Show what would run without calling VLM")

    # pass2
    p2 = sub.add_parser("pass2", parents=[shared], help="Align VLM labels with ALAS log events")
    p2.add_argument("--pass1", default=None, help="Override pass1 JSONL input path")
    p2.add_argument("--window", type=float, default=2.0, help="Timestamp match window in seconds")

    # pass3
    p3 = sub.add_parser("pass3", parents=[shared], help="Adjudicate disagreements with Kimi")
    p3.add_argument("--pass2", default=None, help="Override pass2 JSONL input path")

    # pass4
    p4 = sub.add_parser("pass4", parents=[shared], help="Extract state transition triples")
    p4.add_argument("--pass2", default=None, help="Override pass2 JSONL input path (fallback)")
    p4.add_argument("--pass3", default=None, help="Override pass3 JSONL input path (preferred)")

    # all
    pa = sub.add_parser("all", parents=[shared], help="Run all passes in sequence")
    pa.add_argument("--vlm-url", default="http://localhost:18900/v1")
    pa.add_argument("--vlm-model", default="local-vlm")
    pa.add_argument("--limit", type=int, default=None)
    pa.add_argument("--dry-run", action="store_true")
    pa.add_argument("--window", type=float, default=2.0)

    return parser


def _copy_convenience_output(source: Path, destination: Path, recorder: RunRecorder, label: str) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(source, destination)
    recorder.event("convenience_copy_written", label=label, source=str(source), destination=str(destination))


def main(argv: list[str] | None = None) -> int:
    raw_args = list(argv) if argv is not None else sys.argv[1:]
    parser = build_parser()
    args = parser.parse_args(raw_args)

    recorder = RunRecorder(
        "corpus-sweep",
        command=[str(Path(__file__).resolve()), *raw_args],
        cwd=REPO_ROOT,
    )

    input_paths: dict[str, Path | str] = {"alas_root": ALAS_ROOT}
    if args.command in {"pass1", "all"}:
        input_paths["corpus_dir"] = Path(args.corpus_dir)
    if args.command in {"pass2", "pass3", "pass4"}:
        if getattr(args, "pass1", None):
            input_paths["pass1_input"] = Path(args.pass1)
        if getattr(args, "pass2", None):
            input_paths["pass2_input"] = Path(args.pass2)
        if getattr(args, "pass3", None):
            input_paths["pass3_input"] = Path(args.pass3)

    recorder.start(
        run_id=args.run_id,
        model=getattr(args, "vlm_model", None),
        base_url=getattr(args, "vlm_url", None),
        input_paths=input_paths,
        notes=[f"alas_page_file={ALAS_PAGE_FILE}", f"alas_log_dir={ALAS_LOG_DIR}"],
    )

    output_paths: dict[str, Path | str] = {}
    summary_counts: dict[str, Any] = {}
    warnings: list[str] = []

    try:
        if args.command == "labels":
            labels = derive_candidate_labels()
            label_path = recorder.artifact_path("candidate_labels.json")
            label_path.write_text(json.dumps(labels, indent=2) + "\n", encoding="utf-8")
            recorder.event("phase_completed", phase="labels", count=len(labels), output=str(label_path))
            print(f"{len(labels)} candidate labels:")
            for label in labels:
                print(f"  {label}")
            output_paths["candidate_labels"] = label_path
            summary_counts["candidate_labels"] = len(labels)
        elif args.command == "pass1":
            canonical_out = recorder.artifact_path("pass1_labels.jsonl")
            recorder.event("phase_started", phase="pass1", output=str(canonical_out))
            rows = run_pass1(
                corpus_dir=Path(args.corpus_dir),
                out_file=canonical_out,
                vlm_base_url=args.vlm_url,
                vlm_model=args.vlm_model,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            legacy_out = Path(args.out) if args.out else PASS1_OUT
            _copy_convenience_output(canonical_out, legacy_out, recorder, "pass1")
            output_paths["pass1"] = canonical_out
            output_paths["pass1_legacy"] = legacy_out
            summary_counts["pass1_rows"] = len(rows)
        elif args.command == "pass2":
            pass1_input = Path(args.pass1) if args.pass1 else PASS1_OUT
            canonical_out = recorder.artifact_path("pass2_merged.jsonl")
            recorder.event("phase_started", phase="pass2", input=str(pass1_input), output=str(canonical_out))
            rows = run_pass2(
                pass1_file=pass1_input,
                out_file=canonical_out,
                alas_log_dir=ALAS_LOG_DIR,
                window_s=args.window,
            )
            legacy_out = Path(args.out) if args.out else PASS2_OUT
            _copy_convenience_output(canonical_out, legacy_out, recorder, "pass2")
            output_paths["pass2"] = canonical_out
            output_paths["pass2_legacy"] = legacy_out
            summary_counts["pass2_rows"] = len(rows)
        elif args.command == "pass3":
            pass2_input = Path(args.pass2) if args.pass2 else PASS2_OUT
            canonical_out = recorder.artifact_path("pass3_adjudicated.jsonl")
            disagreement_out = recorder.artifact_path("disagreements.jsonl")
            recorder.event("phase_started", phase="pass3", input=str(pass2_input), output=str(canonical_out))
            rows = run_pass3(
                pass2_file=pass2_input,
                out_file=canonical_out,
                disagreement_file=disagreement_out,
                corpus_dir=Path(args.corpus_dir),
                confidence_threshold=args.confidence,
            )
            legacy_out = Path(args.out) if args.out else PASS3_OUT
            _copy_convenience_output(canonical_out, legacy_out, recorder, "pass3")
            _copy_convenience_output(disagreement_out, DISAGREEMENT_OUT, recorder, "disagreements")
            output_paths["pass3"] = canonical_out
            output_paths["pass3_legacy"] = legacy_out
            output_paths["disagreements"] = disagreement_out
            output_paths["disagreements_legacy"] = DISAGREEMENT_OUT
            summary_counts["pass3_rows"] = len(rows)
        elif args.command == "pass4":
            pass2_input = Path(args.pass2) if args.pass2 else PASS2_OUT
            pass3_input = Path(args.pass3) if args.pass3 else PASS3_OUT
            canonical_out = recorder.artifact_path("pass4_triples.jsonl")
            recorder.event("phase_started", phase="pass4", output=str(canonical_out))
            rows = run_pass4(
                pass3_file=pass3_input,
                pass2_file=pass2_input,
                out_file=canonical_out,
                min_confidence=args.confidence,
            )
            legacy_out = Path(args.out) if args.out else PASS4_OUT
            _copy_convenience_output(canonical_out, legacy_out, recorder, "pass4")
            output_paths["pass4"] = canonical_out
            output_paths["pass4_legacy"] = legacy_out
            summary_counts["pass4_rows"] = len(rows)
        elif args.command == "all":
            pass1_out = recorder.artifact_path("pass1_labels.jsonl")
            pass2_out = recorder.artifact_path("pass2_merged.jsonl")
            pass3_out = recorder.artifact_path("pass3_adjudicated.jsonl")
            pass4_out = recorder.artifact_path("pass4_triples.jsonl")
            disagreement_out = recorder.artifact_path("disagreements.jsonl")

            recorder.event("phase_started", phase="pass1", output=str(pass1_out))
            pass1_rows = run_pass1(
                corpus_dir=Path(args.corpus_dir),
                out_file=pass1_out,
                vlm_base_url=args.vlm_url,
                vlm_model=args.vlm_model,
                limit=args.limit,
                dry_run=args.dry_run,
            )
            _copy_convenience_output(pass1_out, PASS1_OUT, recorder, "pass1")

            recorder.event("phase_started", phase="pass2", input=str(pass1_out), output=str(pass2_out))
            pass2_rows = run_pass2(
                pass1_file=pass1_out,
                out_file=pass2_out,
                alas_log_dir=ALAS_LOG_DIR,
                window_s=args.window,
            )
            _copy_convenience_output(pass2_out, PASS2_OUT, recorder, "pass2")

            recorder.event("phase_started", phase="pass3", input=str(pass2_out), output=str(pass3_out))
            pass3_rows = run_pass3(
                pass2_file=pass2_out,
                out_file=pass3_out,
                disagreement_file=disagreement_out,
                corpus_dir=Path(args.corpus_dir),
                confidence_threshold=args.confidence,
            )
            _copy_convenience_output(pass3_out, PASS3_OUT, recorder, "pass3")
            _copy_convenience_output(disagreement_out, DISAGREEMENT_OUT, recorder, "disagreements")

            recorder.event("phase_started", phase="pass4", input=str(pass3_out), output=str(pass4_out))
            pass4_rows = run_pass4(
                pass3_file=pass3_out,
                pass2_file=pass2_out,
                out_file=pass4_out,
                min_confidence=args.confidence,
            )
            _copy_convenience_output(pass4_out, PASS4_OUT, recorder, "pass4")

            output_paths.update(
                {
                    "pass1": pass1_out,
                    "pass1_legacy": PASS1_OUT,
                    "pass2": pass2_out,
                    "pass2_legacy": PASS2_OUT,
                    "pass3": pass3_out,
                    "pass3_legacy": PASS3_OUT,
                    "pass4": pass4_out,
                    "pass4_legacy": PASS4_OUT,
                    "disagreements": disagreement_out,
                    "disagreements_legacy": DISAGREEMENT_OUT,
                }
            )
            summary_counts.update(
                {
                    "pass1_rows": len(pass1_rows),
                    "pass2_rows": len(pass2_rows),
                    "pass3_rows": len(pass3_rows),
                    "pass4_rows": len(pass4_rows),
                }
            )
        else:
            raise ValueError(f"unsupported command: {args.command}")
    except Exception as exc:
        recorder.event("run_error", command=args.command, error=str(exc))
        warnings.append(str(exc))
        recorder.finish(exit_code=1, output_paths=output_paths, summary_counts=summary_counts, warnings=warnings)
        print(f"[error] {exc}", file=sys.stderr)
        return 1

    recorder.finish(exit_code=0, output_paths=output_paths, summary_counts=summary_counts, warnings=warnings)
    return 0


if __name__ == "__main__":
    sys.exit(main())
