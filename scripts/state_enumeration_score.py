#!/usr/bin/env python3
"""Score live state-enumeration progress from ALAS observation runs.

This tool grades progress conservatively:
- repeated screenshots are deduped into visual clusters
- low-signal clusters (for example black-frame loops) are excluded
- labeled clusters count as enumerated states
- unlabeled but usable clusters count as candidate states

The output is a single progress number that can be tracked against a target.
"""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from alas_corpus_summarize import _translate_windows_drive_path
from screenshot_dedupe import cluster_records, discover_pngs, index_images

from locate import load_json as load_graph_json
from locate import locate
from observe import build_observations, extract_pixel_coords
from session import init_session


def _load_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return None


def _load_ndjson(path: Path) -> list[dict[str, Any]]:
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return []

    records: list[dict[str, Any]] = []
    for line in text.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict):
            records.append(obj)
    return records


def _coerce_path(value: str) -> Path:
    return Path(_translate_windows_drive_path(value)).resolve()


def _frame_signal(path: Path) -> tuple[float, float]:
    from PIL import Image, ImageStat

    with Image.open(path) as img:
        gray = img.convert("L")
        stat = ImageStat.Stat(gray)
        return float(stat.mean[0]), float(stat.stddev[0])


def is_low_signal(path: Path, *, mean_threshold: float, stddev_threshold: float) -> bool:
    mean, stddev = _frame_signal(path)
    return mean <= mean_threshold and stddev <= stddev_threshold


def _choose_label(records: list[dict[str, Any]]) -> str | None:
    labels = Counter()
    for rec in records:
        locate_result = rec.get("locate_result")
        if isinstance(locate_result, dict):
            state = locate_result.get("state")
            if isinstance(state, str) and state and state != "unknown":
                labels[state] += 1

    if not labels:
        return None
    return labels.most_common(1)[0][0]


@dataclass(frozen=True)
class RunArtifacts:
    run_dir: Path
    screenshots: list[Path]
    observations_by_path: dict[Path, list[dict[str, Any]]]
    graph_path: Path | None


def load_run_artifacts(run_dir: Path) -> RunArtifacts:
    run_dir = run_dir.resolve()
    screenshots_dir = run_dir / "screenshots"
    observations = _load_ndjson(run_dir / "observations.jsonl")
    meta = _load_json(run_dir / "meta.json") or {}

    observations_by_path: dict[Path, list[dict[str, Any]]] = {}
    for rec in observations:
        screenshot_value = rec.get("screenshot")
        if not isinstance(screenshot_value, str):
            continue
        path = _coerce_path(screenshot_value)
        observations_by_path.setdefault(path, []).append(rec)

    return RunArtifacts(
        run_dir=run_dir,
        screenshots=discover_pngs(screenshots_dir),
        observations_by_path=observations_by_path,
        graph_path=_coerce_path(meta["graph_path"]) if isinstance(meta.get("graph_path"), str) else None,
    )


def _classify_with_graph(
    screenshot_path: Path,
    *,
    graph_path: Path | None,
    graph_cache: dict[Path, tuple[dict[str, Any], list[tuple[int, int]]]],
) -> str | None:
    if graph_path is None or not graph_path.exists():
        return None
    if graph_path not in graph_cache:
        graph = load_graph_json(graph_path)
        graph_cache[graph_path] = (graph, extract_pixel_coords(graph))

    graph, pixel_coords = graph_cache[graph_path]
    session = init_session(str(graph_path))
    obs = build_observations(screenshot_path, pixel_coords)
    result = locate(graph, session, obs)
    state = result.get("state")
    if isinstance(state, str) and state and state != "unknown":
        return state
    return None


def _list_run_dirs(*, run_dir: Path | None, runs_root: Path | None, latest: int | None) -> list[Path]:
    if run_dir is not None:
        return [run_dir.resolve()]
    if runs_root is None:
        raise ValueError("Either --run-dir or --runs-root is required")

    candidates = [p for p in runs_root.iterdir() if p.is_dir()]
    candidates.sort(key=lambda p: p.name)
    if latest is not None:
        candidates = candidates[-latest:]
    return candidates


def score_runs(
    run_dirs: list[Path],
    *,
    cluster_threshold: int,
    low_signal_mean: float,
    low_signal_stddev: float,
    target: int,
) -> dict[str, Any]:
    artifacts = [load_run_artifacts(run_dir) for run_dir in run_dirs]

    all_screenshots: list[Path] = []
    observations_by_path: dict[Path, list[dict[str, Any]]] = {}
    graph_cache: dict[Path, tuple[dict[str, Any], list[tuple[int, int]]]] = {}
    for item in artifacts:
        all_screenshots.extend(item.screenshots)
        observations_by_path.update(item.observations_by_path)

    records = index_images(all_screenshots, Path("/"))
    clusters = cluster_records(records, cluster_threshold)

    labeled_states: set[str] = set()
    candidate_clusters = 0
    junk_clusters = 0
    junk_screenshots = 0
    usable_screenshots = 0
    cluster_rows: list[dict[str, Any]] = []

    for cluster_id, cluster in enumerate(sorted(clusters, key=len, reverse=True), start=1):
        representative = records[cluster[0]]
        members = [records[index] for index in cluster]
        label = _choose_label(
            [rec for member in members for rec in observations_by_path.get(member.path.resolve(), [])]
        )
        low_signal = is_low_signal(
            representative.path,
            mean_threshold=low_signal_mean,
            stddev_threshold=low_signal_stddev,
        )
        if not label and not low_signal:
            source_run = next((item for item in artifacts if representative.path in item.screenshots), None)
            label = _classify_with_graph(
                representative.path,
                graph_path=source_run.graph_path if source_run else None,
                graph_cache=graph_cache,
            )

        if low_signal:
            junk_clusters += 1
            junk_screenshots += len(members)
        else:
            usable_screenshots += len(members)
            if label:
                labeled_states.add(label)
            else:
                candidate_clusters += 1

        cluster_rows.append(
            {
                "cluster_id": f"cluster_{cluster_id:05d}",
                "size": len(members),
                "representative": str(representative.path),
                "label": label,
                "low_signal": low_signal,
            }
        )

    estimated_states = len(labeled_states) + candidate_clusters
    return {
        "generated_at": datetime.now(UTC).isoformat(),
        "runs_analyzed": [str(path) for path in run_dirs],
        "total_screenshots": len(all_screenshots),
        "total_clusters": len(cluster_rows),
        "junk_clusters": junk_clusters,
        "junk_screenshots": junk_screenshots,
        "usable_clusters": len(cluster_rows) - junk_clusters,
        "usable_screenshots": usable_screenshots,
        "labeled_states": sorted(labeled_states),
        "labeled_state_count": len(labeled_states),
        "candidate_unlabeled_clusters": candidate_clusters,
        "estimated_enumerated_states": estimated_states,
        "target": target,
        "remaining_to_target": max(0, target - estimated_states),
        "cluster_threshold": cluster_threshold,
        "low_signal_mean_threshold": low_signal_mean,
        "low_signal_stddev_threshold": low_signal_stddev,
        "top_clusters": cluster_rows[:20],
    }


def render_text(report: dict[str, Any]) -> str:
    lines = [
        f"estimated_enumerated_states: {report['estimated_enumerated_states']}",
        f"target: {report['target']}",
        f"remaining_to_target: {report['remaining_to_target']}",
        f"total_screenshots: {report['total_screenshots']}",
        f"usable_screenshots: {report['usable_screenshots']}",
        f"junk_screenshots: {report['junk_screenshots']}",
        f"usable_clusters: {report['usable_clusters']}",
        f"junk_clusters: {report['junk_clusters']}",
        f"labeled_state_count: {report['labeled_state_count']}",
        "labeled_states:",
    ]
    for state in report["labeled_states"]:
        lines.append(f"  - {state}")

    lines.append("top_clusters:")
    for row in report["top_clusters"][:10]:
        label = row["label"] if row["label"] else "unlabeled"
        quality = "junk" if row["low_signal"] else "usable"
        lines.append(f"  - {row['cluster_id']}: size={row['size']} label={label} quality={quality}")

    return "\n".join(lines) + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Score live state-enumeration progress from observation runs")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--run-dir", help="Single observation run directory")
    source.add_argument("--runs-root", help="Root directory containing observation runs")
    parser.add_argument("--latest", type=int, help="Analyze only the latest N runs from --runs-root")
    parser.add_argument("--format", choices=["text", "json"], default="text")
    parser.add_argument("--output", help="Write the report to a file instead of stdout")
    parser.add_argument("--target", type=int, default=50, help="Target enumerated-state score")
    parser.add_argument(
        "--cluster-threshold",
        type=int,
        default=8,
        help="Perceptual hash distance threshold for visual clustering",
    )
    parser.add_argument(
        "--low-signal-mean",
        type=float,
        default=8.0,
        help="Mean grayscale threshold below which a representative frame is treated as junk",
    )
    parser.add_argument(
        "--low-signal-stddev",
        type=float,
        default=6.0,
        help="Stddev grayscale threshold below which a representative frame is treated as junk",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    run_dir = Path(args.run_dir).resolve() if args.run_dir else None
    runs_root = Path(args.runs_root).resolve() if args.runs_root else None
    run_dirs = _list_run_dirs(run_dir=run_dir, runs_root=runs_root, latest=args.latest)

    report = score_runs(
        run_dirs,
        cluster_threshold=args.cluster_threshold,
        low_signal_mean=args.low_signal_mean,
        low_signal_stddev=args.low_signal_stddev,
        target=args.target,
    )

    output = json.dumps(report, indent=2) + "\n" if args.format == "json" else render_text(report)
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
    else:
        print(output, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
