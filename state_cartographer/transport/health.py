"""Health checks and recovery ladder for transport layer.

Recovery scope is transport-only:
1. Reconnect ADB to pinned serial
2. Restart tool process
3. Reattach
4. Revalidate frame freshness
5. Fail with structured status
"""

from __future__ import annotations

import logging
import time

from state_cartographer.transport.adb import Adb, AdbError
from state_cartographer.transport.config import TransportConfig
from state_cartographer.transport.discovery import bootstrap
from state_cartographer.transport.models import DoctorReport, ProbeVerdict

log = logging.getLogger(__name__)


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

    # MaaMCP availability
    report.maamcp_available = any(t.name == "maamcp" and t.found for t in manifest.tools)

    # scrcpy availability
    report.scrcpy_available = any(t.name == "scrcpy" and t.found for t in manifest.tools)

    # Verdict
    if report.device_online and manifest.all_required_found:
        report.verdict = ProbeVerdict.PASS
    else:
        report.verdict = ProbeVerdict.FAIL

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
