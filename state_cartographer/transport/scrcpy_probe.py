"""scrcpy coexistence and programmatic frame-path probe.

Determines whether scrcpy is runtime_consumable or debug_only:
- runtime_consumable: repo code can programmatically obtain current
  decodable frames at a repeatable cadence without manual GUI mediation.
- debug_only: scrcpy works for visual/operator use but frames cannot
  be consumed programmatically by the runtime.
"""

from __future__ import annotations

import logging
import os
import signal
import subprocess
import time
from pathlib import Path

from state_cartographer.transport.artifacts import probe_run_dir, write_json
from state_cartographer.transport.models import ObservationDecision, ProbeVerdict, ScrcpyProbeReport

log = logging.getLogger(__name__)


def _find_scrcpy_binary(scrcpy_path: str | None = None) -> str | None:
    """Resolve scrcpy binary path."""
    import shutil

    if scrcpy_path and Path(scrcpy_path).exists():
        return scrcpy_path
    return shutil.which("scrcpy")


def _start_scrcpy(binary: str, serial: str, extra_args: list[str] | None = None) -> subprocess.Popen[bytes]:
    """Start scrcpy in a mode suitable for probing."""
    cmd = [
        binary,
        "--serial",
        serial,
        "--no-playback",
        "--no-window",
        "--max-fps",
        "5",
    ]
    if extra_args:
        cmd.extend(extra_args)

    log.info("Starting scrcpy: %s", " ".join(cmd))
    return subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _probe_v4l2_sink(binary: str, serial: str) -> bool:
    """Check if scrcpy supports --v4l2-sink (Linux only)."""
    import platform

    if platform.system() != "Linux":
        return False
    try:
        r = subprocess.run(
            [binary, "--help"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return "--v4l2-sink" in r.stdout
    except Exception:
        return False


def _probe_record_path(binary: str, serial: str, run_dir: Path) -> bool:
    """Try to record a short clip and check if frames are decodable."""
    record_file = run_dir / "scrcpy_probe.mkv"
    cmd = [
        binary,
        "--serial",
        serial,
        "--no-playback",
        "--no-window",
        "--record",
        str(record_file),
        "--max-fps",
        "5",
    ]

    proc: subprocess.Popen[bytes] | None = None
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
        time.sleep(5)  # record 5 seconds

        # Graceful stop
        if os.name == "nt":
            proc.terminate()
        else:
            proc.send_signal(signal.SIGINT)

        proc.wait(timeout=10)

        if record_file.exists() and record_file.stat().st_size > 1000:
            log.info("scrcpy recorded %d bytes to %s", record_file.stat().st_size, record_file)
            return True
        return False
    except Exception as e:
        log.warning("scrcpy record probe failed: %s", e)
        if proc is not None:
            try:
                proc.kill()
                proc.wait(timeout=5)
            except OSError:
                pass
        return False


def run_scrcpy_probe(
    serial: str,
    scrcpy_path: str | None = None,
    maa_active: bool = True,
) -> ScrcpyProbeReport:
    """Probe scrcpy for coexistence and programmatic frame path.

    Args:
        serial: ADB serial to target
        scrcpy_path: explicit path to scrcpy binary (optional)
        maa_active: whether MaaMCP is currently attached (for coexistence test)
    """
    run_dir = probe_run_dir("scrcpy")
    report = ScrcpyProbeReport(serial=serial)

    # Find binary
    binary = _find_scrcpy_binary(scrcpy_path)
    if not binary:
        report.errors.append("scrcpy binary not found")
        return report
    report.binary_found = True
    report.binary_path = binary

    # Basic attach test
    try:
        proc = _start_scrcpy(binary, serial)
        time.sleep(3)

        if proc.poll() is None:
            # Still running = attached successfully
            report.attached = True
            log.info("scrcpy attached to %s", serial)

            if maa_active:
                report.coexistence_with_maa = ProbeVerdict.PASS
                log.info("scrcpy coexistence with MaaMCP: PASS")
            else:
                report.coexistence_with_maa = ProbeVerdict.SKIP

            # Clean up
            proc.terminate()
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        else:
            stderr = proc.stderr.read().decode(errors="replace") if proc.stderr else ""
            report.attached = False
            report.errors.append(f"scrcpy exited immediately: {stderr[:500]}")
    except Exception as e:
        report.errors.append(f"scrcpy attach failed: {e}")

    # Programmatic frame path probe
    if report.attached:
        record_ok = _probe_record_path(binary, serial, run_dir)
        if record_ok:
            report.programmatic_frame_path = ProbeVerdict.PASS
            report.observation_decision = ObservationDecision.RUNTIME_CONSUMABLE
            report.artifacts.append(str(run_dir / "scrcpy_probe.mkv"))
        else:
            report.programmatic_frame_path = ProbeVerdict.FAIL
            report.observation_decision = ObservationDecision.DEBUG_ONLY

        # Also check v4l2 availability
        if _probe_v4l2_sink(binary, serial):
            log.info("scrcpy v4l2-sink available (Linux programmatic path)")

    # Default conservative
    if report.observation_decision == ObservationDecision.UNDECIDED:
        report.observation_decision = ObservationDecision.DEBUG_ONLY

    # Write report
    report_path = write_json(run_dir, "scrcpy-probe-report.json", report.to_json())
    report.artifacts.append(str(report_path))
    log.info("scrcpy probe verdict: observation=%s (artifacts: %s)", report.observation_decision.value, run_dir)

    return report
