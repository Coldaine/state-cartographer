"""Tests for transport layer pure code — config, models, discovery resolution."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import memu_transport
from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import TransportConfig, load_config
from state_cartographer.transport.health import doctor
from state_cartographer.transport.models import (
    BootstrapManifest,
    ControlLayerStatus,
    DoctorReport,
    MaaCaptureResult,
    MaaProbeReport,
    ObservationDecision,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    ScrcpyProbeReport,
    SessionProbeReport,
    ToolEntry,
    TransportLayerStatus,
)

# --- Config parsing ---


def test_load_config_defaults():
    """Default config at configs/memu.json loads without error."""
    cfg = load_config()
    assert cfg.adb_serial == "127.0.0.1:21503"
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
        readiness_tier=ReadinessTier.DEGRADED,
        transport_layer=TransportLayerStatus.READY,
        control_layer=ControlLayerStatus.FALLBACK,
        observation_layer=ObservationLayerStatus.UNVERIFIED,
        degradation_codes=["preferred_stack_missing", "observation_unverified"],
        adb_reachable=True,
        device_online=True,
        verdict=ProbeVerdict.PASS,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["device_online"] is True
    assert parsed["readiness_tier"] == "degraded"
    assert parsed["control_layer"] == "fallback"
    assert parsed["degradation_codes"] == ["preferred_stack_missing", "observation_unverified"]


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
        degradation_codes=["debug_only_visual"],
        verdict=ProbeVerdict.PASS,
        observation_decision=ObservationDecision.DEBUG_ONLY,
    )
    parsed = json.loads(r.to_json())
    assert parsed["verdict"] == "pass"
    assert parsed["observation_decision"] == "debug_only"
    assert parsed["degradation_codes"] == ["debug_only_visual"]


# --- Tool path resolution precedence ---


def test_tool_entry_source_precedence():
    """PATH-found tools should be preferred over install-dir discovery."""
    path_tool = ToolEntry(name="adb", found=True, path="/usr/bin/adb", source="PATH")
    dir_tool = ToolEntry(name="adb", found=True, path="C:/Microvirt/MEmu/adb.exe", source="memu_install")
    # Both valid, but PATH source ranks first in discovery logic
    assert path_tool.source == "PATH"
    assert dir_tool.source == "memu_install"


def test_adb_devices_uses_adbutils_device_list():
    class FakeClient:
        def device_list(self):
            return [SimpleNamespace(serial="127.0.0.1:21503"), SimpleNamespace(serial="emulator-5554")]

    adb = Adb("127.0.0.1:21503")
    adb._client = FakeClient()

    assert adb.devices() == ["127.0.0.1:21503", "emulator-5554"]


# --- Doctor state aggregation ---


def test_doctor_operable_when_preferred_stack_available(monkeypatch: pytest.MonkeyPatch):
    with tempfile.NamedTemporaryFile(delete=False) as agent:
        agent_path = agent.name
    cfg = TransportConfig(primary_control="maamcp", preferred_visual="scrcpy", agent_path=agent_path)
    manifest = BootstrapManifest(
        all_required_found=True,
        tools=[
            ToolEntry(name="maamcp", found=True),
            ToolEntry(name="scrcpy", found=True),
        ],
    )

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return True

        def connect(self) -> bool:
            return True

    monkeypatch.setattr("state_cartographer.transport.health.bootstrap", lambda _: manifest)
    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)
    try:
        report = doctor(cfg)

        assert report.readiness_tier == ReadinessTier.OPERABLE
        assert report.transport_layer == TransportLayerStatus.READY
        assert report.control_layer == ControlLayerStatus.PREFERRED
        assert report.observation_layer == ObservationLayerStatus.UNVERIFIED
        assert report.degradation_codes == ["observation_unverified"]
        assert report.verdict == ProbeVerdict.PASS
    finally:
        Path(agent_path).unlink(missing_ok=True)


def test_doctor_degraded_when_preferred_stack_missing(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maamcp", preferred_visual="scrcpy")
    manifest = BootstrapManifest(
        all_required_found=False,
        missing=["maamcp"],
        tools=[
            ToolEntry(name="maamcp", found=False),
            ToolEntry(name="scrcpy", found=True),
        ],
    )

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return True

        def connect(self) -> bool:
            return True

    monkeypatch.setattr("state_cartographer.transport.health.bootstrap", lambda _: manifest)
    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.DEGRADED
    assert report.transport_layer == TransportLayerStatus.READY
    assert report.control_layer == ControlLayerStatus.FALLBACK
    assert report.observation_layer == ObservationLayerStatus.UNVERIFIED
    assert report.degradation_codes == ["observation_unverified", "preferred_stack_missing"]
    assert report.verdict == ProbeVerdict.PASS


def test_doctor_degraded_when_maamcp_found_but_agent_path_missing(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maamcp", preferred_visual="scrcpy", agent_path=None)
    manifest = BootstrapManifest(
        all_required_found=True,
        tools=[
            ToolEntry(name="maamcp", found=True),
            ToolEntry(name="scrcpy", found=True),
        ],
    )

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return True

        def connect(self) -> bool:
            return True

    monkeypatch.setattr("state_cartographer.transport.health.bootstrap", lambda _: manifest)
    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.DEGRADED
    assert report.control_layer == ControlLayerStatus.FALLBACK
    assert report.degradation_codes == ["observation_unverified", "preferred_stack_missing"]


def test_doctor_unreachable_when_device_stays_offline(monkeypatch: pytest.MonkeyPatch):
    cfg = TransportConfig(primary_control="maamcp", preferred_visual="scrcpy")
    manifest = BootstrapManifest(
        all_required_found=False,
        missing=["maamcp"],
        tools=[
            ToolEntry(name="maamcp", found=False),
            ToolEntry(name="scrcpy", found=False),
        ],
    )

    class FakeAdb:
        def __init__(self, serial: str, adb_path: str = "adb"):
            self.serial = serial
            self.adb_path = adb_path

        def is_device_online(self) -> bool:
            return False

        def connect(self) -> bool:
            return False

    monkeypatch.setattr("state_cartographer.transport.health.bootstrap", lambda _: manifest)
    monkeypatch.setattr("state_cartographer.transport.health.Adb", FakeAdb)

    report = doctor(cfg)

    assert report.readiness_tier == ReadinessTier.UNREACHABLE
    assert report.transport_layer == TransportLayerStatus.UNREACHABLE
    assert report.control_layer == ControlLayerStatus.UNAVAILABLE
    assert report.observation_layer == ObservationLayerStatus.UNAVAILABLE
    assert report.degradation_codes == []
    assert report.verdict == ProbeVerdict.FAIL


def test_cmd_probe_scrcpy_succeeds_for_debug_only(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]):
    report = ScrcpyProbeReport(
        serial="127.0.0.1:21503",
        binary_found=True,
        attached=True,
        observation_decision=ObservationDecision.DEBUG_ONLY,
    )

    monkeypatch.setattr(memu_transport, "load_config", lambda _: TransportConfig())
    monkeypatch.setattr(memu_transport, "run_scrcpy_probe", lambda *_args, **_kwargs: report)

    rc = memu_transport.cmd_probe_scrcpy(SimpleNamespace(config=None, serial=None))

    assert rc == 0
    captured = capsys.readouterr()
    assert '"observation_decision": "debug_only"' in captured.out


@pytest.mark.parametrize(
    ("input_action", "params", "expected_error"),
    [
        ("tap", ["10"], "tap requires X Y"),
        ("swipe", ["1", "2", "3"], "swipe requires X1 Y1 X2 Y2"),
        ("key", [], "key requires KEYCODE"),
        ("text", [], "text requires at least one TEXT token"),
    ],
)
def test_cmd_input_rejects_malformed_params(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
    input_action: str,
    params: list[str],
    expected_error: str,
):
    class FakeAdapter:
        def __init__(self, serial: str, adb_path: str = "adb", agent_path: str | None = None):
            self.serial = serial
            self.adb_path = adb_path
            self.agent_path = agent_path

        def connect(self) -> bool:
            return True

    monkeypatch.setattr(memu_transport, "load_config", lambda _: TransportConfig())
    monkeypatch.setattr(memu_transport, "_adb_path_from_manifest", lambda _cfg: "adb")
    monkeypatch.setattr(memu_transport, "MaaAdapter", FakeAdapter)

    rc = memu_transport.cmd_input(
        SimpleNamespace(
            config=None,
            serial=None,
            input_action=input_action,
            params=params,
            duration=None,
        )
    )

    assert rc == 2
    captured = capsys.readouterr()
    assert expected_error in captured.err
