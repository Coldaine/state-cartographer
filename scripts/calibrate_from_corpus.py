"""calibrate_from_corpus.py — Learn real pixel anchors from a labeled corpus.

Consumes the JSONL index produced by ``alas_sidecar.py`` and generates
real pixel-color anchors for ``graph.json``.

For each ALAS-labeled page:
 1. Loads all corpus screenshots tagged with that page.
 2. Samples pixel RGB at a grid of candidate coordinates across all images.
 3. Selects coordinates where RGB is *stable* within the page (low variance)
    and *discriminating* across pages (different from other pages' values).
 4. Writes the top anchors back to graph.json.

Usage:
    uv run python scripts/calibrate_from_corpus.py \\
      --corpus data/corpus \\
      --graph  examples/azur-lane/graph.json \\
      --min-samples 3 \\
      --top-k 5

Requires: Pillow (``uv sync --extra vision``).
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np
from PIL import Image

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CORPUS = PROJECT_ROOT / "data" / "corpus"
DEFAULT_GRAPH = PROJECT_ROOT / "examples" / "azur-lane" / "graph.json"

# Grid of candidate coordinates to sample.  Assumes 1280x720 resolution.
# Avoids edges (UI chrome) and center (dynamic content).
GRID_STEP = 40
MARGIN_X = 60
MARGIN_Y = 40
SCREEN_W = 1280
SCREEN_H = 720

# Filtering thresholds
MAX_INTRA_VARIANCE = 200.0  # max per-channel variance within one page
MIN_INTER_DISTANCE = 60.0  # min Euclidean RGB distance to nearest other page
COLOR_TOLERANCE = 30  # tolerance for anchor matching (written to graph)


# ---------------------------------------------------------------------------
# Corpus loading
# ---------------------------------------------------------------------------


def load_corpus(corpus_dir: Path, min_samples: int = 3) -> dict[str, list[Path]]:
    """Load the JSONL index and group screenshot paths by alas_page.

    Only returns pages with at least *min_samples* screenshots.
    """
    index_path = corpus_dir / "index.jsonl"
    if not index_path.exists():
        raise FileNotFoundError(f"Corpus index not found: {index_path}")

    pages: dict[str, list[Path]] = defaultdict(list)

    for line in index_path.read_text(encoding="utf-8").strip().splitlines():
        rec = json.loads(line)
        page = rec.get("alas_page", "unknown")
        rel_path = rec.get("path", "")
        img_path = corpus_dir / rel_path
        if img_path.exists():
            pages[page].append(img_path)

    # Filter to pages with enough samples
    return {p: imgs for p, imgs in pages.items() if len(imgs) >= min_samples}


# ---------------------------------------------------------------------------
# Pixel sampling
# ---------------------------------------------------------------------------


def build_candidate_grid() -> list[tuple[int, int]]:
    """Generate a grid of (x, y) candidate coordinates."""
    coords = []
    for x in range(MARGIN_X, SCREEN_W - MARGIN_X, GRID_STEP):
        for y in range(MARGIN_Y, SCREEN_H - MARGIN_Y, GRID_STEP):
            coords.append((x, y))
    return coords


def sample_pixels(
    image_paths: list[Path],
    coords: list[tuple[int, int]],
) -> np.ndarray:
    """Sample RGB at each coord from each image.

    Returns array of shape (n_images, n_coords, 3).
    """
    n_images = len(image_paths)
    n_coords = len(coords)
    result = np.zeros((n_images, n_coords, 3), dtype=np.float64)

    for i, path in enumerate(image_paths):
        img = Image.open(path).convert("RGB")
        pixels = np.array(img)  # (H, W, 3)
        for j, (x, y) in enumerate(coords):
            if 0 <= y < pixels.shape[0] and 0 <= x < pixels.shape[1]:
                result[i, j] = pixels[y, x]
    return result


# ---------------------------------------------------------------------------
# Anchor selection
# ---------------------------------------------------------------------------


def select_anchors(
    page_samples: dict[str, np.ndarray],
    coords: list[tuple[int, int]],
    top_k: int = 5,
) -> dict[str, list[dict[str, Any]]]:
    """Select the best anchor coordinates for each page.

    Returns {page_name: [anchor_dict, ...]}.
    """
    # Compute mean RGB per page per coord: {page: (n_coords, 3)}
    page_means: dict[str, np.ndarray] = {}
    page_vars: dict[str, np.ndarray] = {}
    for page, samples in page_samples.items():
        page_means[page] = samples.mean(axis=0)  # (n_coords, 3)
        page_vars[page] = samples.var(axis=0)  # (n_coords, 3)

    all_pages = list(page_means.keys())
    result: dict[str, list[dict[str, Any]]] = {}

    for page in all_pages:
        mean_rgb = page_means[page]  # (n_coords, 3)
        var_rgb = page_vars[page]  # (n_coords, 3)
        intra_var = var_rgb.sum(axis=1)  # (n_coords,) — total variance per coord

        # Compute minimum inter-page distance for each coord
        other_means = np.stack([page_means[p] for p in all_pages if p != page])  # (n_other_pages, n_coords, 3)

        # Distance from this page's mean to each other page's mean
        diffs = other_means - mean_rgb[np.newaxis, :]  # (n_other, n_coords, 3)
        distances = np.sqrt((diffs**2).sum(axis=2))  # (n_other, n_coords)
        min_inter_dist = distances.min(axis=0)  # (n_coords,)

        # Score: high inter-page distance, low intra-page variance
        # Filter out bad candidates first
        valid = (intra_var <= MAX_INTRA_VARIANCE) & (min_inter_dist >= MIN_INTER_DISTANCE)
        if not valid.any():
            # Relax constraints — take whatever is least-bad
            score = min_inter_dist - intra_var * 0.1
        else:
            score = np.where(valid, min_inter_dist - intra_var * 0.01, -1e6)

        # Pick top-k by score
        top_indices = np.argsort(-score)[:top_k]

        anchors = []
        for idx in top_indices:
            x, y = coords[idx]
            rgb = mean_rgb[idx].round().astype(int).tolist()
            anchors.append(
                {
                    "type": "pixel_color",
                    "x": int(x),
                    "y": int(y),
                    "expected_rgb": rgb,
                    "cost": 1,
                    "tolerance": COLOR_TOLERANCE,
                    "label": f"corpus-calibrated ({page_samples[page].shape[0]} samples, var={intra_var[idx]:.0f})",
                    "_score": float(score[idx]),
                    "_intra_var": float(intra_var[idx]),
                    "_min_inter_dist": float(min_inter_dist[idx]),
                }
            )

        result[page] = anchors

    return result


# ---------------------------------------------------------------------------
# Graph update
# ---------------------------------------------------------------------------


def update_graph(
    graph: dict[str, Any],
    calibrated: dict[str, list[dict[str, Any]]],
) -> dict[str, Any]:
    """Merge calibrated anchors into graph.json.

    Creates states that don't exist yet, replaces anchors for states
    that do.
    """
    states = graph.setdefault("states", {})

    for page, anchors in calibrated.items():
        # Strip internal scoring fields before writing
        clean_anchors = []
        for a in anchors:
            clean = {k: v for k, v in a.items() if not k.startswith("_")}
            clean_anchors.append(clean)

        if page in states:
            states[page]["anchors"] = clean_anchors
            states[page]["calibration_source"] = "corpus"
        else:
            states[page] = {
                "description": f"{page} (auto-calibrated from corpus)",
                "anchors": clean_anchors,
                "confidence_threshold": 0.66,
                "calibration_source": "corpus",
            }

    # Update metadata
    meta = graph.setdefault("metadata", {})
    meta["last_calibration"] = "calibrate_from_corpus.py"

    return graph


# ---------------------------------------------------------------------------
# Reporting
# ---------------------------------------------------------------------------


def print_report(
    calibrated: dict[str, list[dict[str, Any]]],
    page_counts: dict[str, int],
) -> None:
    """Print a summary of calibration results."""
    print("\n=== Calibration Report ===\n")
    print(f"Pages calibrated: {len(calibrated)}")
    print()

    for page in sorted(calibrated.keys()):
        anchors = calibrated[page]
        n_samples = page_counts.get(page, 0)
        print(f"  {page} ({n_samples} samples)")
        for a in anchors:
            x, y = a["x"], a["y"]
            rgb = a["expected_rgb"]
            score = a.get("_score", 0)
            var = a.get("_intra_var", 0)
            dist = a.get("_min_inter_dist", 0)
            print(f"    ({x:4d}, {y:4d})  RGB={rgb}  score={score:.1f}  var={var:.0f}  dist={dist:.0f}")
        print()

    total = sum(len(a) for a in calibrated.values())
    print(f"Total anchors: {total}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Learn pixel anchors from labeled corpus screenshots",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--corpus",
        default=str(DEFAULT_CORPUS),
        help="Path to corpus directory (default: data/corpus)",
    )
    parser.add_argument(
        "--graph",
        default=str(DEFAULT_GRAPH),
        help="Path to graph.json (default: examples/azur-lane/graph.json)",
    )
    parser.add_argument(
        "--min-samples",
        type=int,
        default=3,
        help="Minimum screenshots per page to calibrate (default: 3)",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=5,
        help="Number of anchor points per page (default: 5)",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print report without writing to graph.json",
    )
    args = parser.parse_args()

    corpus_dir = Path(args.corpus)
    graph_path = Path(args.graph)

    # Load corpus
    print(f"Loading corpus from {corpus_dir} ...")
    pages = load_corpus(corpus_dir, min_samples=args.min_samples)
    if not pages:
        print("No pages with enough samples found in corpus.", file=sys.stderr)
        print(f"Need at least {args.min_samples} screenshots per page.", file=sys.stderr)
        sys.exit(1)

    page_counts = {p: len(imgs) for p, imgs in pages.items()}
    print(f"Found {len(pages)} pages with >= {args.min_samples} samples:")
    for p in sorted(pages):
        print(f"  {p}: {page_counts[p]} screenshots")
    print()

    # Sample pixels
    coords = build_candidate_grid()
    print(f"Sampling {len(coords)} candidate coordinates across {sum(page_counts.values())} images ...")

    page_samples: dict[str, np.ndarray] = {}
    for page, img_paths in pages.items():
        page_samples[page] = sample_pixels(img_paths, coords)

    # Select anchors
    if len(pages) < 2:
        print("Warning: Only 1 page found. Inter-page discrimination not possible.", file=sys.stderr)
        print("         Anchors will be selected by stability only.", file=sys.stderr)
        # For single-page case, fabricate a dummy "other" page of zeros
        only_page = next(iter(page_samples.keys()))
        dummy = np.zeros_like(page_samples[only_page])
        page_samples["__dummy__"] = dummy

    calibrated = select_anchors(page_samples, coords, top_k=args.top_k)

    # Remove dummy if added
    calibrated.pop("__dummy__", None)

    # Report
    print_report(calibrated, page_counts)

    if args.dry_run:
        print("\n--dry-run specified. No files written.")
        return

    # Load graph and update
    if graph_path.exists():
        graph = json.loads(graph_path.read_text(encoding="utf-8"))
    else:
        graph = {"states": {}, "metadata": {"source": "calibrate_from_corpus.py"}}

    graph = update_graph(graph, calibrated)

    graph_path.parent.mkdir(parents=True, exist_ok=True)
    graph_path.write_text(json.dumps(graph, indent=2) + "\n", encoding="utf-8")
    print(f"\nWrote {len(calibrated)} calibrated pages to {graph_path}")


if __name__ == "__main__":
    main()
