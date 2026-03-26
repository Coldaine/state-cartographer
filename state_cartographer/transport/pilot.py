"""Unified transport interface — the Pilot facade.

This is the single entry point for transport operations.
Agents should use this class, not import adb/maatouch/capture directly.
"""

from __future__ import annotations

import logging
from pathlib import Path

from state_cartographer.transport.adb import Adb
from state_cartographer.transport.capture import Capture
from state_cartographer.transport.config import load_config
from state_cartographer.transport.health import DoctorReport, doctor, recovery_ladder
from state_cartographer.transport.maatouch import MaaTouch

log = logging.getLogger(__name__)


class Pilot:
    """Unified transport facade.

    Wraps adb + maatouch + capture into a single interface.
    Use this as the primary entry point for transport operations.
    """

    def __init__(self, serial: str | None = None, config_path: str | None = None):
        self.config = load_config(config_path) if config_path else load_config()
        if serial:
            self.config.adb_serial = serial

        self.adb = Adb(self.config.serial)
        self._maatouch: MaaTouch | None = None
        self.capture = Capture(self.adb)

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
            return False
        if self.maatouch.connect():
            return True
        log.warning("MaaTouch not available, falling back to ADB input")
        return True

    def disconnect(self) -> None:
        """Disconnect maatouch and ADB."""
        if self._maatouch:
            self._maatouch.disconnect()
            self._maatouch = None
        self.adb.disconnect()

    def screenshot(self) -> bytes:
        """Capture screenshot. Returns PNG bytes."""
        return self.adb.screenshot_png()

    def screenshot_to_file(self, path: Path) -> Path:
        """Capture screenshot and save to file."""
        data = self.screenshot()
        path.write_bytes(data)
        return path

    def tap(self, x: int, y: int) -> bool:
        """Tap at coordinates. Uses MaaTouch if available, falls back to ADB."""
        if self._maatouch and self._maatouch.is_connected():
            return self.maatouch.tap(x, y)
        return self.adb.tap(x, y)

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        """Swipe from (x1,y1) to (x2,y2). Uses MaaTouch if available."""
        if self._maatouch and self._maatouch.is_connected():
            return self.maatouch.swipe(x1, y1, x2, y2, duration_ms)
        return self.adb.swipe(x1, y1, x2, y2, duration_ms)

    def keyevent(self, keycode: int | str) -> bool:
        """Send keyevent."""
        return self.adb.keyevent(keycode)

    def input_text(self, text: str) -> bool:
        """Input text."""
        return self.adb.input_text(text)

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
