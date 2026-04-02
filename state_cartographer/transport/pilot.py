"""Unified transport interface — the Pilot facade.

This is the single entry point for transport operations.
Agents should use this class, not import adb/maatouch/capture directly.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path
from typing import ClassVar

from state_cartographer.transport.action_log import action
from state_cartographer.transport.adb import Adb
from state_cartographer.transport.config import load_config
from state_cartographer.transport.health import DoctorReport, doctor, recovery_ladder
from state_cartographer.transport.maatouch import MaaTouch

log = logging.getLogger(__name__)


class Pilot:
    """Unified transport facade.

    Wraps adb + maatouch into a single interface.
    Use this as the primary entry point for transport operations.
    """

    # Semantic key mappings for MEmu keymapper bindings.
    # These map action names to Android keycodes.
    # Requires MEmu keymapper configured with matching bindings.
    KEYMAP: ClassVar[dict[str, int]] = {
        "primary": 62,  # KEYCODE_SPACE — Attack, Battle, Confirm, Sortie
        "back": 61,  # KEYCODE_TAB — Return, Retreat, Close
        "confirm": 66,  # KEYCODE_ENTER — Secondary confirm (Yes, OK, Accept)
        "cancel": 111,  # KEYCODE_ESCAPE — System menu, abort
        "fleet1": 8,  # KEYCODE_1 — Main fleet select
        "fleet2": 9,  # KEYCODE_2 — Sub fleet select
        "engage": 45,  # KEYCODE_Q — Target nearest enemy
        "objective": 33,  # KEYCODE_E — Boss, exit, priority target
        "up": 51,  # KEYCODE_W — directional pan/move via MEmu keymapper
        "down": 47,  # KEYCODE_S — directional pan/move via MEmu keymapper
        "left": 29,  # KEYCODE_A — directional pan/move via MEmu keymapper
        "right": 32,  # KEYCODE_D — directional pan/move via MEmu keymapper
        "emergency": 120,  # KEYCODE_F9 — App kill if frozen
    }

    def __init__(self, serial: str | None = None, config_path: str | None = None):
        self.config = load_config(config_path) if config_path else load_config()
        if serial:
            self.config.adb_serial = serial

        self.adb = Adb(self.config.serial)
        self._maatouch: MaaTouch | None = None

    @property
    def serial(self) -> str:
        return self.config.serial

    @property
    def maatouch(self) -> MaaTouch:
        if self._maatouch is None:
            self._maatouch = MaaTouch(self.adb)
        return self._maatouch

    def connect(self) -> bool:
        """Connect to device and initialize maatouch."""
        if not self.adb.connect():
            action("connect", self.serial, "none", {}, "failure")
            return False
        if self.maatouch.connect():
            action("connect", self.serial, "maatouch", {}, "success")
            return True
        log.warning("MaaTouch not available, falling back to ADB input")
        action("connect", self.serial, "adb", {}, "success")
        return True

    def disconnect(self) -> None:
        """Disconnect maatouch and ADB."""
        had_maatouch = self._maatouch is not None and self._maatouch.is_connected()
        errors: list[str] = []
        if self._maatouch:
            if self._maatouch.disconnect() is False:
                errors.append("maatouch disconnect returned False")
            self._maatouch = None
        if self.adb.disconnect() is False:
            errors.append("adb disconnect returned False")
        control = "maatouch" if had_maatouch else "adb"
        action(
            "disconnect",
            self.serial,
            control,
            {},
            "failure" if errors else "success",
            error="; ".join(errors) if errors else None,
        )

    def screenshot(self) -> bytes:
        """Capture screenshot. Returns PNG bytes."""
        t0 = time.monotonic()
        try:
            data = self.adb.screenshot_png()
            action(
                "screenshot",
                self.serial,
                "adb",
                {"bytes": len(data)},
                "success",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
            return data
        except Exception as e:
            action(
                "screenshot",
                self.serial,
                "adb",
                {},
                "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(e),
            )
            raise

    def screenshot_to_file(self, path: Path) -> Path:
        """Capture screenshot and save to file."""
        data = self.screenshot()
        path.write_bytes(data)
        return path

    def tap_chain(self, steps: list[tuple[int, int, float]], *, capture_dir: Path | None = None) -> list[Path]:
        """Execute a sequence of coordinate taps with delays, capturing screenshots after each.

        Primarily useful for corpus building — capturing before/after screenshots
        during deterministic UI flows. For live automation, prefer ``press()``
        with keymapping which avoids coordinate precision issues (see FM-001).

        Args:
            steps: List of (x, y, delay_seconds) tuples. Delay happens AFTER tap.
            capture_dir: If set, saves screenshot after each tap to this directory.

        Returns:
            List of paths to saved screenshots (if capture_dir was set).
        """
        action(
            "tap_chain_start",
            self.serial,
            "sequence",
            {"steps": len(steps), "capture": capture_dir is not None},
            "success",
        )
        overall_success = True
        steps_executed = 0
        if capture_dir is not None:
            capture_dir.mkdir(parents=True, exist_ok=True)
        saved_paths: list[Path] = []
        failure_params: dict[str, int] = {}
        error_message: str | None = None
        try:
            for i, (x, y, delay) in enumerate(steps):
                if not self.tap(x, y):
                    overall_success = False
                    failure_params = {"failed_step": i, "x": x, "y": y}
                    error_message = f"tap_chain failed at step {i} for coordinates ({x}, {y})"
                    raise RuntimeError(error_message)
                log.debug(f"tap_chain step {i}: tapped ({x}, {y})")
                if delay > 0:
                    time.sleep(delay)
                if capture_dir is not None:
                    path = capture_dir / f"chain_{i:03d}_{x}_{y}.png"
                    saved_paths.append(self.screenshot_to_file(path))
                steps_executed += 1
        except Exception as exc:
            overall_success = False
            error_message = error_message or str(exc)
            raise
        finally:
            end_params = {"steps": len(steps), "executed": steps_executed, "captured": len(saved_paths)}
            end_params.update(failure_params)
            action(
                "tap_chain_end",
                self.serial,
                "sequence",
                end_params,
                "success" if overall_success else "failure",
                error=error_message,
            )
        return saved_paths

    def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates. Uses MaaTouch if available, falls back to ADB."""
        t0 = time.monotonic()
        control = "maatouch" if (self._maatouch and self._maatouch.is_connected()) else "adb"
        try:
            if self._maatouch and self._maatouch.is_connected():
                result = self.maatouch.tap(x, y)
            else:
                result = self.adb.tap(x, y)
            if result:
                action(
                    "tap", self.serial, control, {"x": x, "y": y}, "success", duration_ms=(time.monotonic() - t0) * 1000
                )
            else:
                action(
                    "tap", self.serial, control, {"x": x, "y": y}, "failure", duration_ms=(time.monotonic() - t0) * 1000
                )
            return result
        except Exception as e:
            action(
                "tap",
                self.serial,
                control,
                {"x": x, "y": y},
                "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(e),
            )
            raise

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe from (x1,y1) to (x2,y2). Uses MaaTouch if available."""
        t0 = time.monotonic()
        control = "maatouch" if (self._maatouch and self._maatouch.is_connected()) else "adb"
        try:
            if self._maatouch and self._maatouch.is_connected():
                result = self.maatouch.swipe(x1, y1, x2, y2, duration_ms)
            else:
                result = self.adb.swipe(x1, y1, x2, y2, duration_ms)
            if result:
                action(
                    "swipe",
                    self.serial,
                    control,
                    {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
                    "success",
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            else:
                action(
                    "swipe",
                    self.serial,
                    control,
                    {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
                    "failure",
                    duration_ms=(time.monotonic() - t0) * 1000,
                )
            return result
        except Exception as e:
            action(
                "swipe",
                self.serial,
                control,
                {"x1": x1, "y1": y1, "x2": x2, "y2": y2, "duration_ms": duration_ms},
                "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(e),
            )
            raise

    def press(self, name: str, count: int = 1, delay: float = 0.3) -> bool:
        """Press a mapped key by semantic name.

        Requires MEmu keymapper configured with matching bindings.
        See docs/transport/keymapping-strategy.md for the binding table.

        Args:
            name: Semantic key name from KEYMAP (e.g. "primary", "back").
            count: Number of times to press.
            delay: Seconds between presses when count > 1.

        Returns:
            True if all presses succeeded.

        Raises:
            ValueError: If name is not in KEYMAP.
        """
        keycode = self.KEYMAP.get(name)
        if keycode is None:
            raise ValueError(f"Unknown key action: {name!r}. Valid: {sorted(self.KEYMAP)}")
        if count < 1:
            raise ValueError("count must be >= 1")
        if delay < 0:
            raise ValueError("delay must be >= 0")
        all_ok = True
        for i in range(count):
            ok = self.keyevent(keycode)
            if not ok:
                all_ok = False
            if delay > 0 and i < count - 1:
                time.sleep(delay)
        action(
            "press",
            self.serial,
            "keymap",
            {"name": name, "keycode": keycode, "count": count},
            "success" if all_ok else "failure",
        )
        return all_ok

    def keyevent(self, keycode: int | str) -> bool:
        """Send keyevent."""
        t0 = time.monotonic()
        try:
            result = self.adb.keyevent(keycode)
            action(
                "keyevent",
                self.serial,
                "adb",
                {"keycode": keycode},
                "success" if result else "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
            return result
        except Exception as e:
            action(
                "keyevent",
                self.serial,
                "adb",
                {"keycode": keycode},
                "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(e),
            )
            raise

    def input_text(self, text: str) -> bool:
        """Input text."""
        t0 = time.monotonic()
        try:
            result = self.adb.input_text(text)
            action(
                "input_text",
                self.serial,
                "adb",
                {"length": len(text)},
                "success" if result else "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
            )
            return result
        except Exception as e:
            action(
                "input_text",
                self.serial,
                "adb",
                {"length": len(text)},
                "failure",
                duration_ms=(time.monotonic() - t0) * 1000,
                error=str(e),
            )
            raise

    def health_check(self) -> DoctorReport:
        """Run health/readiness check."""
        return doctor(self.config)

    def recover(self) -> bool:
        """Attempt transport-level recovery (reconnect + revalidate)."""
        return recovery_ladder(self.config)

    def is_healthy(self) -> bool:
        """Quick check if device is reachable."""
        return self.adb.is_device_online()

    def __enter__(self) -> Pilot:
        self.connect()
        return self

    def __exit__(self, *args) -> None:
        self.disconnect()
