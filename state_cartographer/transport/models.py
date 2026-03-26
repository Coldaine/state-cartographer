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


class ReadinessTier(StrEnum):
    """The overall tier of system readiness."""

    UNREACHABLE = "unreachable"
    DEGRADED = "degraded"
    OPERABLE = "operable"


class TransportLayerStatus(StrEnum):
    """Status of the transport layer."""

    UNREACHABLE = "unreachable"
    READY = "ready"


class ControlLayerStatus(StrEnum):
    """Status of the control surface."""

    UNAVAILABLE = "unavailable"
    FALLBACK = "fallback"
    PREFERRED = "preferred"


class ObservationLayerStatus(StrEnum):
    """Status of the observation surface."""

    UNAVAILABLE = "unavailable"
    UNVERIFIED = "unverified"


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
    readiness_tier: ReadinessTier = ReadinessTier.UNREACHABLE
    transport_layer: TransportLayerStatus = TransportLayerStatus.UNREACHABLE
    control_layer: ControlLayerStatus = ControlLayerStatus.UNAVAILABLE
    observation_layer: ObservationLayerStatus = ObservationLayerStatus.UNAVAILABLE
    degradation_codes: list[str] = field(default_factory=list)
    serial: str = ""
    adb_reachable: bool = False
    device_online: bool = False
    maatouch_available: bool = False
    errors: list[str] = field(default_factory=list)
    verdict: ProbeVerdict = ProbeVerdict.FAIL

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["readiness_tier"] = self.readiness_tier.value
        d["transport_layer"] = self.transport_layer.value
        d["control_layer"] = self.control_layer.value
        d["observation_layer"] = self.observation_layer.value
        d["verdict"] = self.verdict.value
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


@dataclass
class SessionProbeReport:
    """Combined session report — bootstrap + doctor."""

    timestamp: str = field(default_factory=lambda: datetime.now(UTC).isoformat())
    serial: str = ""
    bootstrap: BootstrapManifest | None = None
    doctor: DoctorReport | None = None
    degradation_codes: list[str] = field(default_factory=list)
    verdict: ProbeVerdict = ProbeVerdict.FAIL
    artifacts_dir: str | None = None

    def to_dict(self) -> dict[str, Any]:
        d: dict[str, Any] = {
            "timestamp": self.timestamp,
            "serial": self.serial,
            "degradation_codes": self.degradation_codes,
            "verdict": self.verdict.value,
            "artifacts_dir": self.artifacts_dir,
        }
        if self.bootstrap:
            d["bootstrap"] = self.bootstrap.to_dict()
        if self.doctor:
            d["doctor"] = self.doctor.to_dict()
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)
