"""Tests for scripts/adb_bridge.py.

All ADB subprocess calls are mocked — no real ADB or device required.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import adb_bridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_proc(
    stdout: bytes | str = b"",
    stderr: bytes = b"",
    returncode: int = 0,
) -> MagicMock:
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = stdout
    mock.stderr = stderr
    mock.returncode = returncode
    return mock


# ---------------------------------------------------------------------------
# devices()
# ---------------------------------------------------------------------------


class TestDevices:
    def test_returns_empty_list_when_no_devices(self):
        proc = _make_proc(stdout="List of devices attached\n\n")
        with patch("adb_bridge.subprocess.run", return_value=proc):
            result = adb_bridge.devices()
        assert result == []

    def test_parses_single_device(self):
        proc = _make_proc(stdout="List of devices attached\n127.0.0.1:21503\tdevice\n")
        with patch("adb_bridge.subprocess.run", return_value=proc):
            result = adb_bridge.devices()
        assert len(result) == 1
        assert result[0] == {"serial": "127.0.0.1:21503", "state": "device"}

    def test_parses_multiple_devices(self):
        out = "List of devices attached\n127.0.0.1:21503\tdevice\nemulator-5554\toffline\n"
        proc = _make_proc(stdout=out)
        with patch("adb_bridge.subprocess.run", return_value=proc):
            result = adb_bridge.devices()
        assert len(result) == 2
        assert result[1]["state"] == "offline"

    def test_raises_when_adb_not_found(self):
        with (
            patch("adb_bridge.subprocess.run", side_effect=FileNotFoundError),
            pytest.raises(RuntimeError, match="ADB not found"),
        ):
            adb_bridge.devices()


# ---------------------------------------------------------------------------
# connect()
# ---------------------------------------------------------------------------


class TestConnect:
    def test_returns_true_on_success(self):
        proc = _make_proc(stdout="connected to 127.0.0.1:21503\n")
        with patch("adb_bridge.subprocess.run", return_value=proc):
            assert adb_bridge.connect("127.0.0.1:21503") is True

    def test_returns_false_on_failure(self):
        proc = _make_proc(stdout="failed to connect: Connection refused\n")
        with patch("adb_bridge.subprocess.run", return_value=proc):
            assert adb_bridge.connect("127.0.0.1:21503") is False

    def test_already_connected_is_success(self):
        proc = _make_proc(stdout="already connected to 127.0.0.1:21503\n")
        with patch("adb_bridge.subprocess.run", return_value=proc):
            assert adb_bridge.connect("127.0.0.1:21503") is True

    def test_uses_correct_adb_command(self):
        proc = _make_proc(stdout="connected to 127.0.0.1:21503\n")
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.connect("127.0.0.1:21503")
        called_args = mock_run.call_args[0][0]
        assert called_args == ["adb", "connect", "127.0.0.1:21503"]


# ---------------------------------------------------------------------------
# screenshot()
# ---------------------------------------------------------------------------


_PNG_HEADER = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # minimal fake PNG-looking bytes


class TestScreenshot:
    def test_returns_png_bytes(self):
        proc = _make_proc(stdout=_PNG_HEADER)
        with patch("adb_bridge.subprocess.run", return_value=proc):
            data = adb_bridge.screenshot("127.0.0.1:21503")
        assert data == _PNG_HEADER

    def test_writes_file_when_output_path_given(self, tmp_path):
        out_file = tmp_path / "screen.png"
        proc = _make_proc(stdout=_PNG_HEADER)
        with patch("adb_bridge.subprocess.run", return_value=proc):
            data = adb_bridge.screenshot("127.0.0.1:21503", out_file)
        assert out_file.exists()
        assert out_file.read_bytes() == _PNG_HEADER
        assert data == _PNG_HEADER

    def test_raises_on_nonzero_returncode(self):
        proc = _make_proc(
            stdout=b"",
            stderr=b"error: device not found",
            returncode=1,
        )
        with (
            patch("adb_bridge.subprocess.run", return_value=proc),
            pytest.raises(RuntimeError, match="Screenshot failed"),
        ):
            adb_bridge.screenshot("127.0.0.1:21503")

    def test_raises_when_data_is_not_png(self):
        proc = _make_proc(stdout=b"garbage data")
        with (
            patch("adb_bridge.subprocess.run", return_value=proc),
            pytest.raises(RuntimeError, match="invalid PNG"),
        ):
            adb_bridge.screenshot("127.0.0.1:21503")

    def test_raises_when_data_is_empty(self):
        proc = _make_proc(stdout=b"")
        with (
            patch("adb_bridge.subprocess.run", return_value=proc),
            pytest.raises(RuntimeError, match="invalid PNG"),
        ):
            adb_bridge.screenshot("127.0.0.1:21503")

    def test_uses_correct_adb_command(self):
        proc = _make_proc(stdout=_PNG_HEADER)
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.screenshot("127.0.0.1:21503")
        called_args = mock_run.call_args[0][0]
        assert called_args[:3] == ["adb", "-s", "127.0.0.1:21503"]
        assert "screencap" in called_args
        assert "-p" in called_args


# ---------------------------------------------------------------------------
# tap()
# ---------------------------------------------------------------------------


class TestTap:
    def test_sends_correct_adb_command(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.tap("127.0.0.1:21503", 500, 400)
        called_args = mock_run.call_args[0][0]
        assert "tap" in called_args
        assert "500" in called_args
        assert "400" in called_args

    def test_uses_correct_serial(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.tap("127.0.0.1:21513", 0, 0)
        called_args = mock_run.call_args[0][0]
        assert "127.0.0.1:21513" in called_args


# ---------------------------------------------------------------------------
# swipe()
# ---------------------------------------------------------------------------


class TestSwipe:
    def test_sends_correct_adb_command(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.swipe("127.0.0.1:21503", 100, 200, 300, 400, 500)
        called_args = mock_run.call_args[0][0]
        assert "swipe" in called_args
        assert "100" in called_args
        assert "200" in called_args
        assert "300" in called_args
        assert "400" in called_args
        assert "500" in called_args

    def test_default_duration_is_300(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.swipe("127.0.0.1:21503", 0, 0, 100, 100)
        called_args = mock_run.call_args[0][0]
        assert "300" in called_args


# ---------------------------------------------------------------------------
# key_event()
# ---------------------------------------------------------------------------


class TestKeyEvent:
    def test_sends_integer_keycode(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.key_event("127.0.0.1:21503", 4)
        called_args = mock_run.call_args[0][0]
        assert "keyevent" in called_args
        assert "4" in called_args

    def test_sends_string_keycode(self):
        proc = _make_proc()
        with patch("adb_bridge.subprocess.run", return_value=proc) as mock_run:
            adb_bridge.key_event("127.0.0.1:21503", "KEYCODE_BACK")
        called_args = mock_run.call_args[0][0]
        assert "KEYCODE_BACK" in called_args
