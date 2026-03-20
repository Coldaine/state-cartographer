#!/usr/bin/env python3
"""
label_raw_stream.py — Label raw_stream frames using ALAS log page transitions.

For each frame captured in data/raw_stream/, finds the last ALAS page event
before the frame's timestamp and assigns it as the frame's page label.

Output: data/raw_stream/index.jsonl — one JSON line per frame, compatible
with calibrate_from_corpus.py (uses the same "alas_page" + "path" fields).

Usage:
    uv run python scripts/label_raw_stream.py
    uv run python scripts/label_raw_stream.py --log vendor/AzurLaneAutoScript/log/2026-03-20_alas.txt
    uv run python scripts/label_raw_stream.py --dump-pages
    uv run python scripts/label_raw_stream.py --min-samples 3  # skip pages with < 3 frames
"""

from __future__ import annotations

import argparse
import bisect
import json
import re
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent

# ---------------------------------------------------------------------------
# Log parsing
# ---------------------------------------------------------------------------

_LOG_LINE_RE = re.compile(r"^(\d{4}-\d{2}-\d{2}\s+\d{2}:\d{2}:\d{2}\.\d+)\s*\|\s*INFO\s*\|\s*(.*)$")
_PAGE_ARRIVE_RE = re.compile(r"Page arrive: (page_\w+)")
_PAGE_SWITCH_RE = re.compile(r"Page switch: \w+ -> (page_\w+)")
_UI_PAGE_RE = re.compile(r"\[UI\] (page_\w+)")

# Confidence order from most to least authoritative
_CONF_ORDER = {"arrive": 0, "ui": 1, "switch": 2}


def parse_page_events(log_path: Path) -> list[tuple[datetime, str, str]]:
    """Return sorted list of (timestamp, page_name, confidence) from ALAS log.

    confidence is one of: "arrive", "ui", "switch"
    """
    events: list[tuple[datetime, str, str]] = []
    with open(log_path, encoding="utf-8", errors="replace") as fh:
        for line in fh:
            m = _LOG_LINE_RE.match(line)
            if not m:
                continue
            ts_str, msg = m.groups()
            ts = datetime.strptime(ts_str.strip(), "%Y-%m-%d %H:%M:%S.%f")

            arrive = _PAGE_ARRIVE_RE.search(msg)
            if arrive:
                events.append((ts, arrive.group(1), "arrive"))
                continue

            switch = _PAGE_SWITCH_RE.search(msg)
            if switch:
                events.append((ts, switch.group(1), "switch"))
                continue

            ui = _UI_PAGE_RE.search(msg)
            if ui:
                events.append((ts, ui.group(1), "ui"))

    events.sort(key=lambda e: e[0])
    return events


def find_latest_log(log_dir: Path) -> Path | None:
    # Prefer *_alas.txt (the ALAS bot task log), falling back to any .txt
    alas_logs = sorted(log_dir.glob("*_alas.txt"), key=lambda p: p.stat().st_mtime)
    if alas_logs:
        return alas_logs[-1]
    all_logs = sorted(log_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime)
    return all_logs[-1] if all_logs else None


# ---------------------------------------------------------------------------
# Frame labeling
# ---------------------------------------------------------------------------

_FRAME_RE = re.compile(r"^(\d{8}_\d{6}_\d{3})\.png$")


def parse_frame_ts(name: str) -> datetime | None:
    m = _FRAME_RE.match(name)
    if not m:
        return None
    try:
        return datetime.strptime(m.group(1), "%Y%m%d_%H%M%S_%f")
    except ValueError:
        return None


def label_frames(
    raw_stream_dir: Path,
    events: list[tuple[datetime, str, str]],
) -> list[dict]:
    """Label each raw_stream PNG with the closest preceding page event."""
    event_times = [e[0] for e in events]

    records: list[dict] = []
    for frame_path in sorted(raw_stream_dir.glob("*.png")):
        ts = parse_frame_ts(frame_path.name)
        if ts is None:
            continue

        idx = bisect.bisect_right(event_times, ts) - 1
        if idx < 0:
            page, confidence = "unknown", "none"
        else:
            _, page, confidence = events[idx]

        records.append(
            {
                "ts": frame_path.stem,  # YYYYMMDD_HHMMSS_mmm
                "path": frame_path.name,  # relative to raw_stream_dir
                "alas_page": page,  # calibrate_from_corpus compat
                "confidence": confidence,
            }
        )
    return records


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Label raw_stream frames from ALAS log page transitions")
    parser.add_argument(
        "--log",
        type=Path,
        help="ALAS log file (default: most recent .txt in vendor/AzurLaneAutoScript/log/)",
    )
    parser.add_argument(
        "--raw-stream",
        type=Path,
        default=REPO_ROOT / "data" / "raw_stream",
        help="Path to the raw_stream directory",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=None,
        help="Output JSONL path (default: <raw_stream>/index.jsonl)",
    )
    parser.add_argument(
        "--dump-pages",
        action="store_true",
        help="Print the page event timeline extracted from the log and exit",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=1,
        help="Only include pages with at least this many frames (default: 1)",
    )
    args = parser.parse_args(argv)

    # Resolve log file
    if args.log:
        log_path = args.log
    else:
        log_dir = REPO_ROOT / "vendor" / "AzurLaneAutoScript" / "log"
        log_path = find_latest_log(log_dir)
        if not log_path:
            print("ERROR: No ALAS log found in vendor/AzurLaneAutoScript/log/", file=sys.stderr)
            return 1
        print(f"Log: {log_path.name}", file=sys.stderr)

    events = parse_page_events(log_path)
    print(f"Page events parsed: {len(events)}", file=sys.stderr)

    if args.dump_pages:
        for ts, page, src in events:
            print(f"{ts.strftime('%H:%M:%S.%f')[:-3]}  {src:8}  {page}")
        return 0

    raw_stream_dir = args.raw_stream
    if not raw_stream_dir.exists():
        print(f"ERROR: raw_stream dir not found: {raw_stream_dir}", file=sys.stderr)
        return 1

    records = label_frames(raw_stream_dir, events)

    # Apply min-samples filter
    if args.min_samples > 1:
        counts = Counter(r["alas_page"] for r in records)
        records = [r for r in records if counts[r["alas_page"]] >= args.min_samples]

    # Summary
    page_counts = Counter(r["alas_page"] for r in records)
    print(f"\nTotal frames labeled: {len(records)}", file=sys.stderr)
    print("Page distribution:", file=sys.stderr)
    for page, count in sorted(page_counts.items(), key=lambda x: -x[1]):
        print(f"  {page:<35} {count:>4}", file=sys.stderr)

    # Write index
    output_path = args.output or (raw_stream_dir / "index.jsonl")
    with open(output_path, "w", encoding="utf-8") as fh:
        for rec in records:
            fh.write(json.dumps(rec) + "\n")

    print(f"\nWrote {len(records)} records → {output_path}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
