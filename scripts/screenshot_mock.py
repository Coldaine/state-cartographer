"""
screenshot_mock.py — Screenshot Mock Manager

Manages the offline development dataset: capture screenshots, validate anchors against
known-state images, and learn perceptual hash values for screenshot_region anchors.

Usage:
    python screenshot_mock.py capture --state main_menu --file screenshot.png --output-dir mocks/
    python screenshot_mock.py validate --graph graph.json --mock-dir mocks/
    python screenshot_mock.py learn --screenshot screenshot.png --region 0,0,80,40
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
    """Validate anchor coverage and evaluate anchors against mock screenshots.

    For each state with screenshots in mock_dir, runs evaluate_anchors using the
    screenshot as the observation source. Reports per-screenshot confidence scores
    and whether each passes the state's confidence threshold.
    """
    from locate import evaluate_anchors

    states = graph.get("states", {})
    report: dict[str, Any] = {
        "states_with_screenshots": [],
        "states_missing_screenshots": [],
        "anchor_results": {},
    }

    for state_id, state_def in states.items():
        screenshots = list(mock_dir.glob(f"{state_id}_*.png"))
        if not screenshots:
            report["states_missing_screenshots"].append(state_id)
            continue

        report["states_with_screenshots"].append(state_id)
        anchors = state_def.get("anchors", [])
        threshold = state_def.get("confidence_threshold", 0.7)
        state_results = []

        for screenshot_path in sorted(screenshots):
            # Build observations: pixel values for pixel_color anchors + screenshot path
            pixel_coords = [(a.get("x", 0), a.get("y", 0)) for a in anchors if a.get("type") == "pixel_color"]
            obs: dict[str, Any] = {
                "screenshot": str(screenshot_path.resolve()),
                "pixels": {},
                "text_content": None,
                "dom_elements": [],
            }
            if pixel_coords:
                try:
                    from PIL import Image as _Image

                    img = _Image.open(screenshot_path).convert("RGB")
                    for x, y in pixel_coords:
                        if 0 <= x < img.width and 0 <= y < img.height:
                            pixel = img.getpixel((x, y))
                            if isinstance(pixel, tuple) and len(pixel) >= 3:
                                obs["pixels"][f"{x},{y}"] = list(pixel[:3])
                except ImportError:
                    pass  # no pixel data — pixel_color anchors will score 0

            score = evaluate_anchors(state_id, anchors, obs)
            state_results.append(
                {
                    "screenshot": screenshot_path.name,
                    "score": round(score, 3),
                    "threshold": threshold,
                    "pass": score >= threshold,
                }
            )

        report["anchor_results"][state_id] = state_results

    return report


def learn_anchor(screenshot_path: Path, region: dict[str, int], algorithm: str = "phash") -> dict[str, Any]:
    """Compute a perceptual hash for a screenshot region.

    Returns a ready-to-paste screenshot_region anchor definition with the computed hash.
    Requires Pillow and imagehash (vision extra).
    """
    try:
        import imagehash
        from PIL import Image as _Image
    except ImportError:
        sys.stderr.write("Vision extras required: uv sync --extra vision\n")
        sys.exit(2)

    try:
        img = _Image.open(screenshot_path)
    except OSError as e:
        sys.stderr.write(f"Cannot open image '{screenshot_path}': {e}\n")
        sys.exit(2)

    x, y = region.get("x", 0), region.get("y", 0)
    w, h = region.get("width", 64), region.get("height", 64)
    cropped = img.crop((x, y, x + w, y + h))
    hash_func = getattr(imagehash, algorithm, imagehash.phash)
    computed_hash = hash_func(cropped)

    return {
        "type": "screenshot_region",
        "region": region,
        "hash": str(computed_hash),
        "hash_algorithm": algorithm,
        "threshold": 10,
        "cost": 5,
    }


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

    learn_parser = subparsers.add_parser("learn", help="Compute perceptual hash for a screenshot region")
    learn_parser.add_argument("--screenshot", required=True, help="Path to screenshot PNG")
    learn_parser.add_argument(
        "--region",
        required=True,
        help="Region as x,y,width,height (e.g. 0,0,80,40)",
    )
    learn_parser.add_argument(
        "--algorithm",
        default="phash",
        choices=["phash", "dhash", "ahash", "whash"],
        help="Perceptual hash algorithm (default: phash)",
    )

    args = parser.parse_args()

    if args.command == "capture":
        result = capture(args.state, Path(args.file), Path(args.output_dir))
        json.dump(result, sys.stdout, indent=2)
    elif args.command == "validate":
        graph = load_json(Path(args.graph))
        result = validate(graph, Path(args.mock_dir))
        json.dump(result, sys.stdout, indent=2)
    elif args.command == "learn":
        parts = [int(v) for v in args.region.split(",")]
        if len(parts) != 4:
            sys.stderr.write("--region must be x,y,width,height (4 integers)\n")
            sys.exit(2)
        region = {"x": parts[0], "y": parts[1], "width": parts[2], "height": parts[3]}
        result = learn_anchor(Path(args.screenshot), region, args.algorithm)
        json.dump(result, sys.stdout, indent=2)

    print()


if __name__ == "__main__":
    main()
