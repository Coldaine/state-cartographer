"""MaaMCP adapter — connect, screenshot, input, health.

This adapter tries to use the MaaFramework Python bindings (maafw)
when available. Falls back to ADB-direct primitives when MaaFramework
is not installed.

The probe uses whichever path is available to prove the attach/capture/
input/recovery loop on the pinned serial.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.artifacts import probe_run_dir, write_json
from state_cartographer.transport.models import MaaCaptureResult, MaaProbeReport, ProbeVerdict

log = logging.getLogger(__name__)


class MaaAdapter:
    """Wraps MaaMCP / MaaFramework or falls back to ADB-direct."""

    def __init__(self, serial: str, adb_path: str = "adb", agent_path: str | None = None):
        self.serial = serial
        self.adb = Adb(serial, adb_path)
        self.agent_path = agent_path
        self._maa_controller = None
        self._backend = "adb_direct"
        self._try_maafw()

    def _try_maafw(self) -> None:
        """Attempt to import and initialize MaaFramework.

        MaaFramework requires an agent binary running on the Android device.
        The agent_path must point to the compiled MaaAgent .so file.

        Typical usage:
          from maa.controller import AdbController
          from maa.toolkit import Toolkit
          Toolkit.init_option("./")
          controller = AdbController(
              adb_path=self.adb.adb_path,
              address=self.serial,
              agent_path="/path/to/MaaAgent"  # Required
          )
          controller.post_connection().wait()
          controller.post_screencap().wait().get() -> numpy.ndarray
        """
        if not self.agent_path:
            log.info("MaaFramework agent_path not provided, skipping maafw init")
            self._backend = "adb_direct"
            return

        try:
            from maa.controller import AdbController
            from maa.toolkit import Toolkit

            Toolkit.init_option("./")
            controller = AdbController(
                adb_path=self.adb.adb_path,
                address=self.serial,
                agent_path=self.agent_path,
            )
            controller.post_connection().wait()
            self._maa_controller = controller
            self._backend = "maafw"
            log.info("MaaFramework controller initialized on %s", self.serial)
        except ImportError as e:
            log.info("MaaFramework Python bindings not installed: %s", e)
            self._maa_controller = None
            self._backend = "adb_direct"
        except Exception as e:
            log.info("MaaFramework init failed, using ADB fallback: %s", e)
            self._maa_controller = None
            self._backend = "adb_direct"

    @property
    def backend(self) -> str:
        return self._backend

    def connect(self) -> bool:
        if self._maa_controller is not None:
            return True  # already connected via maafw init
        return self.adb.connect()

    def disconnect(self) -> bool:
        if self._maa_controller is not None:
            try:
                del self._maa_controller
                self._maa_controller = None
                return True
            except Exception:
                return False
        return self.adb.disconnect()

    def reconnect(self) -> bool:
        self.disconnect()
        time.sleep(1)
        self._try_maafw()
        if self._maa_controller is not None:
            return True
        return self.adb.connect()

    def screenshot(self, output: Path | None = None) -> tuple[bytes, float]:
        """Capture a screenshot. Returns (png_bytes, elapsed_ms)."""
        t0 = time.perf_counter()

        if self._maa_controller is not None:
            try:
                img = self._maa_controller.post_screencap().wait().get()
                elapsed = (time.perf_counter() - t0) * 1000
                # maafw returns numpy.ndarray (BGR) — encode to PNG
                data = _numpy_to_png(img)
                if output:
                    output.write_bytes(data)
                return data, elapsed
            except Exception as e:
                log.warning("MaaFW screenshot failed, falling back to adb: %s", e)

        data = self.adb.screenshot_png()
        elapsed = (time.perf_counter() - t0) * 1000
        if output:
            output.write_bytes(data)
        return data, elapsed

    def tap(self, x: int, y: int) -> bool:
        if self._maa_controller is not None:
            try:
                self._maa_controller.post_click(x, y).wait()
                return True
            except Exception as e:
                log.warning("MaaFW tap failed: %s", e)
        return self.adb.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        if self._maa_controller is not None:
            try:
                self._maa_controller.post_swipe(x1, y1, x2, y2, duration_ms).wait()
                return True
            except Exception as e:
                log.warning("MaaFW swipe failed: %s", e)
        return self.adb.swipe(x1, y1, x2, y2, duration_ms)

    def key(self, keycode: int | str) -> bool:
        if self._maa_controller is not None:
            try:
                self._maa_controller.post_click_key(int(keycode)).wait()
                return True
            except Exception as e:
                log.warning("MaaFW key failed: %s", e)
        return self.adb.keyevent(keycode)

    def text(self, value: str) -> bool:
        if self._maa_controller is not None:
            try:
                self._maa_controller.post_input_text(value).wait()
                return True
            except Exception as e:
                log.warning("MaaFW text failed: %s", e)
        return self.adb.input_text(value)

    def is_healthy(self) -> bool:
        try:
            data, elapsed = self.screenshot()
            return len(data) > 100 and elapsed < 30_000
        except Exception:
            return False


def _numpy_to_png(img) -> bytes:
    """Convert numpy array (BGR from maafw) to PNG bytes.

    Tries cv2 first (already a project dep), falls back to PIL.
    PIL expects RGB so we must convert BGR->RGB before PIL fallback.
    """
    try:
        import cv2

        ok, buf = cv2.imencode(".png", img)
        if ok:
            return buf.tobytes()
    except ImportError:
        pass
    # Fallback: PIL — requires RGB, maafw returns BGR
    import io

    from PIL import Image

    if len(img.shape) == 3 and img.shape[2] == 3:
        import cv2

        img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    pil_img = Image.fromarray(img)
    buf = io.BytesIO()
    pil_img.save(buf, format="PNG")
    return buf.getvalue()


def _image_dimensions(png_data: bytes) -> tuple[int, int]:
    """Extract width, height from PNG header without PIL."""
    import struct

    if png_data[:8] != b"\x89PNG\r\n\x1a\n":
        return 0, 0
    w, h = struct.unpack(">II", png_data[16:24])
    return w, h


def run_maa_probe(serial: str, adb_path: str = "adb", agent_path: str | None = None, capture_count: int = 3) -> MaaProbeReport:
    """Full MaaMCP acceptance probe.

    1. Connect to serial
    2. Capture repeated frames
    3. Run input smoke actions (tap, swipe, key, text)
    4. Force disconnect + reconnect
    5. Emit structured report with artifacts
    """
    run_dir = probe_run_dir("maa")
    report = MaaProbeReport(serial=serial)

    # Connect
    try:
        adapter = MaaAdapter(serial, adb_path, agent_path=agent_path)
        ok = adapter.connect()
        report.connected = ok
        if not ok:
            report.errors.append("Failed to connect")
            return report
    except Exception as e:
        report.errors.append(f"Connection error: {e}")
        return report

    log.info("MaaMCP probe: backend=%s, serial=%s", adapter.backend, serial)

    # Capture repeated frames
    captures: list[MaaCaptureResult] = []
    for i in range(capture_count):
        try:
            out_path = run_dir / f"capture_{i:02d}.png"
            data, elapsed = adapter.screenshot(out_path)
            w, h = _image_dimensions(data)
            cap = MaaCaptureResult(success=True, path=str(out_path), elapsed_ms=elapsed, width=w, height=h)
            captures.append(cap)
            report.artifacts.append(str(out_path))
            log.info("  capture %d: %dx%d in %.0fms", i, w, h, elapsed)
        except Exception as e:
            captures.append(MaaCaptureResult(success=False, error=str(e)))
            report.errors.append(f"Capture {i} failed: {e}")
    report.captures = captures
    report.capture_verdict = ProbeVerdict.PASS if all(c.success for c in captures) else ProbeVerdict.FAIL

    # Input smoke tests — safe no-op coordinates
    try:
        report.input_tap = ProbeVerdict.PASS if adapter.tap(10, 10) else ProbeVerdict.FAIL
    except Exception as e:
        report.input_tap = ProbeVerdict.FAIL
        report.errors.append(f"Tap failed: {e}")

    try:
        report.input_swipe = ProbeVerdict.PASS if adapter.swipe(100, 300, 100, 500) else ProbeVerdict.FAIL
    except Exception as e:
        report.input_swipe = ProbeVerdict.FAIL
        report.errors.append(f"Swipe failed: {e}")

    try:
        # KEYCODE_UNKNOWN (0) is a no-op
        report.input_key = ProbeVerdict.PASS if adapter.key(0) else ProbeVerdict.FAIL
    except Exception as e:
        report.input_key = ProbeVerdict.FAIL
        report.errors.append(f"Key failed: {e}")

    try:
        report.input_text = ProbeVerdict.PASS if adapter.text("") else ProbeVerdict.FAIL
    except Exception as e:
        report.input_text = ProbeVerdict.FAIL
        report.errors.append(f"Text failed: {e}")

    # Recovery: disconnect then reconnect
    try:
        adapter.disconnect()
        report.recovery_disconnect = ProbeVerdict.PASS
    except Exception as e:
        report.recovery_disconnect = ProbeVerdict.FAIL
        report.errors.append(f"Disconnect failed: {e}")

    try:
        ok = adapter.reconnect()
        report.recovery_reconnect = ProbeVerdict.PASS if ok else ProbeVerdict.FAIL
        if ok:
            # Verify frame freshness after reconnect
            data, elapsed = adapter.screenshot()
            if len(data) > 100:
                log.info("  post-reconnect capture OK (%.0fms)", elapsed)
            else:
                report.recovery_reconnect = ProbeVerdict.FAIL
                report.errors.append("Post-reconnect frame too small")
    except Exception as e:
        report.recovery_reconnect = ProbeVerdict.FAIL
        report.errors.append(f"Reconnect failed: {e}")

    # Overall verdict
    critical = [report.capture_verdict, report.input_tap, report.recovery_reconnect]
    report.verdict = ProbeVerdict.PASS if all(v == ProbeVerdict.PASS for v in critical) else ProbeVerdict.FAIL

    # Write report
    report_path = write_json(run_dir, "maa-probe-report.json", report.to_json())
    report.artifacts.append(str(report_path))
    log.info("MaaMCP probe verdict: %s (artifacts: %s)", report.verdict.value, run_dir)

    return report
