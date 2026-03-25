"""Tests for transport layer — config, models, and health."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import TransportConfig, load_config
from state_cartographer.transport.health import doctor, recovery_ladder
from state_cartographer.transport.models import (
    ControlLayerStatus,
    DoctorReport,
    MaaCaptureResult,
    ObservationDecision,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    ScrcpyProbeReport,
    SessionProbeReport,
    ToolEntry,
    TransportLayerStatus,
)


def test_load_config_defaults():
    cfg = load_config()
    assert cfg.adb_serial == "127.0.0.1:21513"
    assert cfg.emulator_type == "memu"


def test_load_config_custom():
    data = {
        "name": "Test",
        "emulator_type": "memu",
        "adb_serial": "127.0.0.1:5555",
        "primary_control": "maatouch",
        "preferred_visual": "scrcpy",
    }
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(data, f)
        f.flush()
        cfg = load_config(f.name)
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


def test_tool_entry_to_dict():
    t = ToolEntry(name="adb", found=True, path="/usr/bin/adb", version="1.0")
    d = t.to_dict()
    assert d["name"] == "adb"
    assert d["found"] is True
    assert "error" not in d


def test_tool_entry_not_found():
    t = ToolEntry(name="maatouch", found=False, error="not installed")
    d = t.to_dict()
    assert d["found"] is False
    assert d["error"] == "not installed"


def test_tool_entry_source_precedence():
    path_tool = ToolEntry(name="adb", found=True, path="/usr/bin/adb", source="PATH")
    dir_tool = ToolEntry(name="adb", found=True, path="C:/Microvirt/MEmu/adb.exe", source="memu_install")
    assert path_tool.source == "PATH"
    assert dir_tool.source == "memu_install"


def test_adb_devices_uses_adbutils_device_list():
    class FakeClient:
        def device_list(self):
            return [SimpleNamespace(serial="127.0.0.1:21503"), SimpleNamespace(serial="emulator-5554")]

    adb = Adb("127.0.0.1:21503")
    adb._client = FakeClient()

    assert adb.devices() == ["127.0.0.1:21503", "emulator-5554"]


def test_bootstrap_manifest_json():
    m = DoctorReport(
        serial="127.0.0.1:21503",
        readiness_tier=ReadinessTier.DEGRADED,
        transport_layer=TransportLayerStatus.READY,
        control_layer=ControlLayerStatus.FALLBACK,
        observation_layer=ObservationLayerStatus.UNVERIFIED,
        degradation_codes=["preferred_input_missing", "observation_unverified"],
        adb_reachable=True,
        device_online=True,
        verdict=ProbeVerdict.PASS,
    )
    j = m.to_json()
    parsed = json.loads(j)
    assert parsed["verdict"] == "pass"
    assert parsed["device_online"] is True
    assert parsed["readiness_tier"] == "degraded"
    assert parsed["control_layer"] == "fallback"


def test_doctor_report_json():
    r = DoctorReport(
        serial="127.0.0.1:21503",
        readiness_tier=ReadinessTier.DEGRADED,
        transport_layer=TransportLayerStatus.READY,
        control_layer=ControlLayerStatus.FALLBACK,
        observation_layer=ObservationLayerStatus.UNVERIFIED,
        degradation_codes=["preferred_input_missing", "observation_unverified"],
        adb_reachable=True,
        device_online=True,
        verdict=ProbeVerdict.PASS,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["device_online"] is True
    assert parsed["readiness_tier"] == "degraded"
    assert parsed["control_layer"] == "fallback"
    assert parsed["degradation_codes"] == ["preferred_input_missing", "observation_unverified"]


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
        degradation_codes=["debug_only_visual"],
        verdict=ProbeVerdict.PASS,
        observation_decision=ObservationDecision.DEBUG_ONLY,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["observation_decision"] == "debug_only"
    assert parsed["degradation_codes"] == ["debug_only_visual"]


def test_doctor_unreachable_when_device_stays_offline(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maatouch")

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return False

        def connect(self) -> bool:
            return False

    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.UNREACHABLE
    assert report.transport_layer == TransportLayerStatus.UNREACHABLE
    assert report.control_layer == ControlLayerStatus.UNAVAILABLE
    assert report.observation_layer == ObservationLayerStatus.UNAVAILABLE
    assert report.verdict == ProbeVerdict.FAIL


def test_doctor_operable_when_device_online(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maatouch")

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return True

        def connect(self) -> bool:
            return True

    class FakeMaaTouch:
        DEFAULT_LOCAL_PATH = Path("/tmp/fake")

    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)
    monkeypatch.setattr("state_cartographer.transport.maatouch", SimpleNamespace(DEFAULT_LOCAL_PATH=Path("/tmp/fake")))

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.OPERABLE
    assert report.transport_layer == TransportLayerStatus.READY
    assert report.control_layer == ControlLayerStatus.PREFERRED
    assert report.observation_layer == ObservationLayerStatus.UNVERIFIED
    assert "observation_unverified" in report.degradation_codes
    assert report.verdict == ProbeVerdict.PASS


def test_doctor_degraded_when_maatouch_binary_missing(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maatouch")

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return True

        def connect(self) -> bool:
            return True

    def fake_ensure_installed():
        return False

    import state_cartographer.transport.maatouch as maatouch_module

    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)
    monkeypatch.setattr(maatouch_module, "DEFAULT_LOCAL_PATH", Path("/nonexistent"))

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.DEGRADED
    assert report.transport_layer == TransportLayerStatus.READY
    assert report.control_layer == ControlLayerStatus.FALLBACK
    assert "preferred_input_missing" in report.degradation_codes
    assert report.verdict == ProbeVerdict.PASS
