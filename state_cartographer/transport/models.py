"""Structured data models for transport probe results and reports."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class ProbeVerdict(StrEnum):
    PASS = "pass"
    FAIL = "fail"
    SKIP = "skip"


class ObservationDecision(StrEnum):
    """Whether scrcpy is usable as a runtime frame source or debug-only."""

    RUNTIME_CONSUMABLE = "runtime_consumable"
    DEBUG_ONLY = "debug_only"
    UNDECIDED = "undecided"


@dataclass
class ToolEntry:
    """One discovered external tool."""

    name: str
    found: bool
    path: str | None = None
    version: str | None = None
    source: str | None = None  # how it was found (PATH, registry, config, etc.)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {k: v for k, v in asdict(self).items() if v is not None}


@dataclass
class BootstrapManifest:
    """Result of tool bootstrap/discovery."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    tools: list[ToolEntry] = field(default_factory=list)
    all_required_found: bool = False
    missing: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["tools"] = [t.to_dict() for t in self.tools]
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class DoctorReport:
    """Aggregated health/readiness report."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    adb_reachable: bool = False
    serial: str = ""
    device_online: bool = False
    maamcp_available: bool = False
    scrcpy_available: bool = False
    bootstrap: BootstrapManifest | None = None
    errors: list[str] = field(default_factory=list)
    verdict: ProbeVerdict = ProbeVerdict.FAIL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["verdict"] = self.verdict.value
        if self.bootstrap:
            d["bootstrap"] = self.bootstrap.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class MaaCaptureResult:
    """Result of a single MaaMCP screenshot capture."""

    success: bool
    path: str | None = None
    elapsed_ms: float = 0.0
    width: int = 0
    height: int = 0
    error: str | None = None


@dataclass
class MaaProbeReport:
    """Full MaaMCP probe report — connect, capture, input, recovery."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    serial: str = ""
    connected: bool = False
    captures: list[MaaCaptureResult] = field(default_factory=list)
    capture_verdict: ProbeVerdict = ProbeVerdict.FAIL
    input_tap: ProbeVerdict = ProbeVerdict.SKIP
    input_swipe: ProbeVerdict = ProbeVerdict.SKIP
    input_key: ProbeVerdict = ProbeVerdict.SKIP
    input_text: ProbeVerdict = ProbeVerdict.SKIP
    recovery_disconnect: ProbeVerdict = ProbeVerdict.SKIP
    recovery_reconnect: ProbeVerdict = ProbeVerdict.SKIP
    verdict: ProbeVerdict = ProbeVerdict.FAIL
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        for k in (
            "capture_verdict",
            "input_tap",
            "input_swipe",
            "input_key",
            "input_text",
            "recovery_disconnect",
            "recovery_reconnect",
            "verdict",
        ):
            d[k] = getattr(self, k).value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class ScrcpyProbeReport:
    """scrcpy coexistence and frame-path probe report."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    serial: str = ""
    binary_found: bool = False
    binary_path: str | None = None
    attached: bool = False
    coexistence_with_maa: ProbeVerdict = ProbeVerdict.SKIP
    programmatic_frame_path: ProbeVerdict = ProbeVerdict.SKIP
    observation_decision: ObservationDecision = ObservationDecision.UNDECIDED
    artifacts: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["coexistence_with_maa"] = self.coexistence_with_maa.value
        d["programmatic_frame_path"] = self.programmatic_frame_path.value
        d["observation_decision"] = self.observation_decision.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SessionProbeReport:
    """Combined session report — bootstrap + maa + scrcpy."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    serial: str = ""
    bootstrap: BootstrapManifest | None = None
    doctor: DoctorReport | None = None
    maa: MaaProbeReport | None = None
    scrcpy: ScrcpyProbeReport | None = None
    observation_decision: ObservationDecision = ObservationDecision.UNDECIDED
    verdict: ProbeVerdict = ProbeVerdict.FAIL
    artifacts_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "timestamp": self.timestamp,
            "serial": self.serial,
            "observation_decision": self.observation_decision.value,
            "verdict": self.verdict.value,
            "artifacts_dir": self.artifacts_dir,
        }
        if self.bootstrap:
            d["bootstrap"] = self.bootstrap.to_dict()
        if self.doctor:
            d["doctor"] = self.doctor.to_dict()
        if self.maa:
            d["maa"] = self.maa.to_dict()
        if self.scrcpy:
            d["scrcpy"] = self.scrcpy.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
