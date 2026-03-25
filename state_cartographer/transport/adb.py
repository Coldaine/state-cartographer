"""ADB primitives for transport-level device interaction.

Thin subprocess wrapper — no game logic, no workflow reasoning.
"""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15


class AdbError(Exception):
    pass


class Adb:
    """Thin ADB subprocess wrapper scoped to a single serial."""

    def __init__(self, serial: str, adb_path: str = "adb"):
        self.serial = serial
        self.adb_path = adb_path

    def _run(self, args: list[str], timeout: int = _DEFAULT_TIMEOUT) -> subprocess.CompletedProcess[str]:
        cmd = [self.adb_path, "-s", self.serial, *args]
        log.debug("adb: %s", " ".join(cmd))
        try:
            return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        except subprocess.TimeoutExpired as e:
            raise AdbError(f"adb timed out after {timeout}s: {' '.join(cmd)}") from e
        except FileNotFoundError as e:
            raise AdbError(f"adb executable not found at {self.adb_path}") from e

    def _run_bytes(self, args: list[str], timeout: int = _DEFAULT_TIMEOUT) -> bytes:
        cmd = [self.adb_path, "-s", self.serial, *args]
        try:
            r = subprocess.run(cmd, capture_output=True, timeout=timeout)
            if r.returncode != 0:
                raise AdbError(f"adb failed ({r.returncode}): {r.stderr.decode(errors='replace')}")
            return r.stdout
        except subprocess.TimeoutExpired as e:
            raise AdbError(f"adb timed out after {timeout}s") from e

    def connect(self) -> bool:
        r = self._run(["connect", self.serial])
        out = r.stdout.strip()
        return "connected" in out.lower() or "already" in out.lower()

    def disconnect(self) -> bool:
        r = self._run(["disconnect", self.serial])
        return r.returncode == 0

    def devices(self) -> list[str]:
        r = self._run(["devices"])
        lines = r.stdout.strip().split("\n")[1:]  # skip header
        return [line.split("\t")[0] for line in lines if "\tdevice" in line]

    def is_device_online(self) -> bool:
        return self.serial in self.devices()

    def screenshot_png(self) -> bytes:
        """Capture screenshot via exec-out screencap -p."""
        return self._run_bytes(["exec-out", "screencap", "-p"], timeout=30)

    def screenshot_to_file(self, path: Path) -> Path:
        data = self.screenshot_png()
        path.write_bytes(data)
        return path

    def tap(self, x: int, y: int) -> bool:
        r = self._run(["shell", "input", "tap", str(x), str(y)])
        return r.returncode == 0

    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        r = self._run(["shell", "input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        return r.returncode == 0

    def keyevent(self, keycode: int | str) -> bool:
        r = self._run(["shell", "input", "keyevent", str(keycode)])
        return r.returncode == 0

    def input_text(self, text: str) -> bool:
        # ADB input text only handles ASCII without spaces well
        safe = text.replace(" ", "%s")
        r = self._run(["shell", "input", "text", safe])
        return r.returncode == 0

    def shell(self, cmd: str, timeout: int = _DEFAULT_TIMEOUT) -> str:
        r = self._run(["shell", cmd], timeout=timeout)
        return r.stdout.strip()

    def get_state(self) -> str:
        r = self._run(["get-state"])
        return r.stdout.strip()
