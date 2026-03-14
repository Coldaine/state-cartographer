"""Tests for screenshot_dedupe.py."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest
from png_factory import make_rgb_png

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from screenshot_dedupe import ImageFingerprint, discover_pngs, generate_report, write_report


def _write_png(path: Path, rgb: tuple[int, int, int]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    data = make_rgb_png([rgb], width=1, height=1)
    path.write_bytes(data)


def test_discover_pngs_finds_recursive_and_case_insensitive(tmp_path: Path):
    _write_png(tmp_path / "a.png", (1, 2, 3))
    _write_png(tmp_path / "nested" / "b.PNG", (4, 5, 6))
    (tmp_path / "not-image.txt").write_text("x", encoding="utf-8")

    files = discover_pngs(tmp_path)
    assert [f.name for f in files] == ["a.png", "b.PNG"]


def test_generate_report_falls_back_to_sha256_and_clusters_exact_duplicates(tmp_path: Path, monkeypatch):
    import screenshot_dedupe

    monkeypatch.setattr(screenshot_dedupe, "_load_vision_backend", lambda: None)

    duplicate_bytes = make_rgb_png([(10, 20, 30)], width=1, height=1)
    (tmp_path / "dup-a.png").write_bytes(duplicate_bytes)
    (tmp_path / "nested").mkdir()
    (tmp_path / "nested" / "dup-b.png").write_bytes(duplicate_bytes)
    _write_png(tmp_path / "unique.png", (200, 100, 50))

    report = generate_report(tmp_path, distance_threshold=6, include_singletons=False)

    assert report["total_images"] == 3
    assert report["fingerprint_methods"] == {"sha256": 3}
    assert report["cluster_count"] == 1
    assert report["duplicate_images"] == 1
    cluster = report["clusters"][0]
    assert cluster["size"] == 2
    assert {member["path"] for member in cluster["members"]} == {"dup-a.png", "nested/dup-b.png"}


def test_generate_report_uses_phash_distance_clustering_when_available(tmp_path: Path, monkeypatch):
    import screenshot_dedupe

    for name in ["a.png", "b.png", "far.png"]:
        (tmp_path / name).write_bytes(b"png")

    fake_records = {
        "a.png": ImageFingerprint(
            path=tmp_path / "a.png",
            relative_path="a.png",
            size_bytes=3,
            fingerprint_method="phash",
            fingerprint="0000",
            hash_int=0x0000,
        ),
        "b.png": ImageFingerprint(
            path=tmp_path / "b.png",
            relative_path="b.png",
            size_bytes=3,
            fingerprint_method="phash",
            fingerprint="0001",
            hash_int=0x0001,
        ),
        "far.png": ImageFingerprint(
            path=tmp_path / "far.png",
            relative_path="far.png",
            size_bytes=3,
            fingerprint_method="phash",
            fingerprint="00ff",
            hash_int=0x00FF,
        ),
    }

    monkeypatch.setattr(screenshot_dedupe, "_load_vision_backend", lambda: object())
    monkeypatch.setattr(screenshot_dedupe, "fingerprint_path", lambda path, root: fake_records[path.name])

    report = generate_report(tmp_path, distance_threshold=1, include_singletons=False)

    assert report["total_images"] == 3
    assert report["fingerprint_methods"] == {"phash": 3}
    assert report["cluster_count"] == 1
    assert report["duplicate_images"] == 1
    members = report["clusters"][0]["members"]
    assert {member["path"] for member in members} == {"a.png", "b.png"}


def test_write_report_writes_json_file(tmp_path: Path):
    report = {"total_images": 0, "clusters": []}
    output = tmp_path / "out" / "report.json"
    write_report(report, output)

    loaded = json.loads(output.read_text(encoding="utf-8"))
    assert loaded == report


def test_generate_report_raises_on_negative_threshold(tmp_path: Path):
    with pytest.raises(ValueError, match="distance_threshold must be >= 0"):
        generate_report(tmp_path, distance_threshold=-1)
