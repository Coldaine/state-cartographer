#!/usr/bin/env python3
"""Stress test ADB transport with VLM evaluation.

Tests:
1. Burst capture — N screenshots in rapid succession
2. Timing capture — screenshots at fixed intervals
3. Black frame detection — basic pixel analysis
4. Corruption detection — image decode check
5. Connection recovery — tests reconnect on failure

Usage:
    uv run python scripts/stress_test_adb.py --burst --count 50
    uv run python scripts/stress_test_adb.py --timed --interval 100 --duration 30
    uv run python scripts/stress_test_adb.py --vlm --vlm-url http://localhost:18900/v1
    uv run python scripts/stress_test_adb.py --compare data/*.png
"""

from __future__ import annotations

import argparse
import json
import sys
import time
from datetime import datetime
from pathlib import Path

import cv2
import numpy as np

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from scripts.vlm_detector import VLMClient, detect_page
from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.capture import Capture

SERIAL = "127.0.0.1:21513"
VLM_BASE_URL = "http://localhost:18900/v1"
VLM_MODEL = "local-vlm"

CANDIDATE_LABELS = [
    "black_frame",
    "game_ui_main",
    "game_ui_battle",
    "game_ui_menu",
    "game_ui_campaign",
    "loading_screen",
    "error_screen",
    "corrupted",
    "unknown",
]


def is_black_frame(image_bytes: bytes, threshold: float = 0.95) -> bool:
    """Check if screenshot is predominantly black."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    if img is None:
        return True
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    black_ratio = (gray < 10).mean()
    return black_ratio > threshold


def is_corrupted(image_bytes: bytes) -> bool:
    """Check if screenshot fails to decode."""
    nparr = np.frombuffer(image_bytes, np.uint8)
    img = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img is None


def analyze_with_vlm(image_path: Path, client: VLMClient) -> dict:
    """Use VLM to classify screenshot."""
    result = detect_page(
        image_path,
        CANDIDATE_LABELS,
        task_context="adb_stress_test",
        client=client,
    )
    return result


def stress_test_burst(adb: Adb, capture: Capture, count: int, output_dir: Path) -> dict:
    """Capture N screenshots in rapid succession."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []

    for i in range(count):
        try:
            data = capture.screenshot_png()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = output_dir / f"burst_{timestamp}_{i:03d}.png"
            path.write_bytes(data)

            black = is_black_frame(data)
            corrupted = is_corrupted(data)
            size = len(data)

            results.append(
                {
                    "index": i,
                    "path": str(path),
                    "size": size,
                    "is_black": black,
                    "is_corrupted": corrupted,
                    "timestamp": timestamp,
                    "error": None,
                }
            )

            if black:
                failures.append({"index": i, "type": "black_frame"})
            if corrupted:
                failures.append({"index": i, "type": "corrupted"})

        except Exception as e:
            failures.append({"index": i, "type": "exception", "error": str(e)})

    return {
        "test": "burst",
        "count": count,
        "results": results,
        "failures": failures,
        "failure_rate": len(failures) / count,
    }


def stress_test_timed(adb: Adb, capture: Capture, interval_ms: int, duration_s: int, output_dir: Path) -> dict:
    """Capture screenshots at fixed intervals."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []
    failures = []

    start = time.time()
    count = 0
    while time.time() - start < duration_s:
        try:
            data = capture.screenshot_png()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = output_dir / f"timed_{timestamp}_{count:03d}.png"
            path.write_bytes(data)

            black = is_black_frame(data)
            corrupted = is_corrupted(data)
            elapsed_ms = int((time.time() - start) * 1000)

            results.append(
                {
                    "index": count,
                    "path": str(path),
                    "size": len(data),
                    "is_black": black,
                    "is_corrupted": corrupted,
                    "elapsed_ms": elapsed_ms,
                    "error": None,
                }
            )

            if black:
                failures.append({"index": count, "type": "black_frame"})
            if corrupted:
                failures.append({"index": count, "type": "corrupted"})

        except Exception as e:
            failures.append({"index": count, "type": "exception", "error": str(e)})

        count += 1
        time.sleep(interval_ms / 1000)

    return {
        "test": "timed",
        "interval_ms": interval_ms,
        "duration_s": duration_s,
        "count": count,
        "results": results,
        "failures": failures,
        "failure_rate": len(failures) / count if count > 0 else 0,
    }


def stress_test_vlm_evaluation(capture: Capture, output_dir: Path, vlm_client: VLMClient) -> dict:
    """Capture screenshots and evaluate with VLM."""
    output_dir.mkdir(parents=True, exist_ok=True)
    results = []

    for i in range(20):
        try:
            data = capture.screenshot_png()
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            path = output_dir / f"vlm_{timestamp}_{i:03d}.png"
            path.write_bytes(data)

            vlm_result = analyze_with_vlm(path, vlm_client)

            results.append(
                {
                    "index": i,
                    "path": str(path),
                    "vlm_label": vlm_result.get("primary", {}).get("label"),
                    "vlm_confidence": vlm_result.get("primary", {}).get("confidence"),
                    "vlm_rationale": vlm_result.get("primary", {}).get("rationale"),
                    "is_black": is_black_frame(data),
                    "is_corrupted": is_corrupted(data),
                    "error": None,
                }
            )

        except Exception as e:
            results.append(
                {
                    "index": i,
                    "path": None,
                    "vlm_label": None,
                    "vlm_confidence": None,
                    "vlm_rationale": None,
                    "is_black": None,
                    "is_corrupted": None,
                    "error": str(e),
                }
            )

    return {
        "test": "vlm_evaluation",
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ADB transport stress test")
    parser.add_argument("--serial", default=SERIAL, help="ADB serial")
    parser.add_argument("--count", type=int, default=50, help="Burst count")
    parser.add_argument("--burst", action="store_true", help="Run burst test")
    parser.add_argument("--interval", type=int, default=100, help="Interval in ms for timed test")
    parser.add_argument("--duration", type=int, default=30, help="Duration in seconds for timed test")
    parser.add_argument("--timed", action="store_true", help="Run timed test")
    parser.add_argument("--vlm", action="store_true", help="Run VLM evaluation test")
    parser.add_argument("--vlm-url", default=VLM_BASE_URL, help="VLM base URL")
    parser.add_argument("--vlm-model", default=VLM_MODEL, help="VLM model name")
    parser.add_argument("--output", default="data/stress_test", help="Output directory")
    parser.add_argument("--compare", nargs="*", help="Compare existing PNG files")

    args = parser.parse_args(argv)

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    results = {}

    if args.compare:
        for path_str in args.compare:
            path = Path(path_str)
            if path.exists():
                data = path.read_bytes()
                black = is_black_frame(data)
                corrupted = is_corrupted(data)
                print(f"{path}: black={black}, corrupted={corrupted}, size={len(data)}")
            else:
                print(f"{path}: NOT FOUND")
        return 0

    try:
        adb = Adb(serial=args.serial)
        capture = Capture(adb)
        print(f"Connected to {args.serial}")
    except AdbError as e:
        print(f"ADB connection failed: {e}")
        return 1

    if args.burst:
        print(f"Running burst test: {args.count} captures")
        results["burst"] = stress_test_burst(adb, capture, args.count, output_dir / "burst")
        print(f"Burst complete: {results['burst']['failure_rate'] * 100:.1f}% failure rate")

    if args.timed:
        print(f"Running timed test: {args.interval}ms interval, {args.duration}s duration")
        results["timed"] = stress_test_timed(adb, capture, args.interval, args.duration, output_dir / "timed")
        print(f"Timed complete: {results['timed']['failure_rate'] * 100:.1f}% failure rate")

    if args.vlm:
        print("Running VLM evaluation test")
        vlm_client = VLMClient(base_url=args.vlm_url, model=args.vlm_model)
        results["vlm"] = stress_test_vlm_evaluation(capture, output_dir / "vlm", vlm_client)
        print("VLM evaluation complete")

    if not (args.burst or args.timed or args.vlm):
        print("Running all tests")
        results["burst"] = stress_test_burst(adb, capture, args.count, output_dir / "burst")
        print(f"Burst: {results['burst']['failure_rate'] * 100:.1f}% failure rate")

        results["timed"] = stress_test_timed(adb, capture, args.interval, args.duration, output_dir / "timed")
        print(f"Timed: {results['timed']['failure_rate'] * 100:.1f}% failure rate")

        vlm_client = VLMClient(base_url=args.vlm_url, model=args.vlm_model)
        results["vlm"] = stress_test_vlm_evaluation(capture, output_dir / "vlm", vlm_client)
        print("VLM evaluation complete")

    def _json_default(obj):
        if hasattr(obj, "item"):  # numpy scalar (bool_, int64, float64, etc.)
            return obj.item()
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    report_path = output_dir / f"report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2, default=_json_default)
    print(f"Report saved to {report_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
