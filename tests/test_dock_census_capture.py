"""Tests for scripts/dock_census_capture.py.

Tests run offline -- no emulator, no real device required.
All Pilot interactions are mocked; output files go to tmp_path.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

# Put project root on path so the script can resolve its own sys.path.insert.
_ROOT = str(Path(__file__).resolve().parent.parent)
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)

from scripts.dock_census_capture import (  # noqa: E402
    DockLayout,
    _detail_view_opened,
    _detect_scroll_end,
    deep_dive,
    grid_scan,
    main,
)

# ---------------------------------------------------------------------------
# _detect_scroll_end
# ---------------------------------------------------------------------------


class TestDetectScrollEnd:
    def test_identical_bytes_returns_true(self):
        data = b"png_frame_data"
        assert _detect_scroll_end(data, data) is True

    def test_different_bytes_returns_false(self):
        assert _detect_scroll_end(b"frame_a", b"frame_b") is False


def test_detail_view_opened_requires_changed_screen():
    assert _detail_view_opened(b"grid", b"detail") is True
    assert _detail_view_opened(b"grid", b"grid") is False


# ---------------------------------------------------------------------------
# DockLayout
# ---------------------------------------------------------------------------


class TestDockLayout:
    def test_cell_width(self):
        layout = DockLayout()
        # (grid_right - grid_left) // columns == (1280 - 0) // 8 == 160
        assert layout.cell_width == 160

    def test_cell_height(self):
        layout = DockLayout()
        # (grid_bottom - grid_top) // visible_rows == (648 - 94) // 3 == 184
        assert layout.cell_height == 184


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pilot(screenshot_side_effects: list[bytes]) -> MagicMock:
    """Return a mock Pilot whose screenshot() yields bytes in sequence."""
    pilot = MagicMock()
    pilot.tap.return_value = True
    pilot.swipe.return_value = True
    pilot.screenshot.side_effect = screenshot_side_effects
    return pilot


# ---------------------------------------------------------------------------
# grid_scan
# ---------------------------------------------------------------------------


class TestGridScan:
    def test_captures_pages_until_duplicate(self, tmp_path):
        """3 distinct pages then a duplicate triggers scroll-end after 3 saves."""
        # screenshot() call sequence inside grid_scan:
        #   1. Initial screenshot (page_000)
        #   2. After swipe 1 -> page_001  (different from page_000)
        #   3. After swipe 2 -> page_002  (different from page_001)
        #   4. After swipe 3 -> page_002 again (duplicate -> stop)
        # _navigate_to_dock also calls pilot.tap (not screenshot), so no extra
        # screenshot is consumed there.
        screenshots = [
            b"page_0_bytes",
            b"page_1_bytes",
            b"page_2_bytes",
            b"page_2_bytes",  # duplicate -> scroll end
        ]
        pilot = _make_pilot(screenshots)

        with patch("time.sleep"):
            result = grid_scan(pilot, tmp_path)

        grid_dir = tmp_path / "grid"
        saved = sorted(grid_dir.glob("page_*.png"))
        assert len(saved) == 3
        assert saved[0].name == "page_000.png"
        assert saved[1].name == "page_001.png"
        assert saved[2].name == "page_002.png"
        assert result["total_screenshots"] == 3

    def test_immediate_scroll_end_saves_one_page(self, tmp_path):
        """If the very first swipe returns the same screenshot, only one page is saved."""
        # screenshot() sequence:
        #   1. Initial screenshot (page_000)
        #   2. After first swipe -> same bytes -> stop immediately
        screenshots = [
            b"only_page",
            b"only_page",  # duplicate on first swipe
        ]
        pilot = _make_pilot(screenshots)

        with patch("time.sleep"):
            result = grid_scan(pilot, tmp_path)

        grid_dir = tmp_path / "grid"
        saved = list(grid_dir.glob("page_*.png"))
        assert len(saved) == 1
        assert result["total_screenshots"] == 1

    def test_swipe_failure_raises(self, tmp_path):
        pilot = _make_pilot([b"page_0"])
        pilot.swipe.return_value = False

        with patch("time.sleep"):
            try:
                grid_scan(pilot, tmp_path)
            except RuntimeError as exc:
                assert "grid_scan" in str(exc)
            else:
                raise AssertionError("grid_scan should fail when swipe() returns False")


# ---------------------------------------------------------------------------
# deep_dive
# ---------------------------------------------------------------------------


class TestDeepDive:
    def test_limit_caps_ship_count(self, tmp_path):
        """With limit=2, exactly 2 ships are processed (4 screenshots saved)."""
        # deep_dive screenshot() call sequence:
        #   1. Baseline grid screenshot (_navigate_to_dock tap + this call)
        #   Per ship (2 ships):
        #     tap cell, screenshot (detail), tap gear, screenshot (gear), tap back
        #   After processing all visible slots (or hitting limit mid-row):
        #     swipe, screenshot for scroll-end check
        # limit=2 is hit at ship index 1 (0-based) inside the inner loop,
        # so the function returns before the swipe — no scroll-end screenshot needed.
        screenshots = [
            b"baseline",
            b"detail_0",
            b"gear_0",  # ship 0
            b"detail_1",
            b"gear_1",  # ship 1  <- limit hit after this
        ]
        pilot = _make_pilot(screenshots)

        with patch("time.sleep"):
            result = deep_dive(pilot, tmp_path, limit=2)

        ships_dir = tmp_path / "ships"
        saved = sorted(ships_dir.glob("*.png"))
        assert len(saved) == 4
        assert result["total_ships"] == 2
        assert result["total_screenshots"] == 4

    def test_scroll_end_stops_after_one_page(self, tmp_path):
        """One full visible page (visible_rows * columns ships), then scroll end."""
        layout = DockLayout()
        ships_per_page = layout.visible_rows * layout.columns  # 3 * 8 = 24

        # screenshot() sequence:
        #   1. Baseline
        #   24 ships * 2 screenshots each = 48 screenshots
        #   After the page is done: swipe, then screenshot -> same bytes as baseline
        baseline = b"grid_page_0"
        ship_shots: list[bytes] = []
        for i in range(ships_per_page):
            ship_shots.append(f"detail_{i}".encode())
            ship_shots.append(f"gear_{i}".encode())

        screenshots = [baseline, *ship_shots, baseline]  # baseline == scroll end
        pilot = _make_pilot(screenshots)

        with patch("time.sleep"):
            result = deep_dive(pilot, tmp_path, layout=layout)

        ships_dir = tmp_path / "ships"
        saved = list(ships_dir.glob("*.png"))
        assert result["total_ships"] == ships_per_page
        assert result["total_screenshots"] == ships_per_page * 2
        assert len(saved) == ships_per_page * 2

    def test_empty_cell_does_not_emit_ship_artifacts(self, tmp_path):
        screenshots = [
            b"baseline",
            b"baseline",
            b"baseline",
        ]
        pilot = _make_pilot(screenshots)

        with patch("time.sleep"):
            result = deep_dive(pilot, tmp_path, limit=1)

        assert result["total_ships"] == 0
        assert result["total_screenshots"] == 0
        assert list((tmp_path / "ships").glob("*.png")) == []

    def test_swipe_failure_raises(self, tmp_path):
        layout = DockLayout()
        ships_per_page = layout.visible_rows * layout.columns
        screenshots = [b"baseline"]
        for i in range(ships_per_page):
            screenshots.append(f"detail_{i}".encode())
            screenshots.append(f"gear_{i}".encode())
        pilot = _make_pilot(screenshots)
        pilot.swipe.return_value = False

        with patch("time.sleep"):
            try:
                deep_dive(pilot, tmp_path, layout=layout)
            except RuntimeError as exc:
                assert "deep_dive" in str(exc)
            else:
                raise AssertionError("deep_dive should fail when swipe() returns False")


def test_main_health_guard_writes_run_artifacts(tmp_path, monkeypatch):
    class FakeConfig:
        def __init__(self):
            self.serial = "127.0.0.1:21503"
            self.raw = {"render_mode": "test"}

    class FakePilot:
        def __init__(self, config_path=None):
            self.config_path = config_path

        def __enter__(self):
            return self

        def __exit__(self, *args):
            return None

        def is_healthy(self):
            return False

    monkeypatch.setattr("scripts.dock_census_capture.load_config", lambda path: FakeConfig())
    monkeypatch.setattr("scripts.dock_census_capture.Pilot", FakePilot)
    monkeypatch.setenv("SC_RUN_DATA_ROOT", str(tmp_path / "runs"))
    monkeypatch.setenv("SC_RUN_SUMMARY_ROOT", str(tmp_path / "summaries"))

    exit_code = main(["--run-id", "dock-run", "grid-scan"])
    assert exit_code == 1

    manifest = json.loads((tmp_path / "runs" / "dock-run" / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["status"] == "failed"
    assert manifest["serial"] == "127.0.0.1:21503"
    assert manifest["output_paths"]["capture_dir"].endswith("capture")
    assert (tmp_path / "runs" / "dock-run" / "events.ndjson").exists()
