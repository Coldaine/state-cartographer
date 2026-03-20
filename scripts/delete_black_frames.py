"""Delete verified black-frame PNG captures from the observation corpus.

This is a corpus cleanup tool for recorded screenshots, not a live runtime
tool. It targets the large timestamped capture directories where black-frame
spam accumulates:

- data/raw_stream
- data/alas-observe/**/screenshots

Verification rule:
- file size <= max_size_bytes
- grayscale mean <= mean_threshold
- grayscale stddev <= stddev_threshold

The default mode is a dry run. Pass ``--delete`` to actually unlink files.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from PIL import Image, ImageStat

DEFAULT_ROOTS = [
    Path("data/raw_stream"),
    Path("data/alas-observe"),
]


def is_verified_black_frame(
    path: Path,
    *,
    max_size_bytes: int,
    mean_threshold: float,
    stddev_threshold: float,
) -> tuple[bool, dict[str, float | int]]:
    size = path.stat().st_size
    if size > max_size_bytes:
        return False, {"size": size}

    with Image.open(path) as img:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        mean = float(stat.mean[0])
        stddev = float(stat.stddev[0])

    return mean <= mean_threshold and stddev <= stddev_threshold, {
        "size": size,
        "mean": mean,
        "stddev": stddev,
    }


def iter_pngs(roots: list[Path]) -> list[Path]:
    out: list[Path] = []
    for root in roots:
        if not root.exists():
            continue
        out.extend(root.rglob("*.png"))
    return out


def main() -> int:
    parser = argparse.ArgumentParser(description="Delete verified black-frame PNGs from the capture corpus")
    parser.add_argument(
        "--root",
        dest="roots",
        action="append",
        help="Root directory to scan. Repeatable. Defaults to data/raw_stream and data/alas-observe.",
    )
    parser.add_argument(
        "--max-size-bytes",
        type=int,
        default=10_000,
        help="Only inspect PNGs at or below this size. Default: 10000.",
    )
    parser.add_argument(
        "--mean-threshold",
        type=float,
        default=5.0,
        help="Maximum grayscale mean for a verified black frame. Default: 5.0.",
    )
    parser.add_argument(
        "--stddev-threshold",
        type=float,
        default=2.0,
        help="Maximum grayscale stddev for a verified black frame. Default: 2.0.",
    )
    parser.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files. Without this flag, the script performs a dry run.",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit the summary as JSON.",
    )
    args = parser.parse_args()

    roots = [Path(p) for p in args.roots] if args.roots else DEFAULT_ROOTS
    pngs = iter_pngs(roots)
    verified: list[tuple[Path, dict[str, float | int]]] = []
    errors: list[dict[str, str]] = []

    for path in pngs:
        try:
            ok, metrics = is_verified_black_frame(
                path,
                max_size_bytes=args.max_size_bytes,
                mean_threshold=args.mean_threshold,
                stddev_threshold=args.stddev_threshold,
            )
            if ok:
                verified.append((path, metrics))
        except Exception as exc:  # pragma: no cover - defensive
            errors.append({"path": str(path), "error": str(exc)})

    deleted = 0
    if args.delete:
        for path, _metrics in verified:
            path.unlink(missing_ok=False)
            deleted += 1

    by_root: Counter[str] = Counter()
    for path, _metrics in verified:
        path_str = str(path)
        if path_str.startswith("data\\raw_stream") or path_str.startswith("data/raw_stream"):
            by_root["data/raw_stream"] += 1
        elif path_str.startswith("data\\alas-observe") or path_str.startswith("data/alas-observe"):
            by_root["data/alas-observe"] += 1
        else:
            by_root["other"] += 1

    summary = {
        "mode": "delete" if args.delete else "dry-run",
        "roots": [str(root) for root in roots],
        "scanned_pngs": len(pngs),
        "verified_black_frames": len(verified),
        "deleted": deleted,
        "by_root": dict(by_root),
        "thresholds": {
            "max_size_bytes": args.max_size_bytes,
            "mean_threshold": args.mean_threshold,
            "stddev_threshold": args.stddev_threshold,
        },
        "errors": errors,
    }

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Mode: {summary['mode']}")
    print(f"Scanned PNGs: {summary['scanned_pngs']}")
    print(f"Verified black frames: {summary['verified_black_frames']}")
    print(f"Deleted: {summary['deleted']}")
    for key, value in summary["by_root"].items():
        print(f"  {key}: {value}")
    if errors:
        print(f"Errors: {len(errors)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
