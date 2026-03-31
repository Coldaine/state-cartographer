"""Tests for the Pilot facade — press(), tap_chain, and trace coverage.

All tests run offline using mocks. No emulator or ADB connection required.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from state_cartographer.transport.pilot import Pilot


@pytest.fixture
def pilot():
    """Create a Pilot with mocked ADB internals."""
    with patch("state_cartographer.transport.pilot.Adb") as MockAdb:
        mock_adb = MockAdb.return_value
        mock_adb.connect.return_value = True
        mock_adb.screenshot_png.return_value = b"\x89PNG_FAKE_DATA"
        mock_adb.tap.return_value = True
        mock_adb.keyevent.return_value = True
        mock_adb.input_text.return_value = True

        p = Pilot.__new__(Pilot)
        p.config = MagicMock()
        p.config.serial = "127.0.0.1:21503"
        p.config.adb_serial = "127.0.0.1:21503"
        p.adb = mock_adb
        p._maatouch = None
        yield p


# ---------------------------------------------------------------------------
# press()
# ---------------------------------------------------------------------------


class TestPress:
    def test_valid_action(self, pilot):
        assert pilot.press("primary") is True
        pilot.adb.keyevent.assert_called_once_with(62)

    def test_unknown_action_raises(self, pilot):
        with pytest.raises(ValueError, match="Unknown key action"):
            pilot.press("nonexistent")

    def test_count_sends_multiple(self, pilot):
        pilot.press("back", count=3, delay=0)
        assert pilot.adb.keyevent.call_count == 3
        pilot.adb.keyevent.assert_called_with(61)

    def test_partial_failure(self, pilot):
        pilot.adb.keyevent.side_effect = [True, False, True]
        result = pilot.press("primary", count=3, delay=0)
        assert result is False

    def test_all_keymap_entries_are_ints(self):
        for name, keycode in Pilot.KEYMAP.items():
            assert isinstance(name, str)
            assert isinstance(keycode, int)


# ---------------------------------------------------------------------------
# Trace coverage — screenshot, keyevent, input_text
# ---------------------------------------------------------------------------


class TestTraceCoverage:
    @patch("state_cartographer.transport.pilot.action")
    def test_screenshot_traces(self, mock_action, pilot):
        data = pilot.screenshot()
        assert data == b"\x89PNG_FAKE_DATA"
        mock_action.assert_called_once()
        args = mock_action.call_args
        assert args[0][0] == "screenshot"
        assert args[0][4] == "success"
        assert args[1]["duration_ms"] >= 0

    @patch("state_cartographer.transport.pilot.action")
    def test_screenshot_traces_failure(self, mock_action, pilot):
        pilot.adb.screenshot_png.side_effect = RuntimeError("ADB dead")
        with pytest.raises(RuntimeError):
            pilot.screenshot()
        mock_action.assert_called_once()
        args = mock_action.call_args
        assert args[0][0] == "screenshot"
        assert args[0][4] == "failure"

    @patch("state_cartographer.transport.pilot.action")
    def test_keyevent_traces(self, mock_action, pilot):
        pilot.keyevent(62)
        mock_action.assert_called_once()
        args = mock_action.call_args
        assert args[0][0] == "keyevent"
        assert args[0][3] == {"keycode": 62}

    @patch("state_cartographer.transport.pilot.action")
    def test_keyevent_traces_failure(self, mock_action, pilot):
        pilot.adb.keyevent.side_effect = RuntimeError("ADB dead")
        with pytest.raises(RuntimeError):
            pilot.keyevent(62)
        mock_action.assert_called_once()
        args = mock_action.call_args
        assert args[0][0] == "keyevent"
        assert args[0][4] == "failure"

    @patch("state_cartographer.transport.pilot.action")
    def test_input_text_traces(self, mock_action, pilot):
        pilot.input_text("hello")
        mock_action.assert_called_once()
        args = mock_action.call_args
        assert args[0][0] == "input_text"
        assert args[0][3] == {"length": 5}

    @patch("state_cartographer.transport.pilot.action")
    def test_press_traces(self, mock_action, pilot):
        pilot.press("primary")
        # press() calls keyevent() which also traces, so we get 2 calls
        action_names = [c[0][0] for c in mock_action.call_args_list]
        assert "keyevent" in action_names
        assert "press" in action_names


# ---------------------------------------------------------------------------
# tap_chain
# ---------------------------------------------------------------------------


class TestTapChain:
    def test_returns_empty_without_capture_dir(self, pilot):
        paths = pilot.tap_chain([(100, 200, 0), (300, 400, 0)])
        assert paths == []
        assert pilot.adb.tap.call_count == 2

    def test_captures_screenshots_with_capture_dir(self, pilot, tmp_path):
        paths = pilot.tap_chain(
            [(100, 200, 0), (300, 400, 0)],
            capture_dir=tmp_path / "captures",
        )
        assert len(paths) == 2
        assert all(p.exists() for p in paths)
        assert (tmp_path / "captures").is_dir()

    def test_capture_filenames_include_coords(self, pilot, tmp_path):
        paths = pilot.tap_chain(
            [(100, 200, 0)],
            capture_dir=tmp_path / "caps",
        )
        assert "100_200" in paths[0].name

    @patch("state_cartographer.transport.pilot.action")
    def test_chain_level_trace(self, mock_action, pilot):
        pilot.tap_chain([(100, 200, 0), (300, 400, 0)])
        action_names = [c[0][0] for c in mock_action.call_args_list]
        assert action_names[0] == "tap_chain_start"
        assert action_names[-1] == "tap_chain_end"
        # Individual taps should be in between
        assert "tap" in action_names
