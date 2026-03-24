#!/usr/bin/env python3
"""Corpus hygiene tooling for screenshot corpora.

This script owns the retained corpus-cleanup jobs:

- perceptual duplicate clustering
- verified black-frame detection and optional deletion
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any

DEFAULT_BLACK_FRAME_ROOTS = [
    Path("data/raw_stream"),
]


@dataclass(frozen=True)
class ImageFingerprint:
    path: Path
    relative_path: str
    size_bytes: int
    fingerprint_method: str
    fingerprint: str
    hash_int: int | None = None


class UnionFind:
    def __init__(self, size: int):
        self.parent = list(range(size))
        self.rank = [0] * size

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        root_a = self.find(a)
        root_b = self.find(b)
        if root_a == root_b:
            return
        if self.rank[root_a] < self.rank[root_b]:
            self.parent[root_a] = root_b
            return
        if self.rank[root_a] > self.rank[root_b]:
            self.parent[root_b] = root_a
            return
        self.parent[root_b] = root_a
        self.rank[root_a] += 1


class _BKNode:
    def __init__(self, value: int, index: int):
        self.value = value
        self.indices = [index]
        self.children: dict[int, _BKNode] = {}


class BKTree:
    """BK-tree specialized for Hamming distance on integer fingerprints."""

    def __init__(self):
        self.root: _BKNode | None = None

    def add(self, value: int, index: int) -> None:
        if self.root is None:
            self.root = _BKNode(value, index)
            return

        node = self.root
        while True:
            distance = hamming_distance(value, node.value)
            if distance == 0:
                node.indices.append(index)
                return
            child = node.children.get(distance)
            if child is None:
                node.children[distance] = _BKNode(value, index)
                return
            node = child

    def search(self, value: int, max_distance: int) -> list[int]:
        if self.root is None:
            return []

        results: list[int] = []
        stack = [self.root]

        while stack:
            node = stack.pop()
            distance = hamming_distance(value, node.value)
            if distance <= max_distance:
                results.extend(node.indices)

            low = distance - max_distance
            high = distance + max_distance
            for edge_distance, child in node.children.items():
                if low <= edge_distance <= high:
                    stack.append(child)

        return results


def discover_pngs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".png")


def discover_pngs_under_roots(roots: list[Path]) -> list[Path]:
    seen: set[Path] = set()
    for root in roots:
        if not root.exists():
            continue
        seen.update(discover_pngs(root))
    return sorted(seen, key=lambda path: path.as_posix())


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


@lru_cache(maxsize=1)
def _load_dedupe_backend():
    try:
        import imagehash
        from PIL import Image
    except Exception:
        return None
    return Image, imagehash


@lru_cache(maxsize=1)
def _load_black_frame_backend():
    try:
        from PIL import Image, ImageStat
    except Exception as exc:
        raise SystemExit(
            "corpus_cleanup.py black-frames requires Pillow. Run it with "
            "`uv run --extra vision python scripts/corpus_cleanup.py black-frames ...`."
        ) from exc
    return Image, ImageStat


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1 << 20)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest()


def fingerprint_path(path: Path, root: Path) -> ImageFingerprint:
    backend = _load_dedupe_backend()
    if backend is not None:
        image_module, imagehash_module = backend
        try:
            with image_module.open(path) as img:
                perceptual = imagehash_module.phash(img)
            phash_hex = str(perceptual)
            return ImageFingerprint(
                path=path,
                relative_path=_safe_relative(path, root),
                size_bytes=path.stat().st_size,
                fingerprint_method="phash",
                fingerprint=phash_hex,
                hash_int=int(phash_hex, 16),
            )
        except Exception:
            pass

    sha = _sha256_file(path)
    return ImageFingerprint(
        path=path,
        relative_path=_safe_relative(path, root),
        size_bytes=path.stat().st_size,
        fingerprint_method="sha256",
        fingerprint=sha,
        hash_int=None,
    )


def index_images(paths: list[Path], root: Path) -> list[ImageFingerprint]:
    return [fingerprint_path(path, root) for path in paths]


def _cluster_exact(records: list[ImageFingerprint], indices: list[int]) -> list[list[int]]:
    grouped: dict[str, list[int]] = defaultdict(list)
    for record_index in indices:
        grouped[records[record_index].fingerprint].append(record_index)
    return list(grouped.values())


def _cluster_phash(records: list[ImageFingerprint], indices: list[int], threshold: int) -> list[list[int]]:
    tree = BKTree()
    local_hashes: list[int] = []
    for local_index, record_index in enumerate(indices):
        hash_value = records[record_index].hash_int
        if hash_value is None:
            raise ValueError("phash clustering requires integer hash values")
        local_hashes.append(hash_value)
        tree.add(hash_value, local_index)

    uf = UnionFind(len(indices))
    for local_index, hash_value in enumerate(local_hashes):
        for neighbor_index in tree.search(hash_value, threshold):
            if neighbor_index <= local_index:
                continue
            uf.union(local_index, neighbor_index)

    grouped: dict[int, list[int]] = defaultdict(list)
    for local_index, record_index in enumerate(indices):
        grouped[uf.find(local_index)].append(record_index)
    return list(grouped.values())


def cluster_records(records: list[ImageFingerprint], distance_threshold: int) -> list[list[int]]:
    if distance_threshold < 0:
        raise ValueError("distance_threshold must be >= 0")
    if not records:
        return []

    by_method: dict[str, list[int]] = defaultdict(list)
    for index, record in enumerate(records):
        by_method[record.fingerprint_method].append(index)

    clusters: list[list[int]] = []
    for method, method_indices in by_method.items():
        if method == "phash":
            clusters.extend(_cluster_phash(records, method_indices, distance_threshold))
            continue
        clusters.extend(_cluster_exact(records, method_indices))
    return clusters


def _cluster_to_json(records: list[ImageFingerprint], cluster: list[int], cluster_id: int) -> dict[str, Any]:
    sorted_indices = sorted(cluster, key=lambda idx: records[idx].relative_path)
    representative = records[sorted_indices[0]]

    members: list[dict[str, Any]] = []
    for index in sorted_indices:
        record = records[index]
        distance = None
        if (
            representative.fingerprint_method == "phash"
            and representative.hash_int is not None
            and record.hash_int is not None
        ):
            distance = hamming_distance(representative.hash_int, record.hash_int)
        elif representative.fingerprint_method != "phash":
            distance = 0 if record.fingerprint == representative.fingerprint else None

        members.append(
            {
                "path": record.relative_path,
                "size_bytes": record.size_bytes,
                "fingerprint": record.fingerprint,
                "distance_to_representative": distance,
            }
        )

    total_cluster_bytes = sum(records[index].size_bytes for index in sorted_indices)
    return {
        "cluster_id": f"cluster_{cluster_id:05d}",
        "size": len(sorted_indices),
        "fingerprint_method": representative.fingerprint_method,
        "representative": representative.relative_path,
        "representative_size_bytes": representative.size_bytes,
        "cluster_size_bytes": total_cluster_bytes,
        "potential_bytes_saved": total_cluster_bytes - representative.size_bytes,
        "members": members,
    }


def generate_dedupe_report(
    input_root: Path,
    distance_threshold: int = 6,
    include_singletons: bool = False,
) -> dict[str, Any]:
    png_paths = discover_pngs(input_root)
    records = index_images(png_paths, input_root)
    clusters = cluster_records(records, distance_threshold)

    json_clusters: list[dict[str, Any]] = []
    for cluster_id, cluster in enumerate(clusters, start=1):
        if not include_singletons and len(cluster) == 1:
            continue
        json_clusters.append(_cluster_to_json(records, cluster, cluster_id))

    json_clusters.sort(key=lambda cluster: (-cluster["size"], cluster["representative"]))

    duplicate_images = sum(max(0, cluster["size"] - 1) for cluster in json_clusters)
    potential_bytes_saved = sum(cluster["potential_bytes_saved"] for cluster in json_clusters)

    methods_count: dict[str, int] = defaultdict(int)
    for record in records:
        methods_count[record.fingerprint_method] += 1

    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "input_root": str(input_root.resolve()),
        "distance_threshold": distance_threshold,
        "total_images": len(records),
        "cluster_count": len(json_clusters),
        "duplicate_images": duplicate_images,
        "potential_bytes_saved": potential_bytes_saved,
        "perceptual_hash_available": _load_dedupe_backend() is not None,
        "perceptual_hash_used": methods_count.get("phash", 0) > 0,
        "fingerprint_methods": dict(methods_count),
        "clusters": json_clusters,
    }


def write_json_report(report: dict[str, Any], output_path: Path | None) -> None:
    json_payload = json.dumps(report, indent=2, sort_keys=False)
    if output_path is None:
        print(json_payload)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json_payload + "\n", encoding="utf-8")


def classify_root(path: Path) -> str:
    path_str = path.as_posix()
    if path_str.startswith("data/raw_stream"):
        return "data/raw_stream"
    return "other"


def is_verified_black_frame(
    path: Path,
    *,
    max_size_bytes: int,
    mean_threshold: float,
    stddev_threshold: float,
) -> tuple[bool, dict[str, float | int]]:
    image_module, image_stat_module = _load_black_frame_backend()

    size = path.stat().st_size
    if size > max_size_bytes:
        return False, {"size": size}

    with image_module.open(path) as img:
        gray = img.convert("L")
        stat = image_stat_module.Stat(gray)
        mean = float(stat.mean[0])
        stddev = float(stat.stddev[0])

    return mean <= mean_threshold and stddev <= stddev_threshold, {
        "size": size,
        "mean": mean,
        "stddev": stddev,
    }


def generate_black_frame_report(
    roots: list[Path],
    *,
    max_size_bytes: int,
    mean_threshold: float,
    stddev_threshold: float,
    delete: bool,
) -> tuple[dict[str, Any], list[dict[str, object]]]:
    pngs = discover_pngs_under_roots(roots)
    verified: list[tuple[Path, dict[str, float | int]]] = []
    errors: list[dict[str, str]] = []

    for path in pngs:
        try:
            ok, metrics = is_verified_black_frame(
                path,
                max_size_bytes=max_size_bytes,
                mean_threshold=mean_threshold,
                stddev_threshold=stddev_threshold,
            )
            if ok:
                verified.append((path, metrics))
        except Exception as exc:
            errors.append({"path": str(path), "error": str(exc)})

    deleted = 0
    if delete:
        for path, _metrics in verified:
            path.unlink(missing_ok=False)
            deleted += 1

    verified_entries: list[dict[str, object]] = []
    by_root: Counter[str] = Counter()
    for path, metrics in sorted(verified, key=lambda item: item[0].as_posix()):
        root_bucket = classify_root(path)
        by_root[root_bucket] += 1
        verified_entries.append(
            {
                "path": path.as_posix(),
                "root": root_bucket,
                "metrics": metrics,
                "deleted": delete,
            }
        )

    summary = {
        "generated_at": datetime.now(UTC).isoformat(),
        "mode": "delete" if delete else "dry-run",
        "roots": [str(root) for root in roots],
        "scanned_pngs": len(pngs),
        "verified_black_frames": len(verified),
        "deleted": deleted,
        "by_root": dict(by_root),
        "thresholds": {
            "max_size_bytes": max_size_bytes,
            "mean_threshold": mean_threshold,
            "stddev_threshold": stddev_threshold,
        },
        "errors": errors,
    }
    return summary, verified_entries


def run_dedupe(args: argparse.Namespace) -> int:
    input_root = Path(args.input)
    if not input_root.exists():
        raise FileNotFoundError(f"input directory does not exist: {input_root}")
    if not input_root.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_root}")

    report = generate_dedupe_report(
        input_root=input_root,
        distance_threshold=args.threshold,
        include_singletons=args.include_singletons,
    )

    output_path = Path(args.output) if args.output else None
    write_json_report(report, output_path)
    return 0


def run_black_frames(args: argparse.Namespace) -> int:
    roots = [Path(p) for p in args.roots] if args.roots else DEFAULT_BLACK_FRAME_ROOTS
    summary, verified_entries = generate_black_frame_report(
        roots=roots,
        max_size_bytes=args.max_size_bytes,
        mean_threshold=args.mean_threshold,
        stddev_threshold=args.stddev_threshold,
        delete=args.delete,
    )

    if args.report:
        report = {
            **summary,
            "verified_files": verified_entries,
        }
        args.report.parent.mkdir(parents=True, exist_ok=True)
        args.report.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")

    if args.json:
        print(json.dumps(summary, indent=2))
        return 0

    print(f"Mode: {summary['mode']}")
    print(f"Scanned PNGs: {summary['scanned_pngs']}")
    print(f"Verified black frames: {summary['verified_black_frames']}")
    print(f"Deleted: {summary['deleted']}")
    for key, value in summary["by_root"].items():
        print(f"  {key}: {value}")
    if summary["errors"]:
        print(f"Errors: {len(summary['errors'])}")
    if args.report:
        print(f"Report: {args.report}")
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Corpus hygiene tooling for screenshot corpora")
    subparsers = parser.add_subparsers(dest="command", required=True)

    dedupe = subparsers.add_parser("dedupe", help="Cluster visually duplicate PNG screenshots")
    dedupe.add_argument("--input", required=True, help="Directory root containing PNG screenshots")
    dedupe.add_argument("--output", help="Path to output JSON report (default: stdout)")
    dedupe.add_argument(
        "--threshold",
        type=int,
        default=6,
        help="Hamming distance threshold for perceptual hash clustering (default: 6)",
    )
    dedupe.add_argument(
        "--include-singletons",
        action="store_true",
        help="Include one-image clusters in output (default: duplicates only)",
    )
    dedupe.set_defaults(handler=run_dedupe)

    black_frames = subparsers.add_parser(
        "black-frames",
        help="Find verified black-frame PNGs and optionally delete them",
    )
    black_frames.add_argument(
        "--root",
        dest="roots",
        action="append",
        help="Root directory to scan. Repeatable. Defaults to data/raw_stream.",
    )
    black_frames.add_argument(
        "--max-size-bytes",
        type=int,
        default=10_000,
        help="Only inspect PNGs at or below this size. Default: 10000.",
    )
    black_frames.add_argument(
        "--mean-threshold",
        type=float,
        default=5.0,
        help="Maximum grayscale mean for a verified black frame. Default: 5.0.",
    )
    black_frames.add_argument(
        "--stddev-threshold",
        type=float,
        default=2.0,
        help="Maximum grayscale stddev for a verified black frame. Default: 2.0.",
    )
    black_frames.add_argument(
        "--delete",
        action="store_true",
        help="Actually delete files. Without this flag, the script performs a dry run.",
    )
    black_frames.add_argument(
        "--json",
        action="store_true",
        help="Emit the summary as JSON.",
    )
    black_frames.add_argument(
        "--report",
        type=Path,
        help="Optional path to write a full JSON manifest of verified files and thresholds.",
    )
    black_frames.set_defaults(handler=run_black_frames)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())
