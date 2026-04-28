from __future__ import annotations

from pathlib import Path

from scripts import corpus_cleanup as cc


def test_generate_black_frame_report_dry_run_preserves_files(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    black = root / "black.png"
    keep = root / "keep.png"
    black.write_bytes(b"black")
    keep.write_bytes(b"keep")

    monkeypatch.setattr(cc, "discover_pngs_under_roots", lambda roots: [black, keep])

    def fake_is_verified(path: Path, **kwargs):
        return path == black, {"size": path.stat().st_size, "mean": 0.0, "stddev": 0.0}

    monkeypatch.setattr(cc, "is_verified_black_frame", fake_is_verified)

    summary, entries = cc.generate_black_frame_report(
        [root],
        max_size_bytes=10_000,
        mean_threshold=5.0,
        stddev_threshold=2.0,
        delete=False,
    )
    assert summary["verified_black_frames"] == 1
    assert summary["deleted"] == 0
    assert black.exists()
    assert keep.exists()
    assert entries[0]["path"].endswith("black.png")


def test_generate_black_frame_report_delete_removes_verified_files(tmp_path, monkeypatch):
    root = tmp_path / "root"
    root.mkdir()
    black = root / "black.png"
    keep = root / "keep.png"
    black.write_bytes(b"black")
    keep.write_bytes(b"keep")

    monkeypatch.setattr(cc, "discover_pngs_under_roots", lambda roots: [black, keep])

    def fake_is_verified(path: Path, **kwargs):
        return path == black, {"size": path.stat().st_size, "mean": 0.0, "stddev": 0.0}

    monkeypatch.setattr(cc, "is_verified_black_frame", fake_is_verified)

    summary, _entries = cc.generate_black_frame_report(
        [root],
        max_size_bytes=10_000,
        mean_threshold=5.0,
        stddev_threshold=2.0,
        delete=True,
    )
    assert summary["verified_black_frames"] == 1
    assert summary["deleted"] == 1
    assert not black.exists()
    assert keep.exists()
