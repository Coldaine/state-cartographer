"""Tests for scripts/pilot_bridge.py.

These tests mock ADB subprocess calls and HTTP sessions so no real emulator is required.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import pilot_bridge


def _make_proc(stdout: bytes | str = b"", stderr: bytes | str = b"", returncode: int = 0) -> MagicMock:
    mock = MagicMock(spec=subprocess.CompletedProcess)
    mock.stdout = stdout
    mock.stderr = stderr
    mock.returncode = returncode
    return mock


class _DummyResponse:
    def __init__(self, status_code: int = 200, content: bytes = b"{}"):
        self.status_code = status_code
        self.content = content

    def raise_for_status(self):
        return None


class TestPilotBridge:
    def test_screenshot_auto_connects_when_needed(self, tmp_path):
        bridge = pilot_bridge.PilotBridge(record=False, screenshot_dir=tmp_path)
        frame = np.zeros((4, 4, 3), dtype=np.uint8)

        def fake_connect():
            bridge._connected = True

        with (
            patch.object(bridge, "connect", side_effect=fake_connect) as mock_connect,
            patch.object(bridge, "_restart_and_capture", return_value=frame),
        ):
            img = bridge.screenshot()

        assert img.size == (4, 4)
        mock_connect.assert_called_once()

    def test_connect_rejects_local_port_conflict_from_other_serial(self, tmp_path):
        bridge = pilot_bridge.PilotBridge(record=False, screenshot_dir=tmp_path)
        bridge._session.get = MagicMock(return_value=_DummyResponse())

        adb_calls = [
            _make_proc(stdout=b"already connected to 127.0.0.1:21513\n"),
            _make_proc(stdout=b"List of devices attached\n127.0.0.1:21513\tdevice\n"),
            _make_proc(),
            _make_proc(stdout=b"other-serial tcp:17912 tcp:7912\n"),
        ]

        with (
            patch("pilot_bridge._adb", side_effect=adb_calls),
            pytest.raises(RuntimeError, match="already forwarded to other-serial"),
        ):
            bridge.connect()

    def test_connect_adds_droidcast_forward_when_missing_for_this_serial(self, tmp_path):
        bridge = pilot_bridge.PilotBridge(record=False, screenshot_dir=tmp_path)
        bridge._session.get = MagicMock(return_value=_DummyResponse())

        with (
            patch.object(bridge, "_restart_and_capture", return_value=np.zeros((1, 1, 3), dtype=np.uint8)),
            patch.object(bridge, "_alas_running", return_value=False),
            patch("pilot_bridge._adb") as mock_adb,
        ):
            mock_adb.side_effect = [
                _make_proc(stdout=b"already connected to 127.0.0.1:21513\n"),
                _make_proc(stdout=b"List of devices attached\n127.0.0.1:21513\tdevice\n"),
                _make_proc(),
                _make_proc(stdout=b""),
                _make_proc(),
                _make_proc(stdout=b"127.0.0.1:21513 tcp:17912 tcp:7912\n"),
                _make_proc(),
            ]

            bridge.connect()

        calls = [call.args[0:3] for call in mock_adb.call_args_list]
        assert ("forward", "tcp:53516", "tcp:53516") in calls

    def test_connect_rejects_wrong_existing_same_serial_forward_in_shared_mode(self, tmp_path):
        bridge = pilot_bridge.PilotBridge(record=False, screenshot_dir=tmp_path)
        bridge._session.get = MagicMock(return_value=_DummyResponse())

        with (
            patch.object(bridge, "_alas_running", return_value=True),
            patch("pilot_bridge._adb") as mock_adb,
        ):
            mock_adb.side_effect = [
                _make_proc(stdout=b"already connected to 127.0.0.1:21513\n"),
                _make_proc(stdout=b"List of devices attached\n127.0.0.1:21513\tdevice\n"),
                _make_proc(),
                _make_proc(stdout=b"127.0.0.1:21513 tcp:17912 tcp:7912\n"),
                _make_proc(stdout=b"127.0.0.1:21513 tcp:53516 tcp:9999\n"),
            ]

            with pytest.raises(RuntimeError, match="already points to tcp:9999"):
                bridge.connect()
