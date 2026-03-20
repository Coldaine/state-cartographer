"""Tests for siphon.py — ALAS observation siphon pipeline."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

from siphon import RE_PAGE_ARRIVE, RE_START_TASK, RE_UI_IDENTIFY, capture_and_classify, get_latest_log_file


class TestGetLatestLogFile:
    def test_finds_log_in_directory(self, tmp_path):
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        (log_dir / "2026-03-14_PatrickCustom.txt").write_text("log content")
        result = get_latest_log_file(log_dir)
        assert result.name == "2026-03-14_PatrickCustom.txt"

    def test_returns_newest_by_mtime(self, tmp_path):
        import time

        log_dir = tmp_path / "log"
        log_dir.mkdir()
        old = log_dir / "2026-03-13_Old.txt"
        old.write_text("old")
        time.sleep(0.05)
        new = log_dir / "2026-03-14_New.txt"
        new.write_text("new")
        result = get_latest_log_file(log_dir)
        assert result.name == "2026-03-14_New.txt"

    def test_raises_when_explicit_dir_missing_and_no_fallback(self, tmp_path, monkeypatch):
        import siphon

        # Point the fallback away from the real vendor dir
        monkeypatch.setattr(siphon, "PROJECT_ROOT", tmp_path)
        # Passing None forces fallback path, which won't exist in tmp_path
        with pytest.raises(FileNotFoundError):
            get_latest_log_file(None)

    def test_raises_when_dir_empty(self, tmp_path):
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        with pytest.raises(FileNotFoundError, match="No log files"):
            get_latest_log_file(log_dir)

    def test_ignores_files_without_underscore(self, tmp_path):
        log_dir = tmp_path / "log"
        log_dir.mkdir()
        (log_dir / "readme.txt").write_text("not a log")
        with pytest.raises(FileNotFoundError, match="No log files"):
            get_latest_log_file(log_dir)


class TestCaptureAndClassify:
    @pytest.fixture
    def mock_deps(self, tmp_path, monkeypatch):
        """Patch siphon's dirs to tmp_path and mock external calls."""
        import siphon

        monkeypatch.setattr(siphon, "PROJECT_ROOT", tmp_path)
        monkeypatch.setattr(siphon, "SCREENSHOTS_DIR", tmp_path / "screenshots")
        (tmp_path / "screenshots").mkdir()
        monkeypatch.setattr(siphon, "DATA_DIR", tmp_path)

        # Force ADB path — tests should not depend on whether ALAS is live
        monkeypatch.setattr(siphon, "_alas_running", lambda: False)

        mock_screenshot = MagicMock(return_value=b"\x89PNG\r\n\x1a\n" + b"\x00" * 100)
        monkeypatch.setattr(siphon.adb_bridge, "screenshot", mock_screenshot)

        mock_obs = MagicMock(
            return_value={
                "screenshot": str(tmp_path / "screenshots" / "test.png"),
                "pixels": {"903,391": [183, 215, 247]},
                "text_content": None,
                "dom_elements": [],
            }
        )
        monkeypatch.setattr(siphon, "build_observations", mock_obs)

        mock_locate = MagicMock(
            return_value={
                "state": "page_main",
                "confidence": 1.0,
            }
        )
        monkeypatch.setattr(siphon, "locate", mock_locate)

        return {
            "screenshot": mock_screenshot,
            "build_observations": mock_obs,
            "locate": mock_locate,
            "tmp_path": tmp_path,
        }

    def test_returns_complete_record(self, mock_deps):
        graph = {"states": {"page_main": {"anchors": []}}}
        record = capture_and_classify(
            serial="127.0.0.1:21513",
            alas_label="page_main",
            alas_event="PageArrive",
            graph=graph,
            pixel_coords=[(903, 391)],
            task_name="Commission",
        )
        assert record["alas_label"] == "page_main"
        assert record["our_label"] == "page_main"
        assert record["match"] is True
        assert record["alas_event"] == "PageArrive"
        assert record["task"] == "Commission"
        assert "timestamp" in record
        assert "screenshot_path" in record
        assert "pixels" in record["observation"]

    def test_calls_adb_with_correct_serial(self, mock_deps):
        capture_and_classify("1.2.3.4:5555", "page_main", "PageArrive", {}, [], "Test")
        mock_deps["screenshot"].assert_called_once_with("1.2.3.4:5555")

    def test_passes_pixel_coords_to_build_observations(self, mock_deps):
        coords = [(100, 200), (300, 400)]
        capture_and_classify("x", "page_main", "PageArrive", {}, coords, "Test")
        args = mock_deps["build_observations"].call_args[0]
        assert args[1] == coords

    def test_passes_graph_and_session_to_locate(self, mock_deps):
        graph = {"states": {"page_main": {}}}
        capture_and_classify("x", "page_main", "PageArrive", graph, [], "Test")
        args = mock_deps["locate"].call_args[0]
        assert args[0] == graph
        assert args[1] == {"history": []}

    def test_mismatch_sets_match_false(self, mock_deps):
        mock_deps["locate"].return_value = {"state": "page_reward", "confidence": 0.9}
        record = capture_and_classify("x", "page_main", "PageSwitch", {}, [], "Test")
        assert record["our_label"] == "page_reward"
        assert record["match"] is False

    def test_screenshot_failure_returns_empty(self, mock_deps):
        mock_deps["screenshot"].side_effect = RuntimeError("ADB offline")
        record = capture_and_classify("x", "page_main", "PageArrive", {}, [], "Test")
        assert record == {}

    def test_observe_failure_returns_empty(self, mock_deps):
        mock_deps["build_observations"].side_effect = OSError("bad image")
        record = capture_and_classify("x", "page_main", "PageArrive", {}, [], "Test")
        assert record == {}

    def test_locate_failure_sets_error_label(self, mock_deps):
        mock_deps["locate"].side_effect = ValueError("broken graph")
        record = capture_and_classify("x", "page_main", "PageArrive", {}, [], "Test")
        assert record["our_label"] == "error"
        assert record["match"] is False

    def test_screenshot_saved_to_disk(self, mock_deps):
        capture_and_classify("x", "page_main", "PageArrive", {}, [], "Test")
        screenshots = list((mock_deps["tmp_path"] / "screenshots").glob("*.png"))
        assert len(screenshots) == 1
        assert screenshots[0].name.startswith("page_main_")


class TestSiphonEventDetection:
    """Test the regex patterns used in siphon's main loop to detect events.

    These tests import RE_PAGE_ARRIVE, RE_UI_IDENTIFY, and RE_START_TASK
    directly from siphon.py so that if the patterns change in the source,
    the tests will fail and catch the regression.
    """

    def test_page_arrive_regex(self):
        match = RE_PAGE_ARRIVE.search("Page arrive: page_reward")
        assert match is not None
        assert match.group(1) == "page_reward"

    def test_ui_identify_regex(self):
        match = RE_UI_IDENTIFY.search("[UI] page_main")
        assert match is not None
        assert match.group(1) == "page_main"

    def test_ui_identify_with_extra_whitespace(self):
        match = RE_UI_IDENTIFY.search("[UI]  page_commission")
        assert match is not None
        assert match.group(1) == "page_commission"

    def test_start_task_regex(self):
        match = RE_START_TASK.search("Scheduler: Start task `Commission`")
        assert match is not None
        assert match.group(1) == "Commission"

    def test_ui_regex_ignores_non_page(self):
        match = RE_UI_IDENTIFY.search("[UI] Unknown ui page")
        assert match is None

    def test_page_arrive_real_format(self):
        line = "2026-03-14 00:44:20.339 | INFO | Page arrive: page_reward"
        msg = line.split(" | ", 2)[2]
        match = RE_PAGE_ARRIVE.search(msg)
        assert match is not None
        assert match.group(1) == "page_reward"
