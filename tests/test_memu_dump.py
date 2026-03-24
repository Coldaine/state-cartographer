"""Tests for scripts/memu_dump.py.

All memuc subprocess calls are mocked — no real emulator required.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "scripts"))

import memu_dump

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

LISTVMS_OUTPUT = """\
0,MEmu,Running,12345,0
1,MEmu_1,Running,23456,0
2,MEmu_2,Stopped,0,0"""

GETCONFIG_RESPONSES = {
    "graphics_render_mode": "Value: 0",
    "resolution_width": "Value: 1280",
    "resolution_height": "Value: 720",
    "vbox_dpi": "Value: 240",
    "cpus": "Value: 4",
    "memory": "Value: 8192",
    "fps": "Value: 60",
    "enable_su": "Value: 1",
}


def _make_popen(stdout: str = "", stderr: str = "", returncode: int = 0):
    """Create a mock Popen object with communicate() support."""
    mock = MagicMock()
    mock.communicate.return_value = (stdout, stderr)
    mock.returncode = returncode
    mock.kill.return_value = None
    mock.wait.return_value = returncode
    return mock


def _mock_popen_side_effect(cmd, **kwargs):
    """Route memuc subcommands to fixture data."""
    args = cmd[1:]  # skip memuc path
    if args[0] == "listvms":
        return _make_popen(stdout=LISTVMS_OUTPUT)
    if args[0] == "getconfig" and len(args) >= 4:
        key = args[3]
        if key in GETCONFIG_RESPONSES:
            return _make_popen(stdout=GETCONFIG_RESPONSES[key])
        return _make_popen(stdout="", stderr=f"unknown key: {key}", returncode=1)
    return _make_popen(stdout="", stderr="unknown command", returncode=1)


# ---------------------------------------------------------------------------
# 1. Path resolution
# ---------------------------------------------------------------------------


class TestFindMemuc:
    def test_override_existing_file(self, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        result = memu_dump.find_memuc(str(memuc))
        assert result == memuc

    def test_override_missing_file_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError, match="not found at override path"):
            memu_dump.find_memuc(str(tmp_path / "nope.exe"))

    def test_derives_from_alas_config(self, tmp_path, monkeypatch):
        # Set up fake alas config
        config_dir = tmp_path / "vendor" / "AzurLaneAutoScript" / "config"
        config_dir.mkdir(parents=True)
        memu_dir = tmp_path / "MEmu"
        memu_dir.mkdir()
        memuc = memu_dir / "memuc.exe"
        memuc.touch()
        alas_json = config_dir / "alas.json"
        alas_json.write_text(
            json.dumps(
                {
                    "Alas": {
                        "EmulatorInfo": {
                            "path": str(memu_dir / "MEmu.exe"),
                        }
                    }
                }
            )
        )
        # Patch __file__ so the script looks in our tmp_path
        monkeypatch.setattr(
            memu_dump,
            "__file__",
            str(tmp_path / "scripts" / "memu_dump.py"),
        )
        result = memu_dump.find_memuc(None)
        assert result == memuc

    def test_no_paths_found_raises(self, tmp_path, monkeypatch):
        monkeypatch.setattr(
            memu_dump,
            "__file__",
            str(tmp_path / "scripts" / "memu_dump.py"),
        )
        # Also patch Path.is_file to block common install path guesses
        original_is_file = Path.is_file

        def _fake_is_file(self):
            if "memuc.exe" in str(self):
                return False
            return original_is_file(self)

        monkeypatch.setattr(Path, "is_file", _fake_is_file)
        with pytest.raises(FileNotFoundError, match=r"memuc\.exe not found"):
            memu_dump.find_memuc(None)


# ---------------------------------------------------------------------------
# 2. Render mode mapping
# ---------------------------------------------------------------------------


class TestRenderModeMapping:
    def test_opengl(self):
        assert memu_dump.RENDER_MODES["0"] == "OpenGL"

    def test_directx(self):
        assert memu_dump.RENDER_MODES["1"] == "DirectX"

    @patch("memu_dump.subprocess.Popen", side_effect=_mock_popen_side_effect)
    def test_dump_reports_opengl(self, mock_popen, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        data = memu_dump.dump_instance(memuc, 1)
        assert data["rendering"] == "OpenGL"


# ---------------------------------------------------------------------------
# 3. Resolution formatting
# ---------------------------------------------------------------------------


class TestResolutionFormatting:
    @patch("memu_dump.subprocess.Popen", side_effect=_mock_popen_side_effect)
    def test_resolution_in_dump(self, mock_popen, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        data = memu_dump.dump_instance(memuc, 1)
        assert data["resolution"] == {"width": 1280, "height": 720}

    @patch("memu_dump.subprocess.Popen", side_effect=_mock_popen_side_effect)
    def test_human_format_shows_resolution(self, mock_popen, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        data = memu_dump.dump_instance(memuc, 1)
        text = memu_dump.format_human(data)
        assert "1280x720" in text


# ---------------------------------------------------------------------------
# 4. Instance listing
# ---------------------------------------------------------------------------


class TestListVms:
    @patch("memu_dump.subprocess.Popen", side_effect=_mock_popen_side_effect)
    def test_parse_listvms(self, mock_popen, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        vms = memu_dump.list_vms(memuc)
        assert len(vms) == 3
        assert vms[0] == {"index": "0", "name": "MEmu", "status": "Running"}
        assert vms[1] == {"index": "1", "name": "MEmu_1", "status": "Running"}
        assert vms[2] == {"index": "2", "name": "MEmu_2", "status": "Stopped"}


# ---------------------------------------------------------------------------
# 5. Error handling
# ---------------------------------------------------------------------------


class TestErrorHandling:
    def test_missing_memuc_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            memu_dump.find_memuc(str(tmp_path / "nonexistent.exe"))

    @patch("memu_dump.subprocess.Popen")
    def test_getconfig_failure(self, mock_popen, tmp_path):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        mock_popen.return_value = _make_popen(stderr="invalid index", returncode=1)
        with pytest.raises(RuntimeError, match="failed"):
            memu_dump.get_config(memuc, 99, "cpus")

    @patch("memu_dump.subprocess.Popen")
    def test_listvms_failure_graceful_in_dump(self, mock_popen, tmp_path):
        """dump_instance should still work if listvms fails."""
        memuc = tmp_path / "memuc.exe"
        memuc.touch()

        def side_effect(cmd, **kwargs):
            args = cmd[1:]
            if args[0] == "listvms":
                return _make_popen(stderr="connect console failed", returncode=1)
            if args[0] == "getconfig":
                key = args[3]
                if key in GETCONFIG_RESPONSES:
                    return _make_popen(stdout=GETCONFIG_RESPONSES[key])
            return _make_popen(returncode=1, stderr="unknown")

        mock_popen.side_effect = side_effect
        data = memu_dump.dump_instance(memuc, 1)
        # Should still have config data even without VM name
        assert data["rendering"] == "OpenGL"
        assert "name" not in data


# ---------------------------------------------------------------------------
# 6. JSON mode
# ---------------------------------------------------------------------------


class TestJsonMode:
    @patch("memu_dump.subprocess.Popen", side_effect=_mock_popen_side_effect)
    @patch("memu_dump.find_memuc")
    def test_json_output_parseable(self, mock_find, mock_popen, tmp_path, capsys):
        memuc = tmp_path / "memuc.exe"
        memuc.touch()
        mock_find.return_value = memuc
        rc = memu_dump.main(["--json", "--index", "1"])
        assert rc == 0
        captured = capsys.readouterr()
        data = json.loads(captured.out)
        assert data["rendering"] == "OpenGL"
        assert data["resolution"]["width"] == 1280
        assert data["fps"] == 60
        assert data["root_enabled"] is True
