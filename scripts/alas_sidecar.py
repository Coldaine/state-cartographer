"""alas_sidecar.py — Labeled screenshot corpus builder.

Sits alongside a running ALAS session and captures screenshots labeled by
ALAS's OWN log output.  Does NOT call locate() or attempt its own state
classification — ALAS is the source of truth for what page it's on.

The output is a JSONL index (``data/corpus/index.jsonl``) plus PNG screenshots.
This corpus is consumed by ``calibrate_from_corpus.py`` to learn real pixel
anchors for ``graph.json``.

Usage (after ALAS is running in another terminal):

    uv run python scripts/alas_sidecar.py \\
      --serial 127.0.0.1:21513 \\
      --interval 3 \\
      --out data/corpus

The sidecar tails the latest ALAS log file, tracks page and task from
log lines, and captures a DroidCast screenshot every *interval* seconds
(plus an immediate capture on every page-switch event).

Press Ctrl+C to stop.  A summary is printed on exit.
"""

from __future__ import annotations

import argparse
import io
import json
import re
import socket
import sys
import time
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path

# ---------------------------------------------------------------------------
# Ensure sibling imports work regardless of invocation method
# ---------------------------------------------------------------------------
sys.path.insert(0, str(Path(__file__).parent))

from alas_log_parser import LogParser, NavigationAnalyzer, SessionState

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SERIAL = "127.0.0.1:21513"  # MEmu Index 1 (32.87 GB)
DROIDCAST_URL = "http://127.0.0.1:53516/preview"

RE_START_TASK = re.compile(r"Start task `([^`]+)`")
RE_PAGE_ARRIVE = re.compile(r"Page arrive:\s*(\S+)")
RE_UI_IDENTIFY = re.compile(r"\[UI\]\s*(page_\S+)")


# ---------------------------------------------------------------------------
# Screenshot capture — NO dependency on locate.py or observe.py
# ---------------------------------------------------------------------------


def _alas_port_open() -> bool:
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.settimeout(0.5)
        return s.connect_ex(("127.0.0.1", 22267)) == 0


def _capture_droidcast(save_path: Path) -> bool:
    """Grab a frame from ALAS's existing DroidCast HTTP endpoint."""
    import requests
    from PIL import Image

    try:
        r = requests.get(DROIDCAST_URL, timeout=5)
        r.raise_for_status()
        img = Image.open(io.BytesIO(r.content))
        if img.size[0] < 100 or img.size[1] < 100:
            return False
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
        return True
    except Exception:
        return False


def _capture_pilot(save_path: Path, serial: str) -> bool:
    """Fallback: use PilotBridge (manages DroidCast via ATX agent)."""
    from pilot_bridge import PilotBridge

    try:
        bridge = PilotBridge(serial=serial, record=False)
        img = bridge.screenshot()
        save_path.parent.mkdir(parents=True, exist_ok=True)
        img.save(save_path)
        return True
    except Exception:
        return False


def capture_screenshot(save_path: Path, serial: str) -> bool:
    """Capture a screenshot, preferring ALAS's own DroidCast endpoint."""
    if _alas_port_open() and _capture_droidcast(save_path):
        return True
    return _capture_pilot(save_path, serial)


# ---------------------------------------------------------------------------
# Log tailing
# ---------------------------------------------------------------------------


def follow_file(file_path: Path):
    """Yield new lines as they are appended to *file_path* (like ``tail -f``)."""
    with open(file_path, encoding="utf-8", errors="replace") as f:
        f.seek(0, 2)  # start at end
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line


def get_latest_log_file(log_dir: Path | None = None) -> Path:
    """Find the most recent ALAS log file."""
    if log_dir is None:
        log_dir = PROJECT_ROOT / "vendor" / "AzurLaneAutoScript" / "log"
    if not log_dir.exists():
        raise FileNotFoundError(f"ALAS log directory not found: {log_dir}")

    candidates = sorted(log_dir.glob("*.txt"), key=lambda p: p.stat().st_mtime, reverse=True)
    if not candidates:
        raise FileNotFoundError(f"No log files in {log_dir}")
    return candidates[0]


# ---------------------------------------------------------------------------
# JSONL record
# ---------------------------------------------------------------------------


def _make_record(
    *,
    path: Path,
    alas_page: str,
    alas_task: str,
    trigger: str,
    log_line_no: int,
    corpus_dir: Path,
) -> dict:
    rel = path.relative_to(corpus_dir).as_posix() if path.is_relative_to(corpus_dir) else str(path)
    return {
        "ts": datetime.now(tz=UTC).isoformat(),
        "path": rel,
        "alas_page": alas_page,
        "alas_task": alas_task,
        "trigger": trigger,
        "log_line": log_line_no,
    }


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------


def run_sidecar(
    *,
    serial: str = DEFAULT_SERIAL,
    interval: float = 3.0,
    corpus_dir: Path = PROJECT_ROOT / "data" / "corpus",
    log_file: Path | None = None,
    log_dir: Path | None = None,
    max_captures: int = 0,
) -> dict:
    """Run the sidecar capture loop.  Returns a summary dict on exit."""
    corpus_dir.mkdir(parents=True, exist_ok=True)
    index_path = corpus_dir / "index.jsonl"

    if log_file is None:
        log_file = get_latest_log_file(log_dir)

    print(f"Corpus dir  : {corpus_dir}")
    print(f"Log file    : {log_file}")
    print(f"Serial      : {serial}")
    print(f"Interval    : {interval}s")
    print(f"ALAS running: {_alas_port_open()}")
    print()

    nav = NavigationAnalyzer()
    state = SessionState()
    last_page_switches = 0

    capture_index = 0
    page_counter: Counter[str] = Counter()
    current_page: str = "unknown"
    current_task: str = "unknown"
    line_no = 0
    last_capture_time = 0.0

    def _do_capture(trigger: str) -> None:
        nonlocal capture_index, last_capture_time
        capture_index += 1
        fname = f"{capture_index:06d}.png"
        save_path = corpus_dir / fname

        ok = capture_screenshot(save_path, serial)
        if not ok:
            print(f"  [!] Screenshot capture failed for {fname}")
            return

        rec = _make_record(
            path=save_path,
            alas_page=current_page,
            alas_task=current_task,
            trigger=trigger,
            log_line_no=line_no,
            corpus_dir=corpus_dir,
        )
        with open(index_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(rec) + "\n")

        page_counter[current_page] += 1
        last_capture_time = time.monotonic()
        ts_short = datetime.now().strftime("%H:%M:%S")
        print(f"  [{ts_short}] #{capture_index:>4d}  page={current_page:<30s}  task={current_task}")

    print("Sidecar active.  Waiting for ALAS log events…")
    print("Press Ctrl+C to stop.\n")

    for raw_line in follow_file(log_file):
        line_no += 1

        for log_line in LogParser.parse([raw_line]):
            # Track current task
            if m := RE_START_TASK.search(log_line.message):
                current_task = m.group(1)

            nav.feed(log_line, state)

            # Detect page change
            new_page: str | None = None
            trigger = ""

            if len(nav.page_switches) > last_page_switches:
                sw = nav.page_switches[-1]
                new_page = sw["to"]
                trigger = "PageSwitch"
                last_page_switches = len(nav.page_switches)
            elif m := RE_PAGE_ARRIVE.search(log_line.message):
                new_page = m.group(1)
                trigger = "PageArrive"
            elif m := RE_UI_IDENTIFY.search(log_line.message):
                new_page = m.group(1)
                trigger = "UIIdentify"

            if new_page:
                current_page = new_page
                # Immediate capture on page change — let UI settle briefly
                time.sleep(0.3)
                _do_capture(trigger)

        # Periodic capture between events
        now = time.monotonic()
        if now - last_capture_time >= interval:
            _do_capture("periodic")

        if max_captures and capture_index >= max_captures:
            break

    # Summary
    summary = {
        "total_captures": capture_index,
        "unique_pages": len(page_counter),
        "page_counts": dict(page_counter.most_common()),
        "corpus_dir": str(corpus_dir),
        "index_path": str(index_path),
    }
    print(f"\n{'=' * 60}")
    print(f"Sidecar stopped.  {capture_index} captures, {len(page_counter)} unique pages.")
    for page, cnt in page_counter.most_common():
        print(f"  {page:<35s} {cnt:>5d}")
    return summary


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> int:
    parser = argparse.ArgumentParser(
        description="ALAS sidecar — capture labeled screenshot corpus",
    )
    parser.add_argument("--serial", default=DEFAULT_SERIAL, help="ADB serial")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between periodic captures")
    parser.add_argument("--out", default="data/corpus", help="Corpus output directory")
    parser.add_argument("--log", help="Path to specific ALAS log file")
    parser.add_argument("--log-dir", help="Path to ALAS log directory")
    parser.add_argument("--max", type=int, default=0, help="Max captures (0=unlimited)")
    args = parser.parse_args()

    try:
        run_sidecar(
            serial=args.serial,
            interval=args.interval,
            corpus_dir=Path(args.out),
            log_file=Path(args.log) if args.log else None,
            log_dir=Path(args.log_dir) if args.log_dir else None,
            max_captures=args.max,
        )
    except KeyboardInterrupt:
        print("\nStopped by user.")
    except FileNotFoundError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
