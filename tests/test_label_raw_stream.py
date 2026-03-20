"""Tests for label_raw_stream.py — label frames from ALAS log page transitions."""

from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from label_raw_stream import (
    find_latest_log,
    label_frames,
    main,
    parse_frame_ts,
    parse_page_events,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

SAMPLE_LOG = """\
2026-03-20 00:26:55.762 | INFO | [UI] page_main
2026-03-20 00:26:55.777 | INFO | Page switch: page_main_white -> page_reward
2026-03-20 00:26:58.651 | INFO | Page arrive: page_reward
2026-03-20 00:27:34.012 | INFO | [UI] page_commission
2026-03-20 00:27:42.692 | INFO | [UI] page_reward
2026-03-20 00:27:42.704 | INFO | Page switch: page_reward -> page_main
2026-03-20 00:28:20.454 | INFO | Page arrive: page_dorm
"""


@pytest.fixture
def log_file(tmp_path: Path) -> Path:
    p = tmp_path / "test_alas.txt"
    p.write_text(SAMPLE_LOG, encoding="utf-8")
    return p


@pytest.fixture
def raw_dir(tmp_path: Path) -> Path:
    d = tmp_path / "raw_stream"
    d.mkdir()
    return d


def _touch_frame(raw_dir: Path, stem: str) -> Path:
    """Create an empty PNG file with the given timestamp stem."""
    p = raw_dir / f"{stem}.png"
    p.write_bytes(b"")
    return p


# ---------------------------------------------------------------------------
# parse_frame_ts
# ---------------------------------------------------------------------------


def test_parse_frame_ts_valid():
    ts = parse_frame_ts("20260320_002500_895.png")
    assert ts == datetime(2026, 3, 20, 0, 25, 0, 895000)


def test_parse_frame_ts_invalid_ignored():
    assert parse_frame_ts("not-a-frame.png") is None
    assert parse_frame_ts("calibrated.png") is None


# ---------------------------------------------------------------------------
# parse_page_events
# ---------------------------------------------------------------------------


def test_parse_page_events_counts(log_file: Path):
    events = parse_page_events(log_file)
    assert len(events) == 7


def test_parse_page_events_arrive_prioritized(log_file: Path):
    events = parse_page_events(log_file)
    assert ("page_reward", "arrive") in [(page, src) for ts, page, src in events if src == "arrive"]


def test_parse_page_events_sorted(log_file: Path):
    events = parse_page_events(log_file)
    timestamps = [e[0] for e in events]
    assert timestamps == sorted(timestamps)


def test_parse_page_events_switch_extracts_destination(log_file: Path):
    events = parse_page_events(log_file)
    switch_pages = [page for _, page, src in events if src == "switch"]
    assert "page_reward" in switch_pages
    assert "page_main" in switch_pages
    # page_main_white is NOT a destination page we want
    assert "page_main_white" not in switch_pages


# ---------------------------------------------------------------------------
# label_frames
# ---------------------------------------------------------------------------


def test_label_frames_before_any_event(log_file: Path, raw_dir: Path):
    """Frames with timestamps before the first log event → unknown."""
    _touch_frame(raw_dir, "20260320_002200_000")  # 00:22 — before log starts at 00:26
    events = parse_page_events(log_file)
    records = label_frames(raw_dir, events)
    assert len(records) == 1
    assert records[0]["alas_page"] == "unknown"
    assert records[0]["confidence"] == "none"


def test_label_frames_arrives_used(log_file: Path, raw_dir: Path):
    """Frame at 00:27:00 should get page_reward (arrived at 00:26:58)."""
    _touch_frame(raw_dir, "20260320_002700_000")  # 00:27:00
    events = parse_page_events(log_file)
    records = label_frames(raw_dir, events)
    assert records[0]["alas_page"] == "page_reward"
    assert records[0]["confidence"] == "arrive"


def test_label_frames_switch_used_during_transition(log_file: Path, raw_dir: Path):
    """Frame between switch and arrive picks up the switch label."""
    # switch page_main_white -> page_reward at 00:26:55.777
    # arrive page_reward at 00:26:58.651
    # Frame at 00:26:57 is between them — switch label
    _touch_frame(raw_dir, "20260320_002657_000")
    events = parse_page_events(log_file)
    records = label_frames(raw_dir, events)
    assert records[0]["alas_page"] == "page_reward"
    assert records[0]["confidence"] == "switch"


def test_label_frames_output_fields(log_file: Path, raw_dir: Path):
    _touch_frame(raw_dir, "20260320_002700_000")
    events = parse_page_events(log_file)
    records = label_frames(raw_dir, events)
    rec = records[0]
    assert "ts" in rec
    assert "path" in rec
    assert "alas_page" in rec
    assert "confidence" in rec
    assert rec["path"] == "20260320_002700_000.png"


def test_label_frames_skips_non_png(log_file: Path, raw_dir: Path):
    """Non-matching filenames are silently skipped."""
    (raw_dir / "index.jsonl").write_text("{}")
    (raw_dir / "notes.txt").write_text("hello")
    _touch_frame(raw_dir, "20260320_002700_000")
    events = parse_page_events(log_file)
    records = label_frames(raw_dir, events)
    assert len(records) == 1


# ---------------------------------------------------------------------------
# find_latest_log
# ---------------------------------------------------------------------------


def test_find_latest_log_prefers_alas_suffix(tmp_path: Path):
    (tmp_path / "2026-03-20_gui.txt").write_text("gui")
    p_alas = tmp_path / "2026-03-20_alas.txt"
    p_alas.write_text("alas")
    result = find_latest_log(tmp_path)
    assert result == p_alas


def test_find_latest_log_returns_none_when_empty(tmp_path: Path):
    assert find_latest_log(tmp_path) is None


# ---------------------------------------------------------------------------
# main() integration
# ---------------------------------------------------------------------------


def test_main_writes_index(log_file: Path, raw_dir: Path, tmp_path: Path):
    _touch_frame(raw_dir, "20260320_002700_000")
    _touch_frame(raw_dir, "20260320_002200_000")
    out = tmp_path / "out.jsonl"
    rc = main(["--log", str(log_file), "--raw-stream", str(raw_dir), "--output", str(out)])
    assert rc == 0
    assert out.exists()
    lines = [json.loads(line) for line in out.read_text().splitlines()]
    assert len(lines) == 2
    pages = {line["alas_page"] for line in lines}
    assert "page_reward" in pages
    assert "unknown" in pages


def test_main_dump_pages_exits_zero(log_file: Path, capsys):
    rc = main(["--log", str(log_file), "--dump-pages"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "page_reward" in out


def test_main_missing_raw_stream_returns_error(log_file: Path, tmp_path: Path):
    rc = main(["--log", str(log_file), "--raw-stream", str(tmp_path / "nonexistent")])
    assert rc == 1


def test_main_min_samples_filters(log_file: Path, raw_dir: Path, tmp_path: Path):
    """--min-samples 5 should filter pages with < 5 frames."""
    _touch_frame(raw_dir, "20260320_002700_000")
    _touch_frame(raw_dir, "20260320_002200_000")
    out = tmp_path / "out.jsonl"
    rc = main(["--log", str(log_file), "--raw-stream", str(raw_dir), "--output", str(out), "--min-samples", "5"])
    assert rc == 0
    lines = out.read_text().strip().splitlines()
    # Both pages have only 1 frame each → filtered out → 0 output records
    assert len(lines) == 0
