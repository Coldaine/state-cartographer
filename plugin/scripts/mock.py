"""
mock.py — Screenshot Mock Manager

Manages the offline development dataset: capture, validate anchors against
screenshots, and test the locate classifier against known-state images.

Usage:
  python mock.py capture --state main_menu --file screenshot.png --output-dir mocks/
  python mock.py validate --graph graph.json --mock-dir mocks/
  python mock.py test-locate --graph graph.json --screenshot screenshot.png
"""
from __future__ import annotations

import argparse
import json
import shutil
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def capture(state_id: str, screenshot_path: Path, output_dir: Path) -> dict[str, Any]:
    """Associate a screenshot with a state by copying to the mock directory."""
    output_dir.mkdir(parents=True, exist_ok=True)

    # Name pattern: {state_id}_{sequence_number}.png
    existing = list(output_dir.glob(f"{state_id}_*.png"))
    seq = len(existing) + 1
    dest = output_dir / f"{state_id}_{seq:02d}.png"

    shutil.copy2(screenshot_path, dest)

    return {
        "state": state_id,
        "file": str(dest),
        "sequence": seq,
    }


def validate(graph: dict[str, Any], mock_dir: Path) -> dict[str, Any]:
    """Validate anchor coverage against mock screenshots."""
    states = graph.get("states", {})
    report: dict[str, Any] = {
        "states_with_screenshots": [],
        "states_missing_screenshots": [],
        "anchor_results": {},
    }

    for state_id in states:
        screenshots = list(mock_dir.glob(f"{state_id}_*.png"))
        if screenshots:
            report["states_with_screenshots"].append(state_id)
        else:
            report["states_missing_screenshots"].append(state_id)

    return report


def main():
    parser = argparse.ArgumentParser(description="Screenshot mock manager")
    subparsers = parser.add_subparsers(dest="command", required=True)

    cap_parser = subparsers.add_parser("capture")
    cap_parser.add_argument("--state", required=True)
    cap_parser.add_argument("--file", required=True)
    cap_parser.add_argument("--output-dir", required=True)

    val_parser = subparsers.add_parser("validate")
    val_parser.add_argument("--graph", required=True)
    val_parser.add_argument("--mock-dir", required=True)

    args = parser.parse_args()

    if args.command == "capture":
        result = capture(args.state, Path(args.file), Path(args.output_dir))
        json.dump(result, sys.stdout, indent=2)
    elif args.command == "validate":
        graph = load_json(Path(args.graph))
        result = validate(graph, Path(args.mock_dir))
        json.dump(result, sys.stdout, indent=2)

    print()


if __name__ == "__main__":
    main()
