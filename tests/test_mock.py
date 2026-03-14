"""Tests for screenshot_mock.py — Screenshot Mock Manager."""

from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from screenshot_mock import capture, validate


class TestCapture:
    def test_capture_creates_file(self, tmp_path):
        # Create a fake screenshot
        screenshot = tmp_path / "test_screenshot.png"
        screenshot.write_bytes(b"fake png data")

        output_dir = tmp_path / "mocks"
        result = capture("main_menu", screenshot, output_dir)

        assert result["state"] == "main_menu"
        assert result["sequence"] == 1
        assert Path(result["file"]).exists()

    def test_capture_increments_sequence(self, tmp_path):
        screenshot = tmp_path / "test.png"
        screenshot.write_bytes(b"fake")

        output_dir = tmp_path / "mocks"
        result1 = capture("state_a", screenshot, output_dir)
        result2 = capture("state_a", screenshot, output_dir)

        assert result1["sequence"] == 1
        assert result2["sequence"] == 2


class TestValidate:
    def test_reports_coverage(self, full_graph, tmp_path):
        mock_dir = tmp_path / "mocks"
        mock_dir.mkdir()

        # Create a screenshot for main_menu only
        (mock_dir / "main_menu_01.png").write_bytes(b"fake")

        result = validate(full_graph, mock_dir)
        assert "main_menu" in result["states_with_screenshots"]
        assert "dock" in result["states_missing_screenshots"]
