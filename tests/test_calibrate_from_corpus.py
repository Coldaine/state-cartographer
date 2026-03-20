"""Tests for calibrate_from_corpus.py — learn anchors from labeled corpus."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest
from calibrate_from_corpus import (
    build_candidate_grid,
    load_corpus,
    sample_pixels,
    select_anchors,
    update_graph,
)
from png_factory import make_rgb_png


def _make_corpus(tmp_path: Path, pages: dict[str, list[tuple[int, int, int]]]) -> Path:
    """Create a minimal corpus with solid-color PNGs for each page.

    pages: {page_name: [rgb_tuple_per_image, ...]}
    Each rgb tuple becomes a 1280x720 solid-color PNG.
    """
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    index = corpus / "index.jsonl"

    img_num = 0
    records = []
    for page, colors in pages.items():
        for rgb in colors:
            img_num += 1
            fname = f"{img_num:06d}.png"
            pixels = [rgb] * (1280 * 720)
            png_data = make_rgb_png(pixels, 1280, 720)
            (corpus / fname).write_bytes(png_data)
            records.append(
                {
                    "ts": f"2026-01-01T00:00:{img_num:02d}Z",
                    "path": fname,
                    "alas_page": page,
                    "alas_task": "test",
                    "trigger": "test",
                    "log_line": img_num,
                    "confidence": "arrive",
                }
            )

    index.write_text(
        "\n".join(json.dumps(r) for r in records) + "\n",
        encoding="utf-8",
    )
    return corpus


def test_load_corpus_groups_by_page(tmp_path: Path):
    corpus = _make_corpus(
        tmp_path,
        {
            "page_a": [(255, 0, 0)] * 3,
            "page_b": [(0, 255, 0)] * 3,
            "page_c": [(0, 0, 255)] * 2,  # only 2 samples, below default min
        },
    )
    pages = load_corpus(corpus, min_samples=3)
    assert "page_a" in pages
    assert "page_b" in pages
    assert "page_c" not in pages  # filtered out
    assert len(pages["page_a"]) == 3
    assert len(pages["page_b"]) == 3


def test_load_corpus_missing_index(tmp_path: Path):
    with pytest.raises(FileNotFoundError):
        load_corpus(tmp_path / "nonexistent")


def test_build_candidate_grid():
    coords = build_candidate_grid()
    assert len(coords) > 100  # should have hundreds of candidates
    for x, y in coords:
        assert 60 <= x < 1220
        assert 40 <= y < 680


def test_sample_pixels_solid_color(tmp_path: Path):
    """A solid-color image should yield the same RGB at every coordinate."""
    corpus = _make_corpus(tmp_path, {"page_a": [(100, 150, 200)] * 3})
    paths = corpus.glob("*.png")
    img_paths = sorted(paths)

    coords = [(100, 100), (640, 360), (1000, 500)]
    samples = sample_pixels(img_paths, coords)

    assert samples.shape == (3, 3, 3)
    np.testing.assert_array_almost_equal(samples[:, :, 0], 100)
    np.testing.assert_array_almost_equal(samples[:, :, 1], 150)
    np.testing.assert_array_almost_equal(samples[:, :, 2], 200)


def test_select_anchors_discriminates_pages(tmp_path: Path):
    """Red page vs blue page should produce anchors that separate them."""
    corpus = _make_corpus(
        tmp_path,
        {
            "page_red": [(255, 0, 0)] * 4,
            "page_blue": [(0, 0, 255)] * 4,
        },
    )
    pages = load_corpus(corpus, min_samples=3)
    coords = build_candidate_grid()
    page_samples = {p: sample_pixels(imgs, coords) for p, imgs in pages.items()}

    result = select_anchors(page_samples, coords, top_k=3)

    assert "page_red" in result
    assert "page_blue" in result
    assert len(result["page_red"]) == 3
    assert len(result["page_blue"]) == 3

    # Red page anchors should have red-ish expected RGB
    for a in result["page_red"]:
        assert a["expected_rgb"][0] > 200
        assert a["expected_rgb"][2] < 50

    # Blue page anchors should have blue-ish expected RGB
    for a in result["page_blue"]:
        assert a["expected_rgb"][0] < 50
        assert a["expected_rgb"][2] > 200


def test_select_anchors_stable_within_page(tmp_path: Path):
    """All samples same color => zero intra-page variance, scored well."""
    corpus = _make_corpus(
        tmp_path,
        {
            "stable": [(128, 128, 128)] * 5,
            "other": [(0, 0, 0)] * 5,
        },
    )
    pages = load_corpus(corpus, min_samples=3)
    coords = build_candidate_grid()
    page_samples = {p: sample_pixels(imgs, coords) for p, imgs in pages.items()}

    result = select_anchors(page_samples, coords, top_k=2)

    # All anchors for "stable" should have near-zero intra-variance
    for a in result["stable"]:
        assert a["_intra_var"] < 1.0


def test_update_graph_creates_new_states():
    graph = {"states": {}, "metadata": {}}
    calibrated = {
        "page_new": [
            {
                "type": "pixel_color",
                "x": 100,
                "y": 200,
                "expected_rgb": [255, 0, 0],
                "cost": 1,
                "label": "test",
                "_score": 10.0,
                "_intra_var": 0.0,
                "_min_inter_dist": 100.0,
            },
        ]
    }

    updated = update_graph(graph, calibrated)

    assert "page_new" in updated["states"]
    assert updated["states"]["page_new"]["calibration_source"] == "corpus"
    # Internal scoring fields should be stripped
    for a in updated["states"]["page_new"]["anchors"]:
        assert "_score" not in a
        assert "_intra_var" not in a


def test_update_graph_replaces_existing_anchors():
    graph = {
        "states": {
            "page_main": {
                "description": "Main page",
                "anchors": [{"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [0, 0, 0], "cost": 1}],
                "confidence_threshold": 0.66,
            }
        },
        "metadata": {},
    }
    calibrated = {
        "page_main": [
            {"type": "pixel_color", "x": 100, "y": 200, "expected_rgb": [255, 128, 0], "cost": 1, "label": "new"},
        ]
    }

    updated = update_graph(graph, calibrated)

    # Old anchor replaced
    assert len(updated["states"]["page_main"]["anchors"]) == 1
    assert updated["states"]["page_main"]["anchors"][0]["x"] == 100
    assert updated["states"]["page_main"]["anchors"][0]["expected_rgb"] == [255, 128, 0]
    assert updated["states"]["page_main"]["calibration_source"] == "corpus"
