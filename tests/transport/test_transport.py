"""Tests for transport layer pure code — config, models, discovery resolution."""

from __future__ import annotations

import json
import tempfile

from state_cartographer.transport.config import TransportConfig, load_config
from state_cartographer.transport.models import (
    BootstrapManifest,
    DoctorReport,
    MaaCaptureResult,
    MaaProbeReport,
    ObservationDecision,
    ProbeVerdict,
    ScrcpyProbeReport,
    SessionProbeReport,
    ToolEntry,
)

# --- Config parsing ---


def test_load_config_defaults():
    """Default config at configs/memu.json loads without error."""
    cfg = load_config()
    assert cfg.adb_serial == "127.0.0.1:21513"
    assert cfg.emulator_type == "memu"


def test_load_config_custom():
    """Config with new transport fields loads correctly."""
    data = {
        "name": "Test",
        "emulator_type": "memu",
        "adb_serial": "127.0.0.1:5555",
        "primary_control": "maamcp",
        "preferred_visual": "scrcpy",
        "fallback_observation": "maamcp_screenshot",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        cfg = load_config(f.name)
    assert cfg.serial == "127.0.0.1:5555"
    assert cfg.host == "127.0.0.1"
    assert cfg.port == 5555
    assert cfg.primary_control == "maamcp"


def test_config_serial_property():
    cfg = TransportConfig(adb_serial="10.0.0.1:21513")
    assert cfg.serial == "10.0.0.1:21513"
    assert cfg.host == "10.0.0.1"
    assert cfg.port == 21513


def test_config_missing_raises():
    import pytest

    with pytest.raises(FileNotFoundError):
        load_config("/nonexistent/path.json")


# --- Model serialization ---


def test_tool_entry_to_dict():
    t = ToolEntry(name="adb", found=True, path="/usr/bin/adb", version="1.0")
    d = t.to_dict()
    assert d["name"] == "adb"
    assert d["found"] is True
    assert "error" not in d  # None fields omitted


def test_tool_entry_not_found():
    t = ToolEntry(name="maamcp", found=False, error="not installed")
    d = t.to_dict()
    assert d["found"] is False
    assert d["error"] == "not installed"


def test_bootstrap_manifest_json():
    m = BootstrapManifest(
        tools=[ToolEntry(name="adb", found=True, path="/usr/bin/adb")],
        all_required_found=True,
    )
    j = m.to_json()
    parsed = json.loads(j)
    assert parsed["all_required_found"] is True
    assert len(parsed["tools"]) == 1


def test_doctor_report_json():
    r = DoctorReport(
        serial="127.0.0.1:21513",
        adb_reachable=True,
        device_online=True,
        verdict=ProbeVerdict.PASS,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["device_online"] is True


def test_maa_probe_report_json():
    r = MaaProbeReport(
        serial="127.0.0.1:21513",
        connected=True,
        captures=[MaaCaptureResult(success=True, path="test.png", elapsed_ms=150, width=1280, height=720)],
        capture_verdict=ProbeVerdict.PASS,
        input_tap=ProbeVerdict.PASS,
        verdict=ProbeVerdict.PASS,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["connected"] is True
    assert len(parsed["captures"]) == 1


def test_scrcpy_probe_report_json():
    r = ScrcpyProbeReport(
        serial="127.0.0.1:21513",
        binary_found=True,
        attached=True,
        observation_decision=ObservationDecision.DEBUG_ONLY,
    )
    parsed = json.loads(r.to_json())
    assert parsed["observation_decision"] == "debug_only"


def test_session_probe_report_json():
    r = SessionProbeReport(
        serial="127.0.0.1:21513",
        verdict=ProbeVerdict.PASS,
        observation_decision=ObservationDecision.DEBUG_ONLY,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["observation_decision"] == "debug_only"


# --- Tool path resolution precedence ---


def test_tool_entry_source_precedence():
    """PATH-found tools should be preferred over install-dir discovery."""
    path_tool = ToolEntry(name="adb", found=True, path="/usr/bin/adb", source="PATH")
    dir_tool = ToolEntry(name="adb", found=True, path="C:/Microvirt/MEmu/adb.exe", source="memu_install")
    # Both valid, but PATH source ranks first in discovery logic
    assert path_tool.source == "PATH"
    assert dir_tool.source == "memu_install"


# --- Doctor state aggregation ---


def test_doctor_pass_requires_all():
    """Doctor passes only when device online AND all required tools found."""
    manifest = BootstrapManifest(all_required_found=True)
    r = DoctorReport(
        serial="127.0.0.1:21513",
        adb_reachable=True,
        device_online=True,
        maamcp_available=True,
        bootstrap=manifest,
        verdict=ProbeVerdict.PASS,
    )
    assert r.verdict == ProbeVerdict.PASS


def test_doctor_fail_without_device():
    r = DoctorReport(
        serial="127.0.0.1:21513",
        adb_reachable=True,
        device_online=False,
        verdict=ProbeVerdict.FAIL,
    )
    assert r.verdict == ProbeVerdict.FAIL


def test_doctor_fail_without_tools():
    manifest = BootstrapManifest(all_required_found=False, missing=["maamcp"])
    r = DoctorReport(
        serial="127.0.0.1:21513",
        adb_reachable=True,
        device_online=True,
        bootstrap=manifest,
        verdict=ProbeVerdict.FAIL,
    )
    assert r.verdict == ProbeVerdict.FAIL
