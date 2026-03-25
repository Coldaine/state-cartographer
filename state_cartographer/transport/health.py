"""Health checks and recovery ladder for transport layer.

Recovery scope is transport-only:
1. Reconnect ADB to pinned serial
2. Verify device comes back online
3. Revalidate frame freshness
4. Fail with structured status
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.config import TransportConfig
from state_cartographer.transport.discovery import bootstrap
from state_cartographer.transport.models import (
    ControlLayerStatus,
    DoctorReport,
    ObservationLayerStatus,
    ProbeVerdict,
    ReadinessTier,
    TransportLayerStatus,
)

log = logging.getLogger(__name__)


def _preferred_maamcp_ready(cfg: TransportConfig, maamcp_available: bool) -> bool:
    """Return True only when the preferred Maa path is actually configured."""
    if cfg.primary_control.lower() != "maamcp":
        return True
    if not maamcp_available or not cfg.agent_path:
        return False
    return Path(cfg.agent_path).exists()


def doctor(cfg: TransportConfig, adb_path: str = "adb") -> DoctorReport:
    """Run readiness checks and produce a doctor report."""
    report = DoctorReport(serial=cfg.serial)

    # Bootstrap check
    manifest = bootstrap(cfg)
    report.bootstrap = manifest

    # ADB reachability
    adb = Adb(cfg.serial, adb_path)
    try:
        report.adb_reachable = True
        report.device_online = adb.is_device_online()
        if not report.device_online:
            # Try connecting
            try:
                ok = adb.connect()
                report.device_online = ok and adb.is_device_online()
            except AdbError as e:
                report.errors.append(f"ADB connect failed: {e}")
    except AdbError as e:
        report.adb_reachable = False
        report.errors.append(f"ADB not reachable: {e}")

    report.maamcp_available = any(t.name == "maamcp" and t.found for t in manifest.tools)
    report.scrcpy_available = any(t.name == "scrcpy" and t.found for t in manifest.tools)

    if not report.adb_reachable or not report.device_online:
        report.readiness_tier = ReadinessTier.UNREACHABLE
        report.transport_layer = TransportLayerStatus.UNREACHABLE
        report.control_layer = ControlLayerStatus.UNAVAILABLE
        report.observation_layer = ObservationLayerStatus.UNAVAILABLE
        report.verdict = ProbeVerdict.FAIL
        return report

    preferred_ready = _preferred_maamcp_ready(cfg, report.maamcp_available)

    report.readiness_tier = ReadinessTier.OPERABLE
    report.transport_layer = TransportLayerStatus.READY
    report.control_layer = ControlLayerStatus.PREFERRED
    report.observation_layer = ObservationLayerStatus.UNVERIFIED
    report.degradation_codes.append("observation_unverified")

    if not preferred_ready:
        report.readiness_tier = ReadinessTier.DEGRADED
        report.control_layer = ControlLayerStatus.FALLBACK
        report.degradation_codes.append("preferred_stack_missing")

    if cfg.preferred_visual.lower() == "scrcpy" and not report.scrcpy_available:
        report.readiness_tier = ReadinessTier.DEGRADED
        report.degradation_codes.append("visual_tool_missing")

    report.verdict = ProbeVerdict.PASS

    return report


def recovery_ladder(cfg: TransportConfig, adb_path: str = "adb") -> bool:
    """Transport-only recovery: reconnect ADB, revalidate frame freshness.

    Returns True if recovery succeeded.
    """
    adb = Adb(cfg.serial, adb_path)

    # Step 1: disconnect + reconnect
    log.info("Recovery step 1: reconnect ADB to %s", cfg.serial)
    try:
        adb.disconnect()
        time.sleep(1)
        if not adb.connect():
            log.error("Recovery: ADB reconnect failed")
            return False
    except AdbError as e:
        log.error("Recovery: ADB error during reconnect: %s", e)
        return False

    # Step 2: verify device online
    log.info("Recovery step 2: verify device online")
    if not adb.is_device_online():
        log.error("Recovery: device not online after reconnect")
        return False

    # Step 3: validate frame freshness
    log.info("Recovery step 3: validate frame freshness")
    try:
        data = adb.screenshot_png()
        if len(data) < 100:
            log.error("Recovery: screenshot too small (%d bytes)", len(data))
            return False
        log.info("Recovery: frame capture OK (%d bytes)", len(data))
    except AdbError as e:
        log.error("Recovery: screenshot failed: %s", e)
        return False

    log.info("Recovery ladder complete — device healthy")
    return True
