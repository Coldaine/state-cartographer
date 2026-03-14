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

    def test_validate_returns_anchor_results(self, tmp_path):
        # Graph with text_match anchors; validate() builds obs with text_content=None
        # so text_match never fires — score must be 0.0 and pass must be False
        graph = {
            "states": {
                "login": {
                    "anchors": [{"type": "text_match", "pattern": "Login", "cost": 1}],
                    "confidence_threshold": 0.7,
                }
            },
            "transitions": {},
        }
        mock_dir = tmp_path / "mocks"
        mock_dir.mkdir()
        (mock_dir / "login_01.png").write_bytes(b"fake")

        result = validate(graph, mock_dir)
        assert "login" in result["anchor_results"]
        screenshot_result = result["anchor_results"]["login"][0]
        assert screenshot_result["score"] == 0.0  # no text_content in mock obs
        assert screenshot_result["pass"] is False  # 0.0 < threshold 0.7
        assert screenshot_result["threshold"] == 0.7

    def test_validate_no_screenshots_for_state(self, full_graph, tmp_path):
        mock_dir = tmp_path / "empty_mocks"
        mock_dir.mkdir()

        result = validate(full_graph, mock_dir)
        # All states should be missing
        for state_id in full_graph["states"]:
            assert state_id in result["states_missing_screenshots"]
        assert result["anchor_results"] == {}
