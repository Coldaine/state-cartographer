"""ADB primitives using adbutils library.

No subprocess calls. All ADB operations go through adbutils AdbClient.
"""

from __future__ import annotations

import logging
import time
from functools import wraps
from pathlib import Path

from adbutils import AdbClient, AdbDevice
from adbutils.errors import AdbError as AdbutilsError

log = logging.getLogger(__name__)

_DEFAULT_TIMEOUT = 15
_RETRY_TRIES = 3


def retry(func):
    @wraps(func)
    def retry_wrapper(self, *args, **kwargs):
        init = None
        for attempt in range(_RETRY_TRIES):
            try:
                if callable(init):
                    time.sleep(0.5 * (attempt + 1))
                    init()
                return func(self, *args, **kwargs)
            except AdbutilsError as e:
                log.warning(f"AdbError on attempt {attempt + 1}: {e}")

                def init():
                    self._reconnect()
            except ConnectionResetError as e:
                log.error(f"Connection reset: {e}")

                def init():
                    self._reconnect()
            except Exception as e:
                log.exception(f"Unexpected error: {e}")

                def init():
                    pass

        raise AdbError(f"Retry {func.__name__}() failed after {_RETRY_TRIES} attempts")

    return retry_wrapper


class AdbError(Exception):
    pass


class Adb:
    """adbutils-based ADB client scoped to a single serial."""

    def __init__(self, serial: str, adb_path: str | None = None):
        self.serial = serial
        self._client = AdbClient()
        self._device: AdbDevice | None = None
        self._adb_path = adb_path

    def _get_device(self) -> AdbDevice:
        if self._device is None:
            devices = self._client.device_list()
            for d in devices:
                if d.serial == self.serial:
                    self._device = d
                    return self._device
            raise AdbError(f"Device {self.serial} not found")
        return self._device

    @property
    def device(self) -> AdbDevice:
        return self._get_device()

    def _reconnect(self) -> bool:
        self._device = None
        return self.connect()

    def connect(self) -> bool:
        try:
            self._client.connect(self.serial)
            self._device = None
            _ = self.device
            log.info(f"Connected to {self.serial}")
            return True
        except Exception as e:
            log.error(f"Failed to connect to {self.serial}: {e}")
            return False

    def disconnect(self) -> bool:
        try:
            self._client.disconnect(self.serial)
            self._device = None
            return True
        except Exception as e:
            log.error(f"Failed to disconnect: {e}")
            return False

    def devices(self) -> list[str]:
        return [d.serial for d in self._client.list_devices()]

    def is_device_online(self) -> bool:
        try:
            _ = self.device
            return True
        except AdbError:
            return False

    @retry
    def screenshot_png(self) -> bytes:
        """Capture screenshot via exec-out screencap -p."""
        data = self.device.shell(["screencap", "-p"], encoding=None)
        return data

    def screenshot_to_file(self, path: Path) -> Path:
        data = self.screenshot_png()
        path.write_bytes(data)
        return path

    @retry
    def tap(self, x: int, y: int) -> bool:
        self.device.shell(["input", "tap", str(x), str(y)])
        return True

    @retry
    def swipe(self, x1: int, y1: int, x2: int, y2: int, duration_ms: int = 300) -> bool:
        self.device.shell(["input", "swipe", str(x1), str(y1), str(x2), str(y2), str(duration_ms)])
        return True

    @retry
    def keyevent(self, keycode: int | str) -> bool:
        self.device.shell(["input", "keyevent", str(keycode)])
        return True

    @retry
    def input_text(self, text: str) -> bool:
        safe = text.replace(" ", "%s")
        self.device.shell(["input", "text", safe])
        return True

    @retry
    def shell(self, cmd: str | list[str], timeout: int = _DEFAULT_TIMEOUT) -> str:
        if isinstance(cmd, str):
            result = self.device.shell(cmd, timeout=timeout)
        else:
            result = self.device.shell(cmd, timeout=timeout)
        return result.strip() if isinstance(result, str) else result

    def get_state(self) -> str:
        try:
            return "device" if self.is_device_online() else "offline"
        except Exception:
            return "unknown"

    def forward(self, local: int, remote: int) -> bool:
        try:
            self.device.forward(f"tcp:{local}", f"tcp:{remote}")
            return True
        except Exception as e:
            log.error(f"Forward failed: {e}")
            return False

    def forward_remove(self, local: int) -> bool:
        try:
            self.device.forward_remove(f"tcp:{local}")
            return True
        except Exception as e:
            log.error(f"Forward remove failed: {e}")
            return False

    def push(self, local_path: Path, remote_path: str) -> bool:
        try:
            self.device.sync.push(local_path, remote_path)
            return True
        except Exception as e:
            log.error(f"Push failed: {e}")
            return False
