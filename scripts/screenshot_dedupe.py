#!/usr/bin/env python3
"""Cluster and deduplicate large screenshot corpora.

The tool scans a directory tree for PNG files, computes lightweight image
fingerprints, then emits JSON with dedupe clusters and summary stats.

Fingerprint strategy:
1. Prefer perceptual hash (`imagehash.phash`) when Pillow + imagehash exist.
2. Fall back to SHA-256 file hash when vision deps are unavailable or fail.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from collections import defaultdict
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path
from typing import Any


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


@lru_cache(maxsize=1)
def _load_vision_backend():
    try:
        import imagehash
        from PIL import Image
    except Exception:
        return None
    return Image, imagehash


def discover_pngs(root: Path) -> list[Path]:
    return sorted(path for path in root.rglob("*") if path.is_file() and path.suffix.lower() == ".png")


def hamming_distance(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def _safe_relative(path: Path, root: Path) -> str:
    try:
        return path.relative_to(root).as_posix()
    except ValueError:
        return path.as_posix()


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
    backend = _load_vision_backend()
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
            # Fall through to deterministic file-hash fallback.
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


def generate_report(input_root: Path, distance_threshold: int = 6, include_singletons: bool = False) -> dict[str, Any]:
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
        "perceptual_hash_available": _load_vision_backend() is not None,
        "perceptual_hash_used": methods_count.get("phash", 0) > 0,
        "fingerprint_methods": dict(methods_count),
        "clusters": json_clusters,
    }


def write_report(report: dict[str, Any], output_path: Path | None) -> None:
    json_payload = json.dumps(report, indent=2, sort_keys=False)
    if output_path is None:
        print(json_payload)
        return
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json_payload + "\n", encoding="utf-8")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Cluster and dedupe screenshot PNG corpora")
    parser.add_argument("--input", required=True, help="Directory root containing PNG screenshots")
    parser.add_argument("--output", help="Path to output JSON report (default: stdout)")
    parser.add_argument(
        "--threshold",
        type=int,
        default=6,
        help="Hamming distance threshold for perceptual hash clustering (default: 6)",
    )
    parser.add_argument(
        "--include-singletons",
        action="store_true",
        help="Include one-image clusters in output (default: duplicates only)",
    )
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    input_root = Path(args.input)
    if not input_root.exists():
        raise FileNotFoundError(f"input directory does not exist: {input_root}")
    if not input_root.is_dir():
        raise NotADirectoryError(f"input path is not a directory: {input_root}")

    report = generate_report(
        input_root=input_root,
        distance_threshold=args.threshold,
        include_singletons=args.include_singletons,
    )

    output_path = Path(args.output) if args.output else None
    write_report(report, output_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
