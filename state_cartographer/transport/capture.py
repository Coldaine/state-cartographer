"""Screenshot capture methods.

ADB screencap as primary. Extensible for netcat or emulator-specific paths.
"""

from __future__ import annotations

import logging
import time
from pathlib import Path

from state_cartographer.transport.adb import Adb, AdbError

log = logging.getLogger(__name__)


class Capture:
    """Screenshot capture with ADB fallback."""

    def __init__(self, adb: Adb):
        self.adb = adb
        self._last_capture_time: float = 0
        self._capture_count: int = 0

    def screenshot_png(self) -> bytes:
        """Capture PNG screenshot via ADB screencap."""
        data = self.adb.screenshot_png()
        self._last_capture_time = time.time()
        self._capture_count += 1
        return data

    def save_screenshot(self, path: Path) -> Path:
        """Capture and save screenshot to file."""
        data = self.screenshot_png()
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        log.debug(f"Saved screenshot to {path}")
        return path

    def last_capture_age_ms(self) -> int:
        """Milliseconds since last capture."""
        return int((time.time() - self._last_capture_time) * 1000)

    @property
    def capture_count(self) -> int:
        return self._capture_count


def capture_burst(adb: Adb, count: int = 5, interval_ms: int = 100) -> list[bytes]:
    """Capture multiple screenshots in rapid succession."""
    captures = []
    for i in range(count):
        data = adb.screenshot_png()
        captures.append(data)
        if i < count - 1:
            time.sleep(interval_ms / 1000)
    return captures
