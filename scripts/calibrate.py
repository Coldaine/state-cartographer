"""calibrate.py — Anchor Calibrator

Learn anchor values from real screenshots of known states and write them
back to graph.json.

This is the first-mile tool: it bridges from "I have screenshots of each state"
to "I have a graph with real, learned anchor values."

For pixel_color anchors:
    Samples the screenshot at the anchor's (x, y) coordinates.
    Writes the observed RGB to the 'expected_rgb' field.

For screenshot_region anchors:
    Crops the region from the screenshot.
    Computes a perceptual hash using the specified algorithm.
    Writes the hash string to the 'hash' field.

Modifies graph.json in-place unless --dry-run is specified.

Usage:
    python calibrate.py --graph graph.json --screenshot screen.png --state main_menu
    python calibrate.py --graph graph.json --screenshot screen.png --state all
    python calibrate.py --graph graph.json --screenshot screen.png --state login --dry-run

Requirements:
    Pixel color sampling only: uv sync --extra dev  (Pillow)
    Screenshot region hashing: uv sync --extra vision  (Pillow + imagehash)
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def calibrate_state(
    state_id: str,
    state_def: dict[str, Any],
    screenshot_path: Path,
) -> tuple[list[dict[str, Any]], list[str]]:
    """Calibrate anchors for a single state from a screenshot.

    Samples pixel_color coordinates and computes screenshot_region hashes from
    the provided screenshot. Updates anchor dicts in-place with learned values.

    Returns (updated_anchors, warnings).
    """
    anchors = [dict(a) for a in state_def.get("anchors", [])]
    warnings: list[str] = []

    try:
        from PIL import Image

        img = Image.open(screenshot_path).convert("RGB")
    except ImportError:
        warnings.append(
            "Pillow not installed — install with: uv sync --extra dev\n"
            "  pixel_color and screenshot_region anchors cannot be calibrated."
        )
        return anchors, warnings
    except OSError as e:
        warnings.append(f"Cannot open screenshot '{screenshot_path}': {e}")
        return anchors, warnings

    for anchor in anchors:
        anchor_type = anchor.get("type", "")

        if anchor_type == "pixel_color":
            x, y = anchor.get("x", 0), anchor.get("y", 0)
            if 0 <= x < img.width and 0 <= y < img.height:
                pixel = img.getpixel((x, y))
                if not isinstance(pixel, tuple) or len(pixel) < 3:
                    warnings.append(f"  {state_id}: unexpected pixel format at ({x},{y})")
                    continue
                rgb = [int(pixel[0]), int(pixel[1]), int(pixel[2])]
                old_rgb = anchor.get("expected_rgb")
                anchor["expected_rgb"] = rgb
                if old_rgb is not None and old_rgb != rgb:
                    warnings.append(f"  {state_id}: pixel_color ({x},{y}) changed {old_rgb} -> {rgb}")
            else:
                warnings.append(
                    f"  {state_id}: pixel_color ({x},{y}) is outside image bounds ({img.width}x{img.height}) -- skipped"
                )

        elif anchor_type == "screenshot_region":
            try:
                import imagehash
            except ImportError:
                warnings.append(
                    f"  {state_id}: screenshot_region requires imagehash — install with: uv sync --extra vision"
                )
                continue

            region = anchor.get("region", {})
            x, y = region.get("x", 0), region.get("y", 0)
            w, h = region.get("width", 64), region.get("height", 64)
            algorithm = anchor.get("hash_algorithm", "phash")

            try:
                cropped = img.crop((x, y, x + w, y + h))
                hash_func = getattr(imagehash, algorithm, imagehash.phash)
                computed = str(hash_func(cropped))
                old_hash = anchor.get("hash")
                anchor["hash"] = computed
                if old_hash is not None and old_hash != computed:
                    warnings.append(f"  {state_id}: screenshot_region hash changed {old_hash!r} → {computed!r}")
            except Exception as e:
                warnings.append(f"  {state_id}: screenshot_region calibration failed: {e}")

    return anchors, warnings


def calibrate(
    graph: dict[str, Any],
    state_ids: list[str],
    screenshot_path: Path,
) -> tuple[dict[str, Any], list[str]]:
    """Calibrate anchors for one or more states in the graph.

    Returns (updated_graph, all_warnings).
    """
    all_warnings: list[str] = []
    states = graph.get("states", {})

    for state_id in state_ids:
        if state_id not in states:
            all_warnings.append(f"State '{state_id}' not found in graph — skipped")
            continue

        updated_anchors, warnings = calibrate_state(state_id, states[state_id], screenshot_path)
        all_warnings.extend(warnings)
        graph["states"][state_id]["anchors"] = updated_anchors

    return graph, all_warnings


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Learn anchor values from real screenshots and write to graph.json",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""Examples:
  Calibrate one state's anchors from its screenshot:
    python calibrate.py --graph graph.json --screenshot main_menu.png --state main_menu

  Calibrate all states from a single screenshot (only useful if all are on-screen):
    python calibrate.py --graph graph.json --screenshot screen.png --state all

  Preview changes without writing:
    python calibrate.py --graph graph.json --screenshot login.png --state login --dry-run
""",
    )
    parser.add_argument("--graph", required=True, help="Path to graph.json")
    parser.add_argument("--screenshot", required=True, help="Screenshot of the known state")
    parser.add_argument("--state", required=True, help="State ID to calibrate, or 'all' for every state")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be written without modifying graph.json",
    )
    args = parser.parse_args()

    graph_path = Path(args.graph)
    screenshot_path = Path(args.screenshot)

    if not graph_path.exists():
        print(f"Error: graph file not found: {graph_path}", file=sys.stderr)
        sys.exit(2)

    if not screenshot_path.exists():
        print(f"Error: screenshot not found: {screenshot_path}", file=sys.stderr)
        sys.exit(2)

    graph = load_json(graph_path)
    states = graph.get("states", {})

    if args.state == "all":
        state_ids = list(states.keys())
    else:
        state_ids = [args.state]

    updated_graph, warnings = calibrate(graph, state_ids, screenshot_path)

    for w in warnings:
        print(f"Warning: {w}", file=sys.stderr)

    calibrated = [sid for sid in state_ids if sid in states]

    if args.dry_run:
        json.dump(
            {
                "dry_run": True,
                "states_calibrated": calibrated,
                "warnings": warnings,
                "graph": updated_graph,
            },
            sys.stdout,
            indent=2,
        )
        print()
    else:
        with open(graph_path, "w") as f:
            json.dump(updated_graph, f, indent=2)
            f.write("\n")
        json.dump(
            {
                "calibrated": len(calibrated),
                "states": calibrated,
                "warnings": warnings,
                "written_to": str(graph_path),
            },
            sys.stdout,
            indent=2,
        )
        print()


if __name__ == "__main__":
    main()
