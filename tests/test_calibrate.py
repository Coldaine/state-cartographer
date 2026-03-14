"""Tests for calibrate.py — Anchor Calibrator."""

from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))
sys.path.insert(0, str(Path(__file__).parent))

from calibrate import calibrate, calibrate_state
from conftest import make_rgb_png

SCRIPTS_DIR = Path(__file__).parent.parent / "scripts"


@pytest.fixture
def small_png(tmp_path: Path) -> Path:
    """2x2 RGB PNG: (0,0)=red, (1,0)=green, (0,1)=blue, (1,1)=white."""
    pixels = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 255)]
    path = tmp_path / "sample.png"
    path.write_bytes(make_rgb_png(pixels, width=2, height=2))
    return path


class TestCalibrateState:
    def test_pixel_color_learns_rgb(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {
            "anchors": [{"type": "pixel_color", "x": 0, "y": 0, "cost": 1}]  # no expected_rgb yet
        }
        updated, warnings = calibrate_state("main_menu", state_def, small_png)
        assert updated[0]["expected_rgb"] == [255, 0, 0]
        assert not warnings

    def test_pixel_color_different_coords(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {
            "anchors": [
                {"type": "pixel_color", "x": 1, "y": 0, "cost": 1},  # green
                {"type": "pixel_color", "x": 0, "y": 1, "cost": 1},  # blue
            ]
        }
        updated, warnings = calibrate_state("test", state_def, small_png)
        assert updated[0]["expected_rgb"] == [0, 255, 0]  # (1,0) = green
        assert updated[1]["expected_rgb"] == [0, 0, 255]  # (0,1) = blue
        assert not warnings

    def test_pixel_color_overwrites_wrong_value_with_warning(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {"anchors": [{"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [0, 0, 0], "cost": 1}]}
        updated, warnings = calibrate_state("s", state_def, small_png)
        assert updated[0]["expected_rgb"] == [255, 0, 0]  # learned real value
        assert len(warnings) == 1
        assert "[0, 0, 0]" in warnings[0]  # old value mentioned

    def test_pixel_color_same_value_no_warning(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {"anchors": [{"type": "pixel_color", "x": 0, "y": 0, "expected_rgb": [255, 0, 0], "cost": 1}]}
        updated, warnings = calibrate_state("s", state_def, small_png)
        assert updated[0]["expected_rgb"] == [255, 0, 0]
        assert not warnings  # value unchanged — no warning

    def test_out_of_bounds_coord_warns(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {
            "anchors": [
                {"type": "pixel_color", "x": 100, "y": 100, "cost": 1}  # outside 2x2 image
            ]
        }
        updated, warnings = calibrate_state("s", state_def, small_png)
        assert len(warnings) == 1
        assert "outside" in warnings[0]
        # expected_rgb not set (anchor unchanged)
        assert "expected_rgb" not in updated[0]

    def test_text_match_anchor_untouched(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {"anchors": [{"type": "text_match", "pattern": "Hello", "cost": 1}]}
        updated, warnings = calibrate_state("s", state_def, small_png)
        assert updated[0] == {"type": "text_match", "pattern": "Hello", "cost": 1}
        assert not warnings

    def test_missing_screenshot_warns(self, tmp_path: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        state_def = {"anchors": [{"type": "pixel_color", "x": 0, "y": 0, "cost": 1}]}
        missing = tmp_path / "nonexistent.png"
        updated, warnings = calibrate_state("s", state_def, missing)
        _ = updated  # we only care about warnings here
        assert len(warnings) == 1
        assert "Cannot open" in warnings[0]


class TestCalibrate:
    def test_updates_graph_in_place(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        graph = {
            "states": {"s": {"anchors": [{"type": "pixel_color", "x": 1, "y": 1, "cost": 1}]}},
            "transitions": {},
        }
        updated, _ = calibrate(graph, ["s"], small_png)
        assert updated["states"]["s"]["anchors"][0]["expected_rgb"] == [255, 255, 255]

    def test_unknown_state_warn(self, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        graph: dict = {"states": {}, "transitions": {}}
        _, warnings = calibrate(graph, ["nonexistent"], small_png)
        assert any("not found" in w for w in warnings)


class TestCalibrateCLI:
    def run_calibrate(self, *args: str) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "calibrate.py"), *args],
            capture_output=True,
            text=True,
            timeout=15,
        )

    def test_dry_run_does_not_modify_file(self, tmp_path: Path, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        graph = {
            "states": {"s": {"anchors": [{"type": "pixel_color", "x": 0, "y": 0, "cost": 1}]}},
            "transitions": {},
        }
        graph_file = tmp_path / "graph.json"
        graph_file.write_text(json.dumps(graph))
        original = graph_file.read_text()

        result = self.run_calibrate(
            "--graph",
            str(graph_file),
            "--screenshot",
            str(small_png),
            "--state",
            "s",
            "--dry-run",
        )
        assert result.returncode == 0
        data = json.loads(result.stdout)
        assert data["dry_run"] is True
        # File must not have changed
        assert graph_file.read_text() == original

    def test_calibrate_writes_file(self, tmp_path: Path, small_png: Path) -> None:
        pytest.importorskip("PIL", reason="Pillow not installed")
        graph = {
            "states": {"s": {"anchors": [{"type": "pixel_color", "x": 0, "y": 0, "cost": 1}]}},
            "transitions": {},
        }
        graph_file = tmp_path / "graph.json"
        graph_file.write_text(json.dumps(graph))

        result = self.run_calibrate(
            "--graph",
            str(graph_file),
            "--screenshot",
            str(small_png),
            "--state",
            "s",
        )
        assert result.returncode == 0
        updated = json.loads(graph_file.read_text())
        assert updated["states"]["s"]["anchors"][0]["expected_rgb"] == [255, 0, 0]

    def test_missing_graph_returns_exit_2(self, tmp_path: Path, small_png: Path) -> None:
        result = self.run_calibrate(
            "--graph",
            str(tmp_path / "missing.json"),
            "--screenshot",
            str(small_png),
            "--state",
            "s",
        )
        assert result.returncode == 2

    def test_missing_screenshot_returns_exit_2(self, tmp_path: Path) -> None:
        graph_file = tmp_path / "g.json"
        graph_file.write_text('{"states": {}, "transitions": {}}')
        result = self.run_calibrate(
            "--graph",
            str(graph_file),
            "--screenshot",
            str(tmp_path / "missing.png"),
            "--state",
            "s",
        )
        assert result.returncode == 2
