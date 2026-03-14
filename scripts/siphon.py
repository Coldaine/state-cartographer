"""siphon.py — ALAS Observation Siphon

Tails the active ALAS log file in real-time. When ALAS detects a page or makes a
page transition, this script captures a screenshot, builds observations, runs the
state classifier, and saves a labeled dataset record.

Usage:
  python siphon.py --serial 127.0.0.1:21513 --graph ../examples/azur-lane/graph.json
"""

import argparse
import json
import re
import sys
import time
from datetime import datetime
from pathlib import Path

# Add scripts directory to path if run from elsewhere
sys.path.insert(0, str(Path(__file__).parent))

import adb_bridge
from alas_log_parser import LogParser, NavigationAnalyzer, SessionState
from locate import locate
from observe import build_observations, extract_pixel_coords

# Where to save data — module-level so tests can monkeypatch
PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"
SCREENSHOTS_DIR = DATA_DIR / "screenshots"
OBSERVATIONS_FILE = DATA_DIR / "observations.jsonl"


def get_latest_log_file(log_dir_arg: Path | None = None) -> Path:
    """Find the most recent ALAS log file."""
    if log_dir_arg and log_dir_arg.exists():
        log_dir = log_dir_arg
    else:
        # Default fallback
        log_dir = PROJECT_ROOT / "vendor" / "AzurLaneAutoScript" / "log"
        if not log_dir.exists():
            import os

            env_dir = os.environ.get("ALAS_LOG_DIR")
            if env_dir and Path(env_dir).exists():
                log_dir = Path(env_dir)
            else:
                raise FileNotFoundError(f"ALAS log directory not found: {log_dir}")

    log_files = list(log_dir.glob("*_*.txt"))
    if not log_files:
        raise FileNotFoundError(f"No log files found in {log_dir}")

    # Sort by modification time, newest first
    log_files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return log_files[0]


def capture_and_classify(
    serial: str,
    alas_label: str,
    alas_event: str,
    graph: dict,
    pixel_coords: list[tuple[int, int]],
    task_name: str,
) -> dict:
    """Take a screenshot, build observations, and run locate."""
    ts_str = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:19]
    screenshot_path = SCREENSHOTS_DIR / f"{alas_label}_{ts_str}.png"

    # 1. Capture screenshot via ADB
    try:
        png_bytes = adb_bridge.screenshot(serial)
        screenshot_path.write_bytes(png_bytes)
    except Exception as e:
        print(f"Error capturing screenshot: {e}", file=sys.stderr)
        return {}

    # 2. Build observations
    try:
        obs = build_observations(screenshot_path, pixel_coords)
    except Exception as e:
        print(f"Error building observations: {e}", file=sys.stderr)
        return {}

    # 3. Classify state (empty session history for now, just raw matching)
    try:
        session = {"history": []}
        result = locate(graph, session, obs)
        our_label = result.get("state", "unknown")
    except Exception as e:
        print(f"Error classifying state: {e}", file=sys.stderr)
        our_label = "error"

    # 4. Build record
    record = {
        "timestamp": datetime.now().isoformat(),
        "alas_label": alas_label,
        "our_label": our_label,
        "match": alas_label == our_label,
        "screenshot_path": str(screenshot_path.relative_to(PROJECT_ROOT).as_posix()),
        "alas_event": alas_event,
        "observation": {
            "pixels": obs.get("pixels", {}),
        },
        "task": task_name,
    }

    return record


def follow_file(file_path: Path):
    """Generator that yields new lines appended to a file (like tail -f)."""
    with open(file_path, encoding="utf-8", errors="replace") as f:
        # Seek to end of file to start tailing
        f.seek(0, 2)
        while True:
            line = f.readline()
            if not line:
                time.sleep(0.1)
                continue
            yield line


def main():
    parser = argparse.ArgumentParser(description="ALAS Siphon - observe and capture state transitions")
    parser.add_argument("--serial", default="127.0.0.1:21513", help="ADB serial (default: 127.0.0.1:21513)")
    parser.add_argument("--graph", required=True, help="Path to graph.json")
    parser.add_argument("--log", help="Path to specific ALAS log file (default: auto-detect latest)")
    parser.add_argument("--log-dir", help="Path to ALAS log directory (default: auto-detect)")
    args = parser.parse_args()

    # Setup directories
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)

    # Load graph
    try:
        with open(args.graph) as f:
            graph = json.load(f)
        pixel_coords = extract_pixel_coords(graph)
        print(f"Loaded graph with {len(graph.get('states', {}))} states and {len(pixel_coords)} pixel anchors.")
    except Exception as e:
        print(f"Error loading graph: {e}", file=sys.stderr)
        return 1

    # Verify ADB connection
    try:
        if not adb_bridge.connect(args.serial):
            print(f"Warning: Could not connect to {args.serial}", file=sys.stderr)
    except Exception as e:
        print(f"ADB Error: {e}", file=sys.stderr)
        return 1

    # Find log file
    log_dir_arg = Path(args.log_dir) if args.log_dir else None
    log_file = Path(args.log) if args.log else get_latest_log_file(log_dir_arg)
    print(f"Tailing log file: {log_file}")

    # Setup parsers
    nav_analyzer = NavigationAnalyzer()
    state = SessionState()

    print("Siphon active. Waiting for ALAS page events...")

    # Tail loop
    try:
        # Keep track of previous state to know when new events are added
        last_page_switches = len(nav_analyzer.page_switches)

        for raw_line in follow_file(log_file):
            # Parse line
            for log_line in LogParser.parse([raw_line]):
                # Track current task (simple heuristic)
                if match := re.search(r"Start task `([^`]+)`", log_line.message):
                    state.current_task = match.group(1)

                # Feed analyzer
                nav_analyzer.feed(log_line, state)

                # Check for events we want to capture
                trigger_event = None
                target_page = None

                # 1. Page Switch (from NavigationAnalyzer)
                if len(nav_analyzer.page_switches) > last_page_switches:
                    switch = nav_analyzer.page_switches[-1]
                    trigger_event = "PageSwitch"
                    target_page = switch["to"]
                    last_page_switches = len(nav_analyzer.page_switches)

                # 2. Page Arrive (direct match)
                elif match := re.search(r"Page arrive:\s*(\S+)", log_line.message):
                    trigger_event = "PageArrive"
                    target_page = match.group(1)

                # 3. [UI] identify (direct match)
                elif match := re.search(r"\[UI\]\s*(page_\S+)", log_line.message):
                    trigger_event = "PageIdentify"
                    target_page = match.group(1)

                # Execute capture pipeline if triggered
                if trigger_event and target_page:
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Event: {trigger_event} -> {target_page}")

                    # Pause briefly to let UI settle before screenshot
                    time.sleep(0.3)

                    record = capture_and_classify(
                        args.serial, target_page, trigger_event, graph, pixel_coords, state.current_task or "Unknown"
                    )

                    if record:
                        # Append to jsonl
                        with open(OBSERVATIONS_FILE, "a", encoding="utf-8") as f:
                            f.write(json.dumps(record) + "\n")

                        # Print status
                        match_str = (
                            "✓ MATCH"
                            if record["match"]
                            else f"✗ MISMATCH (ALAS: {target_page}, Our: {record['our_label']})"
                        )
                        print(f"  Captured: {record['screenshot_path']}")
                        print(f"  Status:   {match_str}")

    except KeyboardInterrupt:
        print("\nSiphon stopped by user.")
        return 0


if __name__ == "__main__":
    sys.exit(main())
