"""Tests for transport layer — config loading and parsing."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from state_cartographer.transport.config import TransportConfig, load_config


def test_load_config_defaults():
    cfg = load_config()
    assert cfg.adb_serial == "127.0.0.1:21503"
    assert cfg.emulator_type == "memu"


def test_load_config_custom(tmp_path: Path):
    data = {
        "name": "Test",
        "emulator_type": "memu",
        "adb_serial": "127.0.0.1:5555",
        "primary_control": "maatouch",
        "primary_observation": "adb_screencap",
    }
    cfg_path = tmp_path / "memu-custom.json"
    cfg_path.write_text(json.dumps(data), encoding="utf-8")
    cfg = load_config(cfg_path)
    assert cfg.serial == "127.0.0.1:5555"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 5555


def test_config_serial_property():
    cfg = TransportConfig(adb_serial="10.0.0.1:21513")
    assert cfg.serial == "10.0.0.1:21513"
    assert cfg.host == "10.0.0.1"
    assert cfg.port == 21513


def test_config_missing_raises():
    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.json")
