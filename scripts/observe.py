"""observe.py — Observation Extractor

Builds a structured observations dict from a screenshot file for use by locate.py.
This is the glue layer between "I have a screenshot" and "I can run the state classifier."

Extracts pixel color values at coordinates referenced by pixel_color anchors in the graph,
and records the screenshot path so screenshot_region anchors can be evaluated by locate.py.

Requires Pillow for pixel extraction (install with: uv pip install -e ".[vision]")
Text content and DOM elements must be added manually or via integration-specific tooling.

Usage:
  python observe.py --screenshot screen.png --graph graph.json
  python observe.py --screenshot screen.png --graph graph.json --output obs.json
  python observe.py --screenshot screen.png  # just record screenshot path, no pixels
"""

from __future__ import annotations

import argparse
import contextlib
import json
import sys
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    with open(path) as f:
        return json.load(f)


def extract_pixel_coords(graph: dict[str, Any]) -> list[tuple[int, int]]:
    """Extract all pixel sampling coordinates from pixel_color anchors in the graph."""
    coords: set[tuple[int, int]] = set()
    for state_def in graph.get("states", {}).values():
        all_anchors = state_def.get("anchors", []) + state_def.get("negative_anchors", [])
        for anchor in all_anchors:
            if anchor.get("type") == "pixel_color":
                coords.add((anchor.get("x", 0), anchor.get("y", 0)))
    return sorted(coords)


def build_observations(
    screenshot_path: Path,
    pixel_coords: list[tuple[int, int]] | None = None,
) -> dict[str, Any]:
    """Build an observations dict from a screenshot file.

    Samples pixel colors at the specified coordinates. The screenshot path is always
    recorded so locate.py can evaluate screenshot_region anchors directly.

    Returns a dict ready to be serialized and passed to locate.py via --observations.
    """
    obs: dict[str, Any] = {
        "screenshot": str(screenshot_path.resolve()),
        "pixels": {},
        "text_content": None,
        "dom_elements": [],
    }

    if not pixel_coords:
        return obs

    try:
        from PIL import Image as _Image

        img = _Image.open(screenshot_path).convert("RGB")
        for x, y in pixel_coords:
            if 0 <= x < img.width and 0 <= y < img.height:
                pixel = img.getpixel((x, y))
                if isinstance(pixel, tuple) and len(pixel) >= 3:
                    obs["pixels"][f"{x},{y}"] = list(pixel[:3])
    except ImportError:
        sys.stderr.write(
            "Warning: Pillow not installed — pixel color sampling skipped.\n"
            "Install vision extras: uv sync --extra vision\n"
        )
    except OSError as e:
        sys.stderr.write(f"Cannot open image '{screenshot_path}': {e}\n")
        sys.exit(2)

    return obs


def main() -> int:
    parser = argparse.ArgumentParser(description="Observation extractor — builds observations dict from a screenshot")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--screenshot", help="Path to an existing screenshot PNG")
    source.add_argument(
        "--adb",
        metavar="SERIAL",
        help="ADB device serial to capture a live screenshot (e.g. 127.0.0.1:21503)",
    )
    parser.add_argument("--graph", help="Path to graph.json (extracts pixel_color anchor coords)")
    parser.add_argument("--output", help="Write observations JSON to file (default: stdout)")
    args = parser.parse_args()

    # If --adb is supplied, take a live screenshot and save it to a temp file.
    _tmp_path: Path | None = None
    if args.adb:
        import tempfile

        try:
            from adb_bridge import screenshot as _adb_screenshot
        except ImportError:
            sys.stderr.write("adb_bridge module not found. Is it in the same directory?\n")
            return 2
        try:
            png_bytes = _adb_screenshot(args.adb)
        except RuntimeError as e:
            sys.stderr.write(f"ADB screenshot failed: {e}\n")
            return 2
        tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)  # noqa: SIM115
        tmp.write(png_bytes)
        tmp.close()
        _tmp_path = Path(tmp.name)
        args.screenshot = str(_tmp_path)

    screenshot_path = Path(args.screenshot)
    if not screenshot_path.exists():
        sys.stderr.write(f"File not found: {screenshot_path}\n")
        return 2

    pixel_coords: list[tuple[int, int]] = []
    if args.graph:
        graph_path = Path(args.graph)
        if not graph_path.exists():
            sys.stderr.write(f"Graph file not found: {graph_path}\n")
            return 2
        try:
            graph = load_json(graph_path)
        except json.JSONDecodeError as e:
            sys.stderr.write(f"Invalid JSON in graph file: {e}\n")
            return 2
        pixel_coords = extract_pixel_coords(graph)

    obs = build_observations(screenshot_path, pixel_coords)

    output = json.dumps(obs, indent=2) + "\n"
    if args.output:
        Path(args.output).write_text(output)
    else:
        sys.stdout.write(output)

    if _tmp_path is not None:
        with contextlib.suppress(OSError):
            _tmp_path.unlink()

    return 0


if __name__ == "__main__":
    sys.exit(main())
